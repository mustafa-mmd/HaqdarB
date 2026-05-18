# app/services/peca_agent.py
import os
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")

from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

PECA_SYSTEM_INSTRUCTION = """
You are a specialist PECA (Prevention of Electronic Crimes Act) agent for HaqDar AI.
You analyse cybercrime complaints and provide the following in **strict JSON format** with no extra text.
The JSON must have these keys:
- "peca_sections": list of strings of relevant PECA 2016 sections (e.g. ["Section 20", "Section 24"])
- "severity": one of "low", "medium", "high"
- "explanation": a clear, plain‑language explanation in the same language as the user's query (Urdu/English/Punjabi etc.), with specific actions the victim can take.
- "fir_draft": a pre‑filled FIR draft text in English that includes the complainant details placeholder, accused description, evidence summary, and exact PECA sections violated.

If the query is not a cybercrime or does not relate to PECA, return a JSON with "peca_sections": [], "severity": "low", "explanation": "This does not appear to be a PECA related issue.", "fir_draft": "".
"""

def get_peca_analysis(user_query: str) -> dict:
    import json
    config = GenerateContentConfig(
        system_instruction=PECA_SYSTEM_INSTRUCTION,
        response_mime_type="application/json"
    )
    prompt = f"Cybercrime complaint: {user_query}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        # fallback if Gemini doesn't return proper JSON
        return {
            "peca_sections": [],
            "severity": "low",
            "explanation": "Sorry, I could not analyse this cybercrime report. Please try again.",
            "fir_draft": ""
        }