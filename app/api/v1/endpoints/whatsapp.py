# app/api/v1/endpoints/whatsapp.py
import os
import hmac
import hashlib
import base64
import logging
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from google.cloud import firestore
from google.oauth2 import service_account

from app.services.gemini_service import get_legal_explanation
from app.services.vector_search import search_similar_laws
from app.services.transcription_service import transcribe_audio
from app.services.intake_agent import classify_legal_category, detect_language_and_script

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Firestore
CREDENTIALS_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "haqdar-key.json")
try:
    if os.path.exists(CREDENTIALS_PATH):
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        db = firestore.Client(credentials=credentials)
    else:
        db = firestore.Client()
except Exception as e:
    logger.error(f"Error initializing Firestore in WhatsApp endpoint: {e}")
    db = None

def validate_twilio_request(request_url: str, post_data: dict, signature: str, auth_token: str) -> bool:
    """Validate Twilio request signature to prevent webhook spoofing."""
    if not auth_token:
        # If no auth token is configured, skip validation for ease of local testing
        return True
    if not signature:
        return False
        
    # Concatenate URL and sorted post data key-values
    data = request_url
    for key in sorted(post_data.keys()):
        data += key + post_data[key]
        
    # Compute HMAC-SHA1
    computed = hmac.new(
        auth_token.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    computed_signature = base64.b64encode(computed).decode('utf-8')
    return hmac.compare_digest(computed_signature, signature)

@router.post("/webhook")
async def twilio_whatsapp_webhook(request: Request):
    """
    Twilio WhatsApp Webhook.
    Receives messages/voice notes from WhatsApp, processes them via HaqDar AI,
    and returns a TwiML response. Includes security validation and async processing.
    """
    # 1. Twilio request signature validation
    signature = request.headers.get("X-Twilio-Signature", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    form_data = await request.form()
    post_dict = {k: v for k, v in form_data.items()}
    
    # Reconstruct request URL (use X-Forwarded-Proto/Host to handle reverse proxies)
    proto = request.headers.get("X-Forwarded-Proto", "http")
    host = request.headers.get("X-Forwarded-Host", request.url.netloc)
    path = request.url.path
    absolute_url = f"{proto}://{host}{path}"
    
    if auth_token and not validate_twilio_request(absolute_url, post_dict, signature, auth_token):
        logger.warning(f"Twilio webhook signature validation failed for URL: {absolute_url}")
        return PlainTextResponse("Forbidden: Invalid Twilio signature", status_code=403)

    # 2. Parse form inputs
    Body = post_dict.get("Body", "")
    MediaUrl0 = post_dict.get("MediaUrl0", None)
    MediaContentType0 = post_dict.get("MediaContentType0", None)

    user_query = Body.strip()

    # 3. Handle Voice Notes (Async downloading via httpx)
    if MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:
        try:
            logger.info(f"Downloading WhatsApp audio attachment from: {MediaUrl0}")
            async with httpx.AsyncClient() as client:
                audio_response = await client.get(MediaUrl0)
                if audio_response.status_code == 200:
                    audio_bytes = audio_response.content
                    # Transcribe using Groq Whisper (Urdu by default for WhatsApp bot MVP)
                    user_query = transcribe_audio(audio_bytes, "whatsapp_audio.ogg", "ur")
                else:
                    logger.error(f"Failed to download audio from Twilio, status code: {audio_response.status_code}")
                    return _twiml_response("معذرت، میں آپ کا وائس نوٹ ڈاؤن لوڈ نہیں کر سکا۔")
        except Exception as e:
            logger.error(f"Voice note processing error: {e}")
            return _twiml_response("وائس نوٹ پروسیس کرنے میں مسئلہ درپیش ہے۔ براہ کرم ٹائپ کر کے سوال پوچھیں۔")

    if not user_query:
        return _twiml_response("HaqDar AI میں خوش آمدید! اپنا قانونی سوال لکھیں یا وائس نوٹ بھیجیں۔")

    # 4. Process Legal Query with RAG
    try:
        # Detect language and script dynamically to support all regional languages
        language, script = detect_language_and_script(user_query)
        category = classify_legal_category(user_query)
        
        matches = search_similar_laws(
            user_query,
            neighbor_count=3,
            language=language if language != "en" else None,
            category=category if category != "general" else None,
        )
        
        # Get text directly from Qdrant payloads (no Firestore dependency)
        law_texts = [m["text"] for m in matches if m.get("text")]
        
        explanation = get_legal_explanation(
            user_query=user_query,
            law_texts=law_texts,
            top_distance=matches[0]["distance"] if matches else 999.0,
            language=language,
            script=script
        )
        
        # Prepend disclaimer before truncation so it is never lost
        disclaimer = "قانونی دستبرداری: یہ معلومات عام رہنمائی کے لیے ہیں۔ یہ پیشہ ورانہ قانونی مشورہ نہیں ہے۔\n\n"
        full_response = disclaimer + explanation
        
        # WhatsApp limits messages to ~1600 characters, truncate if necessary
        if len(full_response) > 1500:
            allowed_len = 1500 - len(disclaimer)
            full_response = disclaimer + explanation[:allowed_len] + "...\n(مکمل جواب کے لیے ہماری ایپ استعمال کریں)"
            
        return _twiml_response(full_response)
        
    except Exception as e:
        logger.error(f"Error processing legal query for WhatsApp: {e}")
        return _twiml_response("معذرت، سرور پر رش کی وجہ سے جواب دینے میں تاخیر ہے۔ بعد میں دوبارہ کوشش کریں۔")


def _twiml_response(message: str) -> PlainTextResponse:
    """Generate valid Twilio XML response for WhatsApp."""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""
    return PlainTextResponse(content=xml, media_type="text/xml")
