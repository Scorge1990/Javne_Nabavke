"""
Check OpenAI account information associated with the API key.
"""
import os
from dotenv import find_dotenv, load_dotenv
from loguru import logger
import requests


def check_openai_account():
    """Check OpenAI account information."""
    load_dotenv(find_dotenv())
    
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("OPENAI_API_KEY not set in environment.")
        return
    
    logger.info("Checking OpenAI account information...")
    logger.info(f"API Key (first 10 chars): {api_key[:10]}...")
    
    # Try to get account/organization info
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Try to get organization info
    try:
        response = requests.get(
            "https://api.openai.com/v1/organizations",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            orgs = response.json()
            logger.info(f"✓ Successfully retrieved organizations")
            logger.info(f"Organizations: {orgs}")
        else:
            logger.warning(f"Could not get organizations: {response.status_code}")
            logger.info(f"Response: {response.text}")
    except Exception as e:
        logger.warning(f"Error getting organizations: {e}")
    
    # Try to get models (this will at least verify the key works)
    try:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            logger.info(f"✓ API key is valid (retrieved {len(models.get('data', []))} models)")
        elif response.status_code == 401:
            logger.error("✗ Invalid API key")
        else:
            logger.warning(f"Unexpected response: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error checking API key: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("NOTE: OpenAI API does not provide account email via API")
    logger.info("To find which email your API key is associated with:")
    logger.info("1. Go to https://platform.openai.com/api-keys")
    logger.info("2. Check the account/organization shown there")
    logger.info("3. Or go to https://platform.openai.com/account/org-settings")
    logger.info("4. The email will be shown in your account settings")
    logger.info("="*60)


if __name__ == "__main__":
    check_openai_account()

