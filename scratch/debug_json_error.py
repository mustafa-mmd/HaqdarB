import json
import os

INPUT_FILE = "law-embeddings-real.json"

def debug():
    if not os.path.exists(INPUT_FILE):
        print(f"File {INPUT_FILE} does not exist.")
        return

    print(f"Checking {INPUT_FILE} for JSON errors...")
    line_num = 0
    success_count = 0
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
                success_count += 1
            except json.JSONDecodeError as e:
                print(f"\n[ERROR] JSON Error on line {line_num}:")
                print(f"  Error: {e}")
                print(f"  Content (first 100 chars): {stripped[:100]!r}")
                print(f"  Content (last 100 chars): {stripped[-100:]!r}")
                print(f"  Total length of line: {len(stripped)}")
                # Let's see if we can find the issue
                break
    
    print(f"\nSuccessfully parsed {success_count} lines before error (or file ended).")

if __name__ == "__main__":
    debug()
