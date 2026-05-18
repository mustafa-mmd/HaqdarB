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
    all_docs = list(db.collection("legal_aid").stream())

    # ── Pass 1: exact, case‑insensitive ──
    results = []
    for doc in all_docs:
        data = doc.to_dict()
        if data.get("city", "").strip().lower() == query:
            results.append(_format(data))
    if results:
        return results

    # ── Pass 2: substring match ──
    for doc in all_docs:
        data = doc.to_dict()
        doc_city = data.get("city", "").strip().lower()
        if query in doc_city or doc_city in query:
            results.append(_format(data))
    if results:
        return results

    # ── Pass 3: fuzzy match using difflib ──
    known_lower = [c.lower() for c in KNOWN_CITIES]
    close = difflib.get_close_matches(query, known_lower, n=1, cutoff=0.7)
    if close:
        matched_city = close[0]
        for doc in all_docs:
            data = doc.to_dict()
            if data.get("city", "").strip().lower() == matched_city:
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