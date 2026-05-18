
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate("c:/Users/musta/haqdar-ai-backend/haqdar-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
print("Listing ALL lawyers in the database...")
docs = db.collection("lawyers").get()
for doc in docs:
    data = doc.to_dict()
    print(f"Lawyer ID: {doc.id}, Name: {data.get('name')}, UID: {data.get('uid')}")
