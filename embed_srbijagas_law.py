import json
import os
from dotenv import load_dotenv
from database.utils import embed_text
from qdrant_client import QdrantClient
from openai import OpenAI
from langfuse import Langfuse

# Load environment variables
load_dotenv()

def initialize_clients():
    """Initialize Qdrant, OpenAI, and Langfuse clients"""
    # Qdrant client
    qdrant_url = os.environ["QDRANT_CLUSTER_URL"]
    qdrant_api_key = os.environ["QDRANT_API_KEY"]
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # OpenAI client
    openai_api_key = os.environ["OPENAI_API_KEY"]
    openai_client = OpenAI(api_key=openai_api_key)
    
    # Langfuse client
    langfuse_secret_key = os.environ["LANGFUSE_SECRET_KEY"]
    langfuse_public_key = os.environ["LANGFUSE_PUBLIC_KEY"]
    langfuse_host = os.environ["LANGFUSE_HOST"]
    langfuse_client = Langfuse(
        secret_key=langfuse_secret_key,
        public_key=langfuse_public_key,
        host=langfuse_host
    )
    
    return qdrant_client, openai_client, langfuse_client

def main():
    # Initialize clients
    qdrant_client, openai_client, langfuse_client = initialize_clients()
    
    # Load the new law
    with open('scraper/laws/SG_019_2025_020.json', 'r', encoding='utf-8') as f:
        law_data = json.load(f)
    
    print('Embedding Srbijagas guarantee law...')
    
    # Embed each article
    for article in law_data:
        title = article['title']
        texts = article['texts']
        link = article['link']
        
        # Combine title and texts
        full_text = f'{title}: ' + ' '.join(texts)
        
        # Create metadata
        metadata = {
            'title': title,
            'link': link,
            'source': 'SG_019_2025_020',
            'law_name': 'Zakon o davanju garancije Republike Srbije u korist Banca Intesa AD Beograd za izmirivanje obaveza javnog preduzeća Srbijagas Novi Sad, po osnovu ugovora o kreditu radi izgradnje razvodnog gasovoda Beograd-Valjevo-Loznica'
        }
        
        # Embed the text
        try:
            embed_text(full_text, metadata, qdrant_client, openai_client, langfuse_client)
            print(f'Successfully embedded: {title}')
        except Exception as e:
            print(f'Error embedding {title}: {e}')
    
    print('Embedding completed!')

if __name__ == "__main__":
    main()
