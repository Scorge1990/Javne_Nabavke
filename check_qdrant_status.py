"""
Check Qdrant service status and performance metrics.
"""
import os
import time
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient


def main():
    """Check Qdrant service status."""
    load_dotenv(find_dotenv())
    
    qdrant_url = os.environ.get("QDRANT_CLUSTER_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        logger.error("QDRANT_CLUSTER_URL or QDRANT_API_KEY not set.")
        return
    
    logger.info("Checking Qdrant service status...")
    logger.info(f"Qdrant URL: {qdrant_url}")
    
    # Initialize client with longer timeout
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        timeout=180,
    )
    
    # Check collections
    logger.info("\n=== Collection Information ===")
    start_time = time.time()
    try:
        collections = client.get_collections().collections
        elapsed = time.time() - start_time
        logger.info(f"✓ Successfully retrieved collections in {elapsed:.2f} seconds")
        logger.info(f"Total collections: {len(collections)}")
        
        if len(collections) > 0:
            logger.info("\nSample collections (first 10):")
            for i, coll in enumerate(collections[:10], 1):
                try:
                    count_start = time.time()
                    count = client.count(collection_name=coll.name).count
                    count_elapsed = time.time() - count_start
                    logger.info(f"  {i}. {coll.name}: {count} points (count took {count_elapsed:.2f}s)")
                except Exception as e:
                    logger.warning(f"  {i}. {coll.name}: Error getting count - {e}")
        
        # Check if there are many collections
        if len(collections) > 1000:
            logger.warning(f"\n⚠️  WARNING: You have {len(collections)} collections!")
            logger.warning("This is a very large number and may cause performance issues.")
            logger.warning("Consider consolidating collections or upgrading your Qdrant plan.")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ Failed to get collections after {elapsed:.2f} seconds: {e}")
        logger.error("Qdrant service appears to be unresponsive.")
        return
    
    # Test a simple operation
    logger.info("\n=== Performance Test ===")
    if len(collections) > 0:
        test_collection = collections[0].name
        logger.info(f"Testing operation on collection: {test_collection}")
        
        # Test count operation
        start_time = time.time()
        try:
            count = client.count(collection_name=test_collection).count
            elapsed = time.time() - start_time
            logger.info(f"✓ Count operation completed in {elapsed:.2f} seconds")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"✗ Count operation failed after {elapsed:.2f} seconds: {e}")
    
    # Summary
    logger.info("\n=== Summary ===")
    logger.info("Possible reasons for slowness:")
    logger.info("1. Too many collections (>1000 can cause issues)")
    logger.info("2. Large individual collections (millions of points)")
    logger.info("3. Network latency to Qdrant Cloud")
    logger.info("4. Qdrant Cloud service issues or plan limits")
    logger.info("5. Concurrent operations overwhelming the service")
    logger.info("\nRecommendations:")
    logger.info("- Check Qdrant Cloud dashboard for service status")
    logger.info("- Consider upgrading your Qdrant plan if you have many collections")
    logger.info("- Reduce batch sizes and add delays between operations")
    logger.info("- Check network connectivity to Qdrant Cloud")


if __name__ == "__main__":
    main()

