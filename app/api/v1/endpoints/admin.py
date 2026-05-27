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
    return {"is_admin": user_info.get("admin", False)}


@router.get("/verify")
async def verify_admin_status(request: Request):
    """Verifies admin privileges and returns 200 OK, otherwise raises 403 Forbidden."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user_info.get("admin", False):
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
    return {"status": "success", "message": "Admin status verified"}

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
    """Verify if user is an admin via Firebase custom claims."""
    from app.core.firebase import is_admin
    return is_admin(uid)

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
    # Admin check using Firebase custom claims
    if not user_info.get("admin", False):
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
    
    db.collection("users").document(user_id).delete()
    return {"success": True}

@router.get("/users")
async def get_all_users(request: Request):
    """Fetch all users (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    if not user_info.get("admin", False):
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
    
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


@router.get("/costs")
async def get_model_costs(request: Request):
    """Aggregate token counts and compute model expenditure (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    if not user_info.get("admin", False):
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
        
    db = get_db()
    
    total_input_tokens = 0
    total_output_tokens = 0
    model_aggregation = {}
    
    try:
        # Stream the cost log (up to 10000 entries to prevent memory overflow)
        cost_docs = db.collection("cost_log").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10000).stream()
        for doc in cost_docs:
            data = doc.to_dict()
            model = data.get("model_name", "unknown-model")
            in_tokens = data.get("input_tokens", 0)
            out_tokens = data.get("output_tokens", 0)
            
            total_input_tokens += in_tokens
            total_output_tokens += out_tokens
            
            if model not in model_aggregation:
                model_aggregation[model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_calls": 0,
                    "cost_usd": 0.0
                }
            
            model_aggregation[model]["input_tokens"] += in_tokens
            model_aggregation[model]["output_tokens"] += out_tokens
            model_aggregation[model]["total_calls"] += 1
            
        # Compute cost for each model
        # Gemini 2.5 Flash pricing: $0.075 / 1M input, $0.30 / 1M output
        total_expenditure_usd = 0.0
        for model, stats in model_aggregation.items():
            input_rate = 0.075 / 1_000_000
            output_rate = 0.30 / 1_000_000
            
            model_cost = (stats["input_tokens"] * input_rate) + (stats["output_tokens"] * output_rate)
            stats["cost_usd"] = round(model_cost, 6)
            total_expenditure_usd += model_cost
            
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_calls": sum(stats["total_calls"] for stats in model_aggregation.values()),
            "total_expenditure_usd": round(total_expenditure_usd, 6),
            "model_breakdown": model_aggregation
        }
    except Exception as e:
        logger.error(f"Error fetching cost log stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost statistics: {str(e)}")
