"""
Script to delete collections from Qdrant.
"""
import argparse
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient

from database.utils import delete_collection


def main(args: argparse.Namespace) -> None:
    """Delete collections from Qdrant."""
    load_dotenv(find_dotenv())
    
    # Initialize Qdrant client with longer timeout
    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=120,  # 120 second timeout
    )
    
    # If specific collections provided, use those
    if args.collections:
        to_delete = args.collections
        logger.info(f"Will delete specified collections: {to_delete}")
    else:
        # Try to get collections, but if it times out, we can't proceed
        try:
            collections = qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            logger.info(f"Found {len(collection_names)} collections in Qdrant.")
            to_delete = collection_names[:args.limit]
        except Exception as e:
            logger.error(f"Error getting collections: {e}")
            logger.error("Cannot list collections due to timeout. Please specify collection names with --collections option.")
            return
    
    logger.info(f"Deleting {len(to_delete)} collections: {to_delete}")
    
    deleted = 0
    failed = 0
    
    import time
    
    for collection_name in to_delete:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                delete_collection(client=qdrant_client, collection=collection_name, timeout=120)
                logger.info(f"Successfully deleted collection: {collection_name}")
                deleted += 1
                break
            except Exception as e:
                if "timeout" in str(e).lower() or "read" in str(e).lower():
                    if attempt < max_retries - 1:
                        logger.warning(f"Timeout deleting collection {collection_name}, retrying ({attempt + 1}/{max_retries})...")
                        time.sleep(5)
                        continue
                    else:
                        logger.error(f"Error deleting collection '{collection_name}' after {max_retries} attempts: {e}")
                        failed += 1
                        break
                else:
                    logger.error(f"Error deleting collection '{collection_name}': {e}")
                    failed += 1
                    break
        
        # Small delay between deletions
        if deleted + failed < len(to_delete):
            time.sleep(2)
    
    logger.info(f"Deletion complete: {deleted} deleted, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete collections from Qdrant."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of collections to delete (if --collections not specified).",
    )
    parser.add_argument(
        "--collections",
        type=str,
        nargs="+",
        default=None,
        help="Specific collection names to delete.",
    )
    
    args = parser.parse_args()
    main(args=args)

