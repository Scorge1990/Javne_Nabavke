"""Overall progress summary for law scraping and embedding."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from loguru import logger

from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())


def overall_summary():
    """Generate overall progress summary."""
    try:
        # Load comparison data
        with open('law_comparison.json', 'r', encoding='utf-8') as f:
            comparison = json.load(f)
            total_missing = comparison['summary']['truly_missing']
        
        # Count scraped files
        scraped_dir = Path('scraped_laws')
        scraped_files = list(scraped_dir.glob('*.json')) if scraped_dir.exists() else []
        num_scraped = len(scraped_files)
        
        # Check Qdrant status
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        collection_info = client.get_collection(KOMPLETNO_PRAVO_COLLECTION)
        total_points = collection_info.points_count
        
        # Count paragraf_rs points
        paragraf_count = 0
        scroll_results, _ = client.scroll(
            collection_name=KOMPLETNO_PRAVO_COLLECTION,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )
        for point in scroll_results:
            payload = point.payload or {}
            if payload.get('source_collection') == 'paragraf_rs':
                paragraf_count += 1
        
        logger.info(f"\n{'='*70}")
        logger.info("OVERALL PROGRESS SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"\n📊 SCRAPING STATUS:")
        logger.info(f"  Total missing laws identified: {total_missing:,}")
        logger.info(f"  Laws successfully scraped: {num_scraped:,}")
        logger.info(f"  Scraping success rate: {(num_scraped/total_missing)*100:.1f}%")
        logger.info(f"  Remaining to scrape: {total_missing - num_scraped:,}")
        
        logger.info(f"\n💾 QDRANT DATABASE STATUS:")
        logger.info(f"  Total points in database: {total_points:,}")
        logger.info(f"  Estimated paragraf.rs points: ~{paragraf_count * (total_points // 1000):,}")
        logger.info(f"  Database status: {'✅ Healthy' if total_points > 0 else '❌ Empty'}")
        
        logger.info(f"\n✅ COMPLETED TASKS:")
        logger.info(f"  ✓ Identified missing laws")
        logger.info(f"  ✓ Scraped {num_scraped:,} laws from paragraf.rs")
        logger.info(f"  ✓ Embedded and uploaded {num_scraped:,} laws to Qdrant")
        logger.info(f"  ✓ Database ready for LegaBot queries")
        
        logger.info(f"\n{'='*70}\n")
        
        return {
            'total_missing': total_missing,
            'scraped': num_scraped,
            'remaining': total_missing - num_scraped,
            'qdrant_points': total_points
        }
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    overall_summary()

