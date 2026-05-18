
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("c:/Users/musta/haqdar-ai-backend/haqdar-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
lawyer_id = "65FniQUH6etl9h9gj8M3"

print(f"Listing subcollections for lawyer: {lawyer_id}")
doc_ref = db.collection("lawyers").document(lawyer_id)
collections = doc_ref.collections()
for col in collections:
    print(f"Found subcollection: {col.id}")
    docs = col.get()
    for doc in docs:
        print(f"  - {doc.id}: {doc.to_dict()}")
