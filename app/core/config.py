# app/core/config.py
"""
HaqDar AI — Centralized Application Configuration
All settings are loaded from environment variables with sensible defaults.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application-wide configuration settings."""

    # ── Application ──
    APP_NAME: str = "HaqDar AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ── CORS ──
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://haqdar.pk",
        "https://www.haqdar.pk",
        "https://haqdar-app.web.app",
        "https://haqdar-app.firebaseapp.com",
    ]

    # ── Google Cloud / Vertex AI (embeddings only — index vars removed) ──
    PROJECT_ID: str = os.getenv("PROJECT_ID", "")
    LOCATION: str = os.getenv("LOCATION", "us-central1")

    # ── Qdrant Vector Database ──
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "law_corpus")

    # ── AI Keys ──
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── Firebase ──
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH", "haqdar-key.json"
    )

    # ── Rate Limiting ──
    RATE_LIMIT_FREE_PER_MINUTE: str = "20/minute"
    RATE_LIMIT_PRO_PER_MINUTE: str = "100/minute"

    # ── Gemini Model Names ──
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_FLASH_LITE_MODEL: str = "gemini-2.5-flash-lite"

    # ── Notifications (Twilio & SendGrid) ──
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SYSTEM_EMAIL: str = os.getenv("SYSTEM_EMAIL", "notifications@haqdar.pk")

    # ── Timeouts ──
    GEMINI_TIMEOUT_SECONDS: int = 60
    VECTOR_SEARCH_TIMEOUT_SECONDS: int = 10


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()


settings = get_settings()