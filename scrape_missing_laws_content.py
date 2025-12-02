"""Script to scrape the actual content of missing laws from paragraf.rs."""

import json
import os
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm
import re


def normalize_filename(name):
    """Create a safe filename from law name."""
    # Replace special characters with safe equivalents
    filename = name.lower()
    # Remove/replace problematic characters for Windows
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Replace other special chars with underscore
    filename = re.sub(r'[^\w\s-]', '_', filename)
    # Replace spaces and multiple underscores
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    # Limit length and strip underscores
    filename = filename[:180].strip('_')
    return filename


def scrape_law_content(url, law_name):
    """Scrape the content of a single law from its URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content - paragraf.rs typically has content in specific divs
        content_div = soup.find('div', {'class': 'zakon-section'}) or \
                     soup.find('div', {'class': 'propisi'}) or \
                     soup.find('div', {'id': 'content'}) or \
                     soup.find('main') or \
                     soup.find('article')
        
        if not content_div:
            # Try to find any large text content
            content_div = soup.find('body')
        
        if not content_div:
            logger.warning(f"Could not find content for {law_name}")
            return None
        
        # Extract text content
        paragraphs = []
        for p in content_div.find_all(['p', 'div', 'section', 'article']):
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                paragraphs.append(text)
        
        # Also extract any structured law articles
        articles = []
        for elem in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            article_text = elem.get_text(strip=True)
            if article_text:
                articles.append(article_text)
        
        # Combine all content
        full_text = '\n\n'.join(paragraphs)
        
        if len(full_text) < 100:
            logger.warning(f"Very short content for {law_name}: {len(full_text)} chars")
            return None
        
        return {
            'law_name': law_name,
            'url': url,
            'content': full_text,
            'articles': articles,
            'char_count': len(full_text),
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Error scraping {law_name}: {e}")
        return None


def scrape_missing_laws(batch_size=50, start_index=0):
    """Scrape content for missing laws."""
    try:
        # Load comparison results
        with open('law_comparison.json', 'r', encoding='utf-8') as f:
            comparison = json.load(f)
            missing_laws = comparison['missing_laws']
        
        logger.info(f"Total missing laws: {len(missing_laws)}")
        logger.info(f"Starting from index {start_index}, scraping {batch_size} laws")
        
        # Create output directory
        os.makedirs('scraped_laws', exist_ok=True)
        
        # Track progress
        successful = 0
        failed = 0
        
        # Scrape a batch
        end_index = min(start_index + batch_size, len(missing_laws))
        batch = missing_laws[start_index:end_index]
        
        for i, law_info in enumerate(tqdm(batch, desc="Scraping laws")):
            law_name = law_info['name']
            law_url = law_info['url']
            
            if law_url == 'N/A':
                logger.warning(f"No URL for {law_name}, skipping")
                failed += 1
                continue
            
            # Check if already scraped
            filename = normalize_filename(law_name)
            filepath = f'scraped_laws/{filename}.json'
            
            if os.path.exists(filepath):
                logger.info(f"Already scraped: {law_name}")
                successful += 1
                continue
            
            # Scrape the law
            logger.info(f"Scraping {i+1}/{len(batch)}: {law_name[:60]}...")
            content = scrape_law_content(law_url, law_name)
            
            if content:
                # Save to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                successful += 1
                logger.info(f"✓ Saved {law_name} ({content['char_count']} chars)")
            else:
                failed += 1
                logger.warning(f"✗ Failed to scrape {law_name}")
            
            # Rate limiting - be respectful
            time.sleep(1)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Batch complete!")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Next start index: {end_index}")
        logger.info(f"{'='*60}")
        
        return successful, failed, end_index
        
    except Exception as e:
        logger.error(f"Error in batch scraping: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, 0, start_index


if __name__ == "__main__":
    # Test with small batch first
    scrape_missing_laws(batch_size=5, start_index=0)

