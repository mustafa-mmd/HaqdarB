# app/services/vector_search.py
"""
HaqDar AI — Vector Search Service
Embedding: Vertex AI text-embedding-005
Search: Qdrant Cloud via HTTP (no qdrant-client package needed)
"""
import os
import time
import json
import logging
import urllib.request
import urllib.error
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ID   = os.getenv("PROJECT_ID")
LOCATION     = os.getenv("LOCATION")
QDRANT_URL   = os.getenv("QDRANT_URL", "").rstrip("/")
QDRANT_KEY   = os.getenv("QDRANT_API_KEY")
COLLECTION   = os.getenv("QDRANT_COLLECTION", "law_corpus")

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    return _embedding_model


def generate_embedding(text: str) -> list:
    try:
        model = get_embedding_model()
        inputs = [TextEmbeddingInput(text, task_type="RETRIEVAL_QUERY")]
        embeddings = model.get_embeddings(inputs)
        return embeddings[0].values
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
        return [0.0] * 768


def qdrant_search(query_vector, language=None, category=None, limit=5):
    """Search Qdrant via HTTP REST — no qdrant-client needed."""
    url = f"{QDRANT_URL}/collections/{COLLECTION}/points/search"

    body = {
        "vector": query_vector,
        "limit": limit,
        "with_payload": True
    }

    # Add filters if provided
    conditions = []
    if language:
        conditions.append({
            "key": "language",
            "match": {"value": language}
        })
    if category:
        conditions.append({
            "key": "category",
            "match": {"value": category}
        })

    if conditions:
        body["filter"] = {"must": conditions}

    data = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "api-key": QDRANT_KEY
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("result", [])
        except Exception as e:
            if attempt == 2:
                logger.warning(f"Qdrant search failed: {e}")
                return []
            time.sleep(2 ** attempt)

    return []


def search_similar_laws(
    query_text: str,
    neighbor_count: int = 3,
    language: str = None,
    category: str = None
):
    """
    Main search function — same interface as before.
    Returns: [{"id": ..., "distance": ..., "law_name": ..., "text": ...}]
    """
    query_embedding = generate_embedding(query_text)
    hits = qdrant_search(query_embedding, language, category, neighbor_count)

    return [
        {
            "id":             str(hit.get("id", "")),
            "distance":       hit.get("score", 0),
            "law_name":       hit["payload"].get("law_name", ""),
            "section_number": hit["payload"].get("section_number", ""),
            "language":       hit["payload"].get("language", ""),
            "category":       hit["payload"].get("category", ""),
            "text":           hit["payload"].get("text", ""),
            "score":          hit.get("score", 0),
        }
        for hit in hits
    ]