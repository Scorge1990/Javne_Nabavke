import argparse
import os
import time
from typing import Iterable, List, Optional, Sequence, Tuple

from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

TARGET_COLLECTION = "srpsko_pravo"
DEFAULT_VECTOR_SIZE = 1536
DEFAULT_DISTANCE = rest.Distance.COSINE
DEFAULT_BATCH_SIZE = 64
UPSERT_RETRIES = 3
RETRY_SLEEP_SECONDS = 5


def load_env() -> None:
    load_dotenv(find_dotenv())
    if "QDRANT_CLUSTER_URL" not in os.environ or "QDRANT_API_KEY" not in os.environ:
        raise EnvironmentError("QDRANT_CLUSTER_URL and QDRANT_API_KEY must be set in the environment.")


def init_client(timeout: int = 180) -> QdrantClient:
    return QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
        timeout=timeout,
    )


def iter_collections(client: QdrantClient) -> Sequence[rest.CollectionDescription]:
    return client.get_collections().collections


def infer_vector_params(
    client: QdrantClient,
    collections: Sequence[rest.CollectionDescription],
    target_collection: str,
) -> Tuple[int, rest.Distance]:
    """Infer vector size and distance metric from existing collections."""
    # If the target already exists, trust its configuration.
    for collection in collections:
        if collection.name == target_collection:
            info = client.get_collection(collection_name=target_collection)
            params = info.config.params
            if isinstance(params, rest.VectorsConfig):
                # Named vectors configuration – pick the first one.
                name, vector = next(iter(params.named_vectors.items()))
                logger.info(
                    f'Using existing target collection "{target_collection}" '
                    f'configuration (named vector "{name}", size={vector.size}, distance={vector.distance}).'
                )
                return vector.size, vector.distance
            elif isinstance(params, rest.VectorParams):
                logger.info(
                    f'Using existing target collection "{target_collection}" configuration '
                    f'(size={params.size}, distance={params.distance}).'
                )
                return params.size, params.distance

    # Otherwise, inspect the first source collection that has vectors.
    for collection in collections:
        try:
            records, _ = client.scroll(
                collection_name=collection.name,
                limit=1,
                with_vectors=True,
                with_payload=False,
            )
        except Exception as exc:
            logger.warning(f'Failed to inspect collection "{collection.name}" for vector params: {exc}')
            continue

        if not records:
            continue

        vector = extract_vector(records[0])
        if vector is not None:
            logger.info(
                f'Inferred vector size={len(vector)} and distance={DEFAULT_DISTANCE} '
                f'from collection "{collection.name}".'
            )
            return len(vector), DEFAULT_DISTANCE

    logger.warning(
        "Could not infer vector size from existing collections. "
        f"Defaulting to size={DEFAULT_VECTOR_SIZE}, distance={DEFAULT_DISTANCE}."
    )
    return DEFAULT_VECTOR_SIZE, DEFAULT_DISTANCE


def ensure_target_collection(
    client: QdrantClient,
    vector_size: int,
    distance: rest.Distance,
    collection_name: str = TARGET_COLLECTION,
) -> None:
    if client.collection_exists(collection_name=collection_name):
        logger.info(f'Target collection "{collection_name}" already exists.')
        return

    logger.info(
        f'Creating target collection "{collection_name}" (vector_size={vector_size}, distance={distance}).'
    )
    client.create_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(size=vector_size, distance=distance),
    )


def extract_vector(point: rest.Record) -> Optional[List[float]]:
    if point.vector is not None:
        return list(point.vector)
    if point.vectors is not None and point.vectors.vectors:
        # Take the first named vector.
        _, vector = next(iter(point.vectors.vectors.items()))
        return list(vector)
    return None


def build_point_id(source_collection: str, original_id: rest.PointId) -> str:
    return f"{source_collection}_{original_id}"


def to_point_structs(
    source_collection: str,
    points: Iterable[rest.Record],
) -> List[rest.PointStruct]:
    transformed: List[rest.PointStruct] = []
    for point in points:
        vector = extract_vector(point)
        if vector is None:
            logger.warning(f"Skipping point without vector in collection {source_collection}.")
            continue

        payload = point.payload or {}
        payload.setdefault("law_name", source_collection)
        payload.setdefault("law", source_collection.replace("_", " "))
        payload["source_collection"] = source_collection
        payload["original_id"] = str(point.id)

        transformed.append(
            rest.PointStruct(
                id=build_point_id(source_collection, point.id),
                vector=vector,
                payload=payload,
            )
        )
    return transformed


def upsert_with_retry(
    client: QdrantClient,
    target_collection: str,
    points: List[rest.PointStruct],
) -> None:
    attempt = 0
    while attempt < UPSERT_RETRIES:
        attempt += 1
        try:
            client.upsert(collection_name=target_collection, points=points, wait=False)
            return
        except Exception as exc:
            if attempt < UPSERT_RETRIES and "timeout" in str(exc).lower():
                logger.warning(
                    f"Upsert attempt {attempt} timed out for {len(points)} points. "
                    f"Retrying in {RETRY_SLEEP_SECONDS}s..."
                )
                time.sleep(RETRY_SLEEP_SECONDS)
                continue
            raise


def migrate_collection(
    client: QdrantClient,
    source_collection: str,
    target_collection: str,
    batch_size: int,
) -> int:
    logger.info(f'Starting migration for collection "{source_collection}".')
    offset = None
    total_transferred = 0

    while True:
        records, offset = client.scroll(
            collection_name=source_collection,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not records:
            break

        new_points = to_point_structs(source_collection, records)
        if not new_points:
            logger.warning(
                f"No transferable points found in current batch for collection {source_collection}. Continuing."
            )
            continue

        upsert_with_retry(client, target_collection, new_points)
        total_transferred += len(new_points)

        if offset is None:
            break

    logger.info(
        f'Completed migration for collection "{source_collection}" with {total_transferred} points transferred.'
    )
    return total_transferred


def delete_source_collection(client: QdrantClient, collection_name: str) -> None:
    logger.info(f'Deleting source collection "{collection_name}".')
    client.delete_collection(collection_name=collection_name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge all existing Qdrant collections into a single target collection.",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=TARGET_COLLECTION,
        help=f"Name of the target collection (default: {TARGET_COLLECTION}).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of points to pull per scroll batch (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--drop-source",
        action="store_true",
        help="Delete each source collection after a successful migration.",
    )
    args = parser.parse_args()

    load_env()
    client = init_client()

    collections = iter_collections(client)
    source_collections = [c.name for c in collections if c.name != args.target]

    if not source_collections:
        logger.info("No source collections found. Nothing to migrate.")
        return

    vector_size, distance = infer_vector_params(client, collections, args.target)
    ensure_target_collection(client, vector_size, distance, collection_name=args.target)

    total_points = 0
    for source in source_collections:
        transferred = migrate_collection(
            client=client,
            source_collection=source,
            target_collection=args.target,
            batch_size=args.batch_size,
        )
        total_points += transferred
        if args.drop_source and transferred > 0:
            delete_source_collection(client, source)

    logger.info(
        f"Migration complete. {len(source_collections)} collections processed, {total_points} points transferred."
    )


if __name__ == "__main__":
    main()

