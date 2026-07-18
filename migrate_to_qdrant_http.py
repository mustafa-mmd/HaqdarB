"""
migrate_to_qdrant_http.py
─────────────────────────────────────────────────────────────────────────────
Production-ready Qdrant uploader for law corpus embeddings.

Features
  • Incremental uploads  — only NEW chunk_ids are sent on every run
  • Idempotent by design — same chunk_id → same UUID → safe upsert (no dupes)
  • Crash-safe           — tracking file is appended after every successful batch
  • Resumable            — interrupt mid-run, restart, only remainder is uploaded
  • Full retry logic     — exponential back-off on network / timeout errors
  • Rich progress output — per-batch status + final summary table

Usage
  1. Set env vars in .env  (QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION)
  2. python migrate_to_qdrant_http.py
  3. Add new records to the JSONL file and re-run — only new ones are uploaded
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import sys
import uuid
import time
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Config  (all overridable via env)
# ─────────────────────────────────────────────

QDRANT_URL      = os.getenv("QDRANT_URL", "").rstrip("/")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY", "")
COLLECTION      = os.getenv("QDRANT_COLLECTION", "law_corpus")
EMBEDDINGS_FILE = os.getenv("EMBEDDINGS_FILE", "law-embeddings-real.json")
VECTOR_SIZE     = int(os.getenv("VECTOR_SIZE", "768"))
BATCH_SIZE      = int(os.getenv("BATCH_SIZE", "50"))
MAX_RETRIES     = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY     = int(os.getenv("RETRY_DELAY", "10"))   # seconds, multiplied per attempt

# Local file that tracks uploaded chunk_ids (append-only, crash-safe)
UPLOADED_IDS_FILE = "uploaded_chunk_ids.txt"

HEADERS = {
    "Content-Type": "application/json",
    "api-key": QDRANT_API_KEY,
}

# ─────────────────────────────────────────────
# Startup validation
# ─────────────────────────────────────────────

def validate_config():
    errors = []
    if not QDRANT_URL:
        errors.append("QDRANT_URL is not set")
    if not QDRANT_API_KEY:
        errors.append("QDRANT_API_KEY is not set")
    if not os.path.exists(EMBEDDINGS_FILE):
        errors.append(f"Embeddings file not found: {EMBEDDINGS_FILE}")
    if errors:
        print("\n❌ Configuration errors:")
        for e in errors:
            print(f"   • {e}")
        sys.exit(1)

# ─────────────────────────────────────────────
# HTTP client
# ─────────────────────────────────────────────

def qdrant_request(method: str, path: str, body: dict = None) -> dict:
    """
    Make a Qdrant REST API call with automatic retry + exponential back-off.
    Raises on HTTP errors or exhausted retries.
    """
    url  = f"{QDRANT_URL}/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url, data=data, headers=HEADERS, method=method
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            # 4xx errors are not retryable
            if 400 <= e.code < 500:
                raise RuntimeError(
                    f"HTTP {e.code} on {method} /{path}: {detail}"
                ) from e
            # 5xx — retry
            print(f"  ⚠️  HTTP {e.code} (attempt {attempt}/{MAX_RETRIES}): {detail[:120]}")

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  ⚠️  Network error (attempt {attempt}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES:
            wait = RETRY_DELAY * attempt
            print(f"     Retrying in {wait}s...")
            time.sleep(wait)
        else:
            raise RuntimeError(
                f"Failed after {MAX_RETRIES} attempts: {method} /{path}"
            )

# ─────────────────────────────────────────────
# ID helpers
# ─────────────────────────────────────────────

def chunk_id_to_uuid(chunk_id: str) -> str:
    """
    Derive a deterministic UUID v5 from a chunk_id string.
    • Same input  →  same UUID  →  Qdrant upsert is a safe no-op on re-run.
    • Different input  →  different UUID  →  no collisions between records.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

# ─────────────────────────────────────────────
# Tracking file  (source of truth for "already uploaded")
# ─────────────────────────────────────────────

def load_uploaded_ids() -> set:
    """
    Return the set of chunk_ids that have already been successfully uploaded.
    The tracking file is append-only, so it survives mid-run crashes.
    """
    ids = set()
    if not os.path.exists(UPLOADED_IDS_FILE):
        return ids
    with open(UPLOADED_IDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            cid = line.strip()
            if cid:
                ids.add(cid)
    return ids


def append_uploaded_ids(chunk_ids: list):
    """
    Persist a batch of successfully uploaded chunk_ids immediately after the
    Qdrant upsert succeeds.  Uses 'a' (append) mode so a crash mid-run does
    not lose progress already recorded.
    """
    with open(UPLOADED_IDS_FILE, "a", encoding="utf-8") as f:
        for cid in chunk_ids:
            f.write(cid + "\n")

# ─────────────────────────────────────────────
# Collection + index management
# ─────────────────────────────────────────────

def ensure_collection():
    existing = qdrant_request("GET", "collections")
    names    = [c["name"] for c in existing["result"]["collections"]]

    if COLLECTION in names:
        print(f"  Collection '{COLLECTION}' already exists — skipping creation.")
    else:
        body = {
            "vectors": {
                "size":     VECTOR_SIZE,
                "distance": "Cosine",
            }
        }
        qdrant_request("PUT", f"collections/{COLLECTION}", body)
        print(f"  Collection '{COLLECTION}' created  (size={VECTOR_SIZE}, Cosine).")


def ensure_indexes():
    """Create keyword payload indexes for fast filtered search."""
    index_fields = ["language", "law_name", "category", "source", "jurisdiction"]
    created = []
    for field in index_fields:
        try:
            body = {"field_name": field, "field_schema": "keyword"}
            qdrant_request("PUT", f"collections/{COLLECTION}/index", body)
            created.append(field)
        except Exception:
            pass   # Index already exists or non-critical failure — safe to ignore
    if created:
        print(f"  Payload indexes ready: {', '.join(created)}")
    else:
        print("  Payload indexes already up to date.")

# ─────────────────────────────────────────────
# JSONL reader
# ─────────────────────────────────────────────

def read_jsonl(filepath: str) -> list:
    records   = []
    bad_lines = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                bad_lines += 1
                print(f"  ⚠️  Skipping malformed line {line_num}: {e}")
    if bad_lines:
        print(f"  ⚠️  Total malformed lines skipped: {bad_lines}")
    return records

# ─────────────────────────────────────────────
# Upload
# ─────────────────────────────────────────────

def upsert_batch(points: list):
    body = {"points": points}
    qdrant_request("PUT", f"collections/{COLLECTION}/points", body)


def get_qdrant_count() -> int:
    """Return the number of vectors currently in the collection."""
    try:
        info  = qdrant_request("GET", f"collections/{COLLECTION}")
        result = info["result"]
        return result.get("vectors_count") or result.get("points_count", 0)
    except Exception:
        return 0


def run_upload(new_records: list) -> tuple[int, int]:
    """
    Upload only the records that have not been uploaded yet.
    Returns (uploaded_count, skipped_count).
    """
    total    = len(new_records)
    uploaded = 0
    skipped  = 0

    batch_points    = []
    batch_chunk_ids = []

    for i, record in enumerate(new_records, 1):
        chunk_id  = record.get("id", "").strip()
        embedding = record.get("embedding")

        # ── Validate embedding ──
        if not embedding or len(embedding) != VECTOR_SIZE:
            print(
                f"  ⚠️  Skipping record #{i} (id='{chunk_id}') "
                f"— invalid embedding (got {len(embedding) if embedding else 0}, "
                f"expected {VECTOR_SIZE})."
            )
            skipped += 1
            continue

        # ── Stable UUID from chunk_id ──
        point_id = chunk_id_to_uuid(chunk_id) if chunk_id else str(uuid.uuid4())

        batch_points.append({
            "id":     point_id,
            "vector": embedding,
            "payload": {
                "chunk_id":            chunk_id,
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
            },
        })
        batch_chunk_ids.append(chunk_id)

        # ── Flush batch ──
        if len(batch_points) == BATCH_SIZE:
            upsert_batch(batch_points)
            append_uploaded_ids(batch_chunk_ids)   # persist immediately after success
            uploaded += len(batch_points)
            pct = (uploaded / total) * 100
            print(
                f"  ✅  Batch uploaded  |  "
                f"this run: {uploaded}/{total} ({pct:.1f}%)  |  "
                f"last chunk_id: {batch_chunk_ids[-1]}"
            )
            batch_points    = []
            batch_chunk_ids = []
            time.sleep(0.3)   # be gentle with Qdrant Cloud rate limits

    # ── Final partial batch ──
    if batch_points:
        upsert_batch(batch_points)
        append_uploaded_ids(batch_chunk_ids)
        uploaded += len(batch_points)
        print(
            f"  ✅  Final batch  |  "
            f"this run: {uploaded}/{total} (100%)  |  "
            f"last chunk_id: {batch_chunk_ids[-1]}"
        )

    return uploaded, skipped

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    t_start = time.time()

    # ── 1. Validate config ──
    validate_config()

    # ── 2. Connect ──
    print(f"\n🔌  Connecting to Qdrant at {QDRANT_URL} ...")
    qdrant_request("GET", "collections")
    print("    Connected ✓\n")

    # ── 3. Ensure collection + indexes ──
    print("🗄   Collection setup")
    ensure_collection()
    ensure_indexes()

    # ── 4. Read JSONL ──
    print(f"\n📂  Reading {EMBEDDINGS_FILE} ...")
    all_records   = read_jsonl(EMBEDDINGS_FILE)
    total_in_file = len(all_records)
    print(f"    {total_in_file} records found in file.")

    # ── 5. Determine what is new ──
    uploaded_ids = load_uploaded_ids()
    already_done = len(uploaded_ids)
    print(f"    Already uploaded (tracking file): {already_done}")

    new_records = [
        r for r in all_records
        if r.get("id", "").strip() not in uploaded_ids
    ]
    total_new = len(new_records)

    if total_new == 0:
        print(
            "\n✅  Nothing new to upload. "
            "All records are already tracked as uploaded."
        )
        elapsed = time.time() - t_start
        print(f"    Total time: {elapsed:.1f}s\n")
        return

    print(f"    New records to upload: {total_new}\n")

    # ── 6. Upload ──
    print(f"🚀  Uploading {total_new} new records in batches of {BATCH_SIZE} ...")
    uploaded, skipped = run_upload(new_records)

    # ── 7. Final summary ──
    qdrant_count = get_qdrant_count()
    elapsed      = time.time() - t_start

    print(f"""
╔══════════════════════════════════════════╗
║           Migration Complete ✅           ║
╠══════════════════════════════════════════╣
║  Records in file      : {total_in_file:<17} ║
║  Already uploaded     : {already_done:<17} ║
║  New this run         : {uploaded:<17} ║
║  Skipped (bad vector) : {skipped:<17} ║
║  Total vectors Qdrant : {str(qdrant_count):<17} ║
║  Time elapsed         : {f"{elapsed:.1f}s":<17} ║
╚══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()