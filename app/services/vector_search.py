import os
import time
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from dotenv import load_dotenv
from google.api_core import exceptions

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
INDEX_ENDPOINT_ID = os.getenv("INDEX_ENDPOINT_ID")
DEPLOYED_INDEX_ID = os.getenv("DEPLOYED_INDEX_ID")

# Initialize Vertex AI lazily to avoid crashing the server on startup if billing is disabled
_embedding_model = None
_vector_client = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    return _embedding_model

def get_vector_client():
    global _vector_client
    if _vector_client is None:
        PUBLIC_ENDPOINT_DOMAIN = "207991304.asia-south1-1052663637521.vdb.vertexai.goog"
        client_options = {"api_endpoint": PUBLIC_ENDPOINT_DOMAIN}
        _vector_client = aiplatform.gapic.MatchServiceClient(client_options=client_options)
    return _vector_client


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text query."""
    try:
        model = get_embedding_model()
        inputs = [TextEmbeddingInput(text, task_type="RETRIEVAL_QUERY")]
        embeddings = model.get_embeddings(inputs)
        return embeddings[0].values
    except Exception as e:
        print(f"Warning: Could not generate embedding (Billing/API error): {e}")
        # Return a zero vector fallback to prevent complete crashes
        return [0.0] * 768


def search_similar_laws(query_text: str, neighbor_count: int = 3):
    """Search for the most relevant law sections using vector similarity, with retries."""
    query_embedding = generate_embedding(query_text)

    endpoint_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/indexEndpoints/{INDEX_ENDPOINT_ID}"

    request = aiplatform.gapic.FindNeighborsRequest(
        index_endpoint=endpoint_path,
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[
            aiplatform.gapic.FindNeighborsRequest.Query(
                datapoint=aiplatform.gapic.IndexDatapoint(feature_vector=query_embedding),
                neighbor_count=neighbor_count
            )
        ]
    )

    # Retry loop for transient network errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_vector_client()
            response = client.find_neighbors(request=request)
            break  # success, exit loop
        except exceptions.ServiceUnavailable as e:
            if attempt == max_retries - 1:
                print(f"Warning: Vector search failed after retries: {e}")
                return []
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"Vector search temporarily unavailable, retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            # Other errors (permission, etc.) should gracefully fail
            print(f"Warning: Vector search failed (Billing/API error): {e}")
            return []

    results = []
    if response.nearest_neighbors:
        for neighbor in response.nearest_neighbors[0].neighbors:
            results.append({
                "id": neighbor.datapoint.datapoint_id,
                "distance": neighbor.distance
            })
    return results