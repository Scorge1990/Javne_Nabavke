"""
Script to scrape all laws from paragraf.rs/propisi.html that haven't been scraped yet.
"""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm.auto import tqdm

# Import scraper function directly
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", Path(__file__).parent / "scraper.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
run_scraper = scraper_module.run_scraper


def normalize_filename(url: str) -> str:
    """
    Convert a URL to a normalized filename.
    Example: 'https://www.paragraf.rs/propisi/zakon_o_radu.html' -> 'zakon_o_radu.json'
    """
    # Extract the path from URL
    path = urlparse(url).path
    # Get the stem (filename without extension)
    stem = Path(path).stem
    # Replace hyphens with underscores for consistency
    stem = stem.replace("-", "_")
    return f"{stem}.json"


def extract_law_urls(propisi_url: str) -> list[str]:
    """
    Extract all law URLs from the propisi.html page.
    
    Args:
        propisi_url: URL to the propisi.html page
        
    Returns:
        List of law URLs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(propisi_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Failed to fetch propisi page: {e}')
        return []
    
    soup = BeautifulSoup(response.content, "html.parser")
    law_urls = set()  # Use set to avoid duplicates
    
    # Find all <a> tags with href attributes
    all_links = soup.find_all("a", href=True)
    logger.debug(f"Found {len(all_links)} total links on page")
    
    # Check all hrefs to see what we're getting
    sample_hrefs = []
    for link in all_links[:20]:  # First 20 for debugging
        href = link.get("href", "")
        sample_hrefs.append(href)
    
    logger.debug(f"Sample hrefs: {sample_hrefs}")
    
    for link in all_links:
        href = link.get("href", "")
        # Check if it's a link to a law (propisi subdirectory)
        # Also check for relative paths that might be laws
        if ("/propisi/" in href or href.startswith("propisi/")) and href.endswith(".html"):
            # Convert relative URLs to absolute
            full_url = urljoin(propisi_url, href)
            law_urls.add(full_url)
        # Also check for links that might be laws but in different format
        elif href.startswith("/propisi/") and href.endswith(".html"):
            full_url = urljoin(propisi_url, href)
            law_urls.add(full_url)
    
    # Convert to list and sort
    law_urls = sorted(list(law_urls))
    logger.info(f"Found {len(law_urls)} law URLs")
    
    # Log first few URLs for debugging
    if law_urls:
        logger.info(f"Sample URLs: {law_urls[:5]}")
    
    return law_urls


def get_scraped_laws(output_dir: Path) -> set[str]:
    """
    Get a set of already scraped law filenames.
    
    Args:
        output_dir: Directory where scraped laws are saved
        
    Returns:
        Set of normalized filenames (without extension)
    """
    scraped = set()
    if output_dir.exists():
        for json_file in output_dir.glob("*.json"):
            # Get filename without extension and normalize
            stem = json_file.stem.replace("-", "_")
            scraped.add(stem)
    return scraped


def scrape_law(url: str, output_dir: Path) -> bool:
    """
    Scrape a single law from its URL.
    
    Args:
        url: URL of the law to scrape
        output_dir: Directory to save the scraped law
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize filename
    filename = normalize_filename(url)
    save_path = output_dir / filename
    
    # Skip if already exists
    if save_path.exists():
        logger.debug(f"Already scraped: {filename}")
        return True
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Failed to fetch URL: "{url}" - {e}')
        return False
    
    soup = BeautifulSoup(response.content, "html.parser")
    
    try:
        law_articles = run_scraper(soup=soup, url=url)
    except Exception as e:
        logger.error(f'Failed to scrape data from URL: "{url}" - {e}')
        return False
    
    # Skip if no articles found (empty law)
    if not law_articles:
        logger.warning(f"No articles found for {url}, skipping")
        return False
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as file:
            json.dump(law_articles, file, indent=4, ensure_ascii=False)
        logger.info(f'Successfully saved: {filename} ({len(law_articles)} articles)')
        return True
    except Exception as e:
        logger.error(f'Failed to save data to "{save_path}" - {e}')
        return False


def main(propisi_url: str = "https://www.paragraf.rs/propisi.html", output_dir: Path = Path("scraper/laws")):
    """
    Main function to scrape all laws from propisi.html.
    
    Args:
        propisi_url: URL to the propisi.html page
        output_dir: Directory to save scraped laws
    """
    logger.info(f"Fetching law URLs from {propisi_url}")
    law_urls = extract_law_urls(propisi_url)
    
    if not law_urls:
        logger.error("No law URLs found!")
        return
    
    # Get already scraped laws
    scraped = get_scraped_laws(output_dir)
    logger.info(f"Found {len(scraped)} already scraped laws")
    
    # Filter out already scraped laws
    to_scrape = []
    for url in law_urls:
        filename = normalize_filename(url)
        stem = Path(filename).stem
        if stem not in scraped:
            to_scrape.append(url)
    
    logger.info(f"Found {len(to_scrape)} laws to scrape")
    
    if not to_scrape:
        logger.info("All laws have already been scraped!")
        return
    
    # Scrape each law
    successful = 0
    failed = 0
    
    for url in tqdm(to_scrape, desc="Scraping laws"):
        if scrape_law(url, output_dir):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"Scraping complete: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()

