
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("c:/Users/musta/haqdar-ai-backend/haqdar-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
lawyer_id = "65FniQUH6etl9h9gj8M3"

print(f"Checking lawyer: {lawyer_id}")
for folder in ["reviews", "reviews_list", "public_feedback"]:
    docs = db.collection("lawyers").document(lawyer_id).collection(folder).get()
    print(f"Folder '{folder}' has {len(docs)} documents.")
    for doc in docs:
        print(f" - {doc.to_dict()}")
