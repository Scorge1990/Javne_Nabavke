"""Script to scrape the second half of missing laws in batches."""

import json
import time
from loguru import logger
from scrape_missing_laws_content import scrape_missing_laws

def scrape_second_half():
    """Scrape the second half of missing laws in batches of 50."""
    # Load comparison to get total count
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
        total_missing = comparison['summary']['truly_missing']
    
    first_half = total_missing // 2
    second_half_start = first_half
    second_half_end = total_missing
    
    logger.info(f"Total missing laws: {total_missing}")
    logger.info(f"Second half to scrape: {second_half_start} to {second_half_end} ({second_half_end - second_half_start} laws)")
    
    batch_size = 50
    start_index = second_half_start
    total_successful = 0
    total_failed = 0
    
    while start_index < second_half_end:
        batch_num = ((start_index - second_half_start) // batch_size) + 1
        logger.info(f"\n{'='*70}")
        logger.info(f"BATCH {batch_num}: Starting at index {start_index}")
        logger.info(f"Progress: {start_index - second_half_start}/{second_half_end - second_half_start} ({(start_index - second_half_start)/(second_half_end - second_half_start)*100:.1f}%)")
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
        if start_index < second_half_end:
            logger.info("Pausing 5 seconds before next batch...")
            time.sleep(5)
    
    logger.info(f"\n{'='*70}")
    logger.info("SECOND HALF SCRAPING COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Total laws to scrape: {second_half_end - second_half_start}")
    logger.info(f"Successfully scraped: {total_successful}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success rate: {(total_successful/(total_successful+total_failed))*100:.1f}%")
    logger.info(f"{'='*70}\n")

if __name__ == "__main__":
    start_time = time.time()
    scrape_second_half()
    elapsed = time.time() - start_time
    logger.info(f"Total time: {elapsed/60:.1f} minutes")

