# app/services/drafting_agent.py
import os
from datetime import datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import json

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")

def _translate_fields(case_data: dict, language: str) -> dict:
    from app.services.gemini_service import client
    from google.genai import types

    target = "Urdu" if language == "ur" else "English"
    prompt = f"""
    Translate the values in this JSON to {target} language.
    Preserve the keys exactly as they are. ONLY return the valid JSON.
    {{
        "addressed_to": "{case_data.get('addressed_to', 'Deputy Commissioner')}",
        "complainant_name": "{case_data.get('complainant_name', '')}",
        "complainant_address": "{case_data.get('complainant_address', '')}",
        "respondent_name": "{case_data.get('respondent_name', '')}",
        "description": "{case_data.get('description', '')}"
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        # Strip markdown json block if present
        text = response.text.replace("```json", "").replace("```", "").strip()
        translated = json.loads(text)
        
        # Merge back
        for k, v in translated.items():
            if v:
                case_data[k] = v
    except Exception as e:
        print(f"Translation failed: {e}")
    return case_data

def generate_complaint_letter(case_data: dict, language: str = "ur") -> BytesIO:
    # Translate fields into the target language to prevent mixing English and Urdu
    case_data = _translate_fields(case_data, language)

    # Determine template path
    if language == "ur":
        template_path = os.path.join(TEMPLATES_DIR, "complaint_template_ur.docx")
    else:
        template_path = os.path.join(TEMPLATES_DIR, "complaint_template_en.docx")

    # Load or create document
    if os.path.exists(template_path):
        doc = Document(template_path)
        # Dynamically upgrade old templates that have hardcoded authority
        for paragraph in doc.paragraphs:
            if "ڈپٹی کمشنر" in paragraph.text:
                paragraph.text = paragraph.text.replace("ڈپٹی کمشنر", "{{ADDRESSED_TO}}")
            if "Deputy Commissioner" in paragraph.text:
                paragraph.text = paragraph.text.replace("Deputy Commissioner", "{{ADDRESSED_TO}}")
    else:
        doc = Document()
        _create_basic_template(doc, language)

    # Prepare placeholders
    placeholders = {
        "{{ADDRESSED_TO}}": case_data.get("addressed_to", ""),
        "{{COMPLAINANT_NAME}}": case_data.get("complainant_name", ""),
        "{{COMPLAINANT_ADDRESS}}": case_data.get("complainant_address", ""),
        "{{RESPONDENT_NAME}}": case_data.get("respondent_name", ""),
        "{{INCIDENT_DATE}}": case_data.get("incident_date", ""),
        "{{DESCRIPTION}}": case_data.get("description", ""),
        "{{LAW_SECTIONS}}": ", ".join(case_data.get("law_sections", [])),
        "{{DATE}}": datetime.now().strftime("%d-%m-%Y")
    }

    # Replace placeholders in all paragraphs
    for paragraph in doc.paragraphs:
        for key, value in placeholders.items():
            single_brace_key = key.replace("{{", "{").replace("}}", "}")
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, str(value))
            if single_brace_key in paragraph.text:
                paragraph.text = paragraph.text.replace(single_brace_key, str(value))

    # Also replace in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for key, value in placeholders.items():
                        single_brace_key = key.replace("{{", "{").replace("}}", "}")
                        if key in paragraph.text:
                            paragraph.text = paragraph.text.replace(key, str(value))
                        if single_brace_key in paragraph.text:
                            paragraph.text = paragraph.text.replace(single_brace_key, str(value))

    # Apply RTL formatting to Urdu paragraphs (preserve center alignment for title)
    if language == "ur":
        _apply_rtl_formatting(doc)

    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _apply_rtl_formatting(doc: Document):
    """Ensure Urdu paragraphs have RTL direction, but keep title centered."""
    for idx, paragraph in enumerate(doc.paragraphs):
        if not paragraph.text.strip():
            continue

        # Check if this is the title (first paragraph, bold, size 16)
        is_title = False
        if idx == 0:
            for run in paragraph.runs:
                if run.bold and run.font.size and run.font.size.pt == 16:
                    is_title = True
                    break

        if is_title:
            # Keep center alignment for the title
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            # Right align for normal RTL paragraphs
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

        # Add bidi (RTL) property
        pPr = paragraph._element.get_or_add_pPr()
        bidi_exists = pPr.xpath('./w:bidi')
        if not bidi_exists:
            bidi = pPr.makeelement(
                qn('w:bidi'),
                nsmap={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            )
            bidi.set(qn('w:val'), '1')
            pPr.append(bidi)

        # Set Urdu font for runs
        for run in paragraph.runs:
            run.font.name = 'Noto Nastaliq Urdu'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Noto Nastaliq Urdu')


def _create_basic_template(doc: Document, language: str):
    """Create a minimal template with placeholders."""
    if language == "ur":
        style = doc.styles['Normal']
        style.font.name = 'Noto Nastaliq Urdu'
        style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Noto Nastaliq Urdu')

        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run("بخدمت جناب {{ADDRESSED_TO}} صاحب")
        run.font.size = Pt(16)
        run.bold = True

        doc.add_paragraph("جناب عالی،")
        doc.add_paragraph(
            "میں {{COMPLAINANT_NAME}}، ساکن {{COMPLAINANT_ADDRESS}}، آپ کی خدمت میں درخواست گزار ہوں کہ {{RESPONDENT_NAME}} نے مورخہ {{INCIDENT_DATE}} کو میرے ساتھ درج ذیل ناانصافی کی:"
        )
        doc.add_paragraph("{{DESCRIPTION}}")
        doc.add_paragraph(
            "مذکورہ بالا فعل پاکستانی قانون کے درج ذیل دفعات کی خلاف ورزی ہے: {{LAW_SECTIONS}}"
        )
        doc.add_paragraph("برائے مہربانی قانون کے مطابق کارروائی فرمائی جائے۔")
        doc.add_paragraph("تاریخ: {{DATE}}")
        doc.add_paragraph("دستخط: {{COMPLAINANT_NAME}}")   # Typo fixed here
    else:
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run("To,\nThe {{ADDRESSED_TO}}")
        run.font.size = Pt(14)
        run.bold = True

        doc.add_paragraph("Subject: Complaint against {{RESPONDENT_NAME}}")
        doc.add_paragraph("Respected Sir/Madam,")
        doc.add_paragraph(
            f"I, {{COMPLAINANT_NAME}}, resident of {{COMPLAINANT_ADDRESS}}, beg to state that on {{INCIDENT_DATE}}, {{RESPONDENT_NAME}} committed the following wrongful act against me:"
        )
        doc.add_paragraph("{{DESCRIPTION}}")
        doc.add_paragraph(
            "The above act violates the following provisions of Pakistani law: {{LAW_SECTIONS}}"
        )
        doc.add_paragraph("It is requested that legal action be taken against the respondent.")
        doc.add_paragraph("Date: {{DATE}}")
        doc.add_paragraph("Yours faithfully,")
        doc.add_paragraph("{{COMPLAINANT_NAME}}")