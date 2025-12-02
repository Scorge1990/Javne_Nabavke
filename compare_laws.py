"""Script to compare laws from paragraf.rs with existing laws in Qdrant."""

import json
import re
from loguru import logger
from difflib import SequenceMatcher


def normalize_law_name(name):
    """Normalize law name for comparison."""
    # Convert to lowercase
    name = name.lower()
    # Remove special characters and extra spaces
    name = re.sub(r'[^\w\s]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name


def similar(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()


def compare_laws():
    """Compare laws from paragraf.rs with existing laws in Qdrant."""
    try:
        # Load existing laws from Qdrant
        with open('existing_laws_in_qdrant.json', 'r', encoding='utf-8') as f:
            qdrant_data = json.load(f)
            existing_laws = qdrant_data['unique_law_names']
        
        # Load laws from paragraf.rs
        with open('paragraf_rs_laws.json', 'r', encoding='utf-8') as f:
            paragraf_data = json.load(f)
            paragraf_laws = paragraf_data['laws']
            paragraf_urls = paragraf_data['law_urls']
        
        logger.info(f"Existing laws in Qdrant: {len(existing_laws)}")
        logger.info(f"Laws on paragraf.rs: {len(paragraf_laws)}")
        
        # Normalize names for comparison
        normalized_existing = {normalize_law_name(law): law for law in existing_laws}
        normalized_paragraf = {normalize_law_name(law): law for law in paragraf_laws}
        
        # Find missing laws
        missing_normalized = set(normalized_paragraf.keys()) - set(normalized_existing.keys())
        
        # Simple comparison without fuzzy matching for speed
        truly_missing = []
        
        for missing_norm in missing_normalized:
            original_name = normalized_paragraf[missing_norm]
            truly_missing.append({
                'name': original_name,
                'normalized': missing_norm,
                'url': paragraf_urls.get(original_name, 'N/A')
            })
        
        possibly_exist = []
        
        logger.info(f"\nTruly missing laws: {len(truly_missing)}")
        logger.info(f"Possibly existing (similar): {len(possibly_exist)}")
        
        # Save results
        comparison_result = {
            'summary': {
                'qdrant_laws': len(existing_laws),
                'paragraf_laws': len(paragraf_laws),
                'truly_missing': len(truly_missing),
                'possibly_existing': len(possibly_exist),
                'coverage_percentage': round((len(existing_laws) / len(paragraf_laws)) * 100, 2)
            },
            'missing_laws': truly_missing,
            'possibly_existing_laws': possibly_exist
        }
        
        with open('law_comparison.json', 'w', encoding='utf-8') as f:
            json.dump(comparison_result, f, ensure_ascii=False, indent=2)
        
        logger.info("\nSaved comparison results to 'law_comparison.json'")
        
        # Show sample of missing laws
        logger.info("\n=== SAMPLE OF MISSING LAWS ===")
        for i, law in enumerate(truly_missing[:30], 1):
            logger.info(f"{i}. {law['name']}")
        
        if truly_missing:
            logger.info(f"\n... and {len(truly_missing) - 30} more missing laws")
        
        return truly_missing, possibly_exist
        
    except Exception as e:
        logger.error(f"Error comparing laws: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return [], []


if __name__ == "__main__":
    compare_laws()

