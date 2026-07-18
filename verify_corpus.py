import json
import os

pdf_dir = './real_laws/'
total_pdfs = len([f for f in os.listdir(pdf_dir) if f.endswith('.pdf')])

total_chunks = 0
files_done = set()
has_embedding = 0
has_text = 0
missing_embedding = 0

with open('law-embeddings-real.json', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            total_chunks += 1
            files_done.add(record.get('source', ''))
            if record.get('embedding') and len(record['embedding']) == 768:
                has_embedding += 1
            else:
                missing_embedding += 1
            if record.get('text'):
                has_text += 1
        except:
            continue

all_pdfs = set(os.listdir(pdf_dir))
missing_pdfs = all_pdfs - files_done

print('='*50)
print('COMPLETE VERIFICATION REPORT')
print('='*50)
print(f'Total PDFs:              {total_pdfs}')
print(f'PDFs processed:          {len(files_done)}')
print(f'PDFs missing:            {len(missing_pdfs)}')
print(f'Total chunks:            {total_chunks}')
print(f'Has text:                {has_text}')
print(f'Has embedding (768-dim): {has_embedding}')
print(f'Missing embedding:       {missing_embedding}')
print(f'All complete:            {missing_embedding == 0 and has_text == total_chunks}')
print('='*50)

if missing_pdfs:
    print(f'MISSING PDFs ({len(missing_pdfs)}):')
    for p in sorted(missing_pdfs):
        if p.endswith('.pdf'):
            print(f'  - {p}')
else:
    print('ALL PDFs processed! Ready for migration.')