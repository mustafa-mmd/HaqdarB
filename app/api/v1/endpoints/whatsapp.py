import os
import requests
from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
from typing import Optional
from app.services.gemini_service import get_legal_explanation
from app.services.vector_search import search_similar_laws
from app.services.transcription_service import transcribe_audio

router = APIRouter()

@router.post("/webhook")
async def twilio_whatsapp_webhook(
    Body: Optional[str] = Form(""),
    From: str = Form(...),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None)
):
    """
    Twilio WhatsApp Webhook.
    Receives messages/voice notes from WhatsApp, processes them via HaqDar AI,
    and returns a TwiML response.
    """
    user_query = Body.strip()

    # 1. Handle Voice Notes
    if MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:
        try:
            # Download audio from Twilio
            audio_response = requests.get(MediaUrl0)
            if audio_response.status_code == 200:
                audio_bytes = audio_response.content
                # Transcribe using Groq Whisper (assuming Urdu by default for WhatsApp bot MVP)
                user_query = transcribe_audio(audio_bytes, "whatsapp_audio.ogg", "ur")
            else:
                return _twiml_response("معذرت، میں آپ کا وائس نوٹ ڈاؤن لوڈ نہیں کر سکا۔")
        except Exception as e:
            return _twiml_response("وائس نوٹ پروسیس کرنے میں مسئلہ درپیش ہے۔ براہ کرم ٹائپ کر کے سوال پوچھیں۔")

    if not user_query:
        return _twiml_response("HaqDar AI میں خوش آمدید! اپنا قانونی سوال لکھیں یا وائس نوٹ بھیجیں۔")

    # 2. Process Legal Query
    try:
        matches = search_similar_laws(user_query, neighbor_count=3)
        law_texts = []
        # In a real scenario we'd fetch the actual laws from Firestore. 
        # For this MVP webhook, we'll pass an empty context or mock if Firestore is unavailable in this scope.
        
        explanation = get_legal_explanation(
            user_query=user_query,
            law_texts=law_texts,
            top_distance=0.0,
            language="ur", # Default to Urdu for Pakistani WhatsApp users
            script="arabic"
        )
        
        # 3. WhatsApp limits messages to ~1600 characters, truncate if necessary
        if len(explanation) > 1500:
            explanation = explanation[:1500] + "...\n(مکمل جواب کے لیے ہماری ایپ استعمال کریں)"
            
        return _twiml_response(explanation)
        
    except Exception as e:
        return _twiml_response("معذرت، سرور پر رش کی وجہ سے جواب دینے میں تاخیر ہے۔ بعد میں دوبارہ کوشش کریں۔")


def _twiml_response(message: str) -> PlainTextResponse:
    """Generate valid Twilio XML response for WhatsApp."""
    # Using simple plain text response with XML structure for TwiML
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""
    return PlainTextResponse(content=xml, media_type="text/xml")
