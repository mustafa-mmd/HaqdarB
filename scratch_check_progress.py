import os
import json

real_laws_dir = "./real_laws/"
text_cache_dir = "./text_cache/"
embeddings_file = "law-embeddings-real.json"
uploaded_file = "uploaded_ids.txt"

# 1. Get all PDFs
all_pdfs = set()
if os.path.exists(real_laws_dir):
    all_pdfs = set(f for f in os.listdir(real_laws_dir) if f.lower().endswith('.pdf'))

# 2. Get OCR'd PDFs from cache
ocr_pdfs = set()
if os.path.exists(text_cache_dir):
    ocr_pdfs = set(f for f in os.listdir(text_cache_dir) if os.path.isdir(os.path.join(text_cache_dir, f)))

# 3. Get PDFs with embeddings
embedded_pdfs = set()
if os.path.exists(embeddings_file):
    print("Reading embeddings file (this may take a few seconds)...")
    with open(embeddings_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                source = record.get("source")
                if source:
                    embedded_pdfs.add(source)
            except:
                continue

# 4. Get Uploaded PDFs
uploaded_pdfs = set()
if os.path.exists(uploaded_file):
    with open(uploaded_file, "r", encoding="utf-8") as f:
        for line in f:
            chunk_id = line.strip()
            # ID format: {filename}_chunk_{index}
            if "_chunk_" in chunk_id:
                filename = chunk_id.split("_chunk_")[0]
                uploaded_pdfs.add(filename)

# Print Summary
print("\n=== PROGRESS SUMMARY ===")
print(f"Total PDFs found: {len(all_pdfs)}")
print(f"PDFs with OCR cached: {len(ocr_pdfs)}")
print(f"PDFs with Embeddings generated: {len(embedded_pdfs)}")
print(f"PDFs Uploaded to Firestore: {len(uploaded_pdfs)}")

print("\n--- Details ---")
for pdf in sorted(all_pdfs):
    status = []
    if pdf in ocr_pdfs:
        status.append("OCR: Yes")
    else:
        status.append("OCR: No")
        
    if pdf in embedded_pdfs:
        status.append("Embedded: Yes")
    else:
        status.append("Embedded: No")
        
    if pdf in uploaded_pdfs:
        status.append("Uploaded: Yes")
    else:
        status.append("Uploaded: No")
        
    print(f"{pdf} -> {', '.join(status)}")
