import argparse
import json
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from tqdm.auto import tqdm

from database.utils import (
    SRPSKO_PRAVO_COLLECTION,
    create_embeddings,
    load_and_process_embeddings,
    upsert,
)

VECTOR_SIZE = 1536


def main(args: argparse.Namespace) -> None:
    """Main function to create embeddings and vector database."""
    # Load environment variables from .env file
    load_dotenv(find_dotenv())
    
    logger.info("Creating embeddings.")
    create_embeddings(
        scraped_dir=args.scraped_dir,
        to_process_dir=args.to_process_dir,
        embeddings_dir=args.embeddings_dir,
        model=args.model,
    )

    logger.info("Creating vector database.")
    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=180,
    )
    if not qdrant_client.collection_exists(collection_name=SRPSKO_PRAVO_COLLECTION):
        logger.info(f'Creating target collection "{SRPSKO_PRAVO_COLLECTION}".')
        qdrant_client.create_collection(
            collection_name=SRPSKO_PRAVO_COLLECTION,
            vectors_config=rest.VectorParams(size=VECTOR_SIZE, distance=rest.Distance.COSINE),
        )
    # Get list of scraped files to match with embeddings
    scraped_files = {f.stem for f in args.scraped_dir.iterdir() if f.is_file() and f.suffix == ".json"}
    
    data_paths = list(args.embeddings_dir.iterdir())
    for path in tqdm(data_paths, total=len(data_paths), desc="Creating collections"):
        # Only process embeddings for files we scraped
        if path.stem not in scraped_files:
            continue
            
        # Check if this is necessary
        law_name = path.stem.replace("-", "_")
        points = load_and_process_embeddings(path=path, law_name=law_name)
        
        # Skip if no points (embedding failed)
        if not points:
            logger.warning(f"Skipping {law_name} - no valid embeddings")
            continue
        
        # Skip if law already exists (based on source_collection payload)
        try:
            existing, _ = qdrant_client.scroll(
                collection_name=SRPSKO_PRAVO_COLLECTION,
                limit=1,
                with_payload=False,
                with_vectors=False,
                filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="source_collection",
                            match=rest.MatchValue(value=law_name),
                        )
                    ]
                ),
            )
            if existing:
                logger.info(
                    f'Law "{law_name}" already present in {SRPSKO_PRAVO_COLLECTION}. Skipping.'
                )
                continue
        except Exception as exc:
            logger.warning(f"Could not verify existing records for {law_name}: {exc}")

        upsert(
            client=qdrant_client,
            collection=SRPSKO_PRAVO_COLLECTION,
            points=points,
            batch_size=50,
        )

        logger.info(
            f'Upserted {len(points)} points for "{law_name}" into {SRPSKO_PRAVO_COLLECTION}.'
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create embeddings and vector database for scraped files."
    )
    parser.add_argument(
        "--scraped_dir", type=Path, help="Directory to the scraped files."
    )
    parser.add_argument(
        "--to_process_dir",
        type=Path,
        default=Path("./database/to_process"),
        help="Directory to process files.",
    )
    parser.add_argument(
        "--embeddings_dir",
        type=Path,
        default=Path("./database/embeddings"),
        help="Directory for storing embeddings.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="The embedding model to be used. If not set, it will be loaded from the config file.",
    )

    args = parser.parse_args()

    # Load model from config file if not explicitly set
    if args.model is None:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            args.model = config["openai"]["embeddings"]["model"]

    main(args=args)
