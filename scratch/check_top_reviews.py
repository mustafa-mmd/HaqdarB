
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("c:/Users/musta/haqdar-ai-backend/haqdar-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
lawyer_id = "65FniQUH6etl9h9gj8M3"

print(f"Checking top-level 'reviews' for lawyer_id: {lawyer_id}")
docs = db.collection("reviews").where("lawyer_id", "==", lawyer_id).get()
print(f"Found {len(docs)} top-level reviews.")
for doc in docs:
    print(f" - {doc.to_dict()}")
