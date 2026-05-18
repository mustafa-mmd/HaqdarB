import os
import json
import sys

PDF_FOLDER = "./real_laws/"
OUTPUT_FILE = "law-embeddings-real.json"

def verify():
    if not os.path.exists(PDF_FOLDER):
        print(f"PDF folder {PDF_FOLDER} does not exist.")
        return
    
    if not os.path.exists(OUTPUT_FILE):
        print(f"Output file {OUTPUT_FILE} does not exist.")
        return

    # Get all PDFs in the folder
    pdf_files = {f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')}
    print(f"Found {len(pdf_files)} PDF files in {PDF_FOLDER}")

    # Read processed chunks
    processed_sources = set()
    chunk_counts = {}
    
    print(f"Reading {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                source = record.get("source")
                if source:
                    processed_sources.add(source)
                    chunk_counts[source] = chunk_counts.get(source, 0) + 1
            except Exception as e:
                continue

    print(f"Found embeddings for {len(processed_sources)} unique files.")

    # Check for missing files
    missing = pdf_files - processed_sources
    if missing:
        print("\n[MISSING] The following files are MISSING from the embeddings:")
        for m in missing:
            print(f"  - {m}")
    else:
        print("\n[OK] All PDF files are present in the embeddings file.")

    # Check for files with 0 chunks or very few chunks
    print("\nChunk counts per file:")
    for file in sorted(pdf_files):
        count = chunk_counts.get(file, 0)
        status = "[OK]" if count > 0 else "[ERROR] (0 chunks)"
        print(f"  - {file}: {count} chunks {status}")

if __name__ == "__main__":
    verify()
