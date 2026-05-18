# app/services/case_analyzer.py
"""
HaqDar AI — AI Case Strength Analyzer
Analyzes a user's legal situation and provides:
  - Case strength score (0-100)
  - Outcome prediction
  - Required documents checklist
  - Recommended next action
"""
import os
import json
import logging
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")

from app.core.config import settings
import time

# Primary Client: Vertex AI (Higher Quotas)
client_vertex = genai.Client(
    vertexai=True,
    project=settings.PROJECT_ID,
    location=settings.LOCATION
)

# Secondary/Fallback Client: AI Studio
client_api = genai.Client(api_key=settings.GEMINI_API_KEY)

CASE_ANALYZER_INSTRUCTION = r"""
You are HaqDar AI's Case Strength Analyzer — an elite legal assessment engine for Pakistani law.
Your role is to analyze the user's legal situation and provide an objective, structured assessment.

[STRICT INSTRUCTIONS]
- Output MUST be strictly valid JSON. No markdown fences, no preamble.
- Be objective, balanced, and cite specific Pakistani laws.
- The case_score must be an integer 0-100.
- Language: Respond in the EXACT SAME LANGUAGE as the user's query.
- Never guarantee outcomes. Always include the disclaimer.

[JSON SCHEMA — MANDATORY]
{
  "case_score": <integer 0-100>,
  "score_label": "<Weak | Moderate | Strong | Very Strong>",
  "score_reasoning": "<2-3 sentences explaining the score>",
  "legal_domain": "<which area of law applies>",
  "applicable_laws": ["<law name and section>"],
  "outcome_prediction": {
    "favorable_scenario": "<what happens if case is won>",
    "unfavorable_scenario": "<what happens if case is lost>",
    "most_likely_outcome": "<balanced assessment>"
  },
  "required_documents": [
    {"document": "<document name>", "purpose": "<why it's needed>", "priority": "high|medium|low"}
  ],
  "recommended_action": {
    "primary": "<most urgent recommended action>",
    "action_type": "<file_fir | hire_lawyer | send_legal_notice | go_to_court | negotiate | contact_authority | other>",
    "timeline": "<urgency — e.g., 'Within 24 hours' or 'Within 30 days'>",
    "authority": "<which authority/court/agency to approach>"
  },
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "free_legal_aid_available": <true|false>,
  "estimated_duration": "<realistic timeline for resolution>",
  "disclaimers": [
    "This assessment is for informational purposes only and does NOT constitute legal advice.",
    "Case outcomes depend on many factors including evidence quality, court discretion, and legal representation.",
    "Consult a qualified Pakistani lawyer before taking any legal action."
  ]
}

[SCORING GUIDE]
0-25:  Weak — insufficient evidence, legal basis unclear, low chance of success
26-50: Moderate — some legal basis, outcome uncertain, needs strong documentation
51-75: Strong — clear legal violations, good evidence potential, favorable laws apply
76-100: Very Strong — clear-cut case, strong legal basis, strong likelihood of success
"""


def analyze_case_strength(user_query: str, language: str = "en") -> dict:
    """
    Analyze the strength of a user's legal case.
    Returns a comprehensive assessment JSON.
    """
    config = GenerateContentConfig(
        system_instruction=CASE_ANALYZER_INSTRUCTION,
        response_mime_type="application/json",
        temperature=0.1,
    )

    prompt = (
        f"User's Legal Situation (Language: {language}):\n"
        f"{user_query}\n\n"
        "Analyze this situation under Pakistani law and provide a complete case strength assessment."
    )

    max_retries = 3
    for attempt in range(max_retries):
        # Primary: Vertex AI | Fallback: AI Studio
        use_vertex = (attempt % 2 == 0) 
        target_client = client_vertex if use_vertex else client_api
        target_model = "gemini-2.5-flash"
        
        try:
            response = target_client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Case analyzer JSON parse error: {e}")
            return _fallback_case_response()
        except Exception as e:
            logger.warning(f"Case analyzer attempt {attempt+1} failed on {target_model}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return _fallback_case_response()


def _fallback_case_response() -> dict:
    return {
        "case_score": 0,
        "score_label": "Unknown",
        "score_reasoning": "Unable to analyze case at this time. Please try again with more details.",
        "legal_domain": "Unknown",
        "applicable_laws": [],
        "outcome_prediction": {
            "favorable_scenario": "Unable to determine",
            "unfavorable_scenario": "Unable to determine",
            "most_likely_outcome": "Please consult a lawyer for a proper assessment.",
        },
        "required_documents": [],
        "recommended_action": {
            "primary": "Consult a qualified lawyer",
            "action_type": "hire_lawyer",
            "timeline": "As soon as possible",
            "authority": "Local Bar Association",
        },
        "strengths": [],
        "weaknesses": [],
        "next_steps": ["Consult a qualified lawyer for a proper legal assessment."],
        "free_legal_aid_available": True,
        "estimated_duration": "Unknown",
        "disclaimers": [
            "This assessment is for informational purposes only and does NOT constitute legal advice.",
            "Consult a qualified Pakistani lawyer before taking any legal action.",
        ],
    }
