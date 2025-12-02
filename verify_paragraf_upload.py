"""Script to verify if paragraf_rs laws are actually in Kompletno_pravo collection."""

import os
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from loguru import logger

from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())


def verify_paragraf_upload():
    """Verify if paragraf_rs laws are in the collection."""
    try:
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        
        if not client.collection_exists(collection_name=KOMPLETNO_PRAVO_COLLECTION):
            logger.error(f"Collection {KOMPLETNO_PRAVO_COLLECTION} does not exist")
            return
        
        collection_info = client.get_collection(KOMPLETNO_PRAVO_COLLECTION)
        total_points = collection_info.points_count
        
        logger.info(f"\n{'='*70}")
        logger.info("VERIFYING PARAGRAF.RS UPLOADS")
        logger.info(f"{'='*70}")
        logger.info(f"Collection: {KOMPLETNO_PRAVO_COLLECTION}")
        logger.info(f"Total points: {total_points:,}")
        
        # Count paragraf_rs documents by scrolling through all
        paragraf_count = 0
        other_count = 0
        no_source_count = 0
        offset = None
        max_scrolls = 1000  # Check up to 100,000 points
        checked = 0
        
        logger.info(f"\nScanning collection for paragraf_rs documents...")
        
        for scroll_num in range(max_scrolls):
            scroll_results, next_page = client.scroll(
                collection_name=KOMPLETNO_PRAVO_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            
            if not scroll_results:
                break
            
            for point in scroll_results:
                checked += 1
                payload = point.payload or {}
                source = payload.get('source_collection', '')
                
                if source == 'paragraf_rs':
                    paragraf_count += 1
                elif source:
                    other_count += 1
                else:
                    no_source_count += 1
            
            if checked >= total_points:
                break
                
            if not next_page:
                break
            offset = next_page
            
            if scroll_num % 10 == 0:
                logger.info(f"Checked {checked:,} points... (found {paragraf_count:,} paragraf_rs)")
        
        logger.info(f"\n{'='*70}")
        logger.info("VERIFICATION RESULTS")
        logger.info(f"{'='*70}")
        logger.info(f"Total points checked: {checked:,}")
        logger.info(f"Points with source_collection='paragraf_rs': {paragraf_count:,}")
        logger.info(f"Points with other source_collection: {other_count:,}")
        logger.info(f"Points with no source_collection: {no_source_count:,}")
        
        if paragraf_count > 0:
            percentage = (paragraf_count / checked) * 100 if checked > 0 else 0
            logger.info(f"\n✅ Found {paragraf_count:,} paragraf_rs documents ({percentage:.2f}%)")
            logger.info(f"✅ Laws ARE embedded in {KOMPLETNO_PRAVO_COLLECTION}")
        else:
            logger.warning(f"\n❌ No paragraf_rs documents found!")
            logger.warning(f"❌ Laws may NOT be embedded in {KOMPLETNO_PRAVO_COLLECTION}")
        
        # Show sample of paragraf_rs documents if found
        if paragraf_count > 0:
            logger.info(f"\nFetching sample paragraf_rs documents...")
            scroll_results, _ = client.scroll(
                collection_name=KOMPLETNO_PRAVO_COLLECTION,
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )
            
            sample_count = 0
            for point in scroll_results:
                payload = point.payload or {}
                if payload.get('source_collection') == 'paragraf_rs':
                    sample_count += 1
                    if sample_count <= 5:
                        title = payload.get('title', 'N/A')
                        law_name = payload.get('law_name', 'N/A')
                        logger.info(f"  Sample {sample_count}: {title[:80]}...")
                        logger.info(f"    Law name: {law_name[:60]}...")
        
        logger.info(f"{'='*70}\n")
        
        return paragraf_count, checked
        
    except Exception as e:
        logger.error(f"Error verifying upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0


if __name__ == "__main__":
    verify_paragraf_upload()


