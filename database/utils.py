from typing import List, Union

import numpy as np
from langfuse import observe
from langfuse.openai import openai
from openai.types import CreateEmbeddingResponse
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, ScoredPoint


SRPSKO_PRAVO_COLLECTION = "srpsko_pravo"


def search(
    client: QdrantClient,
    collection: str,
    query_vector: Union[list, tuple, np.ndarray],
    limit: int = 10,
    query_filter: Filter = None,
    with_vectors: bool = False,
    score_threshold: float = 0.0,
) -> List:
    """Search Qdrant collection with optional score threshold."""
    return client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_vectors=with_vectors,
        query_filter=query_filter,
        score_threshold=score_threshold,
    ).points


@observe()
def embed_text(text: Union[str, list], model: str) -> CreateEmbeddingResponse:
    """Create embeddings using OpenAI API."""
    return openai.embeddings.create(input=text, model=model)


def format_context(payload: dict) -> str:
    """Format payload data for context."""
    title = payload.get('title', 'N/A')
    link = payload.get('link', 'N/A')
    text = payload.get('text', 'N/A')
    return f"Naslov: {title}\nLink do člana: {link}\n{text}\n\n"


def get_context(search_results: List[ScoredPoint], top_k: int = None) -> str:
    """Format search results into context string."""
    if top_k is not None:
        search_results = sorted(search_results, key=lambda x: x.score, reverse=True)[:top_k]
    return "\n".join([format_context(point.payload) for point in search_results])
