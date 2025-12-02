"""Script to check Qdrant database status."""

import os
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from loguru import logger

from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())


def check_qdrant_status():
    """Check the current status of Qdrant database."""
    try:
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        
        if not client.collection_exists(collection_name=KOMPLETNO_PRAVO_COLLECTION):
            logger.error(f"Collection {KOMPLETNO_PRAVO_COLLECTION} does not exist")
            return
        
        # Get collection info
        collection_info = client.get_collection(KOMPLETNO_PRAVO_COLLECTION)
        
        logger.info(f"\n{'='*70}")
        logger.info("QDRANT DATABASE STATUS")
        logger.info(f"{'='*70}")
        logger.info(f"Collection: {KOMPLETNO_PRAVO_COLLECTION}")
        logger.info(f"Total points: {collection_info.points_count:,}")
        logger.info(f"Vector size: {collection_info.config.params.vectors.size}")
        logger.info(f"Distance metric: {collection_info.config.params.vectors.distance}")
        
        # Check for paragraf_rs source
        logger.info(f"\nChecking for recently uploaded laws from paragraf.rs...")
        
        # Sample scroll to check source
        scroll_results, _ = client.scroll(
            collection_name=KOMPLETNO_PRAVO_COLLECTION,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        
        paragraf_count = 0
        total_checked = 0
        for point in scroll_results:
            total_checked += 1
            payload = point.payload or {}
            if payload.get('source_collection') == 'paragraf_rs':
                paragraf_count += 1
        
        if total_checked > 0:
            paragraf_percentage = (paragraf_count / total_checked) * 100
            logger.info(f"Sample check: {paragraf_count}/{total_checked} points from paragraf.rs ({paragraf_percentage:.1f}%)")
        
        logger.info(f"{'='*70}\n")
        
        return collection_info.points_count
        
    except Exception as e:
        logger.error(f"Error checking Qdrant status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    check_qdrant_status()

