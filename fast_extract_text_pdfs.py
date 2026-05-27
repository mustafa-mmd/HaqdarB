# fast_extract_text_pdfs.py
# Extracts text from ALL PDFs that have a text layer
# Takes minutes, not hours. Free. No API calls.

import fitz
import json
import os
import re
import time
from collections import Counter

PDF_FOLDER = "./real_laws/"
OUTPUT_FILE = "law-embeddings-real.json"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MIN_TEXT_PER_PAGE = 100  # chars — below this = scanned page

def detect_language_simple(text):
    if re.search(r'[\u0600-\u06ff]', text):
        return "ur"
    return "en"

def extract_keywords(text, max_keywords=5):
    common = {'the','and','for','that','this','with','from','section','act',
              'of','to','in','a','on','by','or','as','is','be','are','was',
              'were','been','have','has','had','at','an','but','not','so',
              'such','into','through','during','without','between','among'}
    words = re.findall(r'\b[A-Za-z\u0600-\u06ff]{4,}\b', text)
    counts = Counter([w.lower() for w in words if w.lower() not in common])
    return [w for w, _ in counts.most_common(max_keywords)]

LAW_CATEGORIES = {
    "cyber": ["cyber","peca","electronic","digital","data","computer","internet","social media","electronic crimes"],
    "family": ["marriage","divorce","khula","nikah","maintenance","custody","guardian","child","family court","domestic violence"],
    "property": ["property","land","rent","lease","tenancy","possession","land revenue","acquisition","housing","real estate","waqf"],
    "labour": ["labour","employment","worker","employer","industrial","factory","wages","trade union","civil servant","minimum wage"],
    "constitutional": ["constitution","fundamental","rights","federal","provincial","legislature","election","ombudsman"],
    "taxation": ["tax","taxation","excise","customs","duty","cess","income tax","sales tax","finance","fiscal"],
    "health": ["health","medical","hospital","healthcare","drug","medicine","vaccination","public health"],
    "education": ["education","school","college","university","teacher","lecturer","curriculum","textbook"],
    "environment": ["environment","forest","wildlife","pollution","conservation","climate","biodiversity"],
    "energy": ["energy","electricity","power","hydel","gas","petroleum","mine","mineral","mining"],
    "transport": ["transport","vehicle","motor","road","highway","traffic","driving","mass transit"],
    "criminal": ["crime","offence","punishment","arrest","fir","ppc","criminal","penal","murder","theft","robbery","bail","prison"],
    "civil": ["suit","plaint","civil","procedure","cpc","specific relief","limitation","court fee","injunction","decree"],
    "general": []
}

def detect_category(text, law_name=""):
    combined = (text + " " + law_name).lower()
    for cat, keywords in LAW_CATEGORIES.items():
        if cat == "general":
            continue
        for kw in keywords:
            if kw in combined:
                return cat
    return "general"

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP, metadata=None):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append({"text": text[start:end], "metadata": metadata or {}})
        start = end - overlap
        if start >= len(text) - overlap:
            break
    return chunks

def semantic_chunk(text, filename=""):
    pattern = re.compile(r'(?i)(?:^|\n)(Section\s+\d+|دفعہ\s+\d+|Article\s+\d+)\b')
    matches = list(pattern.finditer(text))
    
    if not matches:
        return chunk_text(text)
    
    chunks = []
    if matches[0].start() > 0:
        chunks.extend(chunk_text(text[:matches[0].start()].strip(), 
                     metadata={"section": "Intro"}))
    
    for idx, match in enumerate(matches):
        section_title = match.group(1).strip()
        end_pos = matches[idx+1].start() if idx+1 < len(matches) else len(text)
        section_text = text[match.start():end_pos].strip()
        if not section_text:
            continue
        meta = {"section": section_title, "chunk_index": len(chunks)}
        if len(section_text) > CHUNK_SIZE:
            chunks.extend(chunk_text(section_text, metadata=meta))
        else:
            chunks.append({"text": section_text, "metadata": meta})
    
    return chunks

def get_processed_ids():
    if not os.path.exists(OUTPUT_FILE):
        return set()
    ids = set()
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                ids.add(json.loads(line.strip())["id"])
            except:
                continue
    return ids

def is_text_pdf(pdf_path, sample_pages=5):
    """Check if PDF has extractable text (not scanned)"""
    doc = fitz.open(pdf_path)
    total = len(doc)
    sample = min(sample_pages, total)
    text_count = 0
    for i in range(sample):
        if len(doc[i].get_text().strip()) > MIN_TEXT_PER_PAGE:
            text_count += 1
    doc.close()
    return (text_count / sample) > 0.5, total

def main():
    files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    processed_ids = get_processed_ids()
    
    text_pdfs = []
    scanned_pdfs = []
    
    print("Scanning PDFs...")
    for filename in sorted(files):
        path = os.path.join(PDF_FOLDER, filename)
        is_text, pages = is_text_pdf(path)
        if is_text:
            text_pdfs.append((filename, pages))
        else:
            scanned_pdfs.append((filename, pages))
    
    print(f"\nText PDFs (will process now): {len(text_pdfs)}")
    print(f"Scanned PDFs (need OCR later): {len(scanned_pdfs)}")
    print("\nScanned PDFs:")
    for name, pages in scanned_pdfs:
        print(f"  {pages:5d} pages | {name}")
    
    print("\n" + "="*60)
    print("Processing text PDFs...")
    print("="*60)
    
    # Collect all chunks first, then embed in batches
    all_chunks = []  # (chunk_data, filename, law_name, category)
    
    for filename, total_pages in text_pdfs:
        # Skip if already fully processed
        test_id = f"{filename}_chunk_0"
        if test_id in processed_ids:
            print(f"  SKIP (done): {filename}")
            continue
        
        print(f"\nExtracting: {filename} ({total_pages} pages)")
        path = os.path.join(PDF_FOLDER, filename)
        doc = fitz.open(path)
        
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        if not full_text.strip():
            print(f"  No text found, skipping.")
            continue
        
        law_name = os.path.splitext(filename)[0]
        category = detect_category(full_text, law_name)
        chunks = semantic_chunk(full_text, filename)
        
        print(f"  {len(chunks)} chunks | category: {category}")
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_chunk_{i}"
            if chunk_id in processed_ids:
                continue
            all_chunks.append({
                "id": chunk_id,
                "text": chunk["text"],
                "source": filename,
                "law_name": law_name,
                "section_number": chunk["metadata"].get("section", "General"),
                "language": detect_language_simple(chunk["text"]),
                "category": category,
                "chunk_index": i,
                "total_chunks_in_law": len(chunks),
                "keywords": extract_keywords(chunk["text"]),
                "jurisdiction": "Pakistan",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "char_count": len(chunk["text"]),
                "word_count": len(chunk["text"].split()),
            })
    
    print(f"\nTotal new chunks to embed: {len(all_chunks)}")
    
    if not all_chunks:
        print("Nothing new to embed.")
        return scanned_pdfs
    
    # ── Generate embeddings in batches ──
    import vertexai
    from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
    
    vertexai.init(project="haqdar-ai", location="asia-south1")
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    
    BATCH = 5
    total = len(all_chunks)
    
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for i in range(0, total, BATCH):
            batch = all_chunks[i:i+BATCH]
            texts = [c["text"] for c in batch]
            
            for attempt in range(5):
                try:
                    inputs = [TextEmbeddingInput(t, "RETRIEVAL_DOCUMENT") for t in texts]
                    embeddings = model.get_embeddings(inputs)
                    break
                except Exception as e:
                    wait = 30 * (2 ** attempt)
                    print(f"  Quota hit, waiting {wait}s...")
                    time.sleep(wait)
            
            for j, emb in enumerate(embeddings):
                record = {**batch[j], "embedding": emb.values}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
            
            if i % 100 == 0:
                print(f"  Embedded {i}/{total}...")
    
    print(f"\nDone. Embedded {total} chunks.")
    print(f"\nScanned PDFs still needing OCR ({len(scanned_pdfs)}):")
    for name, pages in scanned_pdfs:
        print(f"  {pages:5d} pages | {name}")
    
    return scanned_pdfs


if __name__ == "__main__":
    scanned = main()