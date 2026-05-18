# app/services/transcription_service.py
"""
Pro‑Level Multilingual Transcription Service – Groq Whisper + Gemini
Optimized for HaqDar AI. Supports Urdu, Pashto, Punjabi, Sindhi, Balochi, English.
"""
import os
import tempfile
import re
import logging
import base64
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from app.services.gemini_service import refine_transcription, client as gemini_client

logger = logging.getLogger(__name__)

_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)

# Groq Whisper language codes
LANG_MAP = {
    "ur": "ur",
    "ps": "ps",
    "pa": "pa",
    "sd": "sd",
    "bal": None,
    "en": "en",
}

OPTIMISED_PROMPT = (
    "FIR, arrest, bail, remand, police, investigation, prosecutor, accused, "
    "complainant, witness, evidence, trial, conviction, acquittal, appeal, "
    "murder, theft, robbery, fraud, cheating, forgery, assault, kidnapping, "
    "harassment, trespass, corruption, bribery, narcotics, terrorism, "
    "divorce, khula, maintenance, custody, inheritance, property, land, tenant, "
    "pension, constitution, rights, consumer, cybercrime, FIA, PTA, plaintiff, "
    "defendant, stay, affidavit, Lahore, Karachi, Islamabad, Peshawar, Quetta, "
    "ضمانت, گرفتاری, تفتیش, مقدمہ, فوجداری, دیوانی, وکیل, عدالت, اپیل, "
    "شادی, طلاق, خلع, نفقہ, حوالگی, وراثت, جائیداد, کرایہ, قبضہ, "
    "آئین, حقوق, سائبر, ہراسانی, چوری, دھوکہ, پښتو, سنڌي"
)

# Safety check
if len(OPTIMISED_PROMPT) > 700:
    OPTIMISED_PROMPT = OPTIMISED_PROMPT[:697] + "..."

def transcribe_audio(audio_bytes: bytes, filename: str, lang: str = "ur") -> str:
    """
    Transcribes audio using Groq Whisper. Balochi uses Gemini Vertex AI.
    """
    if lang == "bal":
        return _transcribe_with_gemini(audio_bytes, filename)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in .env")

    client = Groq(api_key=api_key)
    whisper_lang = LANG_MAP.get(lang, "ur")

    suffix = ".webm" if "webm" in filename.lower() else ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            print(f"DEBUG: Sending prompt with length {len(OPTIMISED_PROMPT)}")
            
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file),
                model="whisper-large-v3",
                language=whisper_lang,
                prompt=OPTIMISED_PROMPT,
                temperature=0.0,
                response_format="verbose_json",
            )

        raw_text = ""
        if hasattr(transcription, 'text'):
            raw_text = transcription.text.strip()
        elif isinstance(transcription, dict):
            raw_text = transcription.get("text", "").strip()
        else:
            raw_text = str(transcription).strip()

        hallucinations = [
            "Thank you for watching", "Please subscribe", "Subtitles by",
            "YouTube", "Subscribe to my channel", "Like and share"
        ]
        if any(h.lower() in raw_text.lower() for h in hallucinations) and len(raw_text) < 60:
            raw_text = ""

        if not raw_text:
            return ""

        try:
            refined = refine_transcription(raw_text, target_lang=lang)
        except Exception as e:
            logger.warning(f"Refinement failed: {e}")
            refined = raw_text

        refined = re.sub(r'[\u0900-\u097F]', '', refined)
        if lang != "pa_guru":
            refined = re.sub(r'[\u0A00-\u0A7F]', '', refined)

        return refined.strip()

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def _transcribe_with_gemini(audio_bytes: bytes, filename: str) -> str:
    """
    Balochi transcription using Gemini Vertex AI (same client as refinement).
    Ensures Balochi works without needing a separate GEMINI_API_KEY.
    """
    from google.genai.types import Part

    mime_type = "audio/webm" if "webm" in filename.lower() else "audio/wav"
    
    prompt = (
        "Transcribe this Balochi audio accurately into Balochi text (Arabic script). "
        "Preserve all legal terms and names. Output ONLY the transcription, no extra text."
    )

    try:
        # Use the Vertex AI client already initialized in gemini_service
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash", # Consistent with refinement
            contents=[
                Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt
            ]
        )
        return response.text.strip() if response.text else ""
    except Exception as e:
        logger.error(f"Balochi Gemini transcription failed: {e}")
        return ""