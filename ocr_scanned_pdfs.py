"""
ocr_scanned_pdfs.py
─────────────────────────────────────────────────────────────────────────────
Production-ready OCR + embedding pipeline for scanned/image-based law PDFs.

Features
  • Per-file progress tracking  — re-run safely, already-done files are skipped
  • Per-chunk deduplication     — partial files resume from the exact chunk missed
  • Crash-safe writes           — each batch flushed to disk immediately
  • Retry with exponential back-off on API quota errors
  • Raises properly after exhausted retries (no silent wrong-data bug)
  • page_number stored per chunk (required by migrate_to_qdrant_http.py)
  • Embeds per-file, not all-at-once (no large RAM accumulation)

Usage
  For text-based PDFs  → python fast_extract_text_pdfs.py
  For scanned PDFs     → python ocr_scanned_pdfs.py
  Upload to Qdrant     → python migrate_to_qdrant_http.py
─────────────────────────────────────────────────────────────────────────────
"""

import fitz
import json
import os
import re
import sys
import time
import io
from collections import Counter
from PIL import Image
import pytesseract

# ── NEW SDK (replaces deprecated vertexai.language_models) ──
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\musta\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
)

PDF_FOLDER    = "./real_laws/"
OUTPUT_FILE   = "law-embeddings-real.json"   # JSONL — append-only
PROGRESS_FILE = "ocr_progress.txt"           # Tracks fully completed files

CHUNK_SIZE    = 1200
CHUNK_OVERLAP = 200
TESS_LANG     = "urd+eng"
EMBED_BATCH   = 5          # Batch size per API call
MAX_RETRIES   = 5
MIN_OCR_CHARS = 50         # Skip files with less OCR text than this

VERTEXAI_PROJECT  = "haqdar-ai"
VERTEXAI_LOCATION = "asia-south1"
EMBED_MODEL       = "text-embedding-005"

LAW_CATEGORIES = {
    "cyber":          ["cyber", "peca", "electronic", "digital", "data", "computer"],
    "family":         ["marriage", "divorce", "khula", "nikah", "maintenance", "custody", "family"],
    "property":       ["property", "land", "rent", "lease", "tenancy", "waqf"],
    "labour":         ["labour", "employment", "worker", "employer", "wages"],
    "constitutional": ["constitution", "fundamental", "rights", "federal", "election"],
    "taxation":       ["tax", "excise", "customs", "duty", "income tax", "sales tax"],
    "criminal":       ["crime", "offence", "punishment", "arrest", "fir", "ppc", "penal", "murder", "theft"],
    "civil":          ["suit", "civil", "procedure", "cpc", "injunction", "decree"],
    "general":        [],
}

# ─────────────────────────────────────────────
# Text utilities
# ─────────────────────────────────────────────

def detect_language(text: str) -> str:
    return "ur" if re.search(r"[\u0600-\u06ff]", text) else "en"


def extract_keywords(text: str, max_kw: int = 5) -> list:
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from",
        "section", "act", "of", "to", "in", "a", "on", "by",
        "or", "as", "is", "be", "are", "was",
    }
    words  = re.findall(r"\b[A-Za-z\u0600-\u06ff]{4,}\b", text)
    counts = Counter(w.lower() for w in words if w.lower() not in stopwords)
    return [w for w, _ in counts.most_common(max_kw)]


def detect_category(text: str, law_name: str = "") -> str:
    combined = (text + " " + law_name).lower()
    for cat, keywords in LAW_CATEGORIES.items():
        if cat == "general":
            continue
        if any(kw in combined for kw in keywords):
            return cat
    return "general"


def fixed_size_chunks(text: str) -> list:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start: start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
        if start >= len(text) - CHUNK_OVERLAP:
            break
    return chunks


def semantic_chunk(text: str) -> list:
    """
    Split on Section / Article headers first; fall back to fixed-size
    chunking for any segment that exceeds CHUNK_SIZE.
    """
    pattern = re.compile(r"(?i)(?:^|\n)(Section\s+\d+|Article\s+\d+)\b")
    matches = list(pattern.finditer(text))
    if not matches:
        return fixed_size_chunks(text)

    chunks = []
    if matches[0].start() > 0:
        chunks.extend(fixed_size_chunks(text[: matches[0].start()].strip()))

    for idx, match in enumerate(matches):
        end_pos      = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section_text = text[match.start(): end_pos].strip()
        if not section_text:
            continue
        if len(section_text) > CHUNK_SIZE:
            chunks.extend(fixed_size_chunks(section_text))
        else:
            chunks.append(section_text)
    return chunks

# ─────────────────────────────────────────────
# Progress / deduplication
# ─────────────────────────────────────────────

def get_embedded_chunk_ids() -> set:
    """
    Read the output JSONL and return the set of chunk_ids already embedded.
    Used for per-chunk deduplication — handles partial file interruptions.
    """
    ids = set()
    if not os.path.exists(OUTPUT_FILE):
        return ids
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["id"])
            except Exception:
                continue
    return ids


def get_completed_files() -> set:
    """
    Return filenames that were fully processed and saved to progress file.
    A file is marked complete only after ALL its chunks are embedded.
    """
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def mark_file_complete(filename: str):
    """Append filename to progress file once ALL its chunks are embedded."""
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(filename + "\n")

# ─────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────

def is_scanned_pdf(pdf_path: str, min_chars: int = MIN_OCR_CHARS) -> bool:
    doc  = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return len(text.strip()) < min_chars


def ocr_pdf(pdf_path: str) -> tuple[str, list]:
    """
    OCR a PDF and return (full_text, page_texts).
    page_texts is a list where index = page_number (0-based).
    """
    doc        = fitz.open(pdf_path)
    total      = len(doc)
    full_text  = ""
    page_texts = []

    for page_num, page in enumerate(doc):
        print(f"    OCR page {page_num + 1}/{total}...", end="\r")
        mat = fitz.Matrix(300 / 72, 300 / 72)   # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        try:
            page_text = pytesseract.image_to_string(img, lang=TESS_LANG)
        except Exception:
            page_text = pytesseract.image_to_string(img, lang="eng")

        page_texts.append(page_text)
        full_text += page_text + "\n"

    doc.close()
    print()   # newline after \r progress
    return full_text, page_texts

# ─────────────────────────────────────────────
# Embedding  (google-genai SDK)
# ─────────────────────────────────────────────

def embed_with_retry(client: genai.Client, texts: list) -> list:
    """
    Call embedding API with exponential back-off retry.
    RAISES RuntimeError after MAX_RETRIES exhausted — never silently continues
    with wrong data.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                ),
            )
            return [e.values for e in response.embeddings]
        except Exception as e:
            last_error = e
            wait = 30 * (2 ** (attempt - 1))   # 30s, 60s, 120s, 240s, 480s
            print(f"  ⚠️  Embedding error (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                print(f"     Retrying in {wait}s ...")
                time.sleep(wait)

    raise RuntimeError(
        f"Embedding failed after {MAX_RETRIES} attempts: {last_error}"
    )


def embed_and_save_file(
    filename:     str,
    chunks:       list,       # list of {"id", "text", "page_number", ...}
    embedded_ids: set,        # already-embedded chunk_ids (mutated in place)
    client:       genai.Client,
    out_file,                 # open file handle for OUTPUT_FILE
) -> int:
    """
    Embed only NEW chunks for a single file and write to the output JSONL.
    Skips chunks already in embedded_ids (per-chunk deduplication).
    Returns the number of new chunks embedded.
    """
    new_chunks = [c for c in chunks if c["id"] not in embedded_ids]
    if not new_chunks:
        return 0

    total    = len(new_chunks)
    embedded = 0

    for i in range(0, total, EMBED_BATCH):
        batch   = new_chunks[i: i + EMBED_BATCH]
        texts   = [c["text"] for c in batch]
        vectors = embed_with_retry(client, texts)   # raises on exhausted retries

        for chunk, vector in zip(batch, vectors):
            record = {**chunk, "embedding": vector}
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_file.flush()
            embedded_ids.add(chunk["id"])   # keep skip logic accurate in-place

        embedded += len(batch)
        print(f"    Embedded {embedded}/{total} chunks ...")
        time.sleep(1)   # gentle rate-limit buffer

    return embedded

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    # ── Validate setup ──
    if not os.path.isdir(PDF_FOLDER):
        print(f"❌  PDF_FOLDER not found: {PDF_FOLDER}")
        sys.exit(1)

    # ── Load existing state ──
    embedded_ids    = get_embedded_chunk_ids()
    completed_files = get_completed_files()
    print(f"Already embedded chunks : {len(embedded_ids)}")
    print(f"Completed files tracked : {len(completed_files)}")

    # ── Find scanned PDFs ──
    print(f"\nScanning {PDF_FOLDER} for image-based PDFs ...")
    all_pdfs   = sorted(f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf"))
    scanned    = [f for f in all_pdfs if is_scanned_pdf(os.path.join(PDF_FOLDER, f))]
    to_process = [f for f in scanned if f not in completed_files]

    print(f"Total PDFs found        : {len(all_pdfs)}")
    print(f"Scanned (image-based)   : {len(scanned)}")
    print(f"Already completed       : {len(scanned) - len(to_process)}")
    print(f"To process this run     : {len(to_process)}")

    if not to_process:
        print("\n✅  All scanned PDFs are already processed.")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        return

    # ── Init google-genai client (NEW SDK) ──
    print("\nInitialising embedding client ...")
    client = genai.Client(
        vertexai=True,
        project=VERTEXAI_PROJECT,
        location=VERTEXAI_LOCATION,
    )
    print("Embedding client ready ✓\n")

    # ── Process each file ──
    total_new = 0
    skipped   = 0

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_file:
        for filename in to_process:
            pdf_path = os.path.join(PDF_FOLDER, filename)
            law_name = os.path.splitext(filename)[0]
            print(f"\n{'─'*60}")
            print(f"📄  {filename}")

            # ── OCR ──
            try:
                full_text, page_texts = ocr_pdf(pdf_path)
            except Exception as e:
                print(f"  ❌  OCR failed: {e} — skipping file.")
                skipped += 1
                continue

            if len(full_text.strip()) < MIN_OCR_CHARS:
                print(f"  ⚠️  OCR produced no usable text — marking done and skipping.")
                mark_file_complete(filename)
                skipped += 1
                continue

            # ── Chunk ──
            category    = detect_category(full_text, law_name)
            text_chunks = semantic_chunk(full_text)
            print(f"  Chunks: {len(text_chunks)} | Category: {category}")

            # Map chunks to page numbers via character offsets
            page_boundaries = []
            char_offset = 0
            for pg_idx, pg_text in enumerate(page_texts):
                page_boundaries.append((char_offset, char_offset + len(pg_text), pg_idx))
                char_offset += len(pg_text) + 1   # +1 for the "\n" added during OCR

            def page_for_offset(offset: int) -> int:
                for start, end, pg in page_boundaries:
                    if start <= offset < end:
                        return pg
                return len(page_texts) - 1

            chunk_offset = 0
            chunks_meta  = []
            for i, chunk_text_val in enumerate(text_chunks):
                chunk_id = f"{filename}_chunk_{i}"
                chunks_meta.append({
                    "id":                  chunk_id,
                    "text":                chunk_text_val,
                    "source":              filename,
                    "law_name":            law_name,
                    "section_number":      "General",
                    "language":            detect_language(chunk_text_val),
                    "category":            category,
                    "page_number":         page_for_offset(chunk_offset),
                    "chunk_index":         i,
                    "total_chunks_in_law": len(text_chunks),
                    "keywords":            extract_keywords(chunk_text_val),
                    "jurisdiction":        "Pakistan",
                    "timestamp":           time.strftime("%Y-%m-%d %H:%M:%S"),
                    "char_count":          len(chunk_text_val),
                    "word_count":          len(chunk_text_val.split()),
                })
                chunk_offset += len(chunk_text_val)

            # ── Embed and save ──
            try:
                new_count = embed_and_save_file(
                    filename, chunks_meta, embedded_ids, client, out_file
                )
                total_new += new_count
                print(f"  ✅  {new_count} new chunks embedded.")

                # Mark complete ONLY after ALL chunks are saved successfully
                mark_file_complete(filename)

            except RuntimeError as e:
                # Do NOT mark complete — next run will retry this file
                print(f"  ❌  Embedding failed for {filename}: {e}")
                print(f"      File will be retried on next run.")
                skipped += 1
                continue

    # ── Summary ──
    print(f"""
╔══════════════════════════════════════════╗
║           OCR + Embed Complete ✅         ║
╠══════════════════════════════════════════╣
║  Files processed      : {len(to_process):<17} ║
║  Files skipped/failed : {skipped:<17} ║
║  New chunks embedded  : {total_new:<17} ║
║  Total in JSONL now   : {len(embedded_ids):<17} ║
╚══════════════════════════════════════════╝

Next step:  python migrate_to_qdrant_http.py
""")


if __name__ == "__main__":
    main()