# app/services/document_agent.py
"""
HaqDar AI — Legal Document Analysis Agent
Analyzes uploaded legal documents (images or PDFs) using Gemini Vision.
Supports: Court notices, FIRs, contracts, eviction notices, property deeds, etc.
"""
import base64
import json
import logging
import os
from google import genai
from google.genai.types import GenerateContentConfig, Part, HttpOptions
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")

from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

DOCUMENT_ANALYSIS_SYSTEM = """
You are HaqDar AI's Legal Document Analysis Agent.
You are an expert at analyzing Pakistani legal documents.

Analyze the uploaded document and extract all key information.
Output MUST be valid JSON with EXACTLY these fields. No markdown fences.

{
  "document_type": "<type of document — e.g., FIR, Eviction Notice, Employment Contract, Court Summons, Sale Deed, etc.>",
  "language_detected": "<English | Urdu | Punjabi | Sindhi | Pashto | Mixed>",
  "key_parties": [
    {"role": "<Complainant | Accused | Landlord | Tenant | Employer | Employee | etc.>", "name": "<name if visible>"}
  ],
  "dates": {
    "document_date": "<date of document>",
    "incident_date": "<date of incident if mentioned>",
    "deadline_date": "<any deadline or court date>"
  },
  "legal_claims": "<summary of legal claims or reasons stated>",
  "potential_violations": ["<law name or section that may be violated>"],
  "document_sections": [
    {"heading": "<section name>", "content": "<extracted text or summary>"}
  ],
  "action_required": {
    "required": <true|false>,
    "deadline": "<deadline if any>",
    "what_to_do": "<specific action the recipient must take>"
  },
  "severity": "<low | medium | high | critical>",
  "summary": "<plain-language 3-5 sentence summary of what this document means for the recipient>",
  "red_flags": ["<concerning clause or term>"],
  "recommended_next_steps": ["<step 1>", "<step 2>"],
  "disclaimers": ["This analysis is AI-generated and should not substitute professional legal review."]
}
"""


def analyze_legal_document(image_base64: str, mime_type: str = "image/jpeg") -> dict:
    """
    Analyze a legal document image using Gemini Vision.
    Returns a structured JSON analysis.
    """
    config = GenerateContentConfig(
        system_instruction=DOCUMENT_ANALYSIS_SYSTEM,
        response_mime_type="application/json",
        temperature=0.1,
    )

    try:
        contents = [
            Part.from_bytes(
                data=base64.b64decode(image_base64),
                mime_type=mime_type,
            ),
            "Please analyze this Pakistani legal document and extract all key information as specified.",
        ]

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        result = json.loads(response.text)
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Document analysis JSON parse error: {e}")
        return _fallback_doc_response()
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return _fallback_doc_response()


def analyze_legal_document_pdf_pages(pages_base64: list[str]) -> dict:
    """
    Analyze a multi-page PDF by processing each page as an image.
    pages_base64: list of base64-encoded page images
    """
    config = GenerateContentConfig(
        system_instruction=DOCUMENT_ANALYSIS_SYSTEM,
        response_mime_type="application/json",
        temperature=0.1,
    )

    try:
        contents = []
        for i, page_b64 in enumerate(pages_base64[:10]):  # max 10 pages
            contents.append(
                Part.from_bytes(
                    data=base64.b64decode(page_b64),
                    mime_type="image/jpeg",
                )
            )
        contents.append(
            f"This is a {len(pages_base64)}-page legal document. "
            "Please analyze the entire document and extract all key information as specified."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        return json.loads(response.text)

    except json.JSONDecodeError as e:
        logger.error(f"PDF analysis JSON parse error: {e}")
        return _fallback_doc_response()
    except Exception as e:
        logger.error(f"PDF analysis error: {e}")
        return _fallback_doc_response()


def _fallback_doc_response() -> dict:
    return {
        "document_type": "Unknown",
        "language_detected": "Unknown",
        "key_parties": [],
        "dates": {"document_date": "", "incident_date": "", "deadline_date": ""},
        "legal_claims": "Unable to extract legal claims from this document.",
        "potential_violations": [],
        "document_sections": [],
        "action_required": {"required": False, "deadline": "", "what_to_do": ""},
        "severity": "low",
        "summary": "I was unable to analyze this document. Please ensure the image is clear and try again.",
        "red_flags": [],
        "recommended_next_steps": ["Ensure document image is clear and readable.", "Try uploading again."],
        "disclaimers": ["This analysis is AI-generated and should not substitute professional legal review."],
    }