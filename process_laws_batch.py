"""
Script to process a batch of unprocessed laws and commit them to Qdrant.
"""
import argparse
import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from tqdm.auto import tqdm

from database.utils import (
    SRPSKO_PRAVO_COLLECTION,
    create_embeddings,
    load_and_process_embeddings,
    upsert,
)

VECTOR_SIZE = 1536


def law_exists_in_qdrant(client: QdrantClient, law_name: str) -> bool:
    if not client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
        return False
    try:
        points, _ = client.scroll(
            collection_name=SRPSKO_PRAVO_COLLECTION,
            limit=1,
            with_payload=False,
            with_vectors=False,
            filter=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="source_collection",
                        match=rest.MatchValue(value=law_name),
                    )
                ]
            ),
        )
        return bool(points)
    except Exception as exc:
        logger.warning(f"Unable to verify law {law_name} in Qdrant: {exc}")
        return False


def get_unprocessed_laws(scraped_dir: Path, embeddings_dir: Path, qdrant_client: QdrantClient = None, limit: int = 200):
    """Get list of unprocessed law files."""
    scraped_files = {f.stem: f for f in scraped_dir.iterdir() if f.is_file() and f.suffix == ".json"}
    processed_files = {f.stem for f in embeddings_dir.iterdir() if f.is_file() and f.suffix == ".jsonl"}
    
    unprocessed = []
    for stem, file_path in scraped_files.items():
        law_name = stem.replace("-", "_")
        already_embedded = stem in processed_files
        in_qdrant = law_exists_in_qdrant(qdrant_client, law_name) if qdrant_client else False

        if in_qdrant:
            continue

        if not already_embedded or not in_qdrant:
            unprocessed.append(file_path)
            if len(unprocessed) >= limit:
                break
    
    return unprocessed


def main(args: argparse.Namespace) -> None:
    """Main function to process a batch of laws and commit to Qdrant."""
    load_dotenv(find_dotenv())
    
    scraped_dir = Path(args.scraped_dir)
    embeddings_dir = Path(args.embeddings_dir)
    to_process_dir = Path(args.to_process_dir)
    
    # Ensure directories exist
    to_process_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Qdrant client to check existing collections
    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=180,  # 180 second timeout (3 minutes)
    )
    
    # Ensure target collection exists
    if not qdrant_client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
        logger.info(f'Creating target collection "{SRPSKO_PRAVO_COLLECTION}".')
        qdrant_client.create_collection(
            collection_name=SRPSKO_PRAVO_COLLECTION,
            vectors_config=rest.VectorParams(size=VECTOR_SIZE, distance=rest.Distance.COSINE),
        )
    
    # Get unprocessed laws
    logger.info(f"Finding up to {args.limit} unprocessed laws...")
    unprocessed_laws = get_unprocessed_laws(scraped_dir, embeddings_dir, qdrant_client, limit=args.limit)
    
    if not unprocessed_laws:
        logger.info("No unprocessed laws found.")
        return
    
    logger.info(f"Found {len(unprocessed_laws)} unprocessed laws to process.")
    
    # Create temporary directory with only the laws we want to process
    with TemporaryDirectory() as temp_dir:
        temp_scraped_dir = Path(temp_dir) / "scraped"
        temp_scraped_dir.mkdir(parents=True)
        
        # Copy unprocessed laws to temp directory
        logger.info("Copying laws to temporary directory...")
        for law_file in tqdm(unprocessed_laws, desc="Copying files"):
            shutil.copy2(law_file, temp_scraped_dir / law_file.name)
        
        # Create embeddings
        logger.info("Creating embeddings...")
        create_embeddings(
            scraped_dir=temp_scraped_dir,
            to_process_dir=to_process_dir,
            embeddings_dir=embeddings_dir,
            model=args.model,
        )
    
    # Upload to Qdrant
    logger.info("Uploading to Qdrant...")
    
    # Get list of processed embeddings (only the ones we just created)
    # Map original stems to actual embedding files (which may have been hashed)
    processed_stems = {f.stem: f for f in unprocessed_laws}
    
    for original_stem, law_file in processed_stems.items():
        # Try original stem first
        embedding_file = embeddings_dir / f"{original_stem}.jsonl"
        
        # If not found, check if it was hashed (look for files starting with original_stem)
        if not embedding_file.exists():
            # Find matching embedding file (could be hashed)
            matching_files = list(embeddings_dir.glob(f"{original_stem[:50]}*.jsonl"))
            if matching_files:
                embedding_file = matching_files[0]
            else:
                # Try just finding by hash if we have the original
                import hashlib
                stem_hash = hashlib.md5(original_stem.encode('utf-8')).hexdigest()[:16]
                hash_files = list(embeddings_dir.glob(f"*{stem_hash}*.jsonl"))
                if hash_files:
                    embedding_file = hash_files[0]
                else:
                    logger.warning(f"Embedding file not found for: {original_stem}")
                    continue
        
        law_name = original_stem.replace("-", "_")
        points = load_and_process_embeddings(path=embedding_file, law_name=law_name)
        
        if not points:
            logger.warning(f"Skipping {law_name} - no valid embeddings")
            continue
        
        # Skip if law already present (race condition safeguard)
        try:
            if law_exists_in_qdrant(qdrant_client, law_name):
                logger.info(f'Law "{law_name}" already present in {SRPSKO_PRAVO_COLLECTION}. Skipping.')
                continue
        except Exception as exc:
            logger.warning(f"Could not verify existing records for {law_name}: {exc}")
        
        upsert(
            client=qdrant_client,
            collection=SRPSKO_PRAVO_COLLECTION,
            points=points,
            batch_size=50,
        )
        
        logger.info(f'Uploaded {len(points)} vectors for "{law_name}" into {SRPSKO_PRAVO_COLLECTION}.')
    
    logger.info(f"Successfully processed and uploaded {len(processed_stems)} laws to Qdrant.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process a batch of unprocessed laws and commit them to Qdrant."
    )
    parser.add_argument(
        "--scraped_dir",
        type=Path,
        default=Path("./scraper/laws"),
        help="Directory containing scraped law files.",
    )
    parser.add_argument(
        "--to_process_dir",
        type=Path,
        default=Path("./database/to_process"),
        help="Directory to process files.",
    )
    parser.add_argument(
        "--embeddings_dir",
        type=Path,
        default=Path("./database/embeddings"),
        help="Directory for storing embeddings.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of laws to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="The embedding model to be used. If not set, it will be loaded from the config file.",
    )
    
    args = parser.parse_args()
    
    # Load model from config file if not explicitly set
    if args.model is None:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            args.model = config["openai"]["embeddings"]["model"]
    
    main(args=args)

