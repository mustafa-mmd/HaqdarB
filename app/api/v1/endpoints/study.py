# app/api/v1/endpoints/study.py
"""
HaqDar AI Study Mode — "Duolingo for Law"
Endpoints: difficulty, notes, flashcards, quiz, compare, progress, mindmap, case-brief.
All Gemini calls reuse the existing genai.Client from gemini_service.
Firestore persistence uses the backend service account — no client-side Firestore access.
"""
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google.cloud import firestore
from cachetools import TTLCache

from app.core.firebase import verify_token
from app.core.config import settings
from app.services.vector_search import search_similar_laws
from app.services.usage_service import log_audit_event
from app.middleware.pii_scrubber import scrub_pii

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory TTL caches (5 min) ──
_progress_cache: TTLCache = TTLCache(maxsize=5000, ttl=300)
_flashcard_cache: TTLCache = TTLCache(maxsize=5000, ttl=300)

# ── Lazy Firestore singleton ──
_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


# ── Lazy Gemini client (reuse existing key) ──
_gemini_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


def _call_gemini(prompt: str, temperature: float = 0.3, json_mode: bool = False) -> str:
    """Lightweight Gemini call — returns raw text."""
    from google.genai.types import GenerateContentConfig
    config_kwargs = {"temperature": temperature}
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    try:
        response = _get_gemini().models.generate_content(
            model=settings.GEMINI_FLASH_MODEL,
            contents=prompt,
            config=GenerateContentConfig(**config_kwargs),
        )
        return response.text.strip() if response.text else ""
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI generation failed: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════════════════════════════════════════════════════

class TokenBase(BaseModel):
    token: str


class DifficultyRequest(BaseModel):
    token: str
    level: str = Field(..., pattern="^(basic|standard|advanced)$")


class NotesRequest(BaseModel):
    token: str
    topic: str = Field(..., min_length=3, max_length=500)
    context: Optional[str] = Field(default=None, max_length=3000)
    language: str = "en"
    download: bool = False


class FlashcardsRequest(BaseModel):
    token: str
    topic: str = Field(..., min_length=3, max_length=500)
    count: int = Field(default=10, ge=3, le=25)
    difficulty: str = "standard"
    language: str = "en"


class FlashcardReviewRequest(BaseModel):
    token: str
    deck_id: str
    card_index: int
    recalled: bool


class QuizGenerateRequest(BaseModel):
    token: str
    topic: str = Field(..., min_length=3, max_length=500)
    count: int = Field(default=5, ge=3, le=15)
    difficulty: str = "standard"
    language: str = "en"


class QuizAnswer(BaseModel):
    question_id: str
    selected: str


class QuizSubmitRequest(BaseModel):
    token: str
    quiz_id: str
    topic: str
    answers: List[QuizAnswer]


class CompareRequest(BaseModel):
    token: str
    question: str = Field(..., min_length=10, max_length=1000)
    student_answer: str = Field(..., min_length=10, max_length=3000)
    language: str = "en"


class MindMapRequest(BaseModel):
    token: str
    concept: str = Field(..., min_length=3, max_length=300)
    language: str = "en"


class CaseBriefRequest(BaseModel):
    token: str
    citation: str = Field(..., min_length=5, max_length=500)
    language: str = "en"


# ════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _require_auth(token: str) -> dict:
    """Verify token and return user_info dict, raising 401 on failure."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_info


def _lang_directive(language: str) -> str:
    arabic_langs = {"ur": "Urdu (Nastaliq)", "ps": "Pashto", "pa": "Punjabi (Shahmukhi)", "sd": "Sindhi", "bal": "Balochi"}
    if language == "en":
        return "Respond entirely in English."
    name = arabic_langs.get(language, language.upper())
    return f"Respond entirely in {name} using the correct script. Never use Devanagari."


def _difficulty_instruction(level: str) -> str:
    mapping = {
        "basic": "Use very simple language. Avoid jargon. Suitable for a first-year law student.",
        "standard": "Use clear but accurate legal terminology. Suitable for a mid-level law student.",
        "advanced": "Use precise legal language, cite exact act names and section numbers. Suitable for a professional or bar exam candidate.",
    }
    return mapping.get(level, mapping["standard"])


def _make_docx(title: str, content: str) -> io.BytesIO:
    """Build a styled .docx from markdown-ish text."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    import re

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)

    # Title
    title_para = doc.add_heading(title, level=1)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            doc.add_paragraph("")
            continue

        arabic_count = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F]", line))
        is_rtl = arabic_count > len(line) * 0.3

        if line.startswith("## "):
            p = doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            p = doc.add_heading(line[4:], level=3)
        elif line.startswith("**") and line.endswith("**"):
            p = doc.add_paragraph()
            run = p.add_run(line.strip("*"))
            run.bold = True
        else:
            p = doc.add_paragraph()
            text = line.replace("**", "").replace("*", "").lstrip("- •")
            if is_rtl:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                pPr = p._element.get_or_add_pPr()
                bidi = pPr.makeelement(
                    qn("w:bidi"),
                    nsmap={"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"},
                )
                bidi.set(qn("w:val"), "1")
                pPr.append(bidi)
                run = p.add_run(text)
                run.font.name = "Noto Nastaliq Urdu"
            else:
                p.add_run(text)

    # Footer disclaimer
    doc.add_paragraph("")
    footer_p = doc.add_paragraph("⚖️ HaqDar AI Study Notes — Legal information only, not legal advice.")
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ════════════════════════════════════════════════════════════════════════════════
# 1. DIFFICULTY PREFERENCE
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/difficulty")
async def set_difficulty(request: DifficultyRequest):
    """Update user's study difficulty preference in their Firestore profile."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]
    try:
        db = _get_db()
        db.collection("users").document(uid).collection("profile").document("settings").set(
            {"study_difficulty": request.level, "updatedAt": firestore.SERVER_TIMESTAMP},
            merge=True,
        )
        log_audit_event(uid, "study_difficulty_set", {"level": request.level})
        return {"success": True, "level": request.level}
    except Exception as e:
        logger.error(f"Set difficulty failed for {uid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update difficulty preference")


# ════════════════════════════════════════════════════════════════════════════════
# 2. NOTES GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/notes")
async def generate_notes(request: NotesRequest):
    """Generate structured study notes for a legal topic and optionally stream a .docx download."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    # Fetch relevant law context from Qdrant
    try:
        matches = search_similar_laws(request.topic, neighbor_count=4)
        law_context = "\n\n".join(m["text"] for m in matches if m.get("text"))
    except Exception:
        law_context = request.context or ""

    extra_context = request.context or ""
    combined_context = f"{law_context}\n\n{extra_context}".strip()

    prompt = f"""You are HaqDar AI Study — a premium legal education tool for Pakistani law students.

Generate comprehensive, structured study notes on the following topic.

TOPIC: {request.topic}

RELEVANT LAW SECTIONS:
{combined_context if combined_context else "(Use your training knowledge on Pakistani law)"}

INSTRUCTIONS:
- Structure using ## headings for major sections
- Include: Definition, Relevant Laws (act name + section), Key Principles, Practical Examples, Common Exam Points
- Be factually grounded in Pakistani law
- {_lang_directive(request.language)}
- End with a "Quick Summary" section (3 bullet points)
- Do NOT add a disclaimer at the end (it will be added automatically)

Generate the notes now:"""

    notes_md = _call_gemini(prompt, temperature=0.2)

    # Persist to Firestore
    try:
        db = _get_db()
        doc_ref = db.collection("student_notes").add({
            "uid": uid,
            "topic": request.topic,
            "notes": notes_md,
            "language": request.language,
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
        note_id = doc_ref[1].id
    except Exception as e:
        logger.error(f"Notes persist failed: {e}")
        note_id = None

    log_audit_event(uid, "notes_generated", {"topic": request.topic})

    if request.download:
        buf = _make_docx(f"Study Notes: {request.topic}", notes_md)
        safe_name = request.topic[:40].replace(" ", "_").replace("/", "-")
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=HaqDar_Notes_{safe_name}.docx"},
        )

    return {"note_id": note_id, "topic": request.topic, "notes": notes_md, "language": request.language}


# ════════════════════════════════════════════════════════════════════════════════
# 3. FLASHCARD GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/flashcards")
async def generate_flashcards(request: FlashcardsRequest):
    """Generate a set of Leitner-ready flashcards for a legal topic."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    cache_key = f"{uid}:{request.topic}:{request.difficulty}:{request.count}"
    if cache_key in _flashcard_cache:
        return _flashcard_cache[cache_key]

    try:
        matches = search_similar_laws(request.topic, neighbor_count=3)
        law_context = "\n\n".join(m["text"] for m in matches if m.get("text"))
    except Exception:
        law_context = ""

    prompt = f"""You are HaqDar AI Study — generating flashcards for a Pakistani law student.

TOPIC: {request.topic}
DIFFICULTY: {request.difficulty} — {_difficulty_instruction(request.difficulty)}
COUNT: Generate exactly {request.count} flashcards.

RELEVANT LAW:
{law_context if law_context else "(Use your knowledge of Pakistani law)"}

Generate a JSON array of flashcard objects. Each object must have:
- "id": unique string like "fc_1", "fc_2", etc.
- "front": the question or term (concise, max 2 sentences)
- "back": the answer or definition (detailed, citing act + section where applicable)
- "difficulty": "easy" | "medium" | "hard"
- "tags": array of 1-3 relevant legal topic strings
- "hint": a one-line hint to help recall

{_lang_directive(request.language)}

Return ONLY the JSON array. No markdown fences. No commentary."""

    raw = _call_gemini(prompt, temperature=0.25, json_mode=True)
    try:
        cards = json.loads(raw)
        if not isinstance(cards, list):
            raise ValueError("Not a list")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse flashcard JSON from AI")

    # Persist deck to Firestore
    try:
        db = _get_db()
        deck_ref = db.collection("flashcards").add({
            "uid": uid,
            "topic": request.topic,
            "difficulty": request.difficulty,
            "language": request.language,
            "cards": cards,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "leitner_state": {str(i): 1 for i in range(len(cards))},  # all cards start in box 1
        })
        deck_id = deck_ref[1].id
    except Exception as e:
        logger.error(f"Flashcard persist failed: {e}")
        deck_id = None

    log_audit_event(uid, "flashcards_generated", {"topic": request.topic, "count": len(cards)})

    result = {"deck_id": deck_id, "topic": request.topic, "cards": cards, "count": len(cards)}
    _flashcard_cache[cache_key] = result
    return result


# ════════════════════════════════════════════════════════════════════════════════
# 4. QUIZ GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/quiz/generate")
async def generate_quiz(request: QuizGenerateRequest):
    """Generate an MCQ quiz grounded in Pakistani law."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    try:
        matches = search_similar_laws(request.topic, neighbor_count=4)
        law_context = "\n\n".join(m["text"] for m in matches if m.get("text"))
    except Exception:
        law_context = ""

    prompt = f"""You are HaqDar AI Study — a Pakistani law examination question generator.

TOPIC: {request.topic}
DIFFICULTY: {request.difficulty} — {_difficulty_instruction(request.difficulty)}
NUMBER OF QUESTIONS: {request.count}

RELEVANT LAW SECTIONS:
{law_context if law_context else "(Use your knowledge of Pakistani law)"}

Generate a JSON object with this exact structure:
{{
  "quiz_id": "qz_<random 8 char alphanum>",
  "topic": "{request.topic}",
  "difficulty": "{request.difficulty}",
  "questions": [
    {{
      "id": "q_1",
      "question": "The MCQ question text",
      "options": {{
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      }},
      "correct": "B",
      "explanation": "Detailed explanation citing the exact law act and section number",
      "law_reference": "e.g. Section 302, Pakistan Penal Code, 1860"
    }}
  ]
}}

Rules:
- All 4 options must be plausible (no obviously wrong distractors)
- Explanations must cite specific Pakistani law references
- {_lang_directive(request.language)}
- Return ONLY the JSON object. No markdown fences."""

    raw = _call_gemini(prompt, temperature=0.3, json_mode=True)
    try:
        quiz = json.loads(raw)
        if "questions" not in quiz:
            raise ValueError("Missing questions key")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse quiz JSON from AI")

    # Store the answer key in Firestore (hidden from client)
    try:
        db = _get_db()
        answer_key = {q["id"]: q["correct"] for q in quiz.get("questions", [])}
        db.collection("quiz_answer_keys").document(quiz.get("quiz_id", "unknown")).set({
            "uid": uid,
            "topic": request.topic,
            "answer_key": answer_key,
            "difficulty": request.difficulty,
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Quiz answer key persist failed: {e}")

    # Return quiz without answer key to client
    client_quiz = {**quiz}
    for q in client_quiz.get("questions", []):
        q.pop("correct", None)  # never send answer to client during quiz

    log_audit_event(uid, "quiz_generated", {"topic": request.topic, "count": len(quiz.get("questions", []))})
    return client_quiz


# ════════════════════════════════════════════════════════════════════════════════
# 5. QUIZ SUBMIT & SCORE
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/quiz/submit")
async def submit_quiz(request: QuizSubmitRequest):
    """Score a quiz attempt and return results with explanations."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]
    db = _get_db()

    # Fetch answer key from Firestore
    try:
        key_doc = db.collection("quiz_answer_keys").document(request.quiz_id).get()
        if not key_doc.exists:
            raise HTTPException(status_code=404, detail="Quiz not found or expired")
        key_data = key_doc.to_dict()
        if key_data.get("uid") != uid:
            raise HTTPException(status_code=403, detail="Quiz does not belong to this user")
        answer_key: dict = key_data.get("answer_key", {})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz key fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quiz answer key")

    # Score the answers
    results = []
    correct_count = 0
    for ans in request.answers:
        correct = answer_key.get(ans.question_id)
        is_correct = (ans.selected == correct)
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": ans.question_id,
            "selected": ans.selected,
            "correct": correct,
            "is_correct": is_correct,
        })

    total = len(request.answers)
    score_pct = round((correct_count / total) * 100) if total > 0 else 0

    # Persist attempt
    try:
        db.collection("quiz_attempts").add({
            "uid": uid,
            "quiz_id": request.quiz_id,
            "topic": request.topic,
            "score": score_pct,
            "correct": correct_count,
            "total": total,
            "results": results,
            "submittedAt": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Quiz attempt persist failed: {e}")

    log_audit_event(uid, "quiz_submitted", {"topic": request.topic, "score": score_pct})

    return {
        "quiz_id": request.quiz_id,
        "topic": request.topic,
        "score": score_pct,
        "correct": correct_count,
        "total": total,
        "results": results,
        "grade": "Distinction" if score_pct >= 80 else "Pass" if score_pct >= 50 else "Fail",
    }


# ════════════════════════════════════════════════════════════════════════════════
# 6. ANSWER COMPARISON (SELF-ASSESSMENT)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/compare")
async def compare_answer(request: CompareRequest):
    """Compare a student's handwritten answer against the ideal legal answer."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    try:
        matches = search_similar_laws(request.question, neighbor_count=4)
        law_context = "\n\n".join(m["text"] for m in matches if m.get("text"))
    except Exception:
        law_context = ""

    prompt = f"""You are a Pakistani law examiner grading a student's answer.

LEGAL QUESTION:
{request.question}

STUDENT'S ANSWER:
{request.student_answer}

RELEVANT LAW SECTIONS FROM DATABASE:
{law_context if law_context else "(Use your knowledge of Pakistani law)"}

Evaluate the student's answer and return a JSON object with this exact structure:
{{
  "score": <integer 0-100>,
  "grade": "<Distinction|Merit|Pass|Fail>",
  "ideal_answer": "<the complete ideal legal answer citing all relevant laws and sections>",
  "strengths": ["<what the student got right>", ...],
  "improvements": ["<what should be improved>", ...],
  "missing_provisions": ["<important legal provisions, acts, or sections the student omitted>", ...],
  "examiner_note": "<a short, constructive paragraph from the examiner>"
}}

Scoring guide: 80-100 Distinction, 60-79 Merit, 40-59 Pass, 0-39 Fail.
{_lang_directive(request.language)}
Return ONLY the JSON object. No markdown fences."""

    raw = _call_gemini(prompt, temperature=0.2, json_mode=True)
    try:
        result = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse comparison result from AI")

    # Persist
    try:
        db = _get_db()
        db.collection("comparison_attempts").add({
            "uid": uid,
            "question": request.question,
            "student_answer": request.student_answer,
            "score": result.get("score"),
            "grade": result.get("grade"),
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Comparison persist failed: {e}")

    log_audit_event(uid, "answer_compared", {"score": result.get("score")})
    return result


# ════════════════════════════════════════════════════════════════════════════════
# 7. PROGRESS TRACKER
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/progress")
async def get_progress(token: str):
    """Calculate mastery metrics, streak count, and study recommendations."""
    user_info = _require_auth(token)
    uid = user_info["uid"]

    if uid in _progress_cache:
        return _progress_cache[uid]

    db = _get_db()

    # Fetch quiz attempts
    try:
        attempts_query = (
            db.collection("quiz_attempts")
            .where("uid", "==", uid)
            .order_by("submittedAt", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        attempts = [a.to_dict() for a in attempts_query]
    except Exception as e:
        logger.error(f"Progress fetch failed: {e}")
        attempts = []

    # Compute mastery per topic
    topic_stats: dict = {}
    for a in attempts:
        topic = a.get("topic", "General")
        if topic not in topic_stats:
            topic_stats[topic] = {"scores": [], "attempts": 0}
        topic_stats[topic]["scores"].append(a.get("score", 0))
        topic_stats[topic]["attempts"] += 1

    mastery = []
    for topic, data in topic_stats.items():
        avg_score = round(sum(data["scores"]) / len(data["scores"])) if data["scores"] else 0
        mastery.append({
            "topic": topic,
            "mastery_pct": avg_score,
            "attempts": data["attempts"],
            "level": "Expert" if avg_score >= 80 else "Proficient" if avg_score >= 60 else "Developing" if avg_score >= 40 else "Beginner",
        })

    mastery.sort(key=lambda x: x["mastery_pct"], reverse=True)

    # Streak calculation
    streak = 0
    try:
        today = datetime.now(timezone.utc).date()
        study_dates = set()
        for a in attempts:
            ts = a.get("submittedAt")
            if ts:
                if hasattr(ts, "date"):
                    study_dates.add(ts.date())
                else:
                    study_dates.add(datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).date())
        d = today
        while d in study_dates:
            streak += 1
            d -= timedelta(days=1)
    except Exception:
        streak = 0

    # Recommendations: topics with mastery < 60
    weak = [m["topic"] for m in mastery if m["mastery_pct"] < 60]
    recommendations = weak[:3] if weak else ["Keep practicing to maintain your mastery!"]

    # Total stats
    total_quizzes = len(attempts)
    avg_score_overall = round(sum(a.get("score", 0) for a in attempts) / total_quizzes) if total_quizzes else 0

    result = {
        "uid": uid,
        "streak_days": streak,
        "total_quizzes": total_quizzes,
        "average_score": avg_score_overall,
        "mastery": mastery,
        "recommendations": recommendations,
        "badge": (
            "⭐ Law Scholar" if avg_score_overall >= 80 else
            "📚 Dedicated Learner" if avg_score_overall >= 60 else
            "🌱 Rising Advocate" if total_quizzes > 0 else
            "🎓 Just Starting"
        ),
    }
    _progress_cache[uid] = result
    return result


# ════════════════════════════════════════════════════════════════════════════════
# 8. MIND MAP GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/mindmap")
async def generate_mindmap(request: MindMapRequest):
    """Generate a Mermaid.js mind map for a legal concept."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    prompt = f"""You are HaqDar AI Study generating a Mermaid.js mind map for a Pakistani law student.

LEGAL CONCEPT: {request.concept}

Generate a Mermaid mind map diagram using the `mindmap` syntax.
Rules:
- Root node should be the concept name
- Include 4-6 major branches (e.g. Definition, Key Sections, Elements, Exceptions, Penalties, Examples)
- Each branch can have 2-4 sub-nodes with brief labels
- Labels must be concise (max 5 words per node)
- {_lang_directive(request.language)}
- Return ONLY the raw Mermaid code block text (starting with "mindmap"), no markdown fences, no commentary.

Example format:
mindmap
  root((Contract Law))
    Definition
      Agreement
      Consideration
    Key Sections
      Sec 10 Contract Act
      Sec 2 Offer

Generate the mind map now:"""

    mermaid_code = _call_gemini(prompt, temperature=0.2)

    # Clean up any accidental markdown fences
    mermaid_code = mermaid_code.strip()
    if mermaid_code.startswith("```"):
        lines = mermaid_code.split("\n")
        mermaid_code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    log_audit_event(uid, "mindmap_generated", {"concept": request.concept})
    return {"concept": request.concept, "mermaid": mermaid_code}


# ════════════════════════════════════════════════════════════════════════════════
# 9. CASE BRIEF GENERATOR
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/case-brief")
async def generate_case_brief(request: CaseBriefRequest):
    """Generate a structured case brief for a Pakistani court citation."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    prompt = f"""You are HaqDar AI Study — a Pakistani legal case analyst.

Generate a structured case brief for the following citation:

CITATION: {request.citation}

Return a JSON object with this structure:
{{
  "citation": "{request.citation}",
  "court": "<Full court name, e.g. Supreme Court of Pakistan>",
  "year": "<Year of decision>",
  "parties": {{
    "appellant": "<Name>",
    "respondent": "<Name>"
  }},
  "facts": "<2-4 paragraph summary of the key facts>",
  "issues": ["<Legal issue 1>", "<Legal issue 2>", ...],
  "decision": "<The court's final ruling>",
  "ratio_decidendi": "<The legal principle(s) established or applied>",
  "obiter_dicta": "<Any notable obiter remarks, or null if none>",
  "applicable_laws": ["<Act name + Section>", ...],
  "significance": "<Why this case matters — its precedential value>",
  "keywords": ["<tag1>", "<tag2>", ...]
}}

Use your knowledge of Pakistani case law. If the exact case is unknown, generate a realistic brief based on the citation format and any identifiable details. Always clearly note if you cannot confirm the exact case.
{_lang_directive(request.language)}
Return ONLY the JSON object. No markdown fences."""

    raw = _call_gemini(prompt, temperature=0.2, json_mode=True)
    try:
        brief = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse case brief JSON from AI")

    # Persist
    try:
        db = _get_db()
        db.collection("case_briefs").add({
            "uid": uid,
            "citation": request.citation,
            "brief": brief,
            "language": request.language,
            "createdAt": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Case brief persist failed: {e}")

    log_audit_event(uid, "case_brief_generated", {"citation": request.citation})
    return brief


# ════════════════════════════════════════════════════════════════════════════════
# 10. SOCRATIC AI TUTOR
# ════════════════════════════════════════════════════════════════════════════════

class TutorRequest(BaseModel):
    token: str
    topic: str
    difficulty: str = "standard"
    message: str
    conversation_history: List[dict] = []
    language: str = "en"


@router.post("/tutor")
async def socratic_tutor(request: TutorRequest):
    """
    Socratic AI Tutor endpoint. 
    Guides the student through a legal concept by asking questions, checking understanding, 
    and helping them arrive at the correct legal provisions themselves.
    """
    user_info = _require_auth(request.token)
    uid = user_info["uid"]

    # Scrub PII from input topic
    scrubbed_topic = scrub_pii(request.topic)

    # Retrieve matching law text if possible
    try:
        matches = search_similar_laws(scrubbed_topic, neighbor_count=3)
        law_context = "\n\n".join(m["text"] for m in matches if m.get("text"))
    except Exception:
        law_context = ""

    # Build Socratic Tutor system instruction
    system_instruction = f"""You are HaqDar AI Socratic Tutor — a highly encouraging and wise legal tutor for Pakistani law.
Your target topic is: {scrubbed_topic}
Difficulty: {request.difficulty} — {_difficulty_instruction(request.difficulty)}

[SOCRATIC METHOD CORE PRINCIPLE]
- DO NOT just give the student direct answers or complete essays.
- Guide the student by asking open-ended questions, raising legal hypotheticals, and prompting them to explain key concepts.
- Provide gentle hints citing the relevant act name and section when they struggle.
- Highlight mistakes in their legal reasoning constructively.
- Keep responses relatively brief (under 150 words) to maintain an interactive dialogue.
- Ground your teaching in: {law_context if law_context else "(Use your training knowledge of Pakistani law)"}

[LANGUAGE]
- {_lang_directive(request.language)}
"""
    # Build contents from history
    from google.genai.types import Content, Part
    contents = []
    for msg in request.conversation_history:
        role = "user" if msg.get("role") == "user" else "model"
        # Scrub PII from conversation history
        scrubbed_msg_content = scrub_pii(msg.get("content", ""))
        contents.append(Content(role=role, parts=[Part(text=scrubbed_msg_content)]))
    
    # Scrub PII from the current user message
    scrubbed_message = scrub_pii(request.message)
    # Add current message
    contents.append(Content(role="user", parts=[Part(text=scrubbed_message)]))

    # Call Gemini
    from google.genai.types import GenerateContentConfig
    try:
        response = _get_gemini().models.generate_content(
            model=settings.GEMINI_FLASH_MODEL,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )
        tutor_response = response.text.strip() if response.text else ""
    except Exception as e:
        logger.error(f"Tutor Gemini call failed: {e}")
        raise HTTPException(status_code=502, detail=f"Tutor AI failed: {str(e)}")

    log_audit_event(uid, "study_tutor_interact", {"topic": scrubbed_topic})
    return {"response": tutor_response}


@router.post("/flashcards/review")
async def review_flashcard(request: FlashcardReviewRequest):
    """Update spaced repetition progress (Leitner Box level) for a card in a deck."""
    user_info = _require_auth(request.token)
    uid = user_info["uid"]
    
    if not request.deck_id:
        raise HTTPException(status_code=400, detail="Invalid deck_id")
         
    db = _get_db()
    try:
        deck_ref = db.collection("flashcards").document(request.deck_id)
        deck_doc = deck_ref.get()
        if not deck_doc.exists:
            raise HTTPException(status_code=404, detail="Flashcard deck not found")
            
        deck_data = deck_doc.to_dict()
        if deck_data.get("uid") != uid:
            raise HTTPException(status_code=403, detail="Deck does not belong to this user")
            
        # Get current leitner state
        leitner_state = deck_data.get("leitner_state") or {}
        idx_str = str(request.card_index)
        
        current_level = leitner_state.get(idx_str, 1)
        if request.recalled:
            new_level = min(current_level + 1, 5)
        else:
            new_level = 1
            
        leitner_state[idx_str] = new_level
        
        # Update Firestore
        deck_ref.update({
            "leitner_state": leitner_state
        })
        
        return {"success": True, "card_index": request.card_index, "new_level": new_level}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Leitner state: {e}")
        raise HTTPException(status_code=500, detail="Failed to update flashcard review progress")

