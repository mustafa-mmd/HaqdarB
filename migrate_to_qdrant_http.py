import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL").rstrip("/")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION      = os.getenv("QDRANT_COLLECTION", "law_corpus")
EMBEDDINGS_FILE = "law-embeddings-real.json"
VECTOR_SIZE     = 768
BATCH_SIZE      = 100

HEADERS = {
    "Content-Type": "application/json",
    "api-key": QDRANT_API_KEY
}

def qdrant_request(method, path, body=None):
    url = f"{QDRANT_URL}/{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP {e.code}: {error_body}")
        raise

def create_collection():
    existing = qdrant_request("GET", "collections")
    names = [c["name"] for c in existing["result"]["collections"]]
    if COLLECTION in names:
        print(f"Collection '{COLLECTION}' already exists.")
        return
    body = {"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}}
    qdrant_request("PUT", f"collections/{COLLECTION}", body)
    print(f"Collection '{COLLECTION}' created.")

def create_indexes():
    for field in ["language", "law_name", "category", "source", "jurisdiction"]:
        try:
            body = {"field_name": field, "field_schema": "keyword"}
            qdrant_request("PUT", f"collections/{COLLECTION}/index", body)
        except Exception:
            pass
    print("Payload indexes ready.")

def read_jsonl(filepath):
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Skipping bad line {line_num}: {e}")
    return records

def upsert_batch(points):
    body = {"points": points}
    qdrant_request("PUT", f"collections/{COLLECTION}/points", body)

def main():
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    info = qdrant_request("GET", "collections")
    print(f"Connected OK!")

    create_collection()
    create_indexes()

    print(f"\nReading {EMBEDDINGS_FILE}...")
    records = read_jsonl(EMBEDDINGS_FILE)
    total = len(records)
    print(f"Found {total} chunks to upload.")

    points   = []
    uploaded = 0
    skipped  = 0

    for i, record in enumerate(records):
        embedding = record.get("embedding")
        if not embedding or len(embedding) != VECTOR_SIZE:
            skipped += 1
            continue

        points.append({
            "id": i,
            "vector": embedding,
            "payload": {
                "chunk_id":            record.get("id", ""),
                "text":                record.get("text", ""),
                "source":              record.get("source", ""),
                "law_name":            record.get("law_name", ""),
                "section_number":      record.get("section_number", "General"),
                "language":            record.get("language", "en"),
                "category":            record.get("category", "general"),
                "page_number":         record.get("page_number", 0),
                "chunk_index":         record.get("chunk_index", 0),
                "total_chunks_in_law": record.get("total_chunks_in_law", 0),
                "keywords":            record.get("keywords", []),
                "jurisdiction":        record.get("jurisdiction", "Pakistan"),
                "char_count":          record.get("char_count", 0),
                "word_count":          record.get("word_count", 0),
                "timestamp":           record.get("timestamp", ""),
            }
        })

        if len(points) == BATCH_SIZE:
            upsert_batch(points)
            uploaded += len(points)
            points = []
            print(f"  Uploaded {uploaded}/{total}...")

    if points:
        upsert_batch(points)
        uploaded += len(points)

    info = qdrant_request("GET", f"collections/{COLLECTION}")
    count = info["result"]["vectors_count"]
    print(f"\nDone!")
    print(f"  Uploaded:            {uploaded}")
    print(f"  Skipped:             {skipped}")
    print(f"  Qdrant total vectors:{count}")

if __name__ == "__main__":
    main()