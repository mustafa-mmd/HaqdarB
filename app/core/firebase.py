# app/core/firebase.py
"""
HaqDar AI — Firebase Admin SDK Integration
Handles JWT token verification and admin claim checks.
"""
import logging
import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (singleton)
try:
    cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logger.info("✅ Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.error(f"❌ Firebase Admin SDK initialization failed: {e}")
    raise


def verify_token(token: str) -> dict | None:
    """
    Verifies a Firebase ID token and returns the user's UID and Email.
    Returns None if token is invalid or expired.
    """
    if not token:
        return None
    try:
        decoded = auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email")
        }
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase token expired")
        return None
    except auth.InvalidIdTokenError:
        logger.warning("Firebase token invalid")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def verify_token_optional(token: str | None) -> dict | None:
    """Verify token if provided, return None if not provided (anonymous access)."""
    if not token:
        return None
    return verify_token(token)


def is_admin(uid: str) -> bool:
    """Check if user has admin custom claim."""
    try:
        user = auth.get_user(uid)
        custom_claims = user.custom_claims or {}
        return custom_claims.get("admin", False) is True
    except Exception as e:
        logger.error(f"Admin check failed for {uid}: {e}")
        return False


def set_admin_claim(uid: str) -> bool:
    """Grant admin privileges to a user (server-side only)."""
    try:
        auth.set_custom_user_claims(uid, {"admin": True})
        return True
    except Exception as e:
        logger.error(f"Failed to set admin claim for {uid}: {e}")
        return False