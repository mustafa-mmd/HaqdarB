# app/api/v1/endpoints/query.py
"""
HaqDar AI — Main API Router v2.0
All legal endpoints with quota enforcement, audit logging, and streaming support.
"""
import re
import json
import logging
import base64
import io
import difflib
from typing import Optional, List
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google.cloud import firestore

from app.core.firebase import verify_token, verify_token_optional
from app.core.config import settings
from app.services.vector_search import search_similar_laws
from app.services.gemini_service import get_legal_explanation, get_legal_explanation_stream
from app.services.document_agent import analyze_legal_document, analyze_legal_document_pdf_pages
from app.services.intake_agent import classify_legal_category, detect_language_and_script
from app.services.peca_agent import get_peca_analysis
from app.services.referral_agent import get_legal_aid_by_city
from app.services.universal_drafting_agent import (
    generate_universal_document_with_search,
    generate_universal_document_with_context,
    generate_document_from_template,
)
from app.services.case_analyzer import analyze_case_strength
from app.services.usage_service import (
    check_and_increment_usage,
    get_usage_stats,
    get_user_plan,
    get_user_profile,
    update_user_profile,
    log_audit_event,
)
from app.services.transcription_service import transcribe_audio
from app.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Singleton Firestore client ──
_db = None


def get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


# ════════════════════════════════════════════════════════════════════════════════
# PYDANTIC REQUEST / RESPONSE MODELS
# ════════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    token: str
    language: Optional[str] = None
    conversation_history: Optional[List[dict]] = Field(default=None)


class DraftRequest(BaseModel):
    addressed_to: str = Field(default="Deputy Commissioner")
    complainant_name: str
    complainant_address: str
    respondent_name: str
    incident_date: str
    description: str
    law_sections: List[str] = []
    language: str = "ur"
    token: str


class TemplateRequest(BaseModel):
    template_type: str = Field(..., description="e.g., 'Rent Agreement', 'FIR Draft', 'Legal Notice'")
    form_data: dict
    language: str = "en"
    token: str

class DownloadDocxRequest(BaseModel):
    text: str
    filename: str = "HaqDar_Document"


class CaseAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    token: str
    language: Optional[str] = None


class UserProfileUpdate(BaseModel):
    token: str
    preferred_language: Optional[str] = None
    city: Optional[str] = None
    display_name: Optional[str] = None
    legal_interests: Optional[List[str]] = None
    onboarding_complete: Optional[bool] = None
    disclaimer_acknowledged: Optional[bool] = None


class UniversalDraftResponse(BaseModel):
    domain: str = "other"
    document_type: str = "unknown"
    applicable_laws: list = []
    severity: str = "low"
    explanation: str = ""
    document_draft: str = ""
    submission_authority: str = ""
    required_attachments: list = []
    fees_required: str = ""
    time_limitation: str = ""
    next_steps: list = []
    free_legal_aid: str = ""
    disclaimers: list = []


class PecaResponse(BaseModel):
    peca_sections: list = []
    severity: str = "low"
    explanation: str = ""
    fir_draft: str = ""


class DocumentResponse(BaseModel):
    document_type: str = ""
    language_detected: str = ""
    key_parties: list = []
    dates: dict = {}
    legal_claims: str = ""
    potential_violations: list = []
    document_sections: list = []
    action_required: dict = {}
    severity: str = "low"
    summary: str = ""
    red_flags: list = []
    recommended_next_steps: list = []
    disclaimers: list = []


# ════════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """System health check endpoint."""
    health = {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {},
    }
    # Check Firestore
    try:
        get_db().collection("_health").limit(1).get()
        health["services"]["firestore"] = "ok"
    except Exception as e:
        health["services"]["firestore"] = f"error: {str(e)[:50]}"
        health["status"] = "degraded"

    return health


# ════════════════════════════════════════════════════════════════════════════════
# USER PROFILE & DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/user/profile")
async def get_profile(token: str):
    """Get user profile, plan, and usage statistics."""
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    profile = get_user_profile(uid)
    stats = get_usage_stats(uid)
    plan = get_user_plan(uid)

    return {
        "uid": uid,
        "plan": plan,
        "profile": profile,
        "usage": stats,
        "limits": {
            "queries_per_day": 10 if plan == "free" else 500 if plan == "pro" else 9999,
            "drafts_per_month": 2 if plan == "free" else 50 if plan == "pro" else 9999,
            "analyses_per_month": 1 if plan == "free" else 20 if plan == "pro" else 9999,
        },
    }


@router.post("/user/profile")
async def update_profile(request: UserProfileUpdate):
    """Update user profile settings."""
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    data = request.dict(exclude={"token"}, exclude_none=True)
    success = update_user_profile(uid, data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    return {"success": True, "message": "Profile updated successfully"}


# ════════════════════════════════════════════════════════════════════════════════
# LEGAL QUERY (MAIN CHAT)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/query")
@limiter.limit("20/minute")
async def legal_query(query_data: QueryRequest, request: Request):
    """
    Main legal Q&A endpoint.
    Searches law corpus, generates multilingual explanation grounded in Pakistani law.
    Supports conversation history for multi-turn memory.
    """
    user_info = verify_token(query_data.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    # ── Quota check ──
    allowed, msg = check_and_increment_usage(uid, "query")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    # ── Language detection ──
    user_lang = query_data.language
    if user_lang:
        language = user_lang
        script = "arabic" if language in ("ur", "ps", "pa", "sd", "bal") else "latin"
    else:
        language, script = detect_language_and_script(query_data.text)

    category = classify_legal_category(query_data.text)

    # ── Vector search ──
    try:
        matches = search_similar_laws(
            query_data.text,
            neighbor_count=5,
            language=language if language != "en" else None,
            category=category if category != "general" else None,
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        matches = []

    # Qdrant returns text directly in payload — no Firestore needed
    law_texts = [m["text"] for m in matches if m.get("text")]

    # ── Generate explanation with conversation history ──
    top_distance = matches[0]["distance"] if matches else 999.0
    explanation = get_legal_explanation(
        query_data.text,
        law_texts,
        top_distance,
        language,
        script,
        conversation_history=query_data.conversation_history,
        uid=uid,
    )

    # ── Safety: strip any Hindi/Gurmukhi characters ──
    explanation = re.sub(r'[\u0900-\u097F\u0A00-\u0A7F]', '', explanation)

    # ── Audit log ──
    log_audit_event(uid, "query", {"category": category, "language": language})

    return {
        "matches": matches[:3],
        "law_texts": law_texts[:3],
        "explanation": explanation,
        "category": category,
        "language": language,
        "script": script,
    }


@router.post("/query-stream")
async def legal_query_stream(request: QueryRequest):
    """
    Streaming legal Q&A endpoint using Server-Sent Events (SSE).
    """
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "query")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    user_lang = request.language
    if user_lang:
        language = user_lang
        script = "arabic" if language in ("ur", "ps", "pa", "sd", "bal") else "latin"
    else:
        language, script = detect_language_and_script(request.text)

    category = classify_legal_category(request.text)

    try:
        matches = search_similar_laws(
            request.text,
            neighbor_count=5,
            language=language if language != "en" else None,
            category=category if category != "general" else None,
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        matches = []

    # Qdrant returns text directly in payload — no Firestore needed
    law_texts = [m["text"] for m in matches if m.get("text")]

    top_distance = matches[0]["distance"] if matches else 999.0

    async def generate_sse():
        # First yield the metadata
        metadata = {
            "type": "metadata",
            "matches": matches[:3],
            "law_texts": law_texts[:3],
            "category": category,
            "language": language,
            "script": script,
        }
        yield f"data: {json.dumps(metadata)}\n\n"
        
        log_audit_event(uid, "query_stream", {"category": category, "language": language})

        stream = get_legal_explanation_stream(
            request.text,
            law_texts,
            top_distance,
            language,
            script,
            conversation_history=request.conversation_history,
            uid=uid,
        )
        for chunk in stream:
            payload = {"type": "chunk", "text": chunk}
            yield f"data: {json.dumps(payload)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate_sse(), media_type="text/event-stream")


# ════════════════════════════════════════════════════════════════════════════════
# CASE STRENGTH ANALYZER (NEW)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/case-analyze")
async def case_analyze(request: CaseAnalyzeRequest):
    """
    AI Case Strength Analyzer.
    Returns case score (0-100), outcome prediction, required documents, and action plan.
    """
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "query")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    language = request.language or "en"
    if not request.language:
        language, _ = detect_language_and_script(request.text)

    result = analyze_case_strength(request.text, language)
    log_audit_event(uid, "case_analyzed", {"language": language})

    return result


# ════════════════════════════════════════════════════════════════════════════════
# UNIVERSAL LEGAL DOCUMENT DRAFTING
# ════════════════════════════════════════════════════════════════════════════════
@router.post("/draft-legal", response_model=UniversalDraftResponse)
@limiter.limit("10/minute")
async def universal_draft(query_data: QueryRequest, request: Request):
    """
    Universal legal document generator.
    Covers 80 legal categories with validated Pakistani document formats.
    """
    user_info = verify_token(query_data.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "draft")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    # ── Language detection and category classification ──
    user_lang = query_data.language
    if user_lang:
        language = user_lang
    else:
        language, _ = detect_language_and_script(query_data.text)

    category = classify_legal_category(query_data.text)

    # ── Vector search ──
    try:
        matches = search_similar_laws(
            query_data.text,
            neighbor_count=5,
            language=language if language != "en" else None,
            category=category if category != "general" else None,
        )
    except Exception:
        matches = []

    # Qdrant returns text directly in payload — no Firestore needed
    law_texts = [m["text"] for m in matches if m.get("text")]

    top_distance = matches[0]["distance"] if matches else 999.0
    weak_match = not law_texts or top_distance > 0.3

    lang = query_data.language or "en"
    if weak_match:
        result = generate_universal_document_with_search(query_data.text, lang)
    else:
        context = "\n\n".join(law_texts)
        result = generate_universal_document_with_context(query_data.text, context, lang)

    log_audit_event(uid, "draft_generated", {
        "domain": result.get("domain", ""),
        "document_type": result.get("document_type", ""),
    })
    return result
# ════════════════════════════════════════════════════════════════════════════════
# DOCUMENT TEMPLATE GENERATOR (NEW)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/draft-template")
async def draft_from_template(request: TemplateRequest):
    """
    Generate a legal document from a structured template with form data.
    Use for: Rent Agreement, FIR Draft, Nikah Deed, Employment Contract, etc.
    """
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "draft")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    result = generate_document_from_template(
        template_type=request.template_type,
        form_data=request.form_data,
        language=request.language,
    )
    log_audit_event(uid, "template_generated", {"template": request.template_type})
    return result


@router.get("/templates")
async def list_templates():
    """Return the list of available document templates."""
    return {
        "templates": [
            {"id": "fir_draft", "name": "FIR Draft (S.154 CrPC)", "category": "Criminal", "fields": ["complainant_name", "complainant_cnic", "complainant_address", "accused_name", "incident_date", "incident_location", "incident_description", "witnesses"]},
            {"id": "legal_notice", "name": "Legal Notice", "category": "Civil", "fields": ["sender_name", "sender_address", "recipient_name", "recipient_address", "subject", "facts", "demand", "deadline_days"]},
            {"id": "rent_agreement", "name": "Rent / Tenancy Agreement", "category": "Property", "fields": ["landlord_name", "tenant_name", "property_address", "rent_amount", "advance_amount", "lease_start", "lease_duration", "utilities_included"]},
            {"id": "employment_contract", "name": "Employment Contract", "category": "Labour", "fields": ["company_/_organization_name", "employee_name", "designation", "department", "salary", "start_date", "probation_period", "office_hours", "leave_entitlement"]},
            {"id": "partnership_deed", "name": "Partnership Deed", "category": "Corporate", "fields": ["partner1_name", "partner2_name", "business_name", "business_type", "capital_partner1", "capital_partner2", "profit_ratio", "loss_ratio", "duration"]},
            {"id": "sale_deed", "name": "Sale Deed (Bai Nama)", "category": "Property", "fields": ["seller_name", "seller_cnic", "buyer_name", "buyer_cnic", "property_description", "sale_price", "advance_paid", "balance", "witnesses"]},
            {"id": "gift_deed", "name": "Gift Deed (Hiba Nama)", "category": "Property", "fields": ["donor_name", "donor_cnic", "donee_name", "donee_cnic", "relationship", "property_description", "witnesses"]},
            {"id": "khula_petition", "name": "Khula Petition", "category": "Family", "fields": ["wife_name", "husband_name", "nikah_date", "children", "mehr_amount", "grounds_for_khula"]},
            {"id": "maintenance_application", "name": "Maintenance Application", "category": "Family", "fields": ["applicant_name", "respondent_name", "relationship", "children_details", "current_expenses", "respondent_income"]},
            {"id": "succession_certificate", "name": "Succession Certificate Application", "category": "Inheritance", "fields": ["deceased_name", "deceased_cnic", "date_of_death", "heirs_list", "assets_description", "court_jurisdiction"]},
            {"id": "bail_application", "name": "Bail Application", "category": "Criminal", "fields": ["accused_name", "accused_cnic", "fir_number", "sections_applied", "court_name", "grounds_for_bail", "surety_name", "surety_property"]},
            {"id": "consumer_complaint", "name": "Consumer Court Complaint", "category": "Consumer", "fields": ["complainant_name", "seller_name", "product_description", "purchase_date", "amount_paid", "defect_description", "relief_sought"]},
            {"id": "nab_complaint", "name": "NAB Complaint", "category": "Anti-Corruption", "fields": ["complainant_name", "accused_name", "accused_designation", "nature_of_corruption", "estimated_amount", "evidence_description", "witnesses"]},
            {"id": "nepra_complaint", "name": "NEPRA/Electricity Complaint", "category": "Energy", "fields": ["consumer_name", "reference_number", "distribution_company", "issue_type", "billing_period", "disputed_amount", "complaint_history"]},
            {"id": "harassment_complaint", "name": "Workplace Harassment Complaint", "category": "Labour", "fields": ["complainant_name", "designation", "harasser_name", "harasser_designation", "incident_dates", "incident_description", "witnesses", "evidence"]},
            {"id": "writ_habeas_corpus", "name": "Writ Petition — Habeas Corpus", "category": "Constitutional", "fields": ["detainee_name", "detainee_cnic", "date_of_detention", "detaining_authority", "place_of_detention", "grounds"]},
            {"id": "peca_fia_complaint", "name": "FIA Cybercrime Complaint (PECA)", "category": "Cybercrime", "fields": ["complainant_name", "complainant_cnic", "platform", "accused_account", "nature_of_crime", "evidence_list", "peca_sections"]},
            {"id": "dv_protection_order", "name": "Domestic Violence Protection Order", "category": "Family", "fields": ["applicant_name", "applicant_cnic", "respondent_name", "relationship", "nature_of_violence", "children_affected", "witnesses", "evidence"]},
            {"id": "nikah_deed", "name": "Nikah Deed (Marriage Contract)", "category": "Family", "fields": ["groom_name", "groom_cnic", "bride_name", "bride_cnic", "mehr_amount", "mehr_type", "conditions", "witnesses", "nikah_registrar"]},
            {"id": "labour_court_application", "name": "Labour Court Application", "category": "Labour", "fields": ["worker_name", "worker_cnic", "employer_name", "employment_period", "last_salary", "nature_of_dispute", "reliefs_sought"]},
            {"id": "affidavit_passport", "name": "Affidavit for Passport (Lost/Name Change)", "category": "Civil", "fields": ["applicant_name", "applicant_cnic", "father_name", "reason", "declaration_text", "passport_number"]},
            {"id": "indemnity_bond", "name": "Indemnity Bond", "category": "Legal", "fields": ["obligor_name", "obligor_cnic", "beneficiary_name", "subject_matter", "amount", "guarantor_name", "guarantor_cnic"]},
            {"id": "trust_deed", "name": "Trust Deed", "category": "Corporate", "fields": ["settlor_name", "trustee_name", "trust_name", "trust_objectives", "initial_assets", "beneficiaries"]},
            {"id": "lease_cancellation", "name": "Lease Cancellation Agreement", "category": "Property", "fields": ["landlord_name", "tenant_name", "property_address", "cancellation_date", "settlement_amount", "security_refund"]},
            {"id": "stay_order_application", "name": "Stay Order (Injunction) Application", "category": "Civil", "fields": ["plaintiff_name", "defendant_name", "case_number", "property_in_dispute", "reason_for_stay", "immediate_danger"]},
            {"id": "dower_recovery", "name": "Recovery of Dower (Haq Mehr) Petition", "category": "Family", "fields": ["wife_name", "husband_name", "nikah_date", "unpaid_mehr_amount", "mehr_type", "nikah_registrar"]},
            {"id": "restitution_conjugal", "name": "Restitution of Conjugal Rights", "category": "Family", "fields": ["husband_name", "wife_name", "marriage_date", "separation_date", "reason_for_separation", "prayer"]},
            {"id": "arbitration_agreement", "name": "Arbitration Agreement", "category": "Civil", "fields": ["party1_name", "party2_name", "nature_of_dispute", "arbitrator_name", "venue", "governing_law"]},
            {"id": "general_power_of_attorney", "name": "General Power of Attorney", "category": "Legal", "fields": ["principal_name", "principal_cnic", "agent_name", "agent_cnic", "powers_granted", "property_details"]},
            {"id": "special_power_of_attorney", "name": "Special Power of Attorney (Court Matters)", "category": "Legal", "fields": ["principal_name", "agent_name", "case_title", "court_name", "specific_act_authorized"]},
        ]
    }


# ════════════════════════════════════════════════════════════════════════════════
# PECA / CYBERCRIME SPECIALIST
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/peca", response_model=PecaResponse)
async def peca_query(request: QueryRequest):
    """PECA specialist endpoint — cybercrime analysis and FIR draft."""
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "query")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    try:
        result = get_peca_analysis(request.text)
        log_audit_event(uid, "peca_query", {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════════
# COMPLAINT LETTER DRAFTING (WORD DOCUMENT)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/draft")
async def draft_complaint(request: DraftRequest):
    """Generate a formal complaint letter as a downloadable Word document."""
    user_info = verify_token(request.token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "draft")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    from app.services.drafting_agent import generate_complaint_letter
    case_data = request.dict()
    if "token" in case_data:
        del case_data["token"]

    buffer = generate_complaint_letter(case_data, request.language)
    log_audit_event(uid, "complaint_drafted", {"language": request.language})
    filename = f"complaint_{request.language}.docx"
    return StreamingResponse(
        buffer,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.post("/download-docx")
async def download_docx(request: DownloadDocxRequest):
    """Convert raw text to a proper MS Word document (.docx) for download."""
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    import re
    
    doc = Document()
    
    # Very basic styling for a professional look
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    lines = request.text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            doc.add_paragraph("")
            continue
            
        p = doc.add_paragraph()
        
        # Check if RTL (Urdu/Arabic)
        arabic_count = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', line))
        if arabic_count > len(line) * 0.3:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            pPr = p._element.get_or_add_pPr()
            bidi = pPr.makeelement(qn('w:bidi'), nsmap={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
            bidi.set(qn('w:val'), '1')
            pPr.append(bidi)
        
        # Strip markdown bold asterisks but make the line bold if it's a heading
        if line.startswith("**") and line.endswith("**"):
            run = p.add_run(line.strip("*"))
            run.bold = True
            if arabic_count == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            run = p.add_run(line.replace("**", "").replace("*", ""))
            
        if arabic_count > len(line) * 0.3:
            run.font.name = 'Noto Nastaliq Urdu'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Noto Nastaliq Urdu')
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={request.filename}.docx"}
    )

# ════════════════════════════════════════════════════════════════════════════════
# DOCUMENT ANALYSIS (IMAGE + PDF)
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/document")
async def analyze_document(file: UploadFile = File(...), token: str = Form(...)):
    """
    Upload a legal document (image: JPG/PNG or PDF) for AI analysis.
    Returns: document type, parties, dates, legal claims, red flags, severity.
    """
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    uid = user_info["uid"]

    allowed, msg = check_and_increment_usage(uid, "analysis")
    if not allowed:
        raise HTTPException(status_code=429, detail=msg)

    contents = await file.read()
    filename = file.filename or ""
    content_type = file.content_type or ""

    # ── PDF handling ──
    if filename.lower().endswith(".pdf") or "pdf" in content_type:
        try:
            import fitz  # PyMuPDF
            pdf_doc = fitz.open(stream=contents, filetype="pdf")
            pages_b64 = []
            for page_num in range(min(len(pdf_doc), 10)):
                page = pdf_doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                img_bytes = pix.tobytes("jpeg")
                pages_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
            pdf_doc.close()
            result = analyze_legal_document_pdf_pages(pages_b64)
        except ImportError:
            # PyMuPDF not installed — fallback to single-image analysis
            image_b64 = base64.b64encode(contents).decode("utf-8")
            result = analyze_legal_document(image_b64, "application/pdf")
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    else:
        # ── Image handling ──
        mime = content_type if content_type.startswith("image/") else "image/jpeg"
        image_b64 = base64.b64encode(contents).decode("utf-8")
        result = analyze_legal_document(image_b64, mime)

    log_audit_event(uid, "document_analyzed", {"filename": filename[:100]})
    return result


# ════════════════════════════════════════════════════════════════════════════════
# LEGAL AID REFERRAL
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/referral")
async def legal_referral(city: str):
    """Get free legal aid contacts in the specified city or province."""
    results = get_legal_aid_by_city(city)
    if not results:
        return {"message": f"No legal aid providers found in {city}.", "providers": []}
    return {"city": city, "providers": results}


_cached_cities = None
_last_city_cache_time = 0
CITY_CACHE_TTL = 300 # 5 minutes

def get_all_cities_cached(db):
    global _cached_cities, _last_city_cache_time
    import time
    now = time.time()
    if _cached_cities is None or now - _last_city_cache_time > CITY_CACHE_TTL:
        try:
            # Optimize Firestore read: select only "city" field to avoid fetching huge docs
            docs = db.collection("legal_aid").select(["city"]).stream()
            cities = set()
            for doc in docs:
                city = doc.to_dict().get("city", "").strip()
                if city:
                    cities.add(city)
            if cities:
                _cached_cities = list(cities)
                _last_city_cache_time = now
            else:
                from app.services.referral_agent import KNOWN_CITIES
                _cached_cities = KNOWN_CITIES
        except Exception as e:
            logger.error(f"Error fetching cities for cache: {e}")
            from app.services.referral_agent import KNOWN_CITIES
            return KNOWN_CITIES
    return _cached_cities

@router.get("/referral/autocomplete")
async def autocomplete_city(q: str = ""):
    """Return city suggestions based on partial input (with caching)."""
    if not q or len(q.strip()) < 1:
        return {"suggestions": []}

    query = q.strip().lower()
    db = get_db()

    try:
        cities = get_all_cities_cached(db)
        suggestions = []
        for city in cities:
            city_lower = city.lower()
            if city_lower.startswith(query):
                suggestions.append((city, 1))
            elif query in city_lower:
                suggestions.append((city, 2))
            elif difflib.get_close_matches(query, [city_lower], n=1, cutoff=0.7):
                suggestions.append((city, 3))

        suggestions.sort(key=lambda x: (x[1], x[0].lower()))
        return {"suggestions": [s[0] for s in suggestions][:10]}
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return {"suggestions": []}


# ════════════════════════════════════════════════════════════════════════════════
# SPEECH-TO-TEXT TRANSCRIPTION
# ════════════════════════════════════════════════════════════════════════════════

@router.post("/transcribe")
@limiter.limit("10/minute")
async def transcribe_speech(
    request: Request,
    file: UploadFile = File(...),
    lang: str = Form("ur"),
    token: Optional[str] = Form(None),
):
    """Transcribe audio to text using Groq Whisper. Supports 6 regional languages."""
    if token:
        user_info = verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        uid = user_info["uid"]

    try:
        audio_bytes = await file.read()
        if len(audio_bytes) < 100:
            raise HTTPException(status_code=400, detail="Audio file is too small or empty")

        text = transcribe_audio(audio_bytes, file.filename or "recording.webm", lang)

        if not text or not text.strip():
            return {"text": "", "message": "No speech detected"}

        return {"text": text.strip()}

    except ValueError as e:
        logger.error(f"Transcription config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════════
# LEGAL NEWS FEED (NEW)
# ════════════════════════════════════════════════════════════════════════════════

@router.get("/news")
async def get_legal_news(category: str = "general", lang: str = "en", token: str = ""):
    """
    Get latest Pakistani legal news, Supreme Court judgments, and new laws.
    Powered by Gemini + Google Search Grounding.
    """
    if token:
        user_info = verify_token(token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid token")
        uid = user_info["uid"]

    from app.services.gemini_service import get_legal_news_feed
    try:
        news = get_legal_news_feed(category=category, language=lang)
        return {"category": category, "language": lang, "news": news}
    except Exception as e:
        logger.error(f"News feed error: {e}")
        return {"category": category, "language": lang, "news": []}