# upload_real_laws_to_firestore.py
import json
import os
from google.cloud import firestore
from google.oauth2 import service_account

# Path to your service account key
CREDENTIALS_PATH = "haqdar-key.json"
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
db = firestore.Client(credentials=credentials)

# Path to the real law embeddings file
INPUT_FILE = "law-embeddings-real.json"
STATE_FILE = "uploaded_ids.txt"

# Load already uploaded IDs to skip them
uploaded_ids = set()
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        uploaded_ids = set(line.strip() for line in f)

print(f"Skipping {len(uploaded_ids)} already uploaded chunks...")

count = 0
new_uploads = 0
with open(INPUT_FILE, "r", encoding="utf-8") as f, open(STATE_FILE, "a", encoding="utf-8") as state_f:
    for line_num, line in enumerate(f, 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as e:
            print(f"Skipping corrupted JSON on line {line_num}: {e}")
            continue
            
        doc_id = record["id"]
        
        if doc_id in uploaded_ids:
            continue
            
        text = record["text"]
        source = record.get("source", "unknown")
        
        # Write to Firestore
        db.collection("law_corpus").document(doc_id).set({
            "text": text,
            "source": source
        })
        
        # Record success
        state_f.write(doc_id + "\n")
        state_f.flush()
        
        new_uploads += 1
        if new_uploads % 100 == 0:
            print(f"Uploaded {new_uploads} new documents...")

print(f"✅ Complete. Added {new_uploads} new law chunks to Firestore.")