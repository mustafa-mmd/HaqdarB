# update_vertex_index.py
from google.cloud import aiplatform
import json
import time

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"

# ============================================
# IMPORTANT: REPLACE THIS WITH YOUR ACTUAL INDEX ID
# Get it from: gcloud ai indexes list --region=asia-south1
# ============================================
INDEX_ID = "6580717829727715328"  # ← REPLACE THIS with your actual index ID

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def update_index():
    """Update existing Vertex AI index with new embeddings"""
    
    print(f"🔄 Updating index: {INDEX_ID}")
    print("⏳ This may take 5-10 minutes...")
    
    # Get the existing index
    index = aiplatform.MatchingEngineIndex(INDEX_ID)
    
    # Update embeddings from your JSON file
    index.update_embeddings(
        embeddings_file="law-embeddings-real.json",
        embeddings_file_format="jsonl"  # Your file is JSONL format
    )
    
    print(f"\n✅ Index updated successfully!")
    print(f"   Index ID: {INDEX_ID}")

if __name__ == "__main__":
    update_index()