# upload_to_firestore.py
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH"))
firebase_admin.initialize_app(cred)
db = firestore.client()

def upload_chunks():
    """Upload all chunks from law-embeddings-real.json to Firestore"""
    
    # Check if file exists
    if not os.path.exists("law-embeddings-real.json"):
        print("❌ law-embeddings-real.json not found!")
        return
    
    # Read all chunks
    with open("law-embeddings-real.json", "r", encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    
    print(f"📊 Total chunks to upload: {len(chunks)}")
    
    # Upload in batches of 500 (Firestore limit)
    batch = db.batch()
    count = 0
    total = len(chunks)
    
    for chunk in chunks:
        doc_ref = db.collection("law_corpus").document(chunk["id"])
        batch.set(doc_ref, chunk)
        count += 1
        
        # Commit every 500 documents
        if count % 500 == 0:
            batch.commit()
            print(f"   Uploaded {count}/{total} chunks...")
            batch = db.batch()
    
    # Commit remaining
    if count % 500 != 0:
        batch.commit()
    
    print(f"\n✅ Successfully uploaded {count} chunks to Firestore 'law_corpus' collection")

def verify_upload():
    """Verify upload by counting documents"""
    docs = db.collection("law_corpus").limit(10).stream()
    doc_count = len(list(db.collection("law_corpus").get()))
    print(f"📊 Verification: {doc_count} chunks in Firestore")

if __name__ == "__main__":
    upload_chunks()
    verify_upload()