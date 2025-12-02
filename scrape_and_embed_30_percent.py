"""Script to scrape 30% of remaining laws and automatically embed them."""

import json
import time
from pathlib import Path
from loguru import logger
from scrape_missing_laws_content import scrape_missing_laws
from upload_to_qdrant import upload_scraped_laws

def scrape_and_embed_30_percent():
    """Scrape 30% of remaining laws and embed them."""
    # Load comparison to get remaining count
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
        total_missing = comparison['summary']['truly_missing']
    
    # Calculate how many we've already scraped
    scraped_dir = Path('scraped_laws')
    already_scraped = len(list(scraped_dir.glob('*.json'))) if scraped_dir.exists() else 0
    
    remaining = total_missing - already_scraped
    target_30_percent = int(remaining * 0.30)
    
    logger.info(f"\n{'='*70}")
    logger.info("SCRAPING 30% OF REMAINING LAWS")
    logger.info(f"{'='*70}")
    logger.info(f"Total missing laws: {total_missing}")
    logger.info(f"Already scraped: {already_scraped}")
    logger.info(f"Remaining: {remaining}")
    logger.info(f"Target (30%): {target_30_percent} laws")
    logger.info(f"{'='*70}\n")
    
    # Step 1: Scrape
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
        logger.info(f"SCRAPING BATCH {batch_num}: Starting at index {current_index}")
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
    logger.info("SCRAPING COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Target: {target_30_percent} laws")
    logger.info(f"Successfully scraped: {total_successful}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"{'='*70}\n")
    
    # Step 2: Upload to Qdrant
    logger.info(f"\n{'='*70}")
    logger.info("STARTING UPLOAD TO QDRANT")
    logger.info(f"{'='*70}\n")
    
    laws_processed, chunks_uploaded, failed_laws = upload_scraped_laws()
    
    logger.info(f"\n{'='*70}")
    logger.info("COMPLETE SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Laws scraped: {total_successful}")
    logger.info(f"Laws embedded: {laws_processed}")
    logger.info(f"Chunks uploaded: {chunks_uploaded:,}")
    logger.info(f"{'='*70}\n")
    
    return total_successful, laws_processed, chunks_uploaded

if __name__ == "__main__":
    start_time = time.time()
    successful, embedded, chunks = scrape_and_embed_30_percent()
    elapsed = time.time() - start_time
    logger.info(f"Total time: {elapsed/60:.1f} minutes")

