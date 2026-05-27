# deduplicate_laws.py
import os
import re
import sys
import hashlib
import json
import shutil
from collections import defaultdict
from google.cloud import firestore
from google.oauth2 import service_account

PDF_FOLDER = "./real_laws"
CACHE_FOLDER = "./text_cache"
EMBEDDINGS_FILE = "law-embeddings-real.json"
STATE_FILE = "uploaded_ids.txt"
CREDENTIALS_PATH = "haqdar-key.json"

def get_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def select_best_file(filenames):
    """
    Select the cleanest filename to keep.
    Penalizes suffixes like (1), copy, _copy, etc.
    """
    def score(name):
        penalty = 0
        if re.search(r'\s*\(\d+\)\.pdf$', name, re.IGNORECASE):
            penalty += 10
        if re.search(r'\s*copy\.pdf$', name, re.IGNORECASE):
            penalty += 10
        if re.search(r'_copy\.pdf$', name, re.IGNORECASE):
            penalty += 10
        return (penalty, len(name), name)

    return min(filenames, key=score)

def deduplicate():
    print("[*] Scanning for duplicate files in real_laws...")
    if not os.path.exists(PDF_FOLDER):
        print(f"[x] PDF folder {PDF_FOLDER} not found.")
        return

    files = [f for f in os.listdir(PDF_FOLDER) if os.path.isfile(os.path.join(PDF_FOLDER, f))]
    
    # Group files by their MD5 hash
    hash_groups = defaultdict(list)
    for filename in files:
        filepath = os.path.join(PDF_FOLDER, filename)
        try:
            file_hash = get_file_hash(filepath)
            hash_groups[file_hash].append(filename)
        except Exception as e:
            print(f"[!] Error reading {filename}: {e}")

    # Determine files to delete and files to keep
    to_delete = []
    kept_files = set()
    exact_duplicates_found = False

    for file_hash, filenames in hash_groups.items():
        if len(filenames) > 1:
            exact_duplicates_found = True
            best_file = select_best_file(filenames)
            kept_files.add(best_file)
            for filename in filenames:
                if filename != best_file:
                    to_delete.append((filename, best_file))
        else:
            kept_files.add(filenames[0])

    if not exact_duplicates_found:
        print("[+] No duplicate files found in real_laws.")
        return

    print(f"\nFound {len(to_delete)} duplicate files to remove:")
    for del_file, keep_file in to_delete:
        print(f"  - Remove: '{del_file}' (Keeping: '{keep_file}')")

    # Ask or proceed with deletion
    auto_approve = "--yes" in sys.argv or "-y" in sys.argv
    if not auto_approve:
        confirm = input("\nProceed with de-duplication? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[x] Aborted.")
            return
    else:
        print("\n[+] Auto-approve flag set. Proceeding with de-duplication...")

    deleted_filenames = [item[0] for item in to_delete]

    # 1. Delete duplicate files from disk
    print("\n[-] Deleting files from disk...")
    for del_file in deleted_filenames:
        path = os.path.join(PDF_FOLDER, del_file)
        try:
            os.remove(path)
            print(f"  Deleted: {del_file}")
        except Exception as e:
            print(f"  [!] Error deleting {del_file}: {e}")

    # 2. Clean up text_cache directory
    print("\n[-] Cleaning up text_cache folder...")
    for del_file in deleted_filenames:
        cache_path = os.path.join(CACHE_FOLDER, del_file)
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
                print(f"  Removed cache directory for: {del_file}")
            except Exception as e:
                print(f"  [!] Error removing cache for {del_file}: {e}")

    # 3. Clean up local embeddings json
    if os.path.exists(EMBEDDINGS_FILE):
        print(f"\n[-] Cleaning up {EMBEDDINGS_FILE}...")
        temp_file = EMBEDDINGS_FILE + ".tmp"
        removed_chunks_count = 0
        kept_chunks_count = 0
        try:
            with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as in_f, open(temp_file, "w", encoding="utf-8") as out_f:
                for line in in_f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        record = json.loads(stripped)
                        source = record.get("source")
                        if source in deleted_filenames:
                            removed_chunks_count += 1
                        else:
                            out_f.write(line)
                            kept_chunks_count += 1
                    except Exception as e:
                        out_f.write(line)
            
            os.replace(temp_file, EMBEDDINGS_FILE)
            print(f"  Removed {removed_chunks_count} chunks, kept {kept_chunks_count} chunks in embeddings file.")
        except Exception as e:
            print(f"  [!] Error cleaning embeddings file: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    # 4. Clean up uploaded_ids.txt
    removed_ids = set()
    if os.path.exists(STATE_FILE):
        print(f"\n[-] Cleaning up {STATE_FILE}...")
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            
            cleaned_lines = []
            for line in lines:
                # Check if the id contains any of the deleted file names
                is_deleted = False
                for del_file in deleted_filenames:
                    if line.startswith(del_file):
                        is_deleted = True
                        removed_ids.add(line)
                        break
                if not is_deleted:
                    cleaned_lines.append(line)
            
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                for line in cleaned_lines:
                    f.write(line + "\n")
            print(f"  Removed {len(removed_ids)} IDs from upload state file.")
        except Exception as e:
            print(f"  [!] Error cleaning upload state file: {e}")

    # 5. Clean up Firestore Database
    if os.path.exists(CREDENTIALS_PATH):
        print("\n[-] Cleaning up Firestore collection 'law_corpus'...")
        try:
            credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
            db = firestore.Client(credentials=credentials)
            
            total_firestore_deleted = 0
            for del_file in deleted_filenames:
                print(f"  Querying Firestore for documents sourced from: '{del_file}'")
                # Query all documents where source matches the deleted file
                docs_ref = db.collection("law_corpus").where("source", "==", del_file).stream()
                
                batch = db.batch()
                count = 0
                for doc in docs_ref:
                    batch.delete(doc.reference)
                    count += 1
                    total_firestore_deleted += 1
                    if count >= 400:
                        batch.commit()
                        batch = db.batch()
                        count = 0
                if count > 0:
                    batch.commit()
                print(f"    Deleted {count} chunks for '{del_file}' from Firestore.")
            
            print(f"  Total Firestore chunks deleted: {total_firestore_deleted}")
        except Exception as e:
            print(f"  [!] Error connecting to or cleaning Firestore: {e}")
    else:
        print(f"\n[!] Firestore credentials file '{CREDENTIALS_PATH}' not found. Firestore cleanup skipped.")

    print("\n[+] De-duplication complete! All redundant files, local caches, embedding records, and Firestore copies have been cleaned.")

if __name__ == "__main__":
    deduplicate()
