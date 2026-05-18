
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("c:/Users/musta/haqdar-ai-backend/haqdar-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
lawyer_id = "65FniQUH6etl9h9gj8M3"

print(f"Checking lawyer main doc: {lawyer_id}")
doc = db.collection("lawyers").document(lawyer_id).get()
if doc.exists:
    print(f"Main Doc: {doc.to_dict()}")
else:
    print("Main Doc NOT FOUND!")
