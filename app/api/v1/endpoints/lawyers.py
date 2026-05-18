import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from google.cloud import firestore
from typing import List, Optional, Dict
from app.core.firebase import verify_token

class UpdateLawyerProfile(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    experience: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    lawyer_id: Optional[str] = None
    token: str

logger = logging.getLogger(__name__)
router = APIRouter()

_db = None
def get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db

class LawyerOut(BaseModel):
    id: str
    name: str
    specialty: str
    experience: str
    city: str
    rating: float
    reviews: int
    avatar: str
    description: str
    verified: bool
    email: Optional[str] = None
    phone: Optional[str] = None

class LawyerApply(BaseModel):
    name: str
    specialty: str
    experience: str
    city: str
    description: str
    email: str
    phone: str
    token: str

class ReviewIn(BaseModel):
    lawyer_id: str
    rating: int
    comment: str
    token: str

class ConsultationRequest(BaseModel):
    lawyer_id: str
    issue_description: str
    token: str

@router.get("/", response_model=List[LawyerOut])
async def get_lawyers(specialty: Optional[str] = None):
    """Fetch all verified lawyers from Firestore."""
    db = get_db()
    lawyers_ref = db.collection("lawyers")
    
    if specialty and specialty != "All":
        query = lawyers_ref.where("specialty", "==", specialty).where("verified", "==", True)
    else:
        query = lawyers_ref.where("verified", "==", True)
        
    docs = query.stream()
    lawyers = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        lawyers.append(LawyerOut(**data))
        
    return lawyers

@router.post("/request")
async def request_consultation(req: ConsultationRequest):
    """
    Send a consultation request to a lawyer.
    In production, this triggers an Email (SendGrid) or WhatsApp message (Twilio) to the lawyer.
    """
    user_info = verify_token(req.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = user_info["uid"]
        
    db = get_db()
    
    # Save the request in Firestore
    # Fetch lawyer email for record keeping
    lawyer_email = None
    lawyer_doc = db.collection("lawyers").document(req.lawyer_id).get()
    if lawyer_doc.exists:
        lawyer_email = lawyer_doc.to_dict().get("email")

    request_data = {
        "user_id": uid,
        "user_name": user_info.get("name", "Potential Client"),
        "user_email": user_info.get("email"),
        "lawyer_id": req.lawyer_id,
        "lawyer_email": lawyer_email,
        "issue_description": req.issue_description.strip(),
        "status": "pending",
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    
    # Save to top-level for global tracking
    db.collection("consultation_requests").add(request_data)
    
    # Also save to lawyer subcollection for direct access
    db.collection("lawyers").document(req.lawyer_id).collection("consultation_requests").add(request_data)
    
    # ── PRODUCTION REAL-WORLD DELIVERY ──
    # Fetch lawyer contact info
    lawyer_doc = db.collection("lawyers").document(req.lawyer_id).get()
    if lawyer_doc.exists:
        l_data = lawyer_doc.to_dict()
        l_email = l_data.get("email")
        l_phone = l_data.get("phone")
        
        # 1. SEND EMAIL (SendGrid/Mailgun)
        # To make this real, add SENDGRID_API_KEY to your .env
        
        # 2. SEND WHATSAPP REDIRECT (Direct Contact)
        wa_phone = l_phone.replace('+', '').replace(' ', '').replace('-', '')
        whatsapp_link = f"https://wa.me/{wa_phone}?text=Hi {l_data.get('name')}, I found you on HaqDar AI. I have a legal issue: {req.issue_description}"
        
        logger.info(f"Notification queued for Lawyer {req.lawyer_id} via {l_email}/{l_phone}")
        return {
            "success": True, 
            "message": "Consultation request sent! You can also message them directly on WhatsApp.",
            "whatsapp_link": whatsapp_link
        }

    return {"success": True, "message": "Consultation request sent! The lawyer has been notified."}

@router.post("/apply")
async def apply_as_lawyer(req: LawyerApply):
    """Submit a lawyer application for admin review."""
    user_info = verify_token(req.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = user_info["uid"]
        
    db = get_db()
    application_data = {
        "uid": uid,
        "name": req.name,
        "specialty": req.specialty,
        "experience": req.experience,
        "city": req.city,
        "description": req.description,
        "email": req.email,
        "phone": req.phone,
        "verified": False, # Requires admin approval
        "avatar": req.name[0],
        "rating": 0.0,
        "reviews": 0,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    
    db.collection("lawyers").add(application_data)
    
    # ── ADMIN NOTIFICATION ──
    # In production: send_email("admin@haqdar.pk", "New Lawyer Application", f"Lawyer {req.name} has applied.")
    logger.info(f"ADMIN ALERT: New lawyer application from {req.name} ({req.email}). Check dashboard to approve.")

    return {"success": True, "message": "Application submitted! Our team will verify your credentials and approve your profile."}



@router.get("/leads")
async def get_lawyer_leads(request: Request):
    """Fetch consultation requests for the logged-in lawyer."""
    auth_header = request.headers.get("Authorization")
    # For backward compatibility with token in query param
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.query_params.get("token")
        
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
        
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    db = get_db()
    
    # 1. Fetch profiles linked to this UID
    lawyer_docs = list(db.collection("lawyers").where("uid", "==", uid).stream())
    email = user_info.get("email", "").lower().strip()
    
    # Fallback/Update: Ensure ALL profiles with this email are linked to this UID
    # This fixes the case where Account A accidentally linked Account B's profile
    email_docs = list(db.collection("lawyers").where("email", "==", email).stream())
    for d in email_docs:
        l_data = d.to_dict()
        # If the UID is missing or different, RE-CLAIM it for the rightful email owner
        if l_data.get("uid") != uid:
            db.collection("lawyers").document(d.id).update({"uid": uid})
            logger.info(f"DEBUG: Re-claimed profile {d.id} for email {email} (UID updated to {uid})")
    
    # Refresh the list to include newly claimed profiles
    lawyer_docs = list(db.collection("lawyers").where("uid", "==", uid).stream())

    lawyer_ids = []
    for d in lawyer_docs:
        l_data = d.to_dict()
        # Only show leads for profiles matching the current session email
        profile_email = l_data.get("email", "").lower().strip()
        if profile_email == email:
            lawyer_ids.append(d.id)
    
    # 2. FIRM MEMBER logic
    if not lawyer_ids:
        invited_ref = list(db.collection("firm_members").where("email", "==", email).limit(1).stream())
        if invited_ref:
            owner_id = invited_ref[0].to_dict().get("firm_owner_id")
            owner_lawyers = db.collection("lawyers").where("uid", "==", owner_id).stream()
            for d in owner_lawyers:
                lawyer_ids.append(d.id)

    if not lawyer_ids:
        logger.info(f"DEBUG: No lawyer profiles or firm memberships found for email {email}")
        return []
    
    # Ensure lawyer_ids are unique
    lawyer_ids = list(set(lawyer_ids))
    
    # 3. Fetch requests for identified lawyer profiles
    leads = []
    try:
        # Use simple query if only 1 profile to avoid index requirement for 'in'
        if len(lawyer_ids) == 1:
            docs = db.collection("consultation_requests").where("lawyer_id", "==", lawyer_ids[0]).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
        else:
            docs = db.collection("consultation_requests").where("lawyer_id", "in", lawyer_ids[:10]).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
            
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            ts = data.get("timestamp")
            if ts and hasattr(ts, 'strftime'):
                data["time"] = ts.strftime("%Y-%m-%d %H:%M")
            leads.append(data)
        
        logger.info(f"DEBUG: Fetched {len(leads)} leads for lawyer_ids {lawyer_ids}")
    except Exception as e:
        logger.error(f"DEBUG: Ordered leads query failed (likely index): {e}")
        docs = db.collection("consultation_requests").where("lawyer_id", "in", lawyer_ids[:10]).limit(50).stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            leads.append(data)
    
    return leads

@router.post("/update")
async def update_lawyer_profile(req: UpdateLawyerProfile):
    """Updates a specific lawyer profile by ID, with permission checks."""
    user_info = verify_token(req.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    email = user_info.get("email")
    db = get_db()
    
    if not req.lawyer_id:
        raise HTTPException(status_code=400, detail="Lawyer ID is required")
        
    lawyer_ref = db.collection("lawyers").document(req.lawyer_id)
    lawyer = lawyer_ref.get()
    
    if not lawyer.exists:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    l_data = lawyer.to_dict()
    
    # Permission: Owner OR Admin
    admins = ["mustafajamalshabqadar@gmail.com", "mustafajamalsecond@gmail.com"]
    if l_data.get("uid") != uid and email not in admins:
        raise HTTPException(status_code=403, detail="Not authorized to edit this profile")
        
    update_data = req.dict(exclude={"token", "lawyer_id"}, exclude_none=True)
    lawyer_ref.update(update_data)
    return {"success": True}

@router.get("/{lawyer_id}/reviews")
async def get_lawyer_reviews(lawyer_id: str):
    """Public Feedback: Shows both Star Reviews and Consultation Inquiries."""
    db = get_db()
    reviews = []
    
    # 1. Real Reviews (Stars + Comments)
    for folder in ["reviews", "reviews_list"]:
        docs = db.collection("lawyers").document(lawyer_id).collection(folder).get()
        for doc in docs:
            data = doc.to_dict()
            if not any(r["id"] == doc.id for r in reviews):
                reviews.append({
                    "id": doc.id,
                    "user_name": data.get("user_name", "Verified Client"),
                    "rating": data.get("rating", 5),
                    "comment": data.get("comment", "Verified Rating"),
                    "time": "Recently"
                })
    
    # 2. Consultation Requests (Public Activity)
    # We look in the subcollection AND top-level
    sub_requests = db.collection("lawyers").document(lawyer_id).collection("consultation_requests").get()
    for doc in sub_requests:
        data = doc.to_dict()
        msg = data.get("issue_description") or data.get("message")
        if msg and not any(r["id"] == doc.id for r in reviews):
            reviews.append({
                "id": doc.id,
                "user_name": data.get("name") or "Inquiry",
                "rating": 5,
                "comment": f"[Public Inquiry]: {msg}",
                "time": "Recently"
            })
            
    top_requests = db.collection("consultation_requests").where("lawyer_id", "==", lawyer_id).limit(10).get()
    for doc in top_requests:
        data = doc.to_dict()
        msg = data.get("issue_description") or data.get("message")
        if msg and not any(r["id"] == doc.id for r in reviews):
            reviews.append({
                "id": doc.id,
                "user_name": data.get("name") or "Inquiry",
                "rating": 5,
                "comment": f"[Public Inquiry]: {msg}",
                "time": "Recently"
            })
            
    return reviews

@router.post("/review")
async def add_lawyer_review(req: ReviewIn):
    """Submit a review (Unified to 'reviews' collection)."""
    user_info = verify_token(req.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    db = get_db()
    lawyer_ref = db.collection("lawyers").document(req.lawyer_id)
    lawyer = lawyer_ref.get()
    
    if not lawyer.exists:
        raise HTTPException(status_code=404, detail="Lawyer not found")
        
    data = lawyer.to_dict()
    current_rating = data.get("rating", 0)
    current_reviews = data.get("reviews", 0)
    
    # Update average
    new_count = current_reviews + 1
    new_rating = ((current_rating * current_reviews) + req.rating) / new_count
    
    lawyer_ref.update({
        "rating": round(new_rating, 1),
        "reviews": new_count
    })
    
    # ALWAYS save to 'reviews' now
    db.collection("lawyers").document(req.lawyer_id).collection("reviews").add({
        "user_id": user_info["uid"],
        "user_name": user_info.get("name", "Verified Client"),
        "rating": req.rating,
        "comment": req.comment,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    
    return {"success": True, "new_rating": round(new_rating, 1)}

@router.post("/leads/accept")
async def accept_lead(lead_id: str, token: str):
    """Accept a lead (marks it as accepted)."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_db()
    db.collection("consultation_requests").document(lead_id).update({"status": "accepted"})
    return {"success": True}

@router.post("/leads/reject")
async def reject_lead(lead_id: str, token: str):
    """Reject/Delete a lead."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    db = get_db()
    db.collection("consultation_requests").document(lead_id).delete()
    return {"success": True}
