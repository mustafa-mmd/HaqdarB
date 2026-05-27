# app/core/validation.py
"""
HaqDar AI — Startup Environment Validation
Validates critical configuration on startup so the backend fails fast
on misconfiguration rather than failing silently at query time.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_environment():
    """
    Validate all critical environment variables are present.
    Fails fast with ValueError if crucial variables are missing.
    """
    # Required in every environment
    critical_vars = {
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
    }

    if settings.ENVIRONMENT == "production":
        production_critical_vars = {
            "PROJECT_ID": settings.PROJECT_ID,
            "LOCATION": settings.LOCATION,
            "QDRANT_URL": settings.QDRANT_URL,
            "QDRANT_API_KEY": settings.QDRANT_API_KEY,
            "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
        }
        critical_vars.update(production_critical_vars)
    else:
        # Development: warn but don't crash for cloud variables
        dev_warn_vars = {
            "PROJECT_ID": settings.PROJECT_ID,
            "QDRANT_URL": settings.QDRANT_URL,
            "QDRANT_API_KEY": settings.QDRANT_API_KEY,
            "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
        }
        missing_dev = [
            var for var, val in dev_warn_vars.items()
            if not val or val.strip() == ""
        ]
        if missing_dev:
            logger.warning(
                f"DEVELOPMENT WARNING: Missing non-blocking variables: "
                f"{', '.join(missing_dev)}. "
                "Qdrant vector search and Twilio WhatsApp may be degraded."
            )

    missing = [
        var for var, val in critical_vars.items()
        if not val or val.strip() == ""
    ]

    if missing:
        error_msg = (
            f"CRITICAL CONFIGURATION ERROR: Missing environment variables: "
            f"{', '.join(missing)}. Application cannot start."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"Environment validation successful. "
        f"All critical settings verified (Environment: {settings.ENVIRONMENT})."
    )