import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import tiktoken
from dotenv import find_dotenv, load_dotenv
from langfuse import observe
from langfuse.openai import openai
from loguru import logger
from openai.types import CreateEmbeddingResponse
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    UpdateResult,
    VectorParams,
)
from tqdm.auto import tqdm


SRPSKO_PRAVO_COLLECTION = "srpsko_pravo"


def create_collection(
    client: QdrantClient,
    name: str,
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE,
    timeout: int = 180,
) -> bool:
    """Create a collection in Qdrant."""
    logger.info(f'Creating collection: "{name}" with vector size: {vector_size}.')
    return client.recreate_collection(
        collection_name=name,
        vectors_config=VectorParams(size=vector_size, distance=distance),
        timeout=timeout,
    )


def delete_collection(
    client: QdrantClient, collection: str, timeout: int = None
) -> bool:
    logger.info(f'Deleting collection: "{collection}".')
    return client.delete_collection(collection_name=collection, timeout=timeout)


def get_collection_info(client: QdrantClient, collection: str) -> Dict:
    return client.get_collection(collection_name=collection)


def get_count(client: QdrantClient, collection: str) -> int:
    return client.count(collection_name=collection).count


def upsert(
    client: QdrantClient,
    collection: str,
    points: List[PointStruct],
    batch_size: int = 100,
) -> UpdateResult:
    """Upsert data points into a Qdrant collection in batches."""
    if len(points) <= batch_size:
        try:
            return client.upsert(collection_name=collection, points=points)
        except Exception as e:
            logger.error(f"Error upserting to {collection}: {e}")
            raise
    
    # Process in batches to avoid timeouts
    logger.info(f"Uploading {len(points)} points in batches of {batch_size}")
    result = None
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(points) + batch_size - 1) // batch_size
        logger.info(f"Uploading batch {batch_num}/{total_batches}")
        try:
            result = client.upsert(collection_name=collection, points=batch)
        except Exception as e:
            logger.error(f"Error uploading batch {batch_num}/{total_batches} to {collection}: {e}")
            raise
    
    # Return the result from the last batch
    return result


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.info("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens


def search(
    client: QdrantClient,
    collection: str,
    query_vector: Union[list, tuple, np.ndarray],
    limit: int = 10,
    query_filter: Filter = None,
    with_vectors: bool = False,
    score_threshold: float = 0.0,
) -> List:
    """Search with optional score threshold for better filtering."""
    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=limit,
        with_vectors=with_vectors,
        query_filter=query_filter,
        score_threshold=score_threshold,
    ).points
    return results


@observe()
def embed_text(text: Union[str, list], model: str) -> CreateEmbeddingResponse:
    """
    Create embeddings using OpenAI API.
    """
    response = openai.embeddings.create(input=text, model=model)
    return response


def format_context(payload: dict) -> str:
    text = f"Naslov: {payload['title']}\n"
    text += f"Link do člana: {payload['link']}\n"
    text += f"{payload['text']}\n\n"
    return text


def get_context(search_results: List[ScoredPoint], top_k: int = None) -> str:
    if top_k is not None:
        search_results = sorted(search_results, key=lambda x: x.score, reverse=True)[
            :top_k
        ]
    return "\n".join([format_context(point.payload) for point in search_results])


def load_json(path: Path) -> List[Dict]:
    """
    Load JSON data from a file. Handles split files by checking for manifest files
    and merging chunks if necessary.

    Args:
        path (Path): The path to the JSON file.

    Returns:
        List[Dict]: The JSON data loaded from the file (merged if split).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    # Check if file exists directly
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data
    
    # Check if file has been split (manifest file exists)
    manifest_path = path.parent / f"{path.stem}_manifest.json"
    if manifest_path.exists():
        logger.info(f"Loading split file: {path.name} via manifest")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        # Load and merge all chunks
        merged_data = []
        for chunk_filename in manifest["chunks"]:
            chunk_path = path.parent / chunk_filename
            if chunk_path.exists():
                with open(chunk_path, "r", encoding="utf-8") as f:
                    chunk_data = json.load(f)
                    merged_data.extend(chunk_data)
            else:
                logger.warning(f"Chunk file not found: {chunk_path}")
        
        logger.info(f"Loaded {len(merged_data)} items from {len(manifest['chunks'])} chunks")
        return merged_data
    
    # File doesn't exist and no manifest found
    logger.error(f"File: {path} does not exist and no manifest found.")
    raise FileNotFoundError(f"File: {path} does not exist.")


def prepare_for_embedding(
    output_path: Path,
    scraped_data: List[Dict],
    model: str,
    law_id: str,
    law_title: str,
) -> None:
    """
    Prepare data for embedding and save to a file.

    Args:
        output_path (Path): The path to save the prepared data.
        scraped_data (List[Dict]): The scraped data to be prepared.
        model (str): The embedding model to be used.

    Returns:
        None
    """
    jobs = [
        {
            "model": model,
            "id": id,
            "title": sample["title"],
            "link": sample["link"],
            "input": f"{sample['title']}: {' '.join(sample['texts'])}",
            "law_id": law_id,
            "law": law_title,
        }
        for id, sample in enumerate(scraped_data)
    ]
    with open(output_path, "w", encoding="utf-8") as file:
        for job in jobs:
            json_string = json.dumps(job)
            file.write(json_string + "\n")


def get_token_num(text: str, model_name: str) -> int:
    """
    Get the number of tokens in a text for a given model.

    Args:
        text (str): The input text.
        model_name (str): The name of the model.

    Returns:
        int: The number of tokens in the text.
    """
    enc = tiktoken.encoding_for_model(model_name)
    return len(enc.encode(text))


def run_api_request_processor(
    requests_filepath: Path,
    save_path: Path,
    max_requests_per_minute: int = 2500,
    max_tokens_per_minute: int = 900000,
    token_encoding_name: str = "cl100k_base",
    max_attempts: int = 5,
    logging_level: int = 20,
) -> None:
    """
    Run the API request processor to call the OpenAI API in parallel, creating embeddings with the specified model.

    Args:
        requests_filepath (Path): The path to the requests file.
        save_path (Path): The path to save the results.
        max_requests_per_minute (int): Maximum number of requests per minute.
        max_tokens_per_minute (int): Maximum number of tokens per minute.
        token_encoding_name (str): The name of the token encoding.
        max_attempts (int): Maximum number of attempts for each request.
        logging_level (int): Logging level.

    Returns:
        None
    """
    # Load environment variables from .env file
    load_dotenv(find_dotenv())
    
    if not requests_filepath.exists():
        logger.error(f"File {requests_filepath} does not exist.")
        raise FileNotFoundError(f"File {requests_filepath} does not exist.")
    if save_path.suffix != ".jsonl":
        logger.error(f"Save path {save_path} must be JSONL.")
        raise ValueError(f"Save path {save_path} must be JSONL.")

    command = [
        "python",
        "database/api_request_parallel_processor.py",
        "--requests_filepath",
        requests_filepath,
        "--save_filepath",
        save_path,
        "--request_url",
        "https://api.openai.com/v1/embeddings",
        "--max_requests_per_minute",
        str(max_requests_per_minute),
        "--max_tokens_per_minute",
        str(max_tokens_per_minute),
        "--token_encoding_name",
        token_encoding_name,
        "--max_attempts",
        str(max_attempts),
        "--logging_level",
        str(logging_level),
    ]
    result = subprocess.run(command, text=True, capture_output=True)

    if result.returncode == 0:
        logger.info(f"Embeddings saved to: {save_path}")
    else:
        logger.error("Error in Embedding execution!")
        logger.error("Error:", result.stderr)


# Eliminate this or make it more general
def validate_path(path: Path) -> None:
    if not isinstance(path, Path):
        logger.error(f'"{path}" must be a valid Path object')
        raise ValueError(f'"{path}" must be a valid Path object')
    path.mkdir(parents=True, exist_ok=True)


def create_embeddings(
    scraped_dir: Path, to_process_dir: Path, embeddings_dir: Path, model: str
) -> None:
    """
    Embed scraped law files by preparing the data and running the request processor
    to call the OpenAI API in parallel, creating embeddings with the specified model.

    Args:
        scraped_dir (Path): Directory to the law files.
        to_process_dir (Path): Directory to process files.
        embeddings_dir (Path): Directory for storing embeddings.
        model (str): The embedding model to be used.

     Raises:
        ValueError: If any of the provided paths are invalid.
    """
    # Validate input paths
    validate_path(scraped_dir)
    validate_path(to_process_dir)
    validate_path(embeddings_dir)

    scraped_paths = [p for p in scraped_dir.iterdir() if p.is_file() and p.suffix == ".json"]

    for file_path in tqdm(
        scraped_paths, desc="Embedding scraped files", total=len(scraped_paths)
    ):
        scraped_data = load_json(path=file_path)

        law_id = file_path.stem
        law_title = law_id.replace("_", " ")

        # Handle Windows path length limitation (max 260 chars)
        # Use hash for very long filenames to avoid path length issues
        import hashlib
        max_path_length = 200  # Conservative limit for Windows
        stem = law_id
        full_path = to_process_dir / (stem + ".jsonl")
        
        if len(str(full_path)) > max_path_length:
            # Use hash of original filename to create shorter unique name
            stem_hash = hashlib.md5(stem.encode('utf-8')).hexdigest()[:16]
            stem = f"{stem[:50]}_{stem_hash}" if len(stem) > 50 else f"{stem}_{stem_hash}"
            # Ensure final path is short enough
            if len(str(to_process_dir / (stem + ".jsonl"))) > max_path_length:
                stem = stem_hash  # Use just hash if still too long
        
        requests_filepath = to_process_dir / (stem + ".jsonl")
        
        # Ensure parent directory exists
        requests_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        prepare_for_embedding(
            output_path=requests_filepath,
            scraped_data=scraped_data,
            model=model,
            law_id=law_id,
            law_title=law_title,
        )

        # Use same stem logic for embeddings file (use hash if needed)
        import hashlib
        original_stem = file_path.stem
        full_emb_path = embeddings_dir / (original_stem + ".jsonl")
        
        if len(str(full_emb_path)) > max_path_length:
            # Use same hash approach
            stem_hash = hashlib.md5(original_stem.encode('utf-8')).hexdigest()[:16]
            original_stem = f"{original_stem[:50]}_{stem_hash}" if len(original_stem) > 50 else f"{original_stem}_{stem_hash}"
            if len(str(embeddings_dir / (original_stem + ".jsonl"))) > max_path_length:
                original_stem = stem_hash
        
        processed_filepath = embeddings_dir / (original_stem + ".jsonl")
        
        # Ensure parent directory exists
        processed_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing embeddings file if it exists to prevent duplicates
        if processed_filepath.exists():
            logger.info(f"Removing existing embeddings file: {processed_filepath}")
            processed_filepath.unlink()
        
        run_api_request_processor(
            requests_filepath=requests_filepath, save_path=processed_filepath
        )


def _build_point_id(law_name: Optional[str], request_id: Union[int, str]) -> str:
    prefix = law_name if law_name else "law"
    return f"{prefix}_{request_id}"


def load_and_process_embeddings(path: Path, law_name: Optional[str] = None) -> List[PointStruct]:
    """
    Load embeddings from a JSON lines file and process them into data points.

    Args:
        path (Path): The path to the JSON lines file containing embeddings.

    Returns:
        List[PointStruct]: A list of PointStruct objects containing the processed data.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
        json.JSONDecodeError: If there is an error parsing the JSON.
    """
    if not path.exists():
        logger.error(f"File: {path} does not exist.")
        raise FileNotFoundError(f"File: {path} does not exist.")

    try:
        with open(path, "r", encoding="utf-8") as file:
            embedding_data = [json.loads(line) for line in file]
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error reading or parsing file: {e}")
        raise

    points: List[PointStruct] = []
    for item in embedding_data:
        try:
            # Handle the new format: [request_data, response_data]
            if isinstance(item, list) and len(item) >= 2:
                request_data = item[0]
                response_data = item[1]
                
                # Extract embedding vector
                if "data" in response_data and len(response_data["data"]) > 0:
                    embedding_vector = response_data["data"][0]["embedding"]
                else:
                    logger.error(f"No embedding data found in response: {response_data}")
                    continue
            else:
                # Handle old format (fallback)
                embedding_vector = item[1]["data"][0]["embedding"]
                request_data = item[0]

            request_id = request_data.get("id")

            law_id = request_data.get("law_id") or law_name or path.stem.replace("-", "_")
            law_title = request_data.get("law") or (law_id.replace("_", " ") if law_id else None)

            point_id = _build_point_id(
                law_id,
                request_id if request_id is not None else len(points),
            )

            payload = {
                "title": request_data["title"],
                "text": request_data["input"],
                "link": request_data["link"],
            }
            if law_id:
                payload["law_name"] = law_id
                payload["source_collection"] = law_id
            else:
                payload["source_collection"] = path.stem.replace("-", "_")
            if law_title:
                payload["law"] = law_title
            if request_id is not None:
                payload["original_id"] = request_id

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding_vector,
                    payload=payload,
                )
            )
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error processing embedding data: {e}")
            continue
    return points
