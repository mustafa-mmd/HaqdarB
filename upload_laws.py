import json
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin with your service account
cred = credentials.Certificate("haqdar-key.json")
firebase_admin.initialize_app(cred)

# Get Firestore client (defaults to the "(default)" database)
db = firestore.client()

with open("law-embeddings.json", "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        doc_id = record["id"]
        db.collection("law_corpus").document(doc_id).set({
            "text": record["text"],
            "source": record.get("source", "unknown")
        })
        print(f"Uploaded: {doc_id}")

print("✅ Law corpus uploaded to Firestore.")