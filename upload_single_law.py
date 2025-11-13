import argparse
import os
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from database.utils import SRPSKO_PRAVO_COLLECTION, load_and_process_embeddings


def chunk_points(points, batch_size):
    for i in range(0, len(points), batch_size):
        yield points[i : i + batch_size]


def ensure_collection(
    client: QdrantClient, collection_name: str, vector_size: int = 1536
) -> None:
    if client.collection_exists(collection_name=collection_name):
        return
    logger.info(f'Creating new collection "{collection_name}"')
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a single law embedding file to Qdrant.")
    parser.add_argument("embedding_file", type=Path, help="Path to the embedding JSONL file.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of points per upsert batch.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between batches.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for Qdrant to finish writing each batch before returning.",
    )
    parser.add_argument(
        "--verify-retries",
        type=int,
        default=10,
        help="Number of verification attempts when wait is disabled.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=None,
        help="Upload at most this many points from the embedding file.",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Number of points to skip from the start of the embedding file.",
    )
    args = parser.parse_args()

    load_dotenv(find_dotenv())

    client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=180,
    )

    if not args.embedding_file.exists():
        raise FileNotFoundError(f"{args.embedding_file} does not exist")

    law_name = args.embedding_file.stem.replace("-", "_")
    collection_name = SRPSKO_PRAVO_COLLECTION
    logger.info(
        f"Uploading {args.embedding_file} to collection {collection_name} as law {law_name}"
    )

    ensure_collection(client, collection_name=collection_name)

    points = load_and_process_embeddings(path=args.embedding_file, law_name=law_name)
    if not points:
        logger.error("No points to upload.")
        return

    if args.skip:
        points = points[args.skip:]

    if args.max_points is not None:
        points = points[: args.max_points]

    total_points = len(points)
    if total_points == 0:
        logger.error("No points selected for upload after applying skip/max-points.")
        return

    existing_count = None
    try:
        existing_count = client.count(collection_name=collection_name).count
        logger.info(f"Collection currently has {existing_count} points.")
    except Exception as exc:
        logger.warning(f"Could not fetch existing count: {exc}")

    target_count = existing_count + total_points if existing_count is not None else None

    uploaded = 0
    for batch in chunk_points(points, args.batch_size):
        attempt = 0
        success = False
        while attempt < 3 and not success:
            attempt += 1
            try:
                logger.info(
                    f"Upserting batch of {len(batch)} points (attempt {attempt})"
                )
                client.upsert(
                    collection_name=collection_name, points=batch, wait=args.wait
                )
                uploaded += len(batch)
                success = True
            except Exception as exc:
                logger.warning(f"Batch upsert failed: {exc}")
                time.sleep(5)
        if not success:
            logger.error("Failed to upload batch after retries.")
            break
        time.sleep(args.sleep)

    final_count = None
    if not args.wait:
        logger.info("Waiting for Qdrant to finish processing batches...")
        expected = target_count if target_count is not None else total_points
        for attempt in range(1, args.verify_retries + 1):
            try:
                current = client.count(collection_name=collection_name).count
                final_count = current
                logger.info(
                    f"Verification {attempt}/{args.verify_retries}: {current} points present (expected >= {expected})."
                )
                if (target_count is not None and current >= target_count) or (
                    target_count is None and current >= expected
                ):
                    break
            except Exception as exc:
                logger.warning(f"Verification attempt {attempt} failed: {exc}")
            time.sleep(args.sleep)
    else:
        try:
            final_count = client.count(collection_name=collection_name).count
        except Exception as exc:
            logger.warning(f"Could not fetch final count: {exc}")

    if final_count is not None and existing_count is not None:
        uploaded_report = max(final_count - existing_count, 0)
        logger.info(
            f"Uploaded {uploaded_report}/{total_points} points (collection total: {final_count})."
        )
    else:
        logger.info(f"Uploaded {uploaded}/{total_points} points.")


if __name__ == "__main__":
    main()

