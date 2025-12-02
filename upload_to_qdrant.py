"""Script to upload scraped laws to Qdrant database."""

import os
import json
import uuid
from typing import List, Dict
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from loguru import logger
from tqdm import tqdm

from database.utils import embed_text
from constants import KOMPLETNO_PRAVO_COLLECTION
from config import load_config

load_dotenv(find_dotenv())


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_length:
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + len(chunk)
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def create_law_name_from_filename(filename: str) -> str:
    """Create normalized law name from filename."""
    # Remove .json extension and convert to law name format
    name = filename.replace('.json', '')
    # Replace underscores with spaces for better readability
    name = name.replace('_', ' ')
    return name.lower()


def check_law_exists_in_qdrant(client: QdrantClient, normalized_law_name: str, max_check: int = 1000) -> bool:
    """Check if a law already exists in Qdrant by scrolling through points."""
    try:
        # Scroll through collection to check for existing law
        offset = None
        checked = 0
        
        # Limit the check to avoid performance issues
        for _ in range(max_check // 100):
            scroll_results, next_page = client.scroll(
                collection_name=KOMPLETNO_PRAVO_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            if not scroll_results:
                break
            
            for point in scroll_results:
                payload = point.payload or {}
                existing_law_name = payload.get('law_name', '').lower()
                
                # Check if this law matches (normalized name should match)
                if existing_law_name == normalized_law_name.lower():
                    return True
                
                checked += 1
                if checked >= max_check:
                    return False
            
            if not next_page:
                break
            offset = next_page
        
        return False
    except Exception as e:
        logger.warning(f"Error checking if law exists: {e}")
        return False


def upload_scraped_laws(scraped_dir: str = 'scraped_laws', batch_size: int = 100, skip_existing: bool = False):
    """Upload scraped laws to Qdrant."""
    try:
        # Initialize Qdrant client
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        logger.info("Qdrant client initialized")
        
        # Load config for embedding
        config = load_config()
        
        # Get all scraped law files
        scraped_files = list(Path(scraped_dir).glob('*.json'))
        logger.info(f"Found {len(scraped_files)} scraped law files")
        
        if not scraped_files:
            logger.warning("No scraped files found!")
            return
        
        total_points_uploaded = 0
        total_laws_processed = 0
        total_skipped = 0
        failed_laws = []
        
        for law_file in tqdm(scraped_files, desc="Processing laws"):
            try:
                # Load law content
                with open(law_file, 'r', encoding='utf-8') as f:
                    law_data = json.load(f)
                
                law_name = law_data['law_name']
                content = law_data['content']
                url = law_data.get('url', 'N/A')
                
                if not content or len(content) < 50:
                    logger.warning(f"Skipping {law_name} - content too short")
                    failed_laws.append(law_name)
                    continue
                
                # Create normalized law name for database
                normalized_law_name = create_law_name_from_filename(law_file.stem)
                
                # Check if law already exists in Qdrant
                if skip_existing and check_law_exists_in_qdrant(client, normalized_law_name):
                    logger.info(f"⏭ Skipping {law_name} - already embedded")
                    total_skipped += 1
                    continue
                
                # Chunk the content
                chunks = chunk_text(content, chunk_size=1000, overlap=200)
                logger.info(f"Processing {law_name}: {len(chunks)} chunks")
                
                # Create points for upload
                points = []
                for i, chunk in enumerate(chunks):
                    # Generate embedding
                    embedding_response = embed_text(chunk, config.openai.embeddings.model)
                    embedding = embedding_response.data[0].embedding
                    
                    # Create point
                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            'law_name': normalized_law_name,
                            'title': law_name,
                            'content': chunk,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'source_url': url,
                            'source_collection': 'paragraf_rs',
                            'document_type': 'zakon',  # or detect from name
                            'scraped_at': law_data.get('scraped_at', 'unknown')
                        }
                    )
                    points.append(point)
                
                # Upload in batches
                for i in range(0, len(points), batch_size):
                    batch = points[i:i + batch_size]
                    client.upsert(
                        collection_name=KOMPLETNO_PRAVO_COLLECTION,
                        points=batch
                    )
                
                total_points_uploaded += len(points)
                total_laws_processed += 1
                logger.info(f"✓ Uploaded {law_name}: {len(points)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {law_file.name}: {e}")
                failed_laws.append(str(law_file.name))
                continue
        
        logger.info(f"\n{'='*70}")
        logger.info("UPLOAD COMPLETE!")
        logger.info(f"{'='*70}")
        logger.info(f"Laws processed: {total_laws_processed}")
        logger.info(f"Laws skipped (already embedded): {total_skipped}")
        logger.info(f"Total chunks uploaded: {total_points_uploaded}")
        logger.info(f"Failed: {len(failed_laws)}")
        if failed_laws:
            logger.info(f"Failed laws: {failed_laws[:10]}...")  # Show first 10
        logger.info(f"{'='*70}\n")
        
        return total_laws_processed, total_points_uploaded, failed_laws
        
    except Exception as e:
        logger.error(f"Error in upload process: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0, []


if __name__ == "__main__":
    upload_scraped_laws()

