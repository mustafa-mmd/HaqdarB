"""
cleanup_and_reset.py
─────────────────────────────────────────────────────────────────────────────
Deletes the Qdrant collection + local tracking file so migrate_to_qdrant_http.py
can do a clean, deduplication-safe fresh upload.

Run this ONCE to fix the duplicate vectors issue, then re-run:
  python migrate_to_qdrant_http.py
─────────────────────────────────────────────────────────────────────────────
"""

import json
import os
import sys
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL     = os.getenv("QDRANT_URL", "").rstrip("/")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = os.getenv("QDRANT_COLLECTION", "law_corpus")

UPLOADED_IDS_FILE = "uploaded_chunk_ids.txt"

HEADERS = {
    "Content-Type": "application/json",
    "api-key": QDRANT_API_KEY,
}


def qdrant_request(method: str, path: str, body: dict = None) -> dict:
    url  = f"{QDRANT_URL}/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_vector_count() -> int:
    try:
        info   = qdrant_request("GET", f"collections/{COLLECTION}")
        result = info["result"]
        return result.get("vectors_count") or result.get("points_count", 0)
    except Exception:
        return 0


def confirm(prompt: str) -> bool:
    answer = input(f"\n{prompt} [y/N]: ").strip().lower()
    return answer == "y"


def main():
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌  QDRANT_URL or QDRANT_API_KEY not set in .env")
        sys.exit(1)

    print(f"\n🔌  Connecting to Qdrant at {QDRANT_URL} ...")
    qdrant_request("GET", "collections")
    print("    Connected ✓")

    # ── Show current state ──
    current_count = get_vector_count()
    tracking_count = 0
    if os.path.exists(UPLOADED_IDS_FILE):
        with open(UPLOADED_IDS_FILE, "r") as f:
            tracking_count = sum(1 for line in f if line.strip())

    print(f"""
┌─────────────────────────────────────────┐
│           Current State                 │
├─────────────────────────────────────────┤
│  Collection      : {COLLECTION:<22}│
│  Vectors Qdrant  : {str(current_count):<22}│
│  Tracking file   : {str(tracking_count):<22}│
└─────────────────────────────────────────┘""")

    print("""
⚠️   This will:
     1. DELETE the entire Qdrant collection  (all vectors removed)
     2. DELETE uploaded_chunk_ids.txt        (tracking file reset)
     3. You must then re-run migrate_to_qdrant_http.py for a clean upload
""")

    if not confirm("Are you sure you want to continue?"):
        print("\n🚫  Aborted. Nothing was changed.\n")
        sys.exit(0)

    # ── Step 1: Delete Qdrant collection ──
    print(f"\n🗑   Deleting collection '{COLLECTION}' from Qdrant ...")
    try:
        qdrant_request("DELETE", f"collections/{COLLECTION}")
        print(f"    ✅  Collection '{COLLECTION}' deleted.")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"    ℹ️   Collection '{COLLECTION}' did not exist — skipping.")
        else:
            print(f"    ❌  Failed to delete collection: HTTP {e.code}")
            sys.exit(1)
    except Exception as e:
        print(f"    ❌  Unexpected error: {e}")
        sys.exit(1)

    # ── Step 2: Delete local tracking file ──
    if os.path.exists(UPLOADED_IDS_FILE):
        os.remove(UPLOADED_IDS_FILE)
        print(f"    ✅  Tracking file '{UPLOADED_IDS_FILE}' deleted.")
    else:
        print(f"    ℹ️   Tracking file '{UPLOADED_IDS_FILE}' not found — skipping.")

    print(f"""
╔══════════════════════════════════════════╗
║            Reset Complete ✅              ║
╠══════════════════════════════════════════╣
║  Qdrant collection  : DELETED            ║
║  Tracking file      : DELETED            ║
╚══════════════════════════════════════════╝

👉  Now run:  python migrate_to_qdrant_http.py
    Expected result:
      New this run         : 44288
      Total vectors Qdrant : 44288  ✅
""")


if __name__ == "__main__":
    main()