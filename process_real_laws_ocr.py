import os
import json
import base64
import time
import fitz  # PyMuPDF
import google.generativeai as genai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
import vertexai
from dotenv import load_dotenv
from google.api_core import exceptions

load_dotenv()

PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"
PDF_FOLDER = "./real_laws/"
OUTPUT_FILE = "law-embeddings-real.json"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the current 2026 model: Gemini 2.5 Flash Lite
vision_model = genai.GenerativeModel("gemini-2.5-flash-lite") 

CACHE_FOLDER = "./text_cache/"

def extract_text_from_pdf_smart(pdf_path):
    """Extract text using PyMuPDF; only use OCR if page appears scanned. Caches page text."""
    doc = fitz.open(pdf_path)
    base_name = os.path.basename(pdf_path)
    pdf_cache_dir = os.path.join(CACHE_FOLDER, base_name)
    os.makedirs(pdf_cache_dir, exist_ok=True)
    
    full_text = ""
    for page_num in range(len(doc)):
        cache_file = os.path.join(pdf_cache_dir, f"page_{page_num+1}.txt")
        
        # Check if page is already cached
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                page_text = f.read()
            full_text += page_text + "\n"
            continue

        page = doc[page_num]
        text = page.get_text()
        
        if len(text.strip()) > 200:
            page_text = text
            print(f"  Page {page_num+1} text extracted (direct)")
        else:
            print(f"  Page {page_num+1} appears scanned, using OCR (Vertex AI)...")
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            prompt = "Extract all the text from this legal document page. Return only the text."
            success = False
            retries = 0
            page_text = ""
            while not success and retries < 5:
                try:
                    # Using Google AI Studio instead of Vertex AI
                    response = vision_model.generate_content([
                        {"mime_type": "image/png", "data": img_bytes},
                        prompt
                    ])
                    page_text = response.text
                    success = True
                    # Free tier limit is 15 requests per minute, so we wait 4 seconds between OCR calls
                    time.sleep(4) 
                except Exception as e:
                    retries += 1
                    wait = 10 * retries
                    print(f"  OCR error (Vertex): {e}. Retrying in {wait}s...")
                    time.sleep(wait)
            
            if not success:
                print(f"  Failed to OCR page {page_num+1} after {retries} attempts. Skipping.")
                page_text = "[FAILED_OCR_PAGE]"

        # Cache the extracted page text
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(page_text)
        
        full_text += page_text + "\n"
        
    return full_text

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def get_embeddings_with_retry(batch, max_retries=8):
    """Generate embeddings using Google AI Studio with retry and exponential backoff."""
    for attempt in range(max_retries):
        try:
            # Use Google AI Studio embedding model
            result = genai.embed_content(
                model="models/gemini-embedding-2",
                content=batch,
                task_type="retrieval_document"
            )
            # AI Studio returns a list of embeddings in 'embedding' key
            time.sleep(15)  # "Super Stable" mode for very large law datasets
            return result['embedding']
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait = 30 * (2 ** attempt)
                print(f"  Embedding quota exceeded. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Embedding error: {e}. Retrying...")
                time.sleep(10)
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

    # Open in append mode
    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
        for filename in files:
            filepath = os.path.join(PDF_FOLDER, filename)
            print(f"\nProcessing: {filename}")
            text = extract_text_from_pdf_smart(filepath)
            if not text.strip():
                print("  No text extracted, skipping.")
                continue
            chunks = chunk_text(text)
            print(f"  Created {len(chunks)} chunks.")
            
            new_chunks = 0
            for i in range(0, len(chunks), 5):
                batch = chunks[i:i+5]
                # Check if all chunks in this batch are already processed
                batch_ids = [f"{filename}_chunk_{i+j}" for j in range(len(batch))]
                if all(chunk_id in processed_ids for chunk_id in batch_ids):
                    continue
                
                print(f"    Generating embeddings for batch {i//5 + 1}/{(len(chunks)+4)//5}...")
                embeddings = get_embeddings_with_retry(batch)
                for j, emb in enumerate(embeddings):
                    chunk_id = batch_ids[j]
                    if chunk_id in processed_ids:
                        continue
                    record = {
                        "id": chunk_id,
                        "embedding": emb,
                        "text": batch[j],
                        "source": filename
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    out_f.flush()  # Write immediately
                    processed_ids.add(chunk_id)
                    new_chunks += 1
            print(f"  Done. Added {new_chunks} new chunks.")

    print(f"\n✅ All embeddings saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_documents()