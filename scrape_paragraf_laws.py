"""Script to scrape the list of laws from paragraf.rs website."""

import requests
from bs4 import BeautifulSoup
from loguru import logger
import json
import time

BASE_URL = "https://www.paragraf.rs/propisi.html"


def scrape_paragraf_laws():
    """Scrape all law names from paragraf.rs."""
    try:
        logger.info(f"Scraping laws from {BASE_URL}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(BASE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        laws = []
        law_links = {}
        
        # Find all bold text elements which contain law names
        for bold_tag in soup.find_all(['strong', 'b']):
            # Get the parent link if it exists
            parent_link = bold_tag.find_parent('a')
            if parent_link and parent_link.get('href'):
                law_name = bold_tag.get_text(strip=True)
                law_url = parent_link.get('href')
                
                if law_name and law_url and len(law_name) > 5:
                    # Clean up the law name
                    law_name = law_name.replace('\n', ' ').replace('\r', ' ').strip()
                    
                    # Create full URL if relative
                    if not law_url.startswith('http'):
                        if not law_url.startswith('/'):
                            law_url = '/' + law_url
                        law_url = f"https://www.paragraf.rs{law_url}"
                    
                    # Store with URL
                    law_links[law_name] = law_url
                    laws.append(law_name)
        
        # Also try finding links that look like law links
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link.get('href')
            
            # Check if it looks like a law link
            if ('zakon' in text.lower() or 
                'uredba' in text.lower() or 
                'pravilnik' in text.lower() or
                'odluka' in text.lower() or
                'kodeks' in text.lower() or
                'ustav' in text.lower() or
                'protokol' in text.lower() or
                'konvencija' in text.lower()) and len(text) > 10:
                
                if text not in law_links:
                    if href.startswith('http'):
                        full_url = href
                    else:
                        if not href.startswith('/'):
                            href = '/' + href
                        full_url = f"https://www.paragraf.rs{href}"
                    law_links[text] = full_url
                    laws.append(text)
        
        # Remove duplicates while preserving order
        laws = list(dict.fromkeys(laws))
        
        logger.info(f"Found {len(laws)} laws on paragraf.rs")
        
        # Save to file
        output = {
            'total_laws': len(laws),
            'source': BASE_URL,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'laws': laws,
            'law_urls': law_links
        }
        
        with open('paragraf_rs_laws.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info("Saved results to 'paragraf_rs_laws.json'")
        
        # Print sample
        logger.info("\n=== SAMPLE OF LAWS FROM PARAGRAF.RS ===")
        for i, law in enumerate(laws[:20], 1):
            logger.info(f"{i}. {law}")
        
        return laws, law_links
        
    except Exception as e:
        logger.error(f"Error scraping paragraf.rs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], {}


if __name__ == "__main__":
    scrape_paragraf_laws()

