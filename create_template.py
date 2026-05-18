# create_template.py
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# ---------- Urdu Template ----------
doc = Document()
# Set default font for Urdu
style = doc.styles['Normal']
style.font.name = 'Noto Nastaliq Urdu'
style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Noto Nastaliq Urdu')

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("بخدمت جناب ڈپٹی کمشنر صاحب")
run.font.size = Pt(16)
run.bold = True

doc.add_paragraph("جناب عالی،")
doc.add_paragraph("میں {{COMPLAINANT_NAME}}، ساکن {{COMPLAINANT_ADDRESS}}، آپ کی خدمت میں درخواست گزار ہوں کہ {{RESPONDENT_NAME}} نے مورخہ {{INCIDENT_DATE}} کو میرے ساتھ درج ذیل ناانصافی کی:")
doc.add_paragraph("{{DESCRIPTION}}")
doc.add_paragraph("مذکورہ بالا فعل پاکستانی قانون کے درج ذیل دفعات کی خلاف ورزی ہے: {{LAW_SECTIONS}}")
doc.add_paragraph("برائے مہربانی قانون کے مطابق کارروائی فرمائی جائے۔")
doc.add_paragraph("تاریخ: {{DATE}}")
doc.add_paragraph("دستخط: {{COMPLAINANT_NAME}}")

doc.save("templates/complaint_template_ur.docx")
print("✅ Urdu template created at templates/complaint_template_ur.docx")

# ---------- English Template ----------
doc = Document()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("To,\nThe Deputy Commissioner / Concerned Authority")
run.font.size = Pt(14)
run.bold = True

doc.add_paragraph("Subject: Complaint against {{RESPONDENT_NAME}}")
doc.add_paragraph("Respected Sir/Madam,")
doc.add_paragraph(f"I, {{COMPLAINANT_NAME}}, resident of {{COMPLAINANT_ADDRESS}}, beg to state that on {{INCIDENT_DATE}}, {{RESPONDENT_NAME}} committed the following wrongful act against me:")
doc.add_paragraph("{{DESCRIPTION}}")
doc.add_paragraph("The above act violates the following provisions of Pakistani law: {{LAW_SECTIONS}}")
doc.add_paragraph("It is requested that legal action be taken against the respondent.")
doc.add_paragraph(f"Date: {{DATE}}")
doc.add_paragraph("Yours faithfully,")
doc.add_paragraph("{{COMPLAINANT_NAME}}")

doc.save("templates/complaint_template_en.docx")
print("✅ English template created at templates/complaint_template_en.docx")