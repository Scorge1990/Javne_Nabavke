"""Script to monitor the progress of law scraping."""

import json
import os
from pathlib import Path
from loguru import logger
from datetime import datetime


def check_progress():
    """Check the current scraping progress."""
    try:
        # Load comparison to get total
        with open('law_comparison.json', 'r', encoding='utf-8') as f:
            comparison = json.load(f)
            total_missing = comparison['summary']['truly_missing']
            first_half = total_missing // 2
        
        # Count scraped files
        scraped_dir = Path('scraped_laws')
        if not scraped_dir.exists():
            logger.warning("scraped_laws directory doesn't exist yet")
            return
        
        scraped_files = list(scraped_dir.glob('*.json'))
        num_scraped = len(scraped_files)
        
        # Calculate progress
        progress_pct = (num_scraped / first_half) * 100
        remaining = first_half - num_scraped
        
        # Estimate time remaining (assume ~2 seconds per law)
        est_minutes_remaining = (remaining * 2) / 60
        
        logger.info(f"\n{'='*70}")
        logger.info("SCRAPING PROGRESS REPORT")
        logger.info(f"{'='*70}")
        logger.info(f"Target (first half): {first_half} laws")
        logger.info(f"Currently scraped: {num_scraped} laws")
        logger.info(f"Remaining: {remaining} laws")
        logger.info(f"Progress: {progress_pct:.1f}%")
        logger.info(f"Estimated time remaining: {est_minutes_remaining:.0f} minutes")
        logger.info(f"{'='*70}\n")
        
        # Show sample of recently scraped files
        if scraped_files:
            recent_files = sorted(scraped_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            logger.info("Recently scraped:")
            for i, f in enumerate(recent_files, 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%H:%M:%S')
                size_kb = f.stat().st_size / 1024
                logger.info(f"  {i}. {f.stem[:60]}... ({size_kb:.1f} KB at {mtime})")
        
        return num_scraped, first_half, progress_pct
        
    except Exception as e:
        logger.error(f"Error checking progress: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None


if __name__ == "__main__":
    check_progress()

