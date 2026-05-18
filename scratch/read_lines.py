INPUT_FILE = "law-embeddings-real.json"

def read_lines():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if 21500 <= line_num <= 21515:
                print(f"Line {line_num}: {line.strip()!r}")
            if line_num > 21515:
                break

if __name__ == "__main__":
    read_lines()
