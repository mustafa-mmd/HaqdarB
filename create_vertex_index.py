# create_vertex_index.py
from google.cloud import aiplatform
import json
import time

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def create_index():
    """Create a new Vertex AI Vector Search Index"""
    
    my_index = aiplatform.MatchingEngineIndex.create(
        display_name="haqdar-law-index-v5",
        description="Complete Pakistani laws with text-embedding-005 - Semantic chunking",
        dimensions=768,
        approximate_neighbors_count=10,
        distance_measure_type="COSINE",
        index_update_method="BATCH_UPDATE",
    )
    
    print(f"\n✅ Index Created Successfully!")
    print(f"   Index Name: {my_index.display_name}")
    print(f"   Index Resource Name: {my_index.resource_name}")
    print(f"   Index ID: {my_index.name}")
    
    return my_index

if __name__ == "__main__":
    index = create_index()