import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from google.cloud import firestore
from typing import List, Optional
from app.core.firebase import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(redirect_slashes=False)

_db = None
def get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db

class FirmMemberOut(BaseModel):
    id: str
    name: str
    role: str
    email: str
    status: str
    cases: int

@router.get("/members", response_model=List[FirmMemberOut])
async def get_firm_members(token: str):
    """Fetch all members of the firm the user belongs to (as owner or member)."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = user_info["uid"]
    email = user_info.get("email")
    
    db = get_db()
    
    # 1. Identify Owner ID
    owner_id = uid
    invited_ref = list(db.collection("firm_members").where("email", "==", email).limit(1).stream())
    # If I have no firm_owner entries but I am an invited member, my owner is someone else
    if invited_ref and not list(db.collection("firm_members").where("firm_owner_id", "==", uid).limit(1).stream()):
        owner_id = invited_ref[0].to_dict().get("firm_owner_id")
        
    # 2. Fetch all invited members
    members_docs = db.collection("firm_members").where("firm_owner_id", "==", owner_id).stream()
    members = [FirmMemberOut(**{**doc.to_dict(), "id": doc.id}) for doc in members_docs]
    
    # 3. Add the Owner to the list (so they appear in their own dashboard)
    # We only show the owner if there is actually a firm context (invited members exist or they are an invited member themselves)
    owner_user = db.collection("users").document(owner_id).get()
    owner_data = owner_user.to_dict() if owner_user.exists else {}
    
    # Fetch lead count for this owner
    owner_lawyers = db.collection("lawyers").where("uid", "==", owner_id).stream()
    o_lawyer_ids = [d.id for d in owner_lawyers]
    case_count = 0
    if o_lawyer_ids:
        try:
            case_count = len(list(db.collection("consultation_requests").where("lawyer_id", "in", o_lawyer_ids[:10]).stream()))
        except: pass
    
    owner_member = FirmMemberOut(
        id=owner_id,
        name=owner_data.get("name", "Senior Partner (Owner)"),
        role="Managing Partner",
        email=owner_data.get("email") or user_info.get("email") or "",
        status="Active",
        cases=case_count
    )
    
    # Return owner + invited members only. Do NOT auto-add marketplace profiles.
    return [owner_member] + members

@router.delete("/members/{member_id}")
async def delete_firm_member(member_id: str, token: str):
    """Remove a member from the firm (Admin/Owner only)."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    db = get_db()
    
    # Permission check: Only owner or Managing Partner can delete
    # (Simplified: check if this member belongs to the inviter's firm)
    doc_ref = db.collection("firm_members").document(member_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Member not found")
        
    data = doc.to_dict()
    if data["firm_owner_id"] != uid:
        # Check if the inviter is a Managing Partner in the same firm
        inviter_email = user_info.get("email")
        check = list(db.collection("firm_members").where("email", "==", inviter_email).where("firm_owner_id", "==", data["firm_owner_id"]).where("role", "==", "Managing Partner").limit(1).stream())
        if not check:
            raise HTTPException(status_code=403, detail="Unauthorized to delete members")
            
    doc_ref.delete()
    return {"success": True}

@router.post("/members")
async def add_firm_member(token: str, name: str, email: str, role: str):
    """Add a new member to the firm."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = get_db()
    
    # Identify who is doing the inviting
    inviter_uid = user_info["uid"]
    inviter_email = user_info.get("email")
    
    # 1. Determine the Firm Owner ID
    # Check if this user IS an owner of a firm
    owner_id = None
    existing_firm = list(db.collection("firm_members").where("firm_owner_id", "==", inviter_uid).limit(1).stream())
    
    if existing_firm:
        owner_id = inviter_uid
    else:
        # Check if they are a Managing Partner in someone else's firm
        invited_ref = list(db.collection("firm_members").where("email", "==", inviter_email).where("role", "==", "Managing Partner").limit(1).stream())
        if invited_ref:
            owner_id = invited_ref[0].to_dict().get("firm_owner_id")
    
    # If no firm found, this user is starting a new firm as the owner
    if not owner_id:
        owner_id = inviter_uid

    # 2. Permission Check
    if inviter_uid != owner_id:
        # They must be a Managing Partner to continue
        check = list(db.collection("firm_members").where("email", "==", inviter_email).where("firm_owner_id", "==", owner_id).where("role", "==", "Managing Partner").limit(1).stream())
        if not check:
            raise HTTPException(status_code=403, detail="Only a Managing Partner can invite new members.")
    
    member_data = {
        "firm_owner_id": owner_id,
        "name": name,
        "email": email,
        "role": role,
        "status": "Active",
        "cases": 0,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    db.collection("firm_members").add(member_data)
    return {"success": True}

class LawyerUpdate(BaseModel):
    token: str
    name: Optional[str] = None
    specialty: Optional[str] = None
    experience: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

@router.post("/update-lawyer-profile")
async def update_lawyer_profile(req: LawyerUpdate):
    """Update lawyer profile via JSON body to ensure 100% stability."""
    user_info = verify_token(req.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    uid = user_info["uid"]
    db = get_db()
    
    # Find the lawyer profile owned by this user
    lawyers = list(db.collection("lawyers").where("uid", "==", uid).limit(1).stream())
    if not lawyers:
        raise HTTPException(status_code=404, detail="No lawyer profile found for this account.")
        
    lawyer_id = lawyers[0].id
    update_data = req.dict(exclude={"token"}, exclude_none=True)
    update_data["timestamp"] = firestore.SERVER_TIMESTAMP
    
    db.collection("lawyers").document(lawyer_id).update(update_data)
    return {"success": True, "message": "Profile updated successfully"}

@router.get("/stats")
async def get_firm_stats(token: str):
    """Fetch real-time stats for the firm dashboard."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = user_info["uid"]
    email = user_info.get("email")
    db = get_db()
    
    owner_id = uid
    # Check if this user is an invited member instead of owner
    invited_ref = list(db.collection("firm_members").where("email", "==", email).limit(1).stream())
    if invited_ref and not list(db.collection("firm_members").where("firm_owner_id", "==", uid).limit(1).stream()):
        owner_id = invited_ref[0].to_dict().get("firm_owner_id")

    # 1. Total Members
    members_count = len(list(db.collection("firm_members").where("firm_owner_id", "==", owner_id).stream()))
    
    # 2. Total Queries
    user_doc = db.collection("users").document(owner_id).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    
    queries = user_data.get("usage", {}).get("query", 0)
    plan = user_data.get("plan", "Free Tier")
    
    return {
        "total_members": members_count,
        "total_queries": queries,
        "plan_name": plan
    }

@router.get("/my-role")
async def get_my_role(token: str):
    """Fetch the current user's role within their firm."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    uid = user_info["uid"]
    email = user_info.get("email")
    db = get_db()
    
    # Check if they are the owner
    # In our system, if they have invited members, they are the owner
    owner_check = db.collection("firm_members").where("firm_owner_id", "==", uid).limit(1).stream()
    if list(owner_check):
        return {"role": "Managing Partner"}
        
    # Check if they are an invited member
    invited_ref = list(db.collection("firm_members").where("email", "==", email).limit(1).stream())
    if invited_ref:
        return {"role": invited_ref[0].to_dict().get("role", "Advocate")}
        
    # Default for single lawyers
    return {"role": "Managing Partner"}
