# app/services/referral_agent.py
import os
import difflib
from google.cloud import firestore
from google.oauth2 import service_account

CREDENTIALS_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "haqdar-key.json")
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
db = firestore.Client(credentials=credentials)

# Known cities – update this list when you add new cities to the legal_aid collection
KNOWN_CITIES = [
    "Lahore",
    "Karachi",
    "Islamabad",
    "Peshawar",
    "Quetta",
    "Pakistan‑wide",
    "Hyderabad",
    "Multan",
    "Faisalabad",
    "Rawalpindi",
]

# Mapping of Pakistani provinces → capital city (for user‑friendly province search)
PROVINCE_TO_CAPITAL = {
    "balochistan": "quetta",
    "punjab": "lahore",
    "sindh": "karachi",
    "khyber pakhtunkhwa": "peshawar",
    "khyber-pakhtunkhwa": "peshawar",
    "kpk": "peshawar",
    "islamabad capital territory": "islamabad",
}


def _resolve_query(raw_city: str) -> str:
    """
    If the user typed a province name, return the capital city.
    Otherwise return the cleaned input unchanged.
    """
    cleaned = raw_city.strip().lower() if raw_city else ""
    return PROVINCE_TO_CAPITAL.get(cleaned, cleaned)


def get_legal_aid_by_city(city: str):
    """
    Search the 'legal_aid' collection with flexible matching:
    1. Resolve province → capital
    2. Exact case‑insensitive match
    3. Substring match (e.g., 'pesh' → 'Peshawar')
    4. Fuzzy match (e.g., 'peshawer' → 'Peshawar')
    """
    if not city or not city.strip():
        return []

    # Step 0 – convert province to city if needed
    query = _resolve_query(city)
    
    # Try exact match first on capitalized city field to leverage Firestore index
    results = []
    formatted_city = query.title() if query != "pakistan-wide" else "Pakistan-wide"
    docs = db.collection("legal_aid").where("city", "==", formatted_city).stream()
    for doc in docs:
        data = doc.to_dict()
        results.append(_format(data))
        
    if results:
        return results

    # If no results, do substring/fuzzy matching in-memory against KNOWN_CITIES
    matched_cities = []
    
    # Pass 1: exact matching against KNOWN_CITIES list
    for c in KNOWN_CITIES:
        if c.lower() == query:
            matched_cities.append(c)
            
    # Pass 2: substring matching against KNOWN_CITIES list
    if not matched_cities:
        for c in KNOWN_CITIES:
            c_low = c.lower()
            if query in c_low or c_low in query:
                matched_cities.append(c)
                
    # Pass 3: fuzzy matching against KNOWN_CITIES list
    if not matched_cities:
        known_lower = [c.lower() for c in KNOWN_CITIES]
        close = difflib.get_close_matches(query, known_lower, n=1, cutoff=0.7)
        if close:
            matched_cities.extend([c for c in KNOWN_CITIES if c.lower() == close[0]])
            
    # Query Firestore ONLY for the matched known cities
    if matched_cities:
        for m_city in matched_cities:
            docs = db.collection("legal_aid").where("city", "==", m_city).stream()
            for doc in docs:
                data = doc.to_dict()
                results.append(_format(data))
                
    return results


def _format(data: dict) -> dict:
    """Helper to format a Firestore document into the API response."""
    return {
        "name": data.get("name", ""),
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "services": data.get("services", ""),
        "city": data.get("city", ""),
    }