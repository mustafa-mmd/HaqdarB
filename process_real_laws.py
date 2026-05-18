import os
import json
import fitz  # PyMuPDF
from docx import Document
import google.generativeai as genai

# ------------------------- CONFIGURATION -------------------------
PROJECT_ID = "haqdar-ai"
LOCATION = "asia-south1"
PDF_FOLDER = "./real_laws/"          # Place all your PDFs/DOCX here
OUTPUT_FILE = "law-embeddings-real.jsonl"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def process_documents():
    os.makedirs(PDF_FOLDER, exist_ok=True)
    files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(('.pdf', '.docx', '.doc'))]
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for filename in files:
            filepath = os.path.join(PDF_FOLDER, filename)
            print(f"Processing: {filename}")
            
            if filename.endswith('.pdf'):
                text = extract_text_from_pdf(filepath)
            else:
                text = extract_text_from_docx(filepath)
            
            if not text.strip():
                continue
            
            chunks = chunk_text(text)
            print(f"  Created {len(chunks)} chunks. Generating embeddings...")
            
            for i in range(0, len(chunks), 5):
                batch = chunks[i:i+5]
                result = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=batch,
                    task_type="retrieval_document"
                )
                embeddings = result['embedding']
                time.sleep(15)  # Super Stable delay
                
                for j, emb in enumerate(embeddings):
                    chunk_id = f"{filename}_chunk_{i+j}"
                    record = {
                        "id": chunk_id,
                        "embedding": emb,
                        "text": batch[j],
                        "source": filename
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"  Done.")
    print(f"\n✅ Real law embeddings saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_documents()