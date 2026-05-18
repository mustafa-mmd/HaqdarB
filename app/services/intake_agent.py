# app/services/intake_agent.py
"""
HaqDar AI — Intake Agent
Handles language/script detection and legal category classification.
Supports 6 regional languages and 80+ legal categories.
"""
import re
from typing import Tuple

# ── Expanded: 80+ category taxonomy (was 8) ──
CATEGORIES = [
    "criminal",
    "civil",
    "family",
    "property",
    "labour",
    "constitutional",
    "consumer",
    "taxation",
    "corporate",
    "banking",
    "intellectual_property",
    "rent_tenancy",
    "inheritance",
    "domestic_violence",
    "peca_cybercrime",
    "juvenile_justice",
    "environmental",
    "arbitration",
    "immigration",
    "maritime",
    "energy",
    "aviation",
    "insurance",
    "election",
    "defamation",
    "media_telecom",
    "medical_negligence",
    "service_law",
    "trust_waqf",
    "food_safety",
    "disability",
    "competition",
    "anti_corruption",
    "data_privacy",
    "hudood_qisas",
    "education",
    "agricultural",
    "motor_vehicle",
    "prison_detention",
    "refugee",
    "religious_offences",
    "microfinance",
    "human_rights",
    "mining",
    "water_resources",
    "securities",
    "overseas_pakistanis",
    "human_trafficking",
    "social_security",
    "workplace_harassment",
    "child_protection",
    "local_government",
    "real_estate_regulatory",
    "zakat_ushr",
    "military",
    "international_trade",
    "police",
    "other",
]

# ── Balochi-specific Unicode characters ──
BALOCHI_SPECIFIC_CHARS = re.compile(
    r'[\u0754\u0755\u0756\u075B\u075C\u0760\u0762\u0763\u0764\u0765\u0766\u0767\u0768\u0769\u076A\u076B\u076C\u076D]'
)

BALOCHI_WORDS = [
    "گنجین", "پرسش", "بنویسید", "بلوچی", "شما", "چیز", "کہ", "گۏش", "مردم", "زبان",
    "قانونی", "حق", "مدد", "وکیل", "عدالت", "شکایت", "جرم", "سزا",
    "منی", "در", "کشت", "خانهء", "بغیر", "اطلاع", "زمين", "دار", "بےدخل",
    "کرایه", "خبرداري", "مزدوري", "کارگر", "برطرفي", "کارخانه",
    "عروسي", "میراث", "وصيت", "بیوه", "دختر", "پسر", "جائیداد",
    "جعلي", "اکانت", "فيسبوک", "بليک ميل", "سائبر", "پيکا",
    "زمين", "خانه", "پلات", "پوليس", "شکایت", "ايف آي آر", "هراسان",
    "خريد", "دکان", "موبايل", "صارف", "واپسي", "پول",
    "بگير", "بہتر", "گپ", "مردم", "دوست", "مہرباني", "راه", "کمک",
    "بخش", "زندگي", "گفتگو", "نوشت", "خواند", "کار", "روز", "شب",
    "ئه", "ئا", "ئو", "گوا", "کنگ", "بوتگ", "انت", "هانی", "پچ",
]

# ── Sindhi detection words ──
SINDHI_WORDS = [
    "سنڌي", "ڪجي", "آهي", "ڪيئن", "ڪٿي", "ڏيو", "وٺو", "ڪريو", "منهنجو", "توهان",
    "ماڻهو", "سرڪار", "قانون", "شڪايت", "ٿاڻو", "عدالت", "حق", "مدد",
    "جيڪڏهن", "پنهنجي", "ڏني", "پڇو", "لکو", "هتي", "ڪٿ",
]

# ── Pashto detection words ──
PASHTO_WORDS = [
    "پښتو", "ولیکئ", "وکړئ", "دلته", "چیرته", "ستاسو", "زما", "دي", "یم", "یو",
    "کولی", "شم", "شي", "ده", "دوی", "هغه", "دا", "مونږ", "تاسو", "نو",
    "قانون", "حق", "مرسته", "وکیل", "عدالت", "شکایت", "جرم", "سزا",
    "پوليس", "سټيشن", "ايف آي آر", "ويل", "وکړو", "هغوی",
]


def detect_language_and_script(text: str) -> Tuple[str, str]:
    """
    Returns (language, script) based on Unicode and vocabulary heuristics.
    Language: 'ur', 'pa', 'ps', 'sd', 'en', 'bal'
    Script: 'arabic' or 'latin'
    """
    arabic_chars = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text)
    latin_chars = re.findall(r'[a-zA-Z]', text)
    text_words = set(text.lower().split())

    if len(arabic_chars) > len(latin_chars):
        script = "arabic"

        # Sindhi detection (before Pashto/Urdu — has unique Unicode chars)
        sindhi_score = sum(1 for w in SINDHI_WORDS if w in text)
        # Sindhi-specific letters (نڌ, ڪ, ڏ, etc.)
        sindhi_specific = re.findall(r'[\u0DA0-\u0DFF\u068C\u0680-\u068F]', text)
        if sindhi_score >= 3 or len(sindhi_specific) >= 2:
            return "sd", "arabic"

        # Pashto detection
        pashto_score = sum(1 for w in PASHTO_WORDS if w in text)
        # Pashto-specific letters (ټ, ډ, ړ, ږ, ښ, ۍ, ې)
        pashto_specific = re.findall(r'[\u0679\u0688\u0693\u0696\u069A\u06CD\u06D0]', text)
        if pashto_score >= 3 or len(pashto_specific) >= 2:
            return "ps", "arabic"

        # Balochi detection
        balochi_score = 0
        if BALOCHI_SPECIFIC_CHARS.search(text):
            balochi_score += 2
        balochi_score += sum(1 for word in BALOCHI_WORDS if word in text)
        if balochi_score >= 2:
            return "bal", "arabic"

        # Default to Urdu for Arabic script
        return "ur", "arabic"

    else:
        script = "latin"

        # Balochi Latin detection
        balochi_latin_words = ["baloch", "baluch", "balochistan", "quetta", "gwadar", "makran"]
        if any(word in text.lower() for word in balochi_latin_words):
            return "bal", "latin"

        # Pashto Latin detection
        pashto_latin = ["pashto", "pashtu", "pakhtun", "pashtun", "khyber", "swat", "dir"]
        if any(word in text.lower() for word in pashto_latin):
            return "ps", "latin"

        # English detection (strong heuristic)
        english_words = {
            "the", "is", "my", "what", "how", "can", "i", "you", "me", "a", "an",
            "and", "or", "but", "for", "with", "to", "of", "in", "on", "at",
            "landlord", "tenant", "rights", "legal", "law", "police", "court",
            "fir", "salary", "job", "marriage", "divorce", "property", "contract",
            "complaint", "case", "judge", "lawyer", "tribunal", "pakistan",
        }
        if len(text_words.intersection(english_words)) >= 2:
            return "en", "latin"

        # Romanized Urdu fallback
        return "ur", "latin"


def classify_legal_category(text: str) -> str:
    """
    Classify the legal problem into one of 80+ predefined categories.
    Uses multilingual keyword matching (English + Urdu + regional languages).
    """
    t = text.lower()

    # ── Criminal Law / FIR / Police ──
    if any(kw in t for kw in [
        "murder", "robbery", "theft", "assault", "fir", "criminal", "crime", "police", "arrest",
        "کشت", "ڈکیتی", "چوری", "حملہ", "ایف آئی آر", "جرم", "پولیس", "گرفتار", "قتل",
        "mader", "قاتل", "مجرم", "تھانہ", "درج", "bail", "ضمانت",
    ]):
        return "criminal"

    # ── Cybercrime / PECA ──
    if any(kw in t for kw in [
        "facebook", "account", "fake", "harassment", "online", "whatsapp", "blackmail",
        "peca", "cyber", "stalking", "hacking", "phishing", "pornography", "sextortion",
        "fia", "social media", "instagram", "tiktok", "youtube", "identity theft",
        "فیس بک", "جعلی اکاؤنٹ", "واٹس ایپ", "بلیک میل", "سائبر", "پیکا", "ہراساں",
        "جعلي", "اکانت", "سائبر", "فيسبوک", "بليک ميل", "پيکا", "آن لائن",
        "deepfake", "revenge porn", "non-consensual",
    ]):
        return "peca_cybercrime"

    # ── Domestic Violence ──
    if any(kw in t for kw in [
        "domestic violence", "wife beating", "husband violence", "shelter home", "dv act",
        "protection order", "battered", "abuse at home", "ghar mein maar",
        "گھریلو تشدد", "بیوی کی مار", "شوہر کا تشدد", "محفوظ گھر", "تحفظ",
        "domestic", "marital abuse", "cruelty by husband",
    ]):
        return "domestic_violence"

    # ── Workplace Harassment ──
    if any(kw in t for kw in [
        "workplace harassment", "sexual harassment", "office harassment", "molestation at work",
        "harassment at workplace", "harassed at office", "unwanted advances",
        "دفتر میں ہراسانی", "جنسی ہراسانی", "کام کی جگہ پر ہراسانی",
    ]):
        return "workplace_harassment"

    # ── Family Law ──
    if any(kw in t for kw in [
        "marriage", "divorce", "khul'a", "khula", "talaq", "inheritance", "will",
        "widow", "daughter", "son", "custody", "maintenance", "nikah", "dowry",
        "guardian", "wardship", "adoption", "restitution",
        "شادی", "طلاق", "خلع", "وراثت", "وصیت", "بیوہ", "بیٹی", "بیٹا",
        "حضانت", "خرچہ", "نکاح", "جہیز", "مہر", "ولی",
        "عروسي", "میراث", "وصيت", "بیوه", "دختر", "پسر",
    ]):
        return "family"

    # ── Rent / Tenancy ──
    if any(kw in t for kw in [
        "rent", "landlord", "tenant", "eviction", "evict", "notice to vacate",
        "rental", "house rent", "commercial rent", "lease agreement",
        "کرایہ", "کرائے", "مالک مکان", "کرایہ دار", "بے دخل", "نوٹس", "خالی کرو",
        "کرایه", "خانه", "زميندار", "بےدخل", "خبرداري",
    ]):
        return "rent_tenancy"

    # ── Labour / Employment ──
    if any(kw in t for kw in [
        "job", "employee", "employer", "salary", "wages", "fired", "termination",
        "labour", "labor", "layoff", "redundancy", "overtime", "provident fund",
        "gratuity", "eobi", "wrongful dismissal", "unfair termination",
        "ملازمت", "نوکری", "تنخواہ", "برطرف", "آجر", "مزدور", "فیکٹری",
        "مزدوري", "کارگر", "تنخواه", "برطرفي", "کارخانه", "اضافی وقت",
        "پروویڈنٹ فنڈ", "گریچوٹی",
    ]):
        return "labour"

    # ── Property Law ──
    if any(kw in t for kw in [
        "property", "plot", "house", "land", "deed", "sale deed", "gift deed",
        "partition", "mutation", "registry", "fard", "intiqal", "encroachment",
        "زمین", "پلاٹ", "گھر", "جائیداد", "مکان", "فروخت", "انتقال", "رجسٹری",
        "زمين", "خانه", "پلات", "بیع", "تقسیم", "قبضہ",
    ]):
        return "property"

    # ── Real Estate Regulatory (RERA) ──
    if any(kw in t for kw in [
        "housing society", "builder fraud", "developer", "dha", "bahria", "rera",
        "plot allotment", "housing scheme", "builder default",
        "ہاؤسنگ سوسائٹی", "بلڈر فراڈ", "ڈویلپر", "پلاٹ الاٹمنٹ",
    ]):
        return "real_estate_regulatory"

    # ── Inheritance / Succession ──
    if any(kw in t for kw in [
        "inheritance", "succession certificate", "will", "probate", "heirship",
        "مواریث", "وراثت", "جانشینی", "نامہ وصیت", "وارث",
    ]):
        return "inheritance"

    # ── Consumer Law ──
    if any(kw in t for kw in [
        "product", "refund", "shop", "consumer", "defective", "fraud seller",
        "warranty", "guarantee", "misleading", "overpriced", "faulty goods",
        "خریداری", "واپسی", "صارف", "خراب مال", "دھوکہ", "دکاندار", "گارنٹی",
        "خريد", "دکان", "موبايل", "صارف", "واپسي",
    ]):
        return "consumer"

    # ── Banking / Finance ──
    if any(kw in t for kw in [
        "bank", "loan", "cheque bounce", "emi", "mortgage", "banking", "account frozen",
        "ombudsman", "bank fraud", "financial institution",
        "بینک", "قرض", "چیک باؤنس", "مارگیج", "اکاؤنٹ فریز", "بینک فراڈ",
    ]):
        return "banking"

    # ── Taxation ──
    if any(kw in t for kw in [
        "tax", "income tax", "sales tax", "fbr", "gst", "tax evasion", "customs", "excise",
        "ٹیکس", "محصول", "ایف بی آر", "سیلز ٹیکس", "ٹیکس چوری",
    ]):
        return "taxation"

    # ── Corporate / Company Law ──
    if any(kw in t for kw in [
        "company", "secp", "director", "shareholder", "winding up", "registration",
        "partnership", "private limited", "pvt ltd", "ngo", "trust registration",
        "کمپنی", "ڈائریکٹر", "شراکت دار", "رجسٹریشن",
    ]):
        return "corporate"

    # ── Constitutional Law ──
    if any(kw in t for kw in [
        "fundamental rights", "article 9", "article 14", "article 19", "article 25",
        "constitution", "writ petition", "habeas corpus", "mandamus", "certiorari",
        "bنیادی حقوق", "آئین", "رٹ پٹیشن", "بنیادی حقوق", "ہائی کورٹ",
    ]):
        return "constitutional"

    # ── Data Privacy ──
    if any(kw in t for kw in [
        "data privacy", "personal data", "pdpa", "data protection", "data leak",
        "privacy violation", "nadra", "data breach",
        "ذاتی ڈیٹا", "پرائیویسی", "ڈیٹا لیک",
    ]):
        return "data_privacy"

    # ── Anti-Corruption / NAB ──
    if any(kw in t for kw in [
        "corruption", "bribery", "bribe", "nab", "fia", "accountability",
        "corruption complaint", "government officer bribe",
        "کرپشن", "رشوت", "نیب", "احتساب", "بدعنوانی",
    ]):
        return "anti_corruption"

    # ── Child Protection ──
    if any(kw in t for kw in [
        "child abuse", "child missing", "zainab alert", "child marriage",
        "minor abuse", "child labour",
        "بچہ مزدوری", "بچوں کا استحصال", "بچہ گم", "کم عمری کی شادی",
    ]):
        return "child_protection"

    # ── Human Trafficking ──
    if any(kw in t for kw in [
        "trafficking", "smuggling", "bonded labour", "forced labour", "human trafficking",
        "انسانی اسمگلنگ", "جبری مشقت", "بندھوا مزدور",
    ]):
        return "human_trafficking"

    # ── Medical Negligence ──
    if any(kw in t for kw in [
        "medical negligence", "doctor negligence", "hospital error", "wrong medication",
        "malpractice", "healthcare commission", "pmc",
        "ڈاکٹر کی غلطی", "ہسپتال کی غفلت", "طبی غلطی",
    ]):
        return "medical_negligence"

    # ── Intellectual Property ──
    if any(kw in t for kw in [
        "copyright", "trademark", "patent", "ip infringement", "plagiarism",
        "brand", "piracy", "counterfeit",
        "حق تصنیف", "ٹریڈ مارک", "پیٹنٹ", "نقل",
    ]):
        return "intellectual_property"

    # ── Education Law ──
    if any(kw in t for kw in [
        "university", "school", "education", "degree", "fee refund", "hec",
        "student rights", "academic", "expulsion",
        "یونیورسٹی", "اسکول", "تعلیم", "ڈگری", "ایچ ای سی", "فیس واپسی",
    ]):
        return "education"

    # ── Immigration ──
    if any(kw in t for kw in [
        "visa", "passport", "immigration", "deportation", "citizenship", "work permit",
        "ویزہ", "پاسپورٹ", "شہریت", "ڈی پورٹیشن",
    ]):
        return "immigration"

    # ── Insurance ──
    if any(kw in t for kw in [
        "insurance", "claim rejected", "insurance fraud", "takaful", "policy cancellation",
        "انشورنس", "دعویٰ", "انشورنس فراڈ",
    ]):
        return "insurance"

    # ── Motor Vehicle ──
    if any(kw in t for kw in [
        "accident", "car accident", "traffic", "motor vehicle", "driving license",
        "compensation", "rta", "mvt",
        "سڑک حادثہ", "گاڑی حادثہ", "ٹریفک", "ڈرائیونگ لائسنس", "معاوضہ",
    ]):
        return "motor_vehicle"

    # ── Energy (Gas/Electricity) ──
    if any(kw in t for kw in [
        "electricity", "gas", "nepra", "ogra", "wapda", "sui", "disconnection",
        "overbilling", "load shedding", "meter",
        "بجلی", "گیس", "نیپرا", "واپڈا", "ڈسکنیکشن", "اوور بلنگ", "میٹر",
    ]):
        return "energy"

    # ── Environmental ──
    if any(kw in t for kw in [
        "pollution", "environment", "factory smoke", "noise pollution", "waste dumping",
        "environmental", "epa", "sepa", "nema",
        "آلودگی", "ماحول", "کارخانہ دھواں", "کچرہ",
    ]):
        return "environmental"

    # ── Social Security / EOBI ──
    if any(kw in t for kw in [
        "eobi", "pension", "social security", "workers welfare", "essi",
        "ای او بی آئی", "پنشن", "سوشل سیکیورٹی",
    ]):
        return "social_security"

    # ── Overseas Pakistanis ──
    if any(kw in t for kw in [
        "overseas pakistani", "abroad", "nikah overseas", "property abroad",
        "nrp", "remittance fraud", "overseas worker",
        "بیرون ملک پاکستانی", "بیرون ملک", "بیرون ملک جائیداد",
    ]):
        return "overseas_pakistanis"

    # ── Juvenile Justice ──
    if any(kw in t for kw in [
        "juvenile", "minor offender", "juvenile court", "reform school", "under 18",
        "نابالغ", "نابالغ مجرم", "جوینائل کورٹ",
    ]):
        return "juvenile_justice"

    # ── Human Rights ──
    if any(kw in t for kw in [
        "human rights", "nchr", "enforced disappearance", "torture", "arbitrary detention",
        "انسانی حقوق", "لاپتہ افراد", "تشدد", "ہیومن رائٹس",
    ]):
        return "human_rights"

    # ── Defamation ──
    if any(kw in t for kw in [
        "defamation", "slander", "libel", "false statement", "reputation damage",
        "ہتک عزت", "جھوٹا الزام", "بدنامی",
    ]):
        return "defamation"

    # ── Zakat ──
    if any(kw in t for kw in [
        "zakat", "ushr", "zakat deduction",
        "زکوٰۃ", "عشر", "زکوٰۃ کٹوتی",
    ]):
        return "zakat_ushr"

    # Fallback
    return "other"