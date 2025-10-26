import os
import json
from dotenv import load_dotenv
from router.query_router import formate_messages_router
from utils import call_llm, determine_context, embed_text
from qdrant_client import QdrantClient

load_dotenv()

# Test the improved search with your question
query = "Da li narucilac moze da dodeli ugovor preko procenjene vrednosti?"

# Step 1: Router
messages = formate_messages_router(query)
response = call_llm(
    model="gpt-3.5-turbo",
    temperature=0,
    messages=messages,
    json_response=True
)
collections = json.loads(response.choices[0].message.content)["response"]
print(f"Router returned collections: {collections}")

# Step 2: Embedding
embedding_response = embed_text(text=query, model="text-embedding-3-small")
embedding = embedding_response.data[0].embedding

# Step 3: Qdrant search
qdrant_client = QdrantClient(
    url=os.environ["QDRANT_CLUSTER_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

# Step 4: Improved context determination
context = determine_context(collections, embedding, qdrant_client)

# Save results to file
with open("improved_search_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Query: {query}\n")
    f.write(f"Collections: {collections}\n")
    f.write(f"Context length: {len(context)}\n\n")
    f.write("Context content:\n")
    f.write(context)

print(f"Improved search completed. Context length: {len(context)}")
print("Results saved to improved_search_results.txt")

# Check if the specific question appears in the context
if "dodeli ugovor preko procenjene vrednosti" in context.lower():
    print("✅ SUCCESS: The specific question was found in the context!")
else:
    print("❌ The specific question was not found in the context")

