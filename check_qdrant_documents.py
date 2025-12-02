"""Script to check what documents are stored in Qdrant related to ZJN."""

import os
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient
from loguru import logger

from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())


def check_zjn_documents():
    """Check what ZJN-related documents are in Qdrant."""
    try:
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        
        if not client.collection_exists(collection_name=KOMPLETNO_PRAVO_COLLECTION):
            logger.error(f"Collection {KOMPLETNO_PRAVO_COLLECTION} does not exist")
            return
        
        # Get collection info
        collection_info = client.get_collection(KOMPLETNO_PRAVO_COLLECTION)
        logger.info(f"Collection {KOMPLETNO_PRAVO_COLLECTION} has {collection_info.points_count} points")
        
        # Search for ZJN-related documents
        zjn_keywords = [
            'zakon_o_javnim_nabavkama',
            'javne nabavke',
            'javnim nabavkama',
            'zjn',
            'pravilnik',
            'uredba',
            'ministar finansija',
            'kancelarija',
            'vlada'
        ]
        
        # Scroll through collection to find ZJN documents
        found_docs = {}
        offset = None
        max_scrolls = 50  # Check up to 5000 points
        
        for scroll_num in range(max_scrolls):
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
                law_name = payload.get('law_name', '')
                title = payload.get('title', '')
                source = payload.get('source_collection', '')
                doc_type = payload.get('document_type', '')
                
                # Check if it's ZJN related
                text_to_check = f"{law_name} {title} {source} {doc_type}".lower()
                
                if any(keyword in text_to_check for keyword in zjn_keywords):
                    doc_key = f"{title} ({doc_type})"
                    if doc_key not in found_docs:
                        found_docs[doc_key] = {
                            'title': title,
                            'type': doc_type,
                            'law_name': law_name,
                            'source': source,
                            'count': 0
                        }
                    found_docs[doc_key]['count'] += 1
            
            if not next_page:
                break
            offset = next_page
        
        logger.info(f"\nFound {len(found_docs)} unique ZJN-related documents:")
        for doc_key, doc_info in sorted(found_docs.items()):
            logger.info(f"  - {doc_info['title']}")
            logger.info(f"    Type: {doc_info['type']}, Law: {doc_info['law_name']}, Chunks: {doc_info['count']}")
        
        return found_docs
        
    except Exception as e:
        logger.error(f"Error checking documents: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    check_zjn_documents()


