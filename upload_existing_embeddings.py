"""
Script to upload existing embeddings to Qdrant without creating new embeddings.
"""
import argparse
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from tqdm.auto import tqdm

from database.utils import SRPSKO_PRAVO_COLLECTION, load_and_process_embeddings, upsert

VECTOR_SIZE = 1536


def main(args: argparse.Namespace) -> None:
    """Upload existing embeddings to Qdrant."""
    load_dotenv(find_dotenv())
    
    embeddings_dir = Path(args.embeddings_dir)
    
    # Initialize Qdrant client with longer timeout
    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=180,  # 180 second timeout (3 minutes)
    )
    
    # Get all embedding files
    embedding_files = list(embeddings_dir.glob("*.jsonl"))
    
    if not embedding_files:
        logger.info("No embedding files found.")
        return
    
    # Limit to requested number
    to_upload = embedding_files[: args.limit]
    logger.info(
        f"Uploading up to {len(to_upload)} embedding files into {SRPSKO_PRAVO_COLLECTION}."
    )

    if not qdrant_client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
        logger.info(f'Creating target collection "{SRPSKO_PRAVO_COLLECTION}".')
        qdrant_client.create_collection(
            collection_name=SRPSKO_PRAVO_COLLECTION,
            vectors_config=rest.VectorParams(size=VECTOR_SIZE, distance=rest.Distance.COSINE),
        )
    
    # Upload to Qdrant
    successful = 0
    failed = 0
    skipped = 0
    
    for embedding_file in tqdm(to_upload, desc="Uploading to Qdrant"):
        law_name = embedding_file.stem.replace("-", "_")
        
        try:
            # Skip laws already present in the target collection
            try:
                existing, _ = qdrant_client.scroll(
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
                if existing:
                    logger.info(
                        f'Law "{law_name}" already present in {SRPSKO_PRAVO_COLLECTION}. Skipping.'
                    )
                    skipped += 1
                    continue
            except Exception as exc:
                logger.warning(f"Could not verify existing payload for {law_name}: {exc}")
            
            points = load_and_process_embeddings(path=embedding_file, law_name=law_name)
            
            if not points:
                logger.warning(f"Skipping {law_name} - no valid embeddings")
                skipped += 1
                continue
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    upsert(
                        client=qdrant_client,
                        collection=SRPSKO_PRAVO_COLLECTION,
                        points=points,
                        batch_size=50,
                    )
                    break
                except Exception as exc:
                    if "timeout" in str(exc).lower() or "read" in str(exc).lower():
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Timeout upserting {law_name}, retrying ({attempt + 1}/{max_retries})..."
                            )
                            time.sleep(5)
                            continue
                        else:
                            logger.warning(
                                f"Timeout upserting {law_name} after {max_retries} attempts, skipping..."
                            )
                            failed += 1
                            break
                    else:
                        raise
            else:
                continue  # Skip to next if failed after retries
            
            # Small delay to avoid overwhelming Qdrant
            time.sleep(2)
            
            successful += 1

        except Exception as e:
            logger.error(f"Error uploading {law_name}: {e}")
            failed += 1
    
    logger.info(f"Upload complete: {successful} successful, {failed} failed, {skipped} skipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload existing embeddings to Qdrant."
    )
    parser.add_argument(
        "--embeddings_dir",
        type=Path,
        default=Path("./database/embeddings"),
        help="Directory containing embedding files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of embeddings to upload.",
    )
    
    args = parser.parse_args()
    main(args=args)

