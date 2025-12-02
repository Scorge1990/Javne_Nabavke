from typing import List

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Record

from constants import KOMPLETNO_PRAVO_COLLECTION
from database.utils import SRPSKO_PRAVO_COLLECTION, get_context, search
from llm.prompts import DEFAULT_CONTEXT
from router.router_prompt import DEFAULT_ROUTER_RESPONSE
from router_mapping import map_router_to_collection


# Simple wrapper class to convert Record objects to objects with score and payload
# for use with get_context function
class SimpleScoredPoint:
    """Simple wrapper to convert Record to object with score and payload attributes."""
    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload


def determine_context(
    collections: List[str], embedding: List[float], qdrant_client: QdrantClient, original_query: str = None
) -> str:
    """Determines the context for generating responses based on search results from collections."""
    try:
        # Try Kompletno_pravo first, fallback to srpsko_pravo
        target_collection = None
        if qdrant_client.collection_exists(collection_name=KOMPLETNO_PRAVO_COLLECTION):
            target_collection = KOMPLETNO_PRAVO_COLLECTION
            logger.info(f"Using collection: {KOMPLETNO_PRAVO_COLLECTION}")
        elif qdrant_client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
            target_collection = SRPSKO_PRAVO_COLLECTION
            logger.info(f"Using collection: {SRPSKO_PRAVO_COLLECTION}")
        else:
            logger.error(
                f'Neither "{KOMPLETNO_PRAVO_COLLECTION}" nor "{SRPSKO_PRAVO_COLLECTION}" collection exists in Qdrant.'
            )
            return DEFAULT_CONTEXT

        search_results: List = []
        for router_name in collections:
            law_name = map_router_to_collection(router_name)
            if law_name in {DEFAULT_ROUTER_RESPONSE, "nema_zakona"}:
                # If router says "no law", do a general search without filter
                # This allows finding relevant content even if router doesn't identify specific law
                logger.info(f"Router returned '{router_name}', performing general search without filter")
                
                # First, try to find by law name if query looks like a law name
                logger.info(f"Checking direct lookup - original_query is: {original_query is not None}, value: '{original_query}'")
                if original_query:
                    query_normalized = original_query.lower().strip().replace(" ", "_").replace("-", "_")
                    logger.info(f"Original query: '{original_query}', normalized: '{query_normalized}'")
                    # Check if query looks like a law name (contains underscores or matches law naming pattern)
                    has_underscore = "_" in query_normalized
                    is_long = len(query_normalized) > 10
                    logger.info(f"Law name check - has_underscore: {has_underscore}, is_long: {is_long}, will attempt lookup: {has_underscore or is_long}")
                    if "_" in query_normalized or len(query_normalized) > 10:
                        logger.info(f"Query looks like a law name, attempting direct lookup: {query_normalized}")
                        try:
                            # Try scrolling to find law by name - use larger batches for efficiency
                            matching_points = []
                            offset = None
                            max_scrolls = 20  # Scroll through up to 2000 points (20 * 100) to find the law
                            found_law = False
                            
                            for scroll_num in range(max_scrolls):
                                scroll_results, next_page = qdrant_client.scroll(
                                    collection_name=target_collection,
                                    limit=100,
                                    offset=offset,
                                    with_payload=True,
                                    with_vectors=False,
                                )
                                
                                if not scroll_results:
                                    break
                                
                                # Filter results by law_name or source_collection matching the query
                                for point in scroll_results:
                                    payload = point.payload or {}
                                    law_name_in_payload = payload.get("law_name", "").lower().replace(" ", "_").replace("-", "_")
                                    source_collection = payload.get("source_collection", "").lower().replace(" ", "_").replace("-", "_")
                                    
                                    # Check if query matches law name or source collection (exact or partial match)
                                    # Also check for key words to handle variations like "zakonu" vs "zakon"
                                    query_keywords = set(query_normalized.split("_"))
                                    law_keywords = set(law_name_in_payload.split("_"))
                                    source_keywords = set(source_collection.split("_"))
                                    
                                    # Match if: exact match, substring match, or significant keyword overlap
                                    keyword_overlap = len(query_keywords.intersection(law_keywords)) >= 2 or len(query_keywords.intersection(source_keywords)) >= 2
                                    
                                    if (query_normalized == law_name_in_payload or 
                                        query_normalized == source_collection or
                                        query_normalized in law_name_in_payload or 
                                        query_normalized in source_collection or
                                        law_name_in_payload in query_normalized or
                                        source_collection in query_normalized or
                                        keyword_overlap):
                                        matching_points.append(point)
                                        found_law = True
                                        if len(matching_points) >= 20:  # Limit to 20 results
                                            break
                                
                                if len(matching_points) >= 20 or not next_page:
                                    break
                                
                                offset = next_page
                                
                                # If we found the law, we can stop early
                                if found_law and len(matching_points) >= 5:
                                    logger.info(f"Found law early, stopping scroll at batch {scroll_num + 1}")
                                    break
                            
                            if matching_points:
                                logger.info(f"Found {len(matching_points)} points by direct law name lookup for '{query_normalized}'")
                                # Convert Record objects to objects with score and payload attributes
                                scored_points = []
                                for point in matching_points:
                                    if isinstance(point, Record):
                                        payload = point.payload or {}
                                        # Ensure required fields exist
                                        if not all(key in payload for key in ['title', 'link', 'text']):
                                            logger.debug(f"Skipping point {point.id} - missing required payload fields")
                                            continue
                                        scored_point = SimpleScoredPoint(
                                            point_id=point.id,
                                            score=1.0,
                                            payload=payload
                                        )
                                        scored_points.append(scored_point)
                                    else:
                                        scored_points.append(point)
                                if scored_points:
                                    search_results.extend(scored_points)
                                    logger.info(f"Added {len(scored_points)} points to search results")
                                    continue  # Skip semantic search if we found by name
                            else:
                                logger.debug(f"No points found by direct law name lookup for '{query_normalized}'")
                        except Exception as exc:
                            logger.debug(f"Direct law name lookup failed: {exc}")
                            # Continue to semantic search
                
                # Fallback to semantic search
                try:
                    # Increase limit for general search to find more relevant content
                    # Use a higher limit to ensure we find relevant laws even if they're not top matches
                    results = search(
                        client=qdrant_client,
                        collection=target_collection,
                        query_vector=embedding,
                        limit=50,  # Increased to 50 to find more relevant laws
                        with_vectors=True,
                        query_filter=None,  # No filter - search entire collection
                        score_threshold=0.0,  # No threshold - get all results ranked by similarity
                    )
                    if results:
                        logger.info(
                            f"Found {len(results)} results from general search "
                            f'in collection "{target_collection}".'
                        )
                        # Log sample results for debugging
                        if results:
                            sample_law = results[0].payload.get("law_name", "unknown")
                            logger.debug(f"Sample result from general search: {sample_law}")
                    search_results.extend(results)
                except Exception as exc:
                    logger.error(
                        f"Error in general search in "
                        f'collection "{target_collection}": {exc}'
                    )
                continue

            search_limit = 20 if law_name == "pravne_konsultacije" else 10
            try:
                # Note: Filtering by law_name requires an index which may not exist
                # So we search without filter and rely on semantic similarity
                # The results will be ranked by relevance to the query
                results = search(
                    client=qdrant_client,
                    collection=target_collection,
                    query_vector=embedding,
                    limit=search_limit,
                    with_vectors=True,
                    query_filter=None,  # No filter - search entire collection for best results
                )
                if results:
                    logger.info(
                        f"Found {len(results)} results for {law_name} "
                        f'in collection "{target_collection}".'
                    )
                search_results.extend(results)
            except Exception as exc:
                logger.error(
                    f"Error searching law {law_name} in "
                    f'collection "{target_collection}": {exc}'
                )
                continue

        if not search_results:
            logger.warning(
                "No relevant vectors retrieved for routed laws. "
                "Attempting broader search with higher limit..."
            )
            try:
                broader_results = search(
                    client=qdrant_client,
                    collection=target_collection,
                    query_vector=embedding,
                    limit=50,
                    with_vectors=True,
                    query_filter=None,
                    score_threshold=0.0,
                )
                if broader_results:
                    logger.info(f"Found {len(broader_results)} results from broader search")
                    search_results.extend(broader_results)
            except Exception as exc:
                logger.error(f"Error in broader search: {exc}")
            
            if not search_results:
                logger.warning("Still no results found. Falling back to default context.")
                return DEFAULT_CONTEXT

        top_k = 20 if len(collections) > 1 else 15
        logger.info(f"Generating context from {len(search_results)} search results (top_k={top_k})")
        try:
            context = get_context(search_results=search_results, top_k=top_k)
            logger.info(f"Generated context length: {len(context)} characters")
            return context
        except Exception as exc:
            logger.error(f"Error in get_context: {exc}")
            return DEFAULT_CONTEXT
    except Exception as e:
        logger.error(f"Error determining context: {str(e)}")
        return DEFAULT_CONTEXT  # Fallback to default context

