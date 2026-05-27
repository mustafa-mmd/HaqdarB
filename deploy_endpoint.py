# deploy_endpoint.py
from google.cloud import aiplatform
import time

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"

# REPLACE WITH YOUR ACTUAL INDEX ID FROM STEP 4
INDEX_ID = "your-index-id-here"

aiplatform.init(project=PROJECT_ID, location=LOCATION)

def create_and_deploy_endpoint():
    """Create endpoint and deploy the index"""
    
    # Get the index
    index = aiplatform.MatchingEngineIndex(INDEX_ID)
    
    # Create endpoint
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name="haqdar-law-endpoint-prod",
        description="Production endpoint for HaqDar AI legal queries",
    )
    
    print(f"✅ Endpoint Created: {endpoint.resource_name}")
    print(f"   Endpoint ID: {endpoint.name}")
    
    # Deploy index to endpoint
    print("\n🔄 Deploying index to endpoint (takes 5-10 minutes)...")
    
    endpoint.deploy_index(
        index=index,
        deployed_index_id="haqdar_law_index_prod",
    )
    
    print(f"\n✅ Index Deployed Successfully!")
    print(f"   Endpoint Resource Name: {endpoint.resource_name}")
    
    return endpoint

if __name__ == "__main__":
    endpoint = create_and_deploy_endpoint()