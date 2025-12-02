"""Script to scrape 30% of remaining missing laws."""

import json
import time
from loguru import logger
from scrape_missing_laws_content import scrape_missing_laws

def scrape_30_percent_remaining():
    """Scrape 30% of remaining missing laws."""
    # Load comparison to get remaining count
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
        total_missing = comparison['summary']['truly_missing']
    
    # Calculate how many we've already scraped
    from pathlib import Path
    scraped_dir = Path('scraped_laws')
    already_scraped = len(list(scraped_dir.glob('*.json'))) if scraped_dir.exists() else 0
    
    remaining = total_missing - already_scraped
    target_30_percent = int(remaining * 0.30)
    
    logger.info(f"Total missing laws: {total_missing}")
    logger.info(f"Already scraped: {already_scraped}")
    logger.info(f"Remaining: {remaining}")
    logger.info(f"30% of remaining: {target_30_percent} laws")
    
    # Find where to start (after already scraped)
    start_index = already_scraped
    end_index = start_index + target_30_percent
    
    batch_size = 50
    total_successful = 0
    total_failed = 0
    current_index = start_index
    
    while current_index < end_index:
        batch_num = ((current_index - start_index) // batch_size) + 1
        remaining_in_batch = min(batch_size, end_index - current_index)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"BATCH {batch_num}: Starting at index {current_index}")
        logger.info(f"Progress: {current_index - start_index}/{target_30_percent} ({(current_index - start_index)/target_30_percent*100:.1f}%)")
        logger.info(f"{'='*70}\n")
        
        successful, failed, next_index = scrape_missing_laws(
            batch_size=remaining_in_batch,
            start_index=current_index
        )
        
        total_successful += successful
        total_failed += failed
        
        logger.info(f"\nBatch {batch_num} Summary:")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Total successful so far: {total_successful}")
        logger.info(f"  Total failed so far: {total_failed}")
        
        current_index = next_index
        
        # Small delay between batches
        if current_index < end_index:
            logger.info("Pausing 5 seconds before next batch...")
            time.sleep(5)
    
    logger.info(f"\n{'='*70}")
    logger.info("30% SCRAPING COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Target: {target_30_percent} laws")
    logger.info(f"Successfully scraped: {total_successful}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success rate: {(total_successful/(total_successful+total_failed))*100:.1f}%")
    logger.info(f"{'='*70}\n")
    
    return total_successful, total_failed

if __name__ == "__main__":
    start_time = time.time()
    successful, failed = scrape_30_percent_remaining()
    elapsed = time.time() - start_time
    logger.info(f"Total time: {elapsed/60:.1f} minutes")
    logger.info(f"\nNext step: Run 'python upload_to_qdrant.py' to embed the newly scraped laws")

