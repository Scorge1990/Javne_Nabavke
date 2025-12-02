"""Script to list all unique laws currently in the Qdrant database."""

import os
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from loguru import logger
import json

from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())


def list_all_laws():
    """List all unique laws in the Qdrant database."""
    try:
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        
        if not client.collection_exists(collection_name=KOMPLETNO_PRAVO_COLLECTION):
            logger.error(f"Collection {KOMPLETNO_PRAVO_COLLECTION} does not exist")
            return []
        
        # Get collection info
        collection_info = client.get_collection(KOMPLETNO_PRAVO_COLLECTION)
        logger.info(f"Collection {KOMPLETNO_PRAVO_COLLECTION} has {collection_info.points_count} points")
        
        # Scroll through collection to find all unique law names
        unique_laws = set()
        unique_titles = set()
        offset = None
        
        logger.info("Scrolling through database to find all unique laws...")
        
        while True:
            scroll_results, next_page = client.scroll(
                collection_name=KOMPLETNO_PRAVO_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            
            if not scroll_results:
                break
            
            for point in scroll_results:
                payload = point.payload or {}
                law_name = payload.get('law_name', '').strip()
                title = payload.get('title', '').strip()
                
                if law_name:
                    unique_laws.add(law_name)
                if title:
                    unique_titles.add(title)
            
            if not next_page:
                break
            offset = next_page
        
        logger.info(f"\nFound {len(unique_laws)} unique law names in database")
        logger.info(f"Found {len(unique_titles)} unique titles in database")
        
        # Sort and display
        sorted_laws = sorted(unique_laws)
        sorted_titles = sorted(unique_titles)
        
        # Save to file for easy comparison
        output = {
            'total_points': collection_info.points_count,
            'unique_law_names': sorted_laws,
            'unique_titles': sorted_titles,
            'law_count': len(sorted_laws),
            'title_count': len(sorted_titles)
        }
        
        with open('existing_laws_in_qdrant.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info("\nSaved results to 'existing_laws_in_qdrant.json'")
        
        logger.info("\n=== UNIQUE LAW NAMES IN DATABASE ===")
        for law in sorted_laws:
            logger.info(f"  - {law}")
        
        return sorted_laws
        
    except Exception as e:
        logger.error(f"Error listing laws: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


if __name__ == "__main__":
    list_all_laws()

