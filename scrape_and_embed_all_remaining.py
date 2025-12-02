"""Script to scrape all remaining laws and embed them into Qdrant."""

import json
import time
from pathlib import Path
from loguru import logger
from scrape_missing_laws_content import scrape_missing_laws
from upload_to_qdrant import upload_scraped_laws


def scrape_and_embed_all_remaining():
    """Scrape all remaining laws and embed them."""
    # Load comparison to get remaining count
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
        total_missing = comparison['summary']['truly_missing']
        missing_laws = comparison['missing_laws']
    
    # Calculate how many we've already scraped
    scraped_dir = Path('scraped_laws')
    already_scraped = len(list(scraped_dir.glob('*.json'))) if scraped_dir.exists() else 0
    
    remaining = total_missing - already_scraped
    
    logger.info(f"\n{'='*70}")
    logger.info("SCRAPING ALL REMAINING LAWS")
    logger.info(f"{'='*70}")
    logger.info(f"Total missing laws: {total_missing}")
    logger.info(f"Already scraped: {already_scraped}")
    logger.info(f"Remaining to scrape: {remaining}")
    logger.info(f"{'='*70}\n")
    
    if remaining == 0:
        logger.info("All laws have already been scraped!")
        return
    
    # Step 1: Scrape all remaining laws
    start_index = already_scraped
    batch_size = 50
    total_successful = 0
    total_failed = 0
    current_index = start_index
    
    while current_index < len(missing_laws):
        batch_num = ((current_index - start_index) // batch_size) + 1
        remaining_in_batch = min(batch_size, len(missing_laws) - current_index)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"SCRAPING BATCH {batch_num}: Starting at index {current_index}")
        logger.info(f"Progress: {current_index - start_index}/{remaining} ({(current_index - start_index)/remaining*100:.1f}%)")
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
        if current_index < len(missing_laws):
            logger.info("Pausing 5 seconds before next batch...")
            time.sleep(5)
    
    logger.info(f"\n{'='*70}")
    logger.info("SCRAPING COMPLETE!")
    logger.info(f"{'='*70}")
    logger.info(f"Total scraped: {total_successful}")
    logger.info(f"Total failed: {total_failed}")
    logger.info(f"{'='*70}\n")
    
    # Step 2: Upload all newly scraped laws to Qdrant
    logger.info(f"\n{'='*70}")
    logger.info("STARTING UPLOAD TO QDRANT")
    logger.info(f"{'='*70}\n")
    
    laws_processed, chunks_uploaded, failed_laws = upload_scraped_laws()
    
    logger.info(f"\n{'='*70}")
    logger.info("COMPLETE SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Laws scraped in this session: {total_successful}")
    logger.info(f"Laws embedded: {laws_processed}")
    logger.info(f"Chunks uploaded: {chunks_uploaded:,}")
    logger.info(f"{'='*70}\n")
    
    return total_successful, laws_processed, chunks_uploaded


if __name__ == "__main__":
    start_time = time.time()
    successful, embedded, chunks = scrape_and_embed_all_remaining()
    elapsed = time.time() - start_time
    logger.info(f"Total time: {elapsed/60:.1f} minutes")
    logger.info(f"Average time per law: {elapsed/(successful or 1):.1f} seconds")



