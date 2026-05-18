import json
import os

INPUT_FILE = "law-embeddings-real.json"
STATE_FILE = "uploaded_ids.txt"

def verify():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} does not exist.")
        return
    
    if not os.path.exists(STATE_FILE):
        print(f"File {STATE_FILE} does not exist.")
        return

    print("Counting valid lines in embeddings file...")
    total_lines = 0
    valid_lines = 0
    corrupted_lines = 0
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
                valid_lines += 1
            except:
                corrupted_lines += 1

    print(f"Total lines in {INPUT_FILE}: {total_lines}")
    print(f"Valid JSON lines: {valid_lines}")
    print(f"Corrupted lines: {corrupted_lines}")

    print("\nCounting uploaded IDs...")
    uploaded_ids = set()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            uploaded_ids.add(line.strip())

    print(f"Unique IDs in {STATE_FILE}: {len(uploaded_ids)}")

    print("\nComparison:")
    print(f"Expected to upload (valid lines): {valid_lines}")
    print(f"Actually uploaded (recorded in file): {len(uploaded_ids)}")
    
    if len(uploaded_ids) >= valid_lines:
        print("\n[OK] All valid data has been uploaded to Firestore!")
    else:
        print(f"\n[WARNING] {valid_lines - len(uploaded_ids)} chunks are missing from the upload.")

if __name__ == "__main__":
    verify()
