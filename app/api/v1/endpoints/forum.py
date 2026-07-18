import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from google.cloud import firestore
from typing import List, Optional
from app.core.firebase import verify_token, get_db
import datetime

logger = logging.getLogger(__name__)
router = APIRouter()



# ════════════════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════════════════

class PostIn(BaseModel):
    title: str
    content: str
    tags: List[str] = []
    language: str = "en"
    token: str

class EditPostIn(BaseModel):
    title: str
    content: str
    tags: List[str] = []
    token: str

class ReplyIn(BaseModel):
    content: str
    token: str

class TokenBody(BaseModel):
    token: str


# ════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _format_ts(ts) -> str:
    if ts and hasattr(ts, "strftime"):
        return ts.strftime("%b %d, %Y · %H:%M")
    return "Just now"

def _serialize_post(doc) -> dict:
    data = doc.to_dict()
    data["id"] = doc.id
    data["time"] = _format_ts(data.get("timestamp"))
    data.setdefault("likes", 0)
    data.setdefault("replies", 0)
    data.setdefault("tags", [])
    data.setdefault("language", "en")
    data.setdefault("liked_by", [])
    data.setdefault("edited", False)
    return data

def _is_admin(uid: str, db) -> bool:
    try:
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            data = doc.to_dict()
            founders = ["mustafajamalshabqadar@gmail.com"]
            return data.get("is_admin", False) or data.get("email", "") in founders
    except Exception:
        pass
    return False


# ════════════════════════════════════════════════════════════════════════════════
# POSTS — READ
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/")
async def get_posts():
    """Fetch all forum posts, newest first."""
    db = get_db()
    try:
        docs = (
            db.collection("forum_posts")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(100)
            .stream()
        )
        return [_serialize_post(doc) for doc in docs]
    except Exception as e:
        logger.error(f"get_posts error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════════
# POSTS — CREATE
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/")
async def create_post(post: PostIn):
    """
    Any logged-in user can create a discussion.
    """
    user_info = verify_token(post.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in to post.")
    uid = user_info["uid"]

    db = get_db()
    user_doc = db.collection("users").document(uid).get()
    author_name = "User"
    if user_doc.exists:
        author_name = user_doc.to_dict().get("display_name", "User")

    ref = db.collection("forum_posts").add({
        "author": author_name,
        "author_id": uid,
        "title": post.title.strip(),
        "content": post.content.strip(),
        "tags": [t.strip() for t in post.tags if t.strip()],
        "language": post.language,
        "likes": 0,
        "replies": 0,
        "liked_by": [],
        "edited": False,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })
    return {"id": ref[1].id, "success": True}


# ════════════════════════════════════════════════════════════════════════════════
# POSTS — EDIT (author only)
# ════════════════════════════════════════════════════════════════════════════════

@router.put("/{post_id}")
async def edit_post(post_id: str, body: EditPostIn):
    """Only the original author can edit their post."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in.")
    uid = user_info["uid"]

    db = get_db()
    ref = db.collection("forum_posts").document(post_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Post not found.")
    if doc.to_dict().get("author_id") != uid:
        raise HTTPException(status_code=403, detail="You can only edit your own posts.")

    ref.update({
        "title": body.title.strip(),
        "content": body.content.strip(),
        "tags": [t.strip() for t in body.tags if t.strip()],
        "edited": True,
        "edited_at": firestore.SERVER_TIMESTAMP,
    })
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════════════
# POSTS — DELETE (author or admin)
# ════════════════════════════════════════════════════════════════════════════════

@router.delete("/{post_id}")
async def delete_post(post_id: str, body: TokenBody):
    """Author or admin can delete a post (and all its replies)."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in.")
    uid = user_info["uid"]

    db = get_db()
    ref = db.collection("forum_posts").document(post_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Post not found.")

    data = doc.to_dict()
    if data.get("author_id") != uid and not _is_admin(uid, db):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post.")

    # Delete all replies in subcollection first
    for reply_doc in ref.collection("replies").stream():
        reply_doc.reference.delete()

    ref.delete()
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════════════
# LIKES
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/{post_id}/like")
async def toggle_like(post_id: str, body: TokenBody):
    """Toggle like on a post (one like per user)."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in to like.")
    uid = user_info["uid"]

    db = get_db()
    ref = db.collection("forum_posts").document(post_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Post not found.")

    liked_by: list = doc.to_dict().get("liked_by", [])
    if uid in liked_by:
        liked_by.remove(uid)
        liked = False
    else:
        liked_by.append(uid)
        liked = True

    ref.update({"liked_by": liked_by, "likes": len(liked_by)})
    return {"likes": len(liked_by), "liked": liked}


# ════════════════════════════════════════════════════════════════════════════════
# REPLIES — READ
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/{post_id}/replies")
async def get_replies(post_id: str):
    """Fetch all replies for a post, oldest first."""
    db = get_db()
    try:
        docs = (
            db.collection("forum_posts")
            .document(post_id)
            .collection("replies")
            .order_by("timestamp")
            .stream()
        )
        replies = []
        for doc in docs:
            r = doc.to_dict()
            r["id"] = doc.id
            r["time"] = _format_ts(r.get("timestamp"))
            r.setdefault("author", "User")
            r.setdefault("author_id", "")
            replies.append(r)
        return replies
    except Exception as e:
        logger.error(f"get_replies error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════════
# REPLIES — CREATE (any logged-in user)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/{post_id}/replies")
async def create_reply(post_id: str, body: ReplyIn):
    """Any logged-in user can reply."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in to reply.")
    uid = user_info["uid"]

    db = get_db()
    post_ref = db.collection("forum_posts").document(post_id)
    if not post_ref.get().exists:
        raise HTTPException(status_code=404, detail="Post not found.")

    user_doc = db.collection("users").document(uid).get()
    author_name = "User"
    if user_doc.exists:
        author_name = user_doc.to_dict().get("display_name", "User")

    post_ref.collection("replies").add({
        "author": author_name,
        "author_id": uid,
        "content": body.content.strip(),
        "timestamp": firestore.SERVER_TIMESTAMP,
    })
    post_ref.update({"replies": firestore.Increment(1)})
    return {"success": True}


# ── REPLIES — EDIT (reply author only) ──────────────────────────────────────

class EditReplyIn(BaseModel):
    content: str
    token: str

@router.put("/{post_id}/replies/{reply_id}")
async def edit_reply(post_id: str, reply_id: str, body: EditReplyIn):
    """Only the reply author can edit their reply."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in.")
    uid = user_info["uid"]

    db = get_db()
    reply_ref = (
        db.collection("forum_posts")
        .document(post_id)
        .collection("replies")
        .document(reply_id)
    )
    reply_doc = reply_ref.get()
    if not reply_doc.exists:
        raise HTTPException(status_code=404, detail="Reply not found.")
    if reply_doc.to_dict().get("author_id") != uid:
        raise HTTPException(status_code=403, detail="You can only edit your own replies.")

    reply_ref.update({
        "content": body.content.strip(),
        "edited": True,
        "edited_at": firestore.SERVER_TIMESTAMP,
    })
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════════════
# REPLIES — DELETE (reply author or admin)
# ════════════════════════════════════════════════════════════════════════════════

@router.delete("/{post_id}/replies/{reply_id}")
async def delete_reply(post_id: str, reply_id: str, body: TokenBody):
    """Reply author or admin can delete a reply."""
    user_info = verify_token(body.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Please log in.")
    uid = user_info["uid"]

    db = get_db()
    reply_ref = (
        db.collection("forum_posts")
        .document(post_id)
        .collection("replies")
        .document(reply_id)
    )
    reply_doc = reply_ref.get()
    if not reply_doc.exists:
        raise HTTPException(status_code=404, detail="Reply not found.")

    if reply_doc.to_dict().get("author_id") != uid and not _is_admin(uid, db):
        raise HTTPException(status_code=403, detail="Not authorized to delete this reply.")

    reply_ref.delete()
    # Decrement reply count
    db.collection("forum_posts").document(post_id).update({
        "replies": firestore.Increment(-1)
    })
    return {"success": True}
