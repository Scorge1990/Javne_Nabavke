import json
import os
from pathlib import Path
from dotenv import load_dotenv
from database.utils import create_embeddings, create_collection, upsert, load_and_process_embeddings
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()

def main():
    # Initialize Qdrant client
    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_CLUSTER_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )
    
    # Create directories
    scraped_dir = Path("./scraper/laws")
    to_process_dir = Path("./database/to_process")
    embeddings_dir = Path("./database/embeddings")
    
    to_process_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating embeddings for Srbijagas law...")
    
    # Create embeddings using the existing pipeline
    create_embeddings(
        scraped_dir=scraped_dir,
        to_process_dir=to_process_dir,
        embeddings_dir=embeddings_dir,
        model="text-embedding-3-small"
    )
    
    # Find the processed file
    processed_file = embeddings_dir / "SG_019_2025_020.jsonl"
    
    if processed_file.exists():
        print("Creating collection and upserting data...")
        
        # Create collection
        collection_name = "SG_019_2025_020"
        create_collection(client=qdrant_client, name=collection_name)
        
        # Load and process embeddings
        points = load_and_process_embeddings(path=processed_file)
        
        # Upsert to Qdrant
        upsert(client=qdrant_client, collection=collection_name, points=points)
        
        print(f"Successfully embedded {len(points)} articles from Srbijagas law!")
    else:
        print("Error: Processed file not found")

if __name__ == "__main__":
    main()
