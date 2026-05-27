from google.cloud import aiplatform
import json

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"

aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Create new index
my_index = aiplatform.MatchingEngineIndex.create(
    display_name="haqdar-law-index-v3",
    description="Legal documents with text-embedding-005",
    dimensions=768,
    approximate_neighbors_count=10,
    distance_measure_type="COSINE",
    index_update_method="BATCH_UPDATE",
)

print(f"✅ Index created: {my_index.name}")
print(f"Index ID: {my_index.resource_name}")