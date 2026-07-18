import logging
from fastapi import APIRouter, HTTPException, Request
from google.cloud import firestore
from app.core.firebase import verify_token, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


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
    
    # ── Optimized Counts (with fast count aggregation & fallback) ──
    try:
        users_count = db.collection("users").count().get()[0][0].value
    except Exception:
        try:
            users_count = len(list(db.collection("users").limit(1000).stream()))
        except Exception:
            users_count = 0
            
    try:
        queries_count = db.collection("audit_log").where("event", "in", ["query", "query_stream", "peca_query"]).count().get()[0][0].value
    except Exception:
        try:
            queries_count = len(list(db.collection("audit_log").where("event", "in", ["query", "query_stream", "peca_query"]).limit(1000).stream()))
        except Exception:
            queries_count = 0

    try:
        drafts_count = db.collection("audit_log").where("event", "in", ["draft_generated", "template_generated", "complaint_drafted"]).count().get()[0][0].value
    except Exception:
        try:
            drafts_count = len(list(db.collection("audit_log").where("event", "in", ["draft_generated", "template_generated", "complaint_drafted"]).limit(1000).stream()))
        except Exception:
            drafts_count = 0

    try:
        forum_count = db.collection("forum_posts").count().get()[0][0].value
    except Exception:
        try:
            forum_count = len(list(db.collection("forum_posts").limit(1000).stream()))
        except Exception:
            forum_count = 0

    try:
        lawyers_count = db.collection("lawyers").where("verified", "==", True).count().get()[0][0].value
    except Exception:
        try:
            lawyers_count = len(list(db.collection("lawyers").where("verified", "==", True).limit(1000).stream()))
        except Exception:
            lawyers_count = 0

    # Retrieve pending lawyer details
    pending_lawyers = []
    try:
        pending_docs = db.collection("lawyers").where("verified", "==", False).limit(50).stream()
        for doc in pending_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            pending_lawyers.append(data)
    except:
        pass
    
    # ── Weekly Data (Real Trends aggregated in Python from single-field query) ──
    import datetime
    today = datetime.datetime.utcnow()
    past_week = today - datetime.timedelta(days=7)
    past_week_start = past_week.replace(hour=0, minute=0, second=0, microsecond=0)

    weekly_queries = []
    weekly_users = []
    weekly_drafts = []
    weekly_forum = []
    weekly_lawyers = []

    day_map = {}
    for i in range(7):
        day = today - datetime.timedelta(days=6 - i)
        day_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%a")
        day_map[day_str] = {
            "name": day_name,
            "queries": 0,
            "users": 0,
            "drafts": 0,
            "forum": 0,
            "lawyers": 0
        }

    # 1. Fetch past week's audit logs
    try:
        audit_docs = db.collection("audit_log").where("timestamp", ">=", past_week_start).stream()
        for doc in audit_docs:
            d = doc.to_dict()
            ts = d.get("timestamp")
            if ts and hasattr(ts, "strftime"):
                date_str = ts.strftime("%Y-%m-%d")
                if date_str in day_map:
                    event = d.get("event")
                    if event in ["query", "query_stream", "peca_query"]:
                        day_map[date_str]["queries"] += 1
                    elif event in ["draft_generated", "template_generated", "complaint_drafted"]:
                        day_map[date_str]["drafts"] += 1
    except Exception as e:
        logger.error(f"Error fetching weekly audit logs: {e}")

    # 2. Fetch past week's signups
    try:
        user_docs = db.collection("users").where("createdAt", ">=", past_week_start).stream()
        for doc in user_docs:
            d = doc.to_dict()
            ts = d.get("createdAt")
            if ts and hasattr(ts, "strftime"):
                date_str = ts.strftime("%Y-%m-%d")
                if date_str in day_map:
                    day_map[date_str]["users"] += 1
    except Exception as e:
        logger.error(f"Error fetching weekly signups: {e}")

    # 3. Fetch past week's forum posts
    try:
        forum_docs = db.collection("forum_posts").where("timestamp", ">=", past_week_start).stream()
        for doc in forum_docs:
            d = doc.to_dict()
            ts = d.get("timestamp")
            if ts and hasattr(ts, "strftime"):
                date_str = ts.strftime("%Y-%m-%d")
                if date_str in day_map:
                    day_map[date_str]["forum"] += 1
    except Exception as e:
        logger.error(f"Error fetching weekly forum posts: {e}")

    # 4. Fetch past week's lawyer applications
    try:
        lawyer_docs = db.collection("lawyers").where("timestamp", ">=", past_week_start).stream()
        for doc in lawyer_docs:
            d = doc.to_dict()
            ts = d.get("timestamp")
            if ts and hasattr(ts, "strftime"):
                date_str = ts.strftime("%Y-%m-%d")
                if date_str in day_map:
                    day_map[date_str]["lawyers"] += 1
    except Exception as e:
        logger.error(f"Error fetching weekly lawyer applications: {e}")

    # Build weekly lists
    for i in range(7):
        day = today - datetime.timedelta(days=6 - i)
        day_str = day.strftime("%Y-%m-%d")
        data_for_day = day_map[day_str]
        
        weekly_queries.append({"name": data_for_day["name"], "value": data_for_day["queries"]})
        weekly_users.append({"name": data_for_day["name"], "value": data_for_day["users"]})
        weekly_drafts.append({"name": data_for_day["name"], "value": data_for_day["drafts"]})
        weekly_forum.append({"name": data_for_day["name"], "value": data_for_day["forum"]})
        weekly_lawyers.append({"name": data_for_day["name"], "value": data_for_day["lawyers"]})

    # ── Real-Time Storage Estimation ──
    try:
        audit_log_count = db.collection("audit_log").count().get()[0][0].value
        cost_log_count = db.collection("cost_log").count().get()[0][0].value
    except:
        audit_log_count = 0
        cost_log_count = 0

    estimated_bytes = (
        users_count * 1024 + 
        lawyers_count * 2048 + 
        forum_count * 4096 + 
        audit_log_count * 512 + 
        cost_log_count * 300
    )
    storage_usage_mb = max(0.1, estimated_bytes / (1024 * 1024))
    storage_usage_str = f"{storage_usage_mb:.2f} MB"

    # ── Today's query count (real daily figure) ──
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        today_queries = db.collection("audit_log").where("event", "in", ["query", "query_stream", "peca_query"]).where("timestamp", ">=", today_start).count().get()[0][0].value
    except Exception:
        try:
            today_queries = len(list(db.collection("audit_log").where("event", "in", ["query", "query_stream", "peca_query"]).where("timestamp", ">=", today_start).limit(500).stream()))
        except Exception:
            today_queries = 0

    return {
        "total_users": users_count,
        "total_queries": queries_count,      # all-time
        "daily_queries": today_queries,       # today only (kept for backward compat)
        "today_queries": today_queries,       # today only
        "documents_drafted": drafts_count,
        "storage_usage": storage_usage_str,
        "forum_posts": forum_count,
        "pending_lawyers": pending_lawyers,
        "weekly_progress": weekly_queries,
        "weekly_queries_progress": weekly_queries,
        "weekly_users_progress": weekly_users,
        "weekly_drafts_progress": weekly_drafts,
        "weekly_forum_progress": weekly_forum,
        "weekly_lawyers_progress": weekly_lawyers,
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
    docs = db.collection("users").limit(300).stream()
    users = []
    from firebase_admin import auth as firebase_auth
    for doc in docs:
        uid = doc.id
        data = doc.to_dict()
        
        # Check custom claims for admin status
        try:
            auth_user = firebase_auth.get_user(uid)
            data["admin"] = auth_user.custom_claims.get("admin", False) if auth_user.custom_claims else False
            if auth_user.email and not data.get("email"):
                data["email"] = auth_user.email
        except Exception:
            data["admin"] = data.get("admin", False)
        
        # Enrich with profile data if possible
        try:
            profile = db.collection("users").document(uid).collection("profile").document("settings").get()
            if profile.exists:
                p_data = profile.to_dict()
                data["email"] = p_data.get("email") or data.get("email")
                data["plan"] = p_data.get("plan") or data.get("plan")
                data["name"] = p_data.get("display_name")
        except: pass

        # Enrich with usage
        try:
            data["queries"] = data.get("usage", {}).get("query", 0)
        except: pass

        # Fallback values
        if not data.get("email"):
            data["email"] = f"UID: {uid[:8]}..."
        if not data.get("plan"):
            data["plan"] = "Free"

        data["id"] = uid
        users.append(data)
    return users


@router.post("/user/{user_id}/plan")
async def update_user_plan(user_id: str, plan: str, request: Request):
    """Update a user's subscription tier (Admin only)."""
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
    
    # Save plan in top-level user document
    db.collection("users").document(user_id).set({"plan": plan}, merge=True)
    
    # Also save in profile settings subcollection
    db.collection("users").document(user_id).collection("profile").document("settings").set({"plan": plan}, merge=True)
    
    # Invalidate plan cache in usage_service
    from app.services.usage_service import plan_cache
    if user_id in plan_cache:
        del plan_cache[user_id]
        
    return {"success": True, "message": f"User plan updated to {plan}"}


@router.post("/user/{user_id}/admin")
async def update_user_admin_status(user_id: str, admin: bool, request: Request):
    """Toggle a user's admin claims (Admin only)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    if not user_info.get("admin", False):
        raise HTTPException(status_code=403, detail="Unauthorized: Admin access required")
        
    # Prevent lockout (an admin cannot revoke their own admin status)
    if user_id == user_info["uid"] and not admin:
        raise HTTPException(status_code=400, detail="Cannot revoke admin privileges from your own account.")
    
    from firebase_admin import auth as firebase_auth
    try:
        # Get existing custom claims
        user = firebase_auth.get_user(user_id)
        current_claims = user.custom_claims or {}
        new_claims = {**current_claims, "admin": admin}
        
        # Set custom claims
        firebase_auth.set_custom_user_claims(user_id, new_claims)
        
        # Update flag in Firestore users doc
        db = get_db()
        db.collection("users").document(user_id).set({"admin": admin}, merge=True)
        
        return {"success": True, "message": f"User admin status set to {admin}"}
    except Exception as e:
        logger.error(f"Failed to set admin claim for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update admin claims: {str(e)}")


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
