"""Script to scrape the first half of missing laws in batches."""

import json
import time
from loguru import logger
from scrape_missing_laws_content import scrape_missing_laws

def scrape_first_half():
    """Scrape the first half of missing laws in batches of 50."""
    # Load comparison to get total count
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
        total_missing = comparison['summary']['truly_missing']
    
    first_half = total_missing // 2
    logger.info(f"Total missing laws: {total_missing}")
    logger.info(f"First half to scrape: {first_half}")
    
    batch_size = 50
    start_index = 0
    total_successful = 0
    total_failed = 0
    
    while start_index < first_half:
        batch_num = (start_index // batch_size) + 1
        logger.info(f"\n{'='*70}")
        logger.info(f"BATCH {batch_num}: Starting at index {start_index}")
        logger.info(f"Progress: {start_index}/{first_half} ({(start_index/first_half)*100:.1f}%)")
        logger.info(f"{'='*70}\n")
        
        successful, failed, next_index = scrape_missing_laws(
            batch_size=batch_size,
            start_index=start_index
        )
        
        total_successful += successful
        total_failed += failed
        
        logger.info(f"\nBatch {batch_num} Summary:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total successful so far: {total_successful}")
        logger.info(f"  Total failed so far: {total_failed}")
        
        start_index = next_index
        
        # Small delay between batches
        if start_index < first_half:
            logger.info("Pausing 5 seconds before next batch...")
            time.sleep(5)
    
    logger.info(f"\n{'='*70}")
    logger.info("FIRST HALF SCRAPING COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Total laws to scrape: {first_half}")
    logger.info(f"Successfully scraped: {total_successful}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success rate: {(total_successful/(total_successful+total_failed))*100:.1f}%")
    logger.info(f"{'='*70}\n")

if __name__ == "__main__":
    start_time = time.time()
    scrape_first_half()
    elapsed = time.time() - start_time
    logger.info(f"Total time: {elapsed/60:.1f} minutes")

