# app/services/usage_service.py
"""
HaqDar AI — Usage Tracking & Quota Enforcement Service
Tracks per-user API usage and enforces subscription tier limits.
"""
import logging
from datetime import datetime, timezone
from google.cloud import firestore

logger = logging.getLogger(__name__)

# ── Quota limits per plan (per day for queries, per month for others) ──
PLAN_LIMITS = {
    "free": {
        "queries_per_day": 100,
        "drafts_per_month": 50,
        "analyses_per_month": 50,
        "documents_per_month": 50,
    },
    "pro": {
        "queries_per_day": 500,
        "drafts_per_month": 50,
        "analyses_per_month": 20,
        "documents_per_month": 50,
    },
    "firm": {
        "queries_per_day": 9999,
        "drafts_per_month": 9999,
        "analyses_per_month": 9999,
        "documents_per_month": 9999,
    },
}

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def get_user_plan(uid: str) -> str:
    """Get the user's subscription plan from Firestore. Defaults to 'free'."""
    try:
        db = _get_db()
        doc = db.collection("users").document(uid).collection("profile").document("settings").get()
        if doc.exists:
            return doc.to_dict().get("plan", "free")
    except Exception as e:
        logger.error(f"Failed to get user plan for {uid}: {e}")
    return "free"


def get_usage_stats(uid: str) -> dict:
    """Get current usage stats for a user."""
    try:
        db = _get_db()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        day_doc = db.collection("users").document(uid).collection("usage_daily").document(today).get()
        month_doc = db.collection("users").document(uid).collection("usage_monthly").document(month).get()

        day_data = day_doc.to_dict() if day_doc.exists else {}
        month_data = month_doc.to_dict() if month_doc.exists else {}

        return {
            "queries_today": day_data.get("queries", 0),
            "drafts_this_month": month_data.get("drafts", 0),
            "analyses_this_month": month_data.get("analyses", 0),
            "documents_this_month": month_data.get("documents", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get usage stats for {uid}: {e}")
        return {
            "queries_today": 0,
            "drafts_this_month": 0,
            "analyses_this_month": 0,
            "documents_this_month": 0,
        }


def check_and_increment_usage(uid: str, feature: str) -> tuple[bool, str]:
    """
    Check if user is within quota, then increment usage counter.
    Returns (allowed: bool, message: str).
    feature: 'query' | 'draft' | 'analysis' | 'document'
    """
    try:
        db = _get_db()
        
        # ENSURE TOP-LEVEL USER DOC EXISTS (for Admin Dashboard)
        # We try to get user info if possible, or just create a stub
        user_ref = db.collection("users").document(uid)
        if not user_ref.get().exists:
            user_ref.set({
                "uid": uid,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "lastActive": firestore.SERVER_TIMESTAMP,
                "plan": "free"
            }, merge=True)
        else:
            user_ref.update({"lastActive": firestore.SERVER_TIMESTAMP})

        plan = get_user_plan(uid)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        stats = get_usage_stats(uid)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        if feature == "query":
            if stats["queries_today"] >= limits["queries_per_day"]:
                return False, f"Daily limit reached ({limits['queries_per_day']} queries/day). Upgrade to Pro for unlimited queries."
            # Increment
            db.collection("users").document(uid).collection("usage_daily").document(today).set(
                {"queries": firestore.Increment(1)}, merge=True
            )

        elif feature == "draft":
            if stats["drafts_this_month"] >= limits["drafts_per_month"]:
                return False, f"Monthly draft limit reached ({limits['drafts_per_month']} drafts/month). Upgrade to Pro."
            db.collection("users").document(uid).collection("usage_monthly").document(month).set(
                {"drafts": firestore.Increment(1)}, merge=True
            )

        elif feature == "analysis":
            if stats["analyses_this_month"] >= limits["analyses_per_month"]:
                return False, f"Monthly analysis limit reached. Upgrade to Pro for more analyses."
            db.collection("users").document(uid).collection("usage_monthly").document(month).set(
                {"analyses": firestore.Increment(1)}, merge=True
            )

        elif feature == "document":
            if stats["documents_this_month"] >= limits["documents_per_month"]:
                return False, f"Monthly document limit reached. Upgrade to Pro for more documents."
            db.collection("users").document(uid).collection("usage_monthly").document(month).set(
                {"documents": firestore.Increment(1)}, merge=True
            )

        return True, "OK"

    except Exception as e:
        logger.error(f"Usage check failed for {uid}: {e}")
        # Fail open — don't block users if usage tracking has an issue
        return True, "OK"


def get_user_profile(uid: str) -> dict:
    """Get the complete user profile from Firestore."""
    try:
        db = _get_db()
        doc = db.collection("users").document(uid).collection("profile").document("settings").get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        logger.error(f"Failed to get profile for {uid}: {e}")
    return {"plan": "free", "onboarding_complete": False}


def update_user_profile(uid: str, data: dict) -> bool:
    """Update user profile fields."""
    try:
        db = _get_db()
        db.collection("users").document(uid).collection("profile").document("settings").set(
            {**data, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to update profile for {uid}: {e}")
        return False


def log_audit_event(uid: str, event_type: str, metadata: dict = None) -> None:
    """
    Log an immutable audit event to Firestore for compliance.
    event_type: 'query' | 'draft_generated' | 'document_analyzed' | 'login' | 'logout'
    """
    try:
        db = _get_db()
        db.collection("audit_log").add({
            "uid": uid,
            "event": event_type,
            "metadata": metadata or {},
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Audit log failed: {e}")
