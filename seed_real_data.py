import os
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client()

def seed_lawyers():
    lawyers = [
        {
            "name": "Adv. Tariq Mahmood",
            "specialty": "Criminal Law",
            "experience": "15 Years",
            "city": "Lahore",
            "rating": 4.9,
            "reviews": 120,
            "avatar": "T",
            "description": "Expert in criminal defense, bail applications, and high court appeals.",
            "verified": True,
            "email": "tariq@lawyer.pk",
            "phone": "+923001234567"
        },
        {
            "name": "Adv. Ayesha Siddiqa",
            "specialty": "Family Law",
            "experience": "8 Years",
            "city": "Karachi",
            "rating": 4.8,
            "reviews": 85,
            "avatar": "A",
            "description": "Specialized in Khula, child custody, and maintenance petitions.",
            "verified": True,
            "email": "ayesha@lawyer.pk",
            "phone": "+923219876543"
        },
        {
            "name": "Adv. Ali Reza",
            "specialty": "Property Law",
            "experience": "12 Years",
            "city": "Islamabad",
            "rating": 4.7,
            "reviews": 94,
            "avatar": "A",
            "description": "Handles real estate disputes, tenant eviction, and property transfers.",
            "verified": True,
            "email": "ali@lawyer.pk",
            "phone": "+923335556667"
        }
    ]
    
    for l in lawyers:
        db.collection("lawyers").add(l)
    print("Seeded lawyers.")

def seed_forum():
    posts = [
        {
            "author": "Ahmad R.",
            "author_id": "system",
            "title": "How long does a Khula process take in Punjab?",
            "content": "I want to file for Khula in Family Court Lahore. Can someone tell me the exact timeframe and process according to the latest amendments?",
            "tags": ["Family Law", "Khula"],
            "likes": 12,
            "replies": 4,
            "language": "en",
            "timestamp": firestore.SERVER_TIMESTAMP
        },
        {
            "author": "User_992",
            "author_id": "system",
            "title": "کیا مکان مالک کرایہ دار کو بغیر نوٹس نکال سکتا ہے؟",
            "content": "میرے مکان مالک نے مجھے کل گھر خالی کرنے کا بولا ہے حالانکہ ہمارا 11 مہینے کا معاہدہ ہے۔ کیا یہ قانونی ہے؟",
            "tags": ["Property", "Tenancy", "Urdu"],
            "likes": 24,
            "replies": 8,
            "language": "ur",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
    ]
    for p in posts:
        db.collection("forum_posts").add(p)
    print("Seeded forum posts.")

if __name__ == "__main__":
    seed_lawyers()
    seed_forum()
