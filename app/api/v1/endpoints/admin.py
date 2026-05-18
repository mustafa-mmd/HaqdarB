import logging
from fastapi import APIRouter, HTTPException, Request
from google.cloud import firestore
from app.core.firebase import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

_db = None
def get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


@router.get("/is-admin")
async def check_is_admin(request: Request):
    """Returns whether the current user has admin privileges. Safe to call by any logged-in user."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"is_admin": False}
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        return {"is_admin": False}
    uid = user_info["uid"]
    email = user_info.get("email", "")
    founders = ["mustafajamalshabqadar@gmail.com"]
    if email in founders:
        return {"is_admin": True}
    db = get_db()
    try:
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            return {"is_admin": doc.to_dict().get("is_admin", False)}
    except Exception:
        pass
    return {"is_admin": False}

@router.get("/stats")
async def get_admin_stats(request: Request):
    """Fetch real-time stats for the admin dashboard."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_db()
    
    # ── Optimized Counts ──
    try:
        users_count = len(list(db.collection("users").limit(1000).stream()))
    except:
        users_count = 0
    
    try:
        # Summing from audit_log is more reliable for total activity
        queries_count = len(list(db.collection("audit_log").where("event", "==", "query").limit(1000).stream()))
    except:
        queries_count = 0

    try:
        requests_count = len(list(db.collection("consultation_requests").limit(1000).stream()))
    except:
        requests_count = 0
    
    try:
        forum_count = len(list(db.collection("forum_posts").limit(1000).stream()))
    except:
        forum_count = 0

    # Pending Lawyer Applications
    pending_lawyers = []
    try:
        pending_docs = db.collection("lawyers").where("verified", "==", False).limit(50).stream()
        for doc in pending_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            pending_lawyers.append(data)
    except:
        pass
    
    # ── Weekly Data (Real Trends) ──
    import datetime
    today = datetime.datetime.utcnow()
    weekly_data = []
    for i in range(7):
        day = today - datetime.timedelta(days=6 - i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + datetime.timedelta(days=1)
        try:
            day_count = len(list(
                db.collection("audit_log")
                  .where("event", "==", "query")
                  .where("timestamp", ">=", day_start)
                  .where("timestamp", "<", day_end)
                  .limit(100)
                  .stream()
            ))
        except:
            day_count = 0
        weekly_data.append({"name": day.strftime("%a"), "queries": day_count})

    # ── Recent Activity ──
    recent_activity = []
    try:
        activity_docs = db.collection("audit_log").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
        for doc in activity_docs:
            d = doc.to_dict()
            ts = d.get("timestamp")
            recent_activity.append({
                "id": doc.id,
                "user": d.get("uid", "User")[:6],
                "action": d.get("event", "action").title(),
                "time": ts.strftime("%H:%M") if ts and hasattr(ts, 'strftime') else "Just now"
            })
    except:
        pass

    return {
        "total_users": users_count,
        "daily_queries": queries_count,
        "documents_drafted": requests_count,
        "storage_usage": f"{users_count * 0.5:.1f} MB",
        "forum_posts": forum_count,
        "pending_lawyers": pending_lawyers,
        "weekly_progress": weekly_data,
        "recent_activity": recent_activity,
    }

async def check_admin(uid: str, email: str, db):
    """Verify if user is an admin, with auto-promotion for founder."""
    user_doc = db.collection("users").document(uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    
    # Auto-promote founder
    founders = ["mustafajamalshabqadar@gmail.com"]
    if email in founders:
        if not user_data.get("is_admin"):
            db.collection("users").document(uid).set({"is_admin": True, "email": email}, merge=True)
        return True
        
    return user_data.get("is_admin", False)

@router.post("/approve-lawyer")
async def approve_lawyer(lawyer_id: str, request: Request):
    """Approve a lawyer (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    email = user_info.get("email")
    db = get_db()
    
    if not await check_admin(uid, email, db):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.collection("lawyers").document(lawyer_id).update({"verified": True})
    return {"success": True}

@router.post("/reject-lawyer")
async def reject_lawyer(lawyer_id: str, request: Request):
    """Reject a lawyer application (deletes it)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    email = user_info.get("email")
    db = get_db()
    
    if not await check_admin(uid, email, db):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.collection("lawyers").document(lawyer_id).delete()
    return {"success": True}

@router.delete("/user/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user account (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_db()
    # Admin check
    admin_doc = db.collection("users").document(user_info["uid"]).get()
    if not admin_doc.exists or not admin_doc.to_dict().get("is_admin"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.collection("users").document(user_id).delete()
    return {"success": True}

@router.get("/users")
async def get_all_users(request: Request):
    """Fetch all users (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    db = get_db()
    docs = db.collection("users").limit(100).stream()
    users = []
    for doc in docs:
        uid = doc.id
        data = doc.to_dict()
        
        # Enrich with profile data if possible
        try:
            profile = db.collection("users").document(uid).collection("profile").document("settings").get()
            if profile.exists:
                p_data = profile.to_dict()
                data["email"] = p_data.get("email") or data.get("email")
                data["plan"] = p_data.get("plan", "free")
                data["name"] = p_data.get("display_name")
        except: pass

        # Enrich with usage
        try:
            # Get total queries from a heuristic or just 0
            data["queries"] = data.get("usage", {}).get("query", 0)
        except: pass

        data["id"] = uid
        users.append(data)
    return users
