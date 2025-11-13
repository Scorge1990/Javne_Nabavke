"""
Check usage and limits for OpenAI, Qdrant, and other services.
"""
import os
import time
from dotenv import find_dotenv, load_dotenv
from loguru import logger
from qdrant_client import QdrantClient
import requests


def check_openai_usage():
    """Check OpenAI API usage and limits."""
    logger.info("\n=== OpenAI API Usage ===")
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY not set.")
        return
    
    try:
        # Check usage via OpenAI API
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            "https://api.openai.com/v1/usage",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            usage = response.json()
            logger.info(f"✓ OpenAI API usage retrieved")
            logger.info(f"Usage data: {usage}")
        elif response.status_code == 401:
            logger.error("✗ Invalid OpenAI API key")
        elif response.status_code == 403:
            logger.warning("✗ OpenAI API key doesn't have permission to check usage")
        else:
            logger.warning(f"✗ Could not check OpenAI usage: {response.status_code}")
            logger.info("Note: OpenAI doesn't provide a public API to check usage.")
            logger.info("Check your usage at: https://platform.openai.com/usage")
    except Exception as e:
        logger.warning(f"Could not check OpenAI usage: {e}")
        logger.info("Check your usage manually at: https://platform.openai.com/usage")
    
    logger.info("\nTo check OpenAI usage manually:")
    logger.info("1. Go to https://platform.openai.com/usage")
    logger.info("2. Check your billing and usage dashboard")
    logger.info("3. Look for rate limits or quota exceeded errors")


def check_qdrant_usage():
    """Check Qdrant Cloud usage and limits."""
    logger.info("\n=== Qdrant Cloud Usage ===")
    qdrant_url = os.environ.get("QDRANT_CLUSTER_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        logger.warning("QDRANT_CLUSTER_URL or QDRANT_API_KEY not set.")
        return
    
    logger.info(f"Qdrant URL: {qdrant_url}")
    
    try:
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=60,
        )
        
        # Try to get collections count
        start_time = time.time()
        try:
            collections = client.get_collections().collections
            elapsed = time.time() - start_time
            logger.info(f"✓ Retrieved collections in {elapsed:.2f} seconds")
            logger.info(f"Total collections: {len(collections)}")
            
            # Count total points across collections (sample first 10)
            total_points = 0
            sample_collections = collections[:10]
            for coll in sample_collections:
                try:
                    count = client.count(collection_name=coll.name).count
                    total_points += count
                    logger.info(f"  - {coll.name}: {count} points")
                except Exception as e:
                    logger.warning(f"  - {coll.name}: Error getting count - {e}")
            
            if len(collections) > 10:
                logger.info(f"  ... and {len(collections) - 10} more collections")
            
            logger.info(f"\nSample total points (first 10 collections): {total_points}")
            
            # Check for potential issues
            if len(collections) > 1000:
                logger.warning(f"\n⚠️  WARNING: You have {len(collections)} collections!")
                logger.warning("This may exceed your Qdrant plan limits.")
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"✗ Failed to get collections after {elapsed:.2f} seconds: {e}")
            logger.error("Qdrant service appears to be unresponsive or overloaded.")
        
    except Exception as e:
        logger.error(f"Could not connect to Qdrant: {e}")
    
    logger.info("\nTo check Qdrant Cloud usage manually:")
    logger.info("1. Go to your Qdrant Cloud dashboard")
    logger.info("2. Check your plan limits (collections, storage, operations)")
    logger.info("3. Look for any service status warnings")


def check_langfuse_usage():
    """Check Langfuse usage if configured."""
    logger.info("\n=== Langfuse Usage ===")
    langfuse_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    langfuse_public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    langfuse_host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if not langfuse_secret or not langfuse_public:
        logger.info("Langfuse not configured (LANGFUSE_SECRET_KEY or LANGFUSE_PUBLIC_KEY not set).")
        return
    
    logger.info(f"Langfuse Host: {langfuse_host}")
    logger.info("To check Langfuse usage:")
    logger.info(f"1. Go to {langfuse_host}")
    logger.info("2. Check your project dashboard for usage statistics")


def main():
    """Check usage for all configured services."""
    load_dotenv(find_dotenv())
    
    logger.info("Checking service usage and limits...")
    
    check_openai_usage()
    check_qdrant_usage()
    check_langfuse_usage()
    
    logger.info("\n=== Summary ===")
    logger.info("Common reasons for service slowness or errors:")
    logger.info("1. OpenAI: Rate limits, quota exceeded, or billing issues")
    logger.info("2. Qdrant: Too many collections, storage limits, or plan limits")
    logger.info("3. Network: Connectivity issues or high latency")
    logger.info("\nRecommendations:")
    logger.info("- Check each service's dashboard for detailed usage")
    logger.info("- Monitor for rate limit errors in logs")
    logger.info("- Consider upgrading plans if hitting limits")
    logger.info("- Reduce batch sizes and add delays between operations")


if __name__ == "__main__":
    main()

