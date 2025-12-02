"""Script to fix malformed URLs in law_comparison.json."""

import json
from loguru import logger

def fix_urls_in_comparison():
    """Fix malformed URLs in law_comparison.json."""
    logger.info("Loading law_comparison.json...")
    
    with open('law_comparison.json', 'r', encoding='utf-8') as f:
        comparison = json.load(f)
    
    missing_laws = comparison.get('missing_laws', [])
    fixed_count = 0
    
    logger.info(f"Found {len(missing_laws)} missing laws to check")
    
    for law in missing_laws:
        url = law.get('url', '')
        if not url or url == 'N/A':
            continue
            
        # Fix malformed URLs
        if 'www.paragraf.rspropisi' in url:
            # Fix the malformed URL
            fixed_url = url.replace('www.paragraf.rspropisi', 'www.paragraf.rs/propisi')
            law['url'] = fixed_url
            fixed_count += 1
        elif url.startswith('www.paragraf.rs') and not url.startswith('http'):
            # Ensure https:// prefix
            fixed_url = 'https://' + url
            law['url'] = fixed_url
            fixed_count += 1
        elif not url.startswith('http'):
            # If it's a relative path, make it absolute
            if url.startswith('/'):
                fixed_url = 'https://www.paragraf.rs' + url
            else:
                fixed_url = 'https://www.paragraf.rs/propisi/' + url
            law['url'] = fixed_url
            fixed_count += 1
    
    logger.info(f"Fixed {fixed_count} malformed URLs")
    
    # Save the fixed comparison
    logger.info("Saving fixed law_comparison.json...")
    with open('law_comparison.json', 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    
    logger.info("✓ Successfully fixed URLs in law_comparison.json")
    
    # Show some examples
    logger.info("\n=== SAMPLE OF FIXED URLS ===")
    for i, law in enumerate(missing_laws[:5], 1):
        if 'www.paragraf.rs/propisi' in law.get('url', ''):
            logger.info(f"{i}. {law['name'][:60]}...")
            logger.info(f"   URL: {law['url']}")

if __name__ == "__main__":
    fix_urls_in_comparison()

