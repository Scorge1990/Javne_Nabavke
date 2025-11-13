import argparse
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from qdrant_client import QdrantClient


def main(limit: int = 5) -> None:
    load_dotenv(find_dotenv())

    embeddings_dir = Path("database/embeddings")

    client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=60,
    )

    collections = {c.name for c in client.get_collections().collections}

    unuploaded = []
    for emb_file in sorted(embeddings_dir.glob("*.jsonl")):
        collection_name = emb_file.stem.replace("-", "_")
        if collection_name not in collections:
            unuploaded.append((collection_name, emb_file))
            if len(unuploaded) >= limit:
                break

    print(f"Found {len(unuploaded)} unuploaded (showing up to {limit}):")
    for name, path in unuploaded:
        print(f"{name} -> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List unuploaded embedding files.")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of unuploaded embeddings to show.",
    )
    args = parser.parse_args()
    main(limit=args.limit)

