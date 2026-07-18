# content_dedup.py
import json
import hashlib
import os

INPUT_FILE  = "law-embeddings-real.json"
OUTPUT_FILE = "law-embeddings-deduped.json"

seen_hashes = {}   # hash → first chunk_id that had this content
duplicates  = 0
kept        = 0

print("Reading and deduplicating by content hash...")

with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

    for line in fin:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except Exception:
            continue

        # Hash the actual text content — not the filename
        text       = record.get("text", "").strip()
        text_hash  = hashlib.md5(text.encode("utf-8")).hexdigest()

        if text_hash in seen_hashes:
            duplicates += 1
            # Uncomment to see what's being removed:
            # print(f"  DUP: {record['id']}  ==  {seen_hashes[text_hash]}")
        else:
            seen_hashes[text_hash] = record["id"]
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            kept += 1

print(f"""
╔══════════════════════════════════════════╗
║        Content Deduplication Done        ║
╠══════════════════════════════════════════╣
║  Total chunks read    : {kept + duplicates:<17} ║
║  Unique chunks kept   : {kept:<17} ║
║  Duplicates removed   : {duplicates:<17} ║
╚══════════════════════════════════════════╝
""")

# Replace original with deduped version
os.replace(OUTPUT_FILE, INPUT_FILE)
print(f"Saved clean data back to {INPUT_FILE}")