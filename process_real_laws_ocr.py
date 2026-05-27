import os
import json
import base64
import time
import fitz  # PyMuPDF
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import vertexai
from dotenv import load_dotenv
from google.api_core import exceptions
from PIL import Image as PILImage
import io
import re
from collections import Counter

load_dotenv()

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"
PDF_FOLDER = "./real_laws/"
OUTPUT_FILE = "law-embeddings-real.json"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ============================================
# COMPLETE LAW CATEGORIES - Pakistan All Provinces
# ============================================

LAW_CATEGORIES = {
    "criminal": [
        "crime", "offence", "punishment", "arrest", "fir", "ppc", "criminal", "penal", 
        "murder", "theft", "robbery", "assault", "kidnapping", "rape", "zina", "hudood", 
        "qisas", "diyat", "police", "prosecution", "anti corruption", "nab", "corruption",
        "prevention of crime", "criminal procedure", "crpc", "bail", "sentence", "prison", 
        "jail", "detention", "offender", "probation", "parole", "forensic", "evidence"
    ],
    "civil": [
        "suit", "plaint", "defendant", "plaintiff", "civil", "procedure", "code of civil procedure", 
        "cpc", "specific relief", "limitation", "court fee", "evidence", "civil court", 
        "injunction", "decree", "appeal", "revision", "review", "reference"
    ],
    "family": [
        "marriage", "divorce", "khula", "nikah", "maintenance", "custody", "guardian", 
        "child", "family court", "muslim family", "dower", "mehr", "guardianship", 
        "minor", "guardian and wards", "family laws", "dissolution of marriage", 
        "dowry", "women protection", "domestic violence", "child protection", "juvenile"
    ],
    "property": [
        "property", "land", "rent", "lease", "tenancy", "possession", "land revenue", 
        "acquisition", "urban immovable", "land improvement", "mortgage", "pre-emption", 
        "succession", "inheritance", "katchi abadi", "housing", "real estate", "property tax", 
        "land reform", "waqf", "trust", "evacuee property", "registration", "stamp"
    ],
    "labour": [
        "labour", "employment", "worker", "employer", "industrial", "factory", "wages", 
        "trade union", "service", "terms of service", "civil servant", "appointment", 
        "regularization", "contract", "employee", "pension", "provident fund", 
        "industrial relations", "workplace", "minimum wage", "social security", 
        "employees", "workman", "compensation", "beneficiary", "bonded labour", 
        "child labour", "forced labour", "termination", "dismissal"
    ],
    "cyber": [
        "cyber", "peca", "electronic", "digital", "data", "hate speech", "information technology", 
        "computer", "internet", "social media", "electronic crimes", "prevention of electronic crimes",
        "data protection", "privacy", "cyber crime", "telecom", "pta"
    ],
    "taxation": [
        "tax", "taxation", "municipal", "valuation", "assessment", "revenue", "excise", 
        "customs", "duty", "cess", "surcharge", "income tax", "sales tax", "property tax", 
        "capital value tax", "professional tax", "infrastructure tax", "fee", "levy", 
        "finance", "fiscal", "budget", "appropriation", "loan", "government dues",
        "bank", "banking", "insurance", "financial institution", "credit"
    ],
    "corporate": [
        "society", "registration", "company", "corporation", "firm", "partnership", 
        "business", "trade", "commerce", "investment", "industrial", "enterprise", 
        "small industries", "board of investment", "commercial", "license", "permit", 
        "contractor", "society registration", "secp", "companies act"
    ],
    "constitutional": [
        "constitution", "fundamental", "rights", "federal", "provincial", "legislature", 
        "executive", "judiciary", "provincial assembly", "governor", "chief minister", 
        "parliament", "senate", "national assembly", "election", "ombudsman", 
        "ehtesab", "accountability", "service tribunal", "administrative"
    ],
    "health": [
        "health", "medical", "hospital", "healthcare", "drug", "medicine", "pharmaceutical", 
        "vaccination", "tuberculosis", "blood transfusion", "health services", 
        "public health", "medical teaching", "nursing", "sehat card", "health commission",
        "infectious disease", "food safety", "halal food"
    ],
    "education": [
        "education", "school", "college", "university", "teacher", "lecturer", "student", 
        "curriculum", "textbook", "board of education", "higher education", "technical education",
        "vocational training", "literacy", "scholarship", "educational institution", 
        "private school", "university act", "academic"
    ],
    "local_government": [
        "local government", "municipal", "town committee", "union council", "village council", 
        "neighborhood council", "district government", "city district", "municipality", 
        "corporation", "development authority", "urban development", "housing authority", 
        "master plan", "building control", "bylaw"
    ],
    "agriculture": [
        "agriculture", "farm", "crop", "irrigation", "water", "canal", "drainage", 
        "fertilizer", "pesticide", "food", "grain", "sugarcane", "cotton", "wheat", 
        "rice", "vegetable", "fruit", "livestock", "dairy", "poultry", "fisheries",
        "farming", "harvest", "land cultivation"
    ],
    "environment": [
        "environment", "forest", "wildlife", "pollution", "conservation", "ecological", 
        "climate change", "forestry", "tree", "biodiversity", "water resources", 
        "protected area", "national park", "sanctuary", "hunting", "fishing", 
        "aquaculture", "natural resources"
    ],
    "energy": [
        "energy", "electricity", "power", "hydel", "solar", "wind", "gas", "petroleum", 
        "oil", "mine", "mineral", "coal", "mining", "exploration", "extraction", 
        "crusher", "quarry", "transmission", "distribution"
    ],
    "transport": [
        "transport", "vehicle", "motor", "road", "highway", "bridge", "railway", 
        "traffic", "driving", "licensing", "mass transit", "bus", "truck", "goods vehicle",
        "carriage", "hackney", "rickshaw", "taxi", "communication", "telecom"
    ],
    "media": [
        "media", "press", "newspaper", "journalist", "publication", "broadcasting", 
        "television", "radio", "film", "censor", "advertisement", "bill", "hoarding",
        "information", "publicity", "propaganda", "print", "electronic media"
    ],
    "sports": [
        "sports", "tourism", "culture", "heritage", "antiquity", "museum", "archive", 
        "library", "arts", "performing arts", "drama", "theatre", "recreation", 
        "park", "playground", "stadium", "tourist", "hotel", "hospitality"
    ],
    "social_welfare": [
        "social welfare", "bait ul mal", "zakat", "ushr", "poor", "needy", "destitute", 
        "orphan", "widow", "disabled", "special person", "handicapped", "rehabilitation", 
        "relief", "human rights", "minorities", "women development", "gender"
    ],
    "military": [
        "military", "army", "navy", "air force", "defense", "security", "paramilitary", 
        "frontier corps", "levies", "khasadar", "civil armed forces", "national guard",
        "reserve", "martial law", "armed forces", "defence"
    ],
    "narcotics": [
        "narcotics", "drug", "opium", "heroin", "cocaine", "cannabis", "hashish", 
        "controlled substance", "psychotropic", "intoxicant", "liquor", "alcohol", 
        "smoking", "tobacco", "cigarette", "prohibition", "substance abuse"
    ],
    "regulatory": [
        "regulation", "compliance", "licensing", "registration", "certification", 
        "standard", "quality control", "inspection", "monitoring", "enforcement", 
        "penalty", "fine", "sanction", "authorization", "permit", "approval"
    ],
    "judicial": [
        "court", "judge", "magistrate", "judicial", "adjudication", "tribunal", 
        "bench", "appeal", "revision", "review", "reference", "case", "litigation", 
        "legal proceeding", "summons", "warrant", "decree", "order", "judgment", 
        "verdict", "sentence", "execution", "alternative dispute resolution", "adr"
    ],
    "general": []
}


def detect_law_category(text, law_name=""):
    """Detect law category from text and law name using comprehensive categories"""
    text_lower = (text + " " + law_name).lower()
    
    for category, keywords in LAW_CATEGORIES.items():
        if category == "general" or not keywords:
            continue
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return "general"


def extract_keywords(text, max_keywords=5):
    """Extract important keywords from text"""
    common_words = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'section', 'act',
                    'of', 'to', 'in', 'a', 'on', 'by', 'or', 'as', 'is', 'be', 'are',
                    'was', 'were', 'been', 'have', 'has', 'had', 'at', 'an', 'but', 'not',
                    'so', 'such', 'into', 'through', 'during', 'without', 'between', 'among'}
    
    words = re.findall(r'\b[A-Za-z\u0600-\u06ff]{4,}\b', text)
    word_counts = Counter([w.lower() for w in words if w.lower() not in common_words])
    
    return [word for word, count in word_counts.most_common(max_keywords)]


# ============================================
# VERTEX AI OCR MODEL - Gemini 2.5 Flash
# ============================================

_vision_model = None

def get_vision_model():
    """Lazy initialization of Vertex AI Generative Model for OCR using Gemini 2.5 Flash"""
    global _vision_model
    if _vision_model is None:
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        _vision_model = GenerativeModel("gemini-2.5-flash")
    return _vision_model


CACHE_FOLDER = "./text_cache/"


def extract_text_from_pdf_smart(pdf_path):
    """Extract text using PyMuPDF; only use OCR if page appears scanned. Caches page text."""
    doc = fitz.open(pdf_path)
    base_name = os.path.basename(pdf_path)
    pdf_cache_dir = os.path.join(CACHE_FOLDER, base_name)
    os.makedirs(pdf_cache_dir, exist_ok=True)
    
    full_text = ""
    page_texts = []
    
    for page_num in range(len(doc)):
        cache_file = os.path.join(pdf_cache_dir, f"page_{page_num+1}.txt")
        
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                page_text = f.read()
            full_text += page_text + "\n"
            page_texts.append(page_text)
            continue

        page = doc[page_num]
        text = page.get_text()
        
        if len(text.strip()) > 200:
            page_text = text
            print(f"  Page {page_num+1} text extracted (direct)")
        else:
            print(f"  Page {page_num+1} appears scanned, using OCR (Gemini 2.5 Flash)...")
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            prompt = "Extract all the text from this legal document page. Return only the text."
            success = False
            retries = 0
            page_text = ""
            
            while not success and retries < 5:
                try:
                    # Using Vertex AI Generative Model with Gemini 2.5 Flash
                    vision_model = get_vision_model()
                    
                    # Convert bytes to PIL Image
                    pil_image = PILImage.open(io.BytesIO(img_bytes))
                    
                    # Convert PIL Image back to bytes (ensures correct format)
                    img_byte_arr = io.BytesIO()
                    pil_image.save(img_byte_arr, format='PNG')
                    img_bytes_correct = img_byte_arr.getvalue()
                    
                    # Create Part with correct mime type
                    from vertexai.generative_models import Part
                    image_part = Part.from_data(data=img_bytes_correct, mime_type="image/png")
                    
                    # Generate text from image
                    response = vision_model.generate_content([prompt, image_part])
                    page_text = response.text
                    success = True
                    time.sleep(2)
                except Exception as e:
                    retries += 1
                    wait = 10 * retries
                    print(f"  OCR error: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
            
            if not success:
                print(f"  Failed to OCR page {page_num+1}. Skipping.")
                page_text = "[FAILED_OCR_PAGE]"

        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        full_text += page_text + "\n"
        page_texts.append(page_text)
        
    return full_text, page_texts


_embedding_model = None


def detect_language_simple(text):
    """Detect language from text - Urdu/Arabic vs English"""
    if re.search(r'[\u0600-\u06ff]', text):
        return "ur"
    return "en"


def chunk_text_by_size(text, size, overlap, metadata=None):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk_val = text[start:end]
        chunks.append({
            "text": chunk_val,
            "metadata": metadata or {"section": "General"}
        })
        start = end - overlap
        if start >= len(text) - overlap:
            break
    return chunks


def semantic_chunk_text(text, page_texts=None, filename=""):
    """Enhanced chunking with page tracking and metadata"""
    pattern = re.compile(r'(?i)(?:^|\n)(Section\s+\d+|دفعہ\s+\d+|Article\s+\d+)\b')
    
    matches = list(pattern.finditer(text))
    
    if not matches:
        chunks = chunk_text_by_size(text, 1200, 200)
        if page_texts:
            for chunk in chunks:
                for idx, page_text in enumerate(page_texts, 1):
                    if chunk["text"][:200] in page_text:
                        chunk["metadata"]["page"] = idx
                        break
        return chunks
        
    chunks = []
    
    if matches[0].start() > 0:
        pre_text = text[:matches[0].start()].strip()
        if pre_text:
            pre_chunks = chunk_text_by_size(pre_text, 1200, 200, metadata={"section": "Intro"})
            chunks.extend(pre_chunks)
            
    for idx, match in enumerate(matches):
        section_title = match.group(1).strip()
        start_pos = match.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        
        section_text = text[start_pos:end_pos].strip()
        if not section_text:
            continue
            
        metadata = {
            "section": section_title,
            "chunk_index": len(chunks),
            "total_sections": len(matches)
        }
        
        if page_texts:
            for page_num, page_text in enumerate(page_texts, 1):
                if section_text[:200] in page_text:
                    metadata["page"] = page_num
                    break
        
        if len(section_text) > 1200:
            sub_chunks = chunk_text_by_size(section_text, 1200, 200, metadata=metadata)
            chunks.extend(sub_chunks)
        else:
            chunks.append({
                "text": section_text,
                "metadata": metadata
            })
            
    return chunks


def get_embeddings_with_retry(batch, max_retries=8):
    """Generate embeddings using Vertex AI text-embedding-005 with retry and exponential backoff."""
    global _embedding_model
    for attempt in range(max_retries):
        try:
            if _embedding_model is None:
                vertexai.init(project=PROJECT_ID, location=LOCATION)
                _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
            
            inputs = [TextEmbeddingInput(text, task_type="RETRIEVAL_DOCUMENT") for text in batch]
            embeddings = _embedding_model.get_embeddings(inputs)
            return [emb.values for emb in embeddings]
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait = 30 * (2 ** attempt)
                print(f"  Embedding quota exceeded. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                wait = 10 * (attempt + 1)
                print(f"  Embedding error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
    raise Exception("Max retries exceeded for embedding generation.")


def get_processed_chunk_ids():
    """Read existing output file and return set of already processed chunk IDs."""
    if not os.path.exists(OUTPUT_FILE):
        return set()
    ids = set()
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                ids.add(record["id"])
            except:
                continue
    return ids


def process_documents():
    os.makedirs(PDF_FOLDER, exist_ok=True)
    files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    if not files:
        print(f"No PDF files found in {PDF_FOLDER}")
        return

    processed_ids = get_processed_chunk_ids()
    print(f"Already processed {len(processed_ids)} chunks. Resuming...")
    print("=" * 70)

    total_new_chunks = 0
    total_pages_processed = 0
    category_counts = {}

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
        for filename in files:
            filepath = os.path.join(PDF_FOLDER, filename)
            print(f"\n📄 Processing: {filename}")
            
            text, page_texts = extract_text_from_pdf_smart(filepath)
            total_pages_processed += len(page_texts)
            
            if not text.strip():
                print("  ❌ No text extracted, skipping.")
                continue
            
            chunks = semantic_chunk_text(text, page_texts, filename)
            law_name = os.path.splitext(filename)[0]
            
            category = detect_law_category(text, law_name)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            print(f"  📊 Stats: {len(page_texts)} pages → {len(chunks)} chunks")
            print(f"  📂 Category: {category.upper()}")
            
            new_chunks = 0
            
            for i in range(0, len(chunks), 5):
                batch_data = chunks[i:i+5]
                batch = [c["text"] for c in batch_data]
                
                batch_ids = [f"{filename}_chunk_{i+j}" for j in range(len(batch_data))]
                if all(chunk_id in processed_ids for chunk_id in batch_ids):
                    continue
                
                print(f"    🔄 Generating embeddings for batch {i//5 + 1}/{(len(chunks)+4)//5}...")
                embeddings = get_embeddings_with_retry(batch)
                
                for j, emb in enumerate(embeddings):
                    chunk_id = batch_ids[j]
                    if chunk_id in processed_ids:
                        continue
                    
                    c_data = batch_data[j]
                    section_number = c_data["metadata"].get("section", "General")
                    page_num = c_data["metadata"].get("page", 0)
                    chunk_index = c_data["metadata"].get("chunk_index", i+j)
                    total_sections = c_data["metadata"].get("total_sections", len(chunks))
                    language = detect_language_simple(c_data["text"])
                    keywords = extract_keywords(c_data["text"])
                    
                    record = {
                        "id": chunk_id,
                        "embedding": emb,
                        "text": c_data["text"],
                        "source": filename,
                        "law_name": law_name,
                        "section_number": section_number,
                        "language": language,
                        "category": category,
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                        "total_chunks_in_law": len(chunks),
                        "total_sections_in_law": total_sections,
                        "keywords": keywords,
                        "char_count": len(c_data["text"]),
                        "word_count": len(c_data["text"].split()),
                        "jurisdiction": "Pakistan",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()
                    processed_ids.add(chunk_id)
                    new_chunks += 1
            
            total_new_chunks += new_chunks
            print(f"  ✅ Done. Added {new_chunks} new chunks")

    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    print(f"✅ Total pages processed: {total_pages_processed}")
    print(f"✅ Total new chunks added: {total_new_chunks}")
    print(f"✅ Total chunks in database: {len(processed_ids)}")
    print(f"✅ Output file: {OUTPUT_FILE}")
    print("\n📂 Category Distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   - {cat.upper()}: {count} law(s)")
    print("\n🎉 All embeddings saved successfully!")


if __name__ == "__main__":
    process_documents()