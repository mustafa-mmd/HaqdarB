import json
import os

INPUT_FILE = "law-embeddings-real.json"
STATE_FILE = "uploaded_ids.txt"

def find_missing():
    if not os.path.exists(INPUT_FILE) or not os.path.exists(STATE_FILE):
        print("Files missing.")
        return

    print("Loading IDs from embeddings file...")
    all_ids = set()
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                all_ids.add(record["id"])
            except:
                continue

    print(f"Total unique IDs in embeddings: {len(all_ids)}")

    print("Loading IDs from state file...")
    uploaded_ids = set()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            uploaded_ids.add(line.strip())

    print(f"Total unique IDs in state file: {len(uploaded_ids)}")

    missing = all_ids - uploaded_ids
    print(f"Missing IDs count: {len(missing)}")

    if missing:
        print("\nExamples of missing IDs:")
        for i, mid in enumerate(list(missing)[:10]):
            print(f"  {i+1}. {mid}")

if __name__ == "__main__":
    find_missing()
