# HaqDar AI — Pakistan's Legal Rights Companion

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/haqdar)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)
[![Status](https://img.shields.io/badge/status-Production%20Ready-green.svg)](#)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](#)
[![React](https://img.shields.io/badge/React-19-blue.svg)](#)

> **AI-powered legal rights companion for Pakistani citizens — available in Urdu, English, Pashto, Punjabi, Sindhi, and Balochi.**

---

## 🏛️ What is HaqDar AI?

HaqDar AI ("حق دار" — "Rightful") is a Silicon Valley-standard SaaS platform that democratizes access to legal knowledge for 220+ million Pakistanis. Using Google Gemini 2.5 Flash with Google Search Grounding, it provides:

- **AI Legal Q&A** in 6 regional languages with full Pakistani law corpus
- **Document Drafting** — 80+ legal categories, validated formats (FIR, legal notices, court petitions)
- **Case Strength Analyzer** — AI scores your case 0-100 with outcome prediction
- **Document Analysis** — Upload FIRs, eviction notices, contracts for instant AI review
- **Voice Input** — Speak your question in any regional language via Groq Whisper
- **Lawyer Marketplace** — Verified advocate verification with direct WhatsApp redirect
- **Firm Dashboard (Shared)** — Multi-tenant workspace where teams collaborate on incoming case leads
- **Admin Dashboard** — Full community management, real-time stats, and user moderation
- **PWA** — Works offline, installable on Android/iOS

---

## 🏗️ Architecture

```
haqdar/
├── haqdar-ai-backend/          # FastAPI Python Backend
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── query.py        # Main legal Q&A & doc drafting endpoints
│   │   │   └── study.py        # Study Academy backend endpoints
│   │   ├── core/
│   │   │   ├── config.py       # Centralized settings
│   │   │   └── firebase.py     # Firebase Admin SDK
│   │   ├── services/
│   │   │   ├── gemini_service.py         # Core AI (multi-turn conv.)
│   │   │   ├── universal_drafting_agent.py # 80-cat document drafting
│   │   │   ├── case_analyzer.py           # Case strength scoring
│   │   │   ├── document_agent.py          # PDF/image analysis
│   │   │   ├── intake_agent.py            # Language + category detection
│   │   │   ├── peca_agent.py              # Cybercrime specialist
│   │   │   ├── referral_agent.py          # Legal aid lookup
│   │   │   ├── usage_service.py           # Quota enforcement
│   │   │   ├── transcription_service.py   # Groq Whisper ASR
│   │   │   └── vector_search.py           # Qdrant vector search
│   │   └── main.py             # FastAPI app with middleware
│   ├── fast_extract_text_pdfs.py   # ⭐ Extract chunks + embeddings
│   ├── migrate_to_qdrant_http.py   # ⭐ Upload vectors to Qdrant
│   ├── deduplicate_laws.py         # Remove duplicate chunks
│   ├── requirements.txt
│   └── .env                    # Backend secrets (git-ignored)
│
└── Haqdar/haqdar-frontend/     # React 19 + Vite + Tailwind Frontend
    ├── public/
    │   ├── manifest.json        # PWA manifest
    │   ├── sw.js               # Service Worker
    │   └── offline.html        # Offline fallback
    ├── src/
    │   ├── pages/
    │   │   ├── Chat.jsx            # Main chat interface
    │   │   ├── CaseAnalyzerPage.jsx # Case strength analyzer
    │   │   ├── DraftComplaintPage.jsx
    │   │   ├── LegalDocPage.jsx
    │   │   ├── TermsPage.jsx       # Terms of Service
    │   │   ├── PrivacyPage.jsx     # Privacy Policy
    │   │   ├── StudyMode.jsx       # Study dashboard page
    │   │   └── DocumentationPage.jsx # Built-in app documentation
    │   ├── components/
    │   │   ├── Sidebar.jsx         # Navigation sidebar
    │   │   ├── TutorChat.jsx       # Socratic AI Tutor component
    │   │   ├── NotesGenerator.jsx  # Notes generator + docx downloader
    │   │   ├── FlashcardDeck.jsx   # Leitner spaced repetition flashcards
    │   │   ├── QuizRenderer.jsx    # Timed MCQ Quiz + results review
    │   │   ├── ProgressDashboard.jsx # Learning streaks and mastery logs
    │   │   └── MindMap.jsx         # Interactive Mermaid.js mind maps
    │   ├── context/
    │   │   └── AuthContext.jsx     # Firebase Auth context
    │   └── App.jsx                 # Router with lazy-loading
    └── .env                        # Frontend env vars
```

---

## ⚡ Tech Stack

| Layer             | Technology                                               |
| ----------------- | -------------------------------------------------------- |
| **AI**            | Google Gemini 2.5 Flash (with Google Search Grounding)   |
| **Vector Search** | Qdrant Cloud (replaces Vertex AI Vector Search)          |
| **Embeddings**    | text-embedding-005 (Vertex AI)                           |
| **ASR**           | Groq Whisper (6 languages)                               |
| **Backend**       | Python 3.12, FastAPI 0.115, Uvicorn                      |
| **Database**      | Google Cloud Firestore                                   |
| **Auth**          | Firebase Authentication (Google OAuth + Phone)           |
| **Frontend**      | React 19, Vite 6, Tailwind CSS                           |
| **PWA**           | Service Worker, Web App Manifest                         |
| **Hosting**       | Google Cloud Run (backend) + Firebase Hosting (frontend) |
| **Payments**      | Stripe (international) + JazzCash/Easypaisa (local)      |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Google Cloud project with Vertex AI enabled
- Firebase project
- Qdrant Cloud account (free tier available at cloud.qdrant.io)
- Groq API key (for voice transcription)

### Backend Setup

```bash
cd haqdar-ai-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd Haqdar/haqdar-frontend

# Install dependencies
npm install

# Configure environment
cp .env .env.local
# Edit VITE_API_URL if needed

# Run development server
npm run dev
```

---

## ⚙️ Environment Variables

### Backend `.env`

```env
# AI
GEMINI_API_KEY=your-gemini-api-key

# Google Cloud (embeddings only — Vector Search index removed)
PROJECT_ID=your-gcp-project-id
LOCATION=asia-south1

# Firebase
FIREBASE_SERVICE_ACCOUNT_PATH=haqdar-key.json

# Qdrant Vector Database (replaces Vertex AI Vector Search)
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=law_corpus

# App Settings
ENVIRONMENT=development  # development | production
DEBUG=true               # false in production

# Groq (for ASR)
GROQ_API_KEY=your-groq-api-key

# Twilio (WhatsApp Bot)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# SendGrid (Email Notifications)
SENDGRID_API_KEY=your-sendgrid-api-key
SYSTEM_EMAIL=notifications@haqdar.pk
```

### Frontend `.env`

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 📡 API Reference

### Base URL

- Development: `http://localhost:8000/api/v1`
- Production: `https://api.haqdar.pk/api/v1`

### Endpoints

| Method | Endpoint                 | Description                  | Auth     |
| ------ | ------------------------ | ---------------------------- | -------- |
| GET    | `/health`                | System health check          | None     |
| POST   | `/query`                 | AI legal Q&A with RAG        | Required |
| POST   | `/case-analyze`          | Case strength analysis       | Required |
| POST   | `/draft-legal`           | Universal document drafting  | Required |
| POST   | `/draft-template`        | Template-based document gen  | Required |
| GET    | `/templates`             | List available templates     | None     |
| POST   | `/document`              | Upload document for analysis | Required |
| POST   | `/peca`                  | Cybercrime/PECA specialist   | Required |
| POST   | `/draft`                 | Complaint letter (Word)      | Required |
| POST   | `/transcribe`            | Speech-to-text               | Optional |
| GET    | `/referral`              | Legal aid by city            | None     |
| GET    | `/referral/autocomplete` | City autocomplete            | None     |
| GET    | `/user/profile`          | Get user profile + usage     | Required |
| POST   | `/user/profile`          | Update user profile          | Required |
| GET    | `/news`                  | Legal news feed              | Optional |
| POST   | `/study/difficulty`      | Set difficulty preference     | Required |
| POST   | `/study/notes`           | Study notes + DOCX download   | Required |
| POST   | `/study/flashcards`      | Leitner flashcards generator  | Required |
| POST   | `/study/quiz/generate`   | MCQ quiz generator            | Required |
| POST   | `/study/quiz/submit`     | Submit MCQ quiz for grading   | Required |
| POST   | `/study/compare`         | Compare written answer to ideal | Required |
| GET    | `/study/progress`        | Subject mastery, streaks & recs | Required |
| POST   | `/study/mindmap`         | Mermaid.js mind map generator | Required |
| POST   | `/study/case-brief`      | Legal case brief generator   | Required |
| POST   | `/study/tutor`           | Socratic AI Tutor session     | Required |


### Authentication

All protected endpoints require a Firebase ID token in the request body:

```json
{
  "token": "firebase-id-token-here",
  "text": "My landlord is threatening to evict me..."
}
```

---

## 📋 Legal Document Templates (20 Available)

1. **FIR Draft** (S.154 CrPC) — Full police complaint format
2. **Legal Notice** — Registered post format with 15/30-day demand
3. **Rent Agreement** — Monthly/annual tenancy with all clauses
4. **Employment Contract** — Full employment terms
5. **Partnership Deed** — Business partnership agreement
6. **Sale Deed (Bai Nama)** — Property transfer with sub-registrar format
7. **Gift Deed (Hiba Nama)** — Property gift format
8. **Khula Petition** — Family court petition format
9. **Maintenance Application** — MFLO 1961 format
10. **Succession Certificate** — Civil court application
11. **Bail Application** — Criminal court format
12. **Consumer Court Complaint** — Provincial consumer protection format
13. **NAB Complaint** — National Accountability Bureau complaint
14. **NEPRA/Electricity Complaint** — Consumer utility complaint
15. **Workplace Harassment Complaint** — PAH Act 2010 format
16. **Habeas Corpus Writ** — High Court petition format
17. **FIA Cybercrime Complaint** (PECA 2016) — NR3C format
18. **Domestic Violence Protection Order** — DV Court application
19. **Nikah Deed** — Islamic marriage contract
20. **Labour Court Application** — NIRC/Labour Court format

---

## 💰 Subscription Plans

| Feature                 | Free | Pro (PKR 999/mo) | Firm (PKR 9,999/mo) |
| ----------------------- | ---- | ---------------- | ------------------- |
| AI Queries/Day          | 10   | 500              | Unlimited           |
| Document Drafts/Month   | 2    | 50               | Unlimited           |
| Document Analysis/Month | 1    | 20               | Unlimited           |
| PDF Upload              | ❌   | ✅               | ✅                  |
| Case Analyzer           | ✅   | ✅               | ✅                  |
| Chat Export             | ❌   | ✅               | ✅                  |
| Priority Support        | ❌   | ✅               | ✅                  |
| API Access              | ❌   | ❌               | ✅                  |

---

## 🌍 Supported Languages

| Code  | Language | Script            | Voice Input |
| ----- | -------- | ----------------- | ----------- |
| `ur`  | Urdu     | Nastaliq (Arabic) | ✅          |
| `en`  | English  | Latin             | ✅          |
| `ps`  | Pashto   | Arabic            | ✅          |
| `pa`  | Punjabi  | Shahmukhi         | ✅          |
| `sd`  | Sindhi   | Arabic            | ✅          |
| `bal` | Balochi  | Arabic            | ✅          |

---

## 🔒 Security & System Resilience

### 🛡️ Core Security Architecture

- **Firebase Authentication & Authorization**: All sensitive API routes are protected. Incoming Firebase JWT ID tokens are decoded and cryptographically verified using custom claims for admin permissions.
- **Fail-Closed Billing Quotas**: The usage and plan validation loops in `app/services/usage_service.py` are strictly **fail-closed**. If database reads, quota updates, or network calls fail, the service refuses the request with an `HTTPException(503 Service Unavailable)` rather than failing open, completely preventing subscription bypass exploits.
- **PII & Privacy Protection Scrubber**: A robust Personally Identifiable Information (PII) scrubber (`app/middleware/pii_scrubber.py`) acts as an inline anonymizer before sending queries to external LLMs. It uses highly optimized regular expressions to automatically scrub:
  - **Pakistani CNICs**: `\b\d{5}-\d{7}-\d\b` replaced with `[CNIC-REDACTED]`
  - **Pakistani Phone Numbers**: Standard and international formats replaced with `[PHONE-REDACTED]`
  - **Email Addresses**: Standard RFC 5322 emails replaced with `[EMAIL-REDACTED]`
  - **Street Address Fragments**: Heuristics flagging local suffixes replaced with `[ADDRESS-REDACTED]`
- **Rate Limiting Middleware**: Built-in protection against DoS using `slowapi`:
  - `/api/v1/query` and `/api/v1/query-stream`: **20 requests/minute**
  - `/api/v1/draft-legal`: **10 requests/minute**
  - `/api/v1/transcribe`: **10 requests/minute**
- **Twilio Webhook Verification**: Strict HMAC-SHA1 signature verification on WhatsApp webhook.
- **Environment Validation**: Startup validator (`app/core/validation.py`) checks all required secrets. Fails fast in production if any are missing.

### ⚡ Caching & Performance Optimizations

- **Plan Tier Caching**: User subscription plans cached in-memory with **5-minute TTL**.
- **Usage Count Caching**: Daily consumption stats cached with **60-second TTL**.
- **Automatic Cache Invalidation**: Cache cleared immediately on usage increments or profile edits.

### 💰 Token Usage & Cost Logging

- **Firestore Cost Logs**: After each LLM invocation, granular logs persisted to `cost_log` collection tracking `uid`, `endpoint`, `model_name`, `input_tokens`, `output_tokens`.
- **Secure Admin Analytics**: `GET /api/v1/admin/costs` aggregates usage using live Gemini 2.5 Flash pricing.

### 🏛️ Semantic Legal Chunking & Qdrant Alignment

- **RAG Model Alignment**: `fast_extract_text_pdfs.py` and `vector_search.py` both use `text-embedding-005` (768 dimensions, Cosine similarity).
- **Legal Semantic Boundaries**: Text split on legal section markers (`Section \d+`, `دفعہ \d+`, `Article \d+`) keeping law sections intact.
- **Rich Chunk Metadata stored in Qdrant payload**: `law_name`, `section_number`, `language`, `category`, `keywords`, `jurisdiction`, `page_number`, `chunk_index`.
- **Payload Filtering**: Qdrant pre-filters by `language` and `category` before ANN search — improves recall and reduces latency simultaneously.

---

## 📚 Adding New Laws to the Vector Database

### Complete Pipeline

```
PDF file
   ↓
PyMuPDF (text extraction — free, instant)
   ↓
Semantic chunking (Section/Article boundaries)
   ↓
text-embedding-005 (Vertex AI — 768 dimensions)
   ↓
Qdrant Cloud (vector storage + search)
```

### Steps to Add New Laws

**Step 1** — Place new `.pdf` files in the `real_laws/` directory.

**Step 2** — Generate chunks and embeddings (auto-skips already processed files):

```bash
venv\Scripts\activate
python fast_extract_text_pdfs.py
```

**Step 3** — Verify chunks and embeddings are correct:

```bash
python -c "
import json
count = 0
has_embedding = 0
has_text = 0
with open('law-embeddings-real.json', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        count += 1
        record = json.loads(line)
        if record.get('embedding'):
            has_embedding += 1
        if record.get('text'):
            has_text += 1
print(f'Total chunks:      {count}')
print(f'Has text:          {has_text}')
print(f'Has embedding:     {has_embedding}')
print(f'Both match:        {has_text == has_embedding}')
"
```

**Step 4** — Remove duplicates:

```bash
python deduplicate_laws.py -y
```

##to verify complete data report
python -c "
import json
import os

# ── 1. Real laws folder mein kitni PDFs hain

pdf_dir = './real_laws/'
total_pdfs = len([f for f in os.listdir(pdf_dir) if f.endswith('.pdf')])

# ── 2. Embeddings file mein kitne chunks hain

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

# ── 3. Kaunsi PDFs missing hain

all_pdfs = set(os.listdir(pdf_dir))
processed = files_done
missing_pdfs = all_pdfs - processed

print('='*50)
print('COMPLETE VERIFICATION REPORT')
print('='*50)
print(f'Total PDFs in real_laws: {total_pdfs}')
print(f'PDFs processed: {len(files_done)}')
print(f'PDFs missing: {len(missing_pdfs)}')
print(f'')
print(f'Total chunks: {total_chunks}')
print(f'Has text: {has_text}')
print(f'Has embedding (768-dim): {has_embedding}')
print(f'Missing embedding: {missing_embedding}')
print(f'')
print(f'All chunks complete: {missing_embedding == 0 and has_text == total_chunks}')
print('='\*50)

if missing_pdfs:
print(f'MISSING PDFs ({len(missing_pdfs)}):')
for p in sorted(missing_pdfs):
if p.endswith('.pdf'):
print(f' - {p}')
else:
print('ALL PDFs processed! Ready for migration.')
"

**Step 5** — Upload to Qdrant (auto-skips existing, safe to re-run):

```bash
python migrate_to_qdrant_http.py
```

**Step 6** — Verify file count in real_laws directory:

```powershell
(Get-ChildItem -Path .\real_laws -File).Count
```

**Step 7** — Test search is working:

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from app.services.vector_search import search_similar_laws
results = search_similar_laws('landlord eviction tenant rights', neighbor_count=3)
for r in results:
    print(r['score'], '|', r['law_name'], '|', r['text'][:80])
"
```

### Old Commands (DO NOT USE)

```bash
# These are replaced — do not run:
# python process_real_laws_ocr.py          ← replaced by fast_extract_text_pdfs.py
# python upload_real_laws_to_firestore.py  ← replaced by migrate_to_qdrant_http.py
```

---

## 🔍 Vector Search Architecture

```
User query (any language)
      ↓
intake_agent.py → detects language + category
      ↓
text-embedding-005 → 768-dim query vector
      ↓
Qdrant Cloud Search
  filter: {language: "ur", category: "criminal"}
  → top-5 chunks + scores  [<10ms]
      ↓
Chunk text returned inline from Qdrant payload
(no extra Firestore call needed)
      ↓
Gemini 2.5 Flash → streamed legal answer
```

### Why Qdrant over Vertex AI Vector Search

|                   | Vertex AI (old) | Qdrant Cloud (new)             |
| ----------------- | --------------- | ------------------------------ |
| Cost at 1k users  | ~$220/mo        | ~$0-25/mo                      |
| Cost at 10k users | ~$600/mo        | ~$100/mo                       |
| Minimum billing   | ~$150/mo always | $0 free tier                   |
| Payload filtering | Basic           | Advanced (language + category) |
| Latency           | 80-200ms        | 1-10ms                         |
| Startup cost      | High            | Free tier available            |

---

## 📊 Qdrant Collection Structure

```
Collection: law_corpus
Vector size: 768 (text-embedding-005)
Distance: Cosine

Payload fields (indexed for filtering):
  language      → "ur" | "en" | "ps" | "pa" | "sd" | "bal"
  category      → "criminal" | "civil" | "family" | "property" | ...
  law_name      → "Pakistan_Penal_Code1860"
  source        → "Pakistan Penal Code1860.pdf"
  jurisdiction  → "Pakistan"

Other payload fields (stored, not indexed):
  text          → full chunk text
  section_number → "Section 302"
  page_number   → 45
  chunk_index   → 12
  keywords      → ["murder", "qatl", "punishment"]
  char_count    → 1150
  word_count    → 210
  timestamp     → "2026-05-23 22:00:00"
```

---

## 🛠️ Real Backend Integrations (v2.1.0)

### 🏛️ Lawyer Marketplace & Lead Gen

- **Persistence**: Lawyers fetched from Firestore `lawyers` collection.
- **Consultation Requests**: Saved to `consultation_requests` in Firestore.
- **Notifications**: Structured for instant WhatsApp/Email forwarding to the lawyer.
- **Verification**: New lawyers enter "Pending" state — require Admin approval to go live.

### 💬 Community Forum

- **Posts & Replies**: Stored in global `forum_posts` and `forum_replies` collections.
- **Moderation**: Admin-level users can flag or remove posts directly.
- **Language**: Supports RTL (Urdu/Pashto) and LTR (English) scripts natively.

### 🏢 Firm Dashboard (Multi-Tenant)

- **Architecture**: Multi-tenant data isolation.
- **Team Management**: Real-time member invitation and role assignment (Admin, Associate, Paralegal).
- **Usage Tracking**: Aggregated AI query counts for firm-wide quota management.

### 🎓 Study Academy (Beta)

- **Interactive Study Tools**: Leitner Spaced Repetition flashcards, Socratic AI Tutor chats, timed MCQ quizzes, auto-compiled notes, and Mermaid.js mind maps.
- **ASR dictation**: Regional language voice recognition integrated next to the tutor.
- **PII Scrubbing**: Regex-based sanitization in Socratic AI tutor chats to mask CNICs, emails, phones, and addresses.
- **Spaced Repetition Sync**: Leitner box rating states (Forgot / Recalled) are synced directly to the Firestore `flashcards` collection.
- **Academic Standing**: Fetches daily learning streaks and mastery statuses from `/progress` to display interactive badges on home dashboards.

---

## 📜 Legal Categories (80+)

Criminal, Civil, Family, Property, Labour, Constitutional, Consumer, Taxation, Corporate, Banking, Intellectual Property, Rent/Tenancy, Inheritance, Domestic Violence, PECA/Cybercrime, Juvenile Justice, Environmental, Arbitration, Immigration, Maritime, Energy, Aviation, Insurance, Election, Defamation, Media/Telecom, Medical Negligence, Service Law, Trust/Waqf, Food Safety, Disability, Competition, Anti-Corruption, Data Privacy, Hudood/Qisas, Education, Agricultural, Motor Vehicle, Prison/Detention, Refugee, Religious Offences, Microfinance, Human Rights, Mining, Water Resources, Securities, Overseas Pakistanis, Human Trafficking, Social Security, Workplace Harassment, Child Protection, Local Government, Real Estate Regulatory, Zakat/Ushr, Military, International Trade, and more.

---

## 🗺️ Roadmap

### ✅ Completed (v2.1.0)

- [x] Qdrant Cloud vector search (replaces Vertex AI Vector Search)
- [x] Fast text extraction pipeline (PyMuPDF — replaces Gemini Vision OCR)
- [x] HTTP-based Qdrant migration (no extra dependencies)
- [x] Payload filtering by language + category
- [x] Production CORS configuration
- [x] Centralized config with Settings class
- [x] Usage tracking & quota enforcement
- [x] Case Strength Analyzer (AI scoring 0-100)
- [x] PDF document analysis (multi-page)
- [x] 20 document templates with form builder
- [x] Admin analytics dashboard (Real-time Firestore Stats)
- [x] Chat history export (JSON)
- [x] Streaming AI responses (Server-Sent Events)
- [x] Lawyer Marketplace (Real Firestore Backend + Lead Generation)
- [x] Community Legal Forum (Real Multilingual Posts & Replies)
- [x] Multi-tenant Firm Dashboard (Real Team Management)
- [x] WhatsApp Bot integration (Voice notes → Legal advice)
- [x] Multi-turn conversation memory
- [x] 80-category legal taxonomy
- [x] Terms of Service page
- [x] Privacy Policy (PDPB compliant)
- [x] PWA manifest + Service Worker v2
- [x] SEO-optimized index.html
- [x] Global error handling middleware
- [x] Request timing/logging middleware
- [x] Health check endpoint
- [x] Audit log for compliance
- [x] Legal news feed (Gemini + Google Search)

### 🔄 In Progress (v2.1)

- [ ] Subscription billing (Stripe + JazzCash integration)

### 📅 Planned (v3.0)

- [ ] Mobile apps (React Native)
- [ ] Qdrant Mumbai region (when available on free tier)

---

## 🚀 Deployment

### Backend — Google Cloud Run

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/haqdar-backend .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/haqdar-backend

# Deploy to Cloud Run
gcloud run deploy haqdar-backend \
  --image gcr.io/YOUR_PROJECT_ID/haqdar-backend \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production
```

### Frontend — Firebase Hosting

```bash
cd haqdar-frontend
npm run build
firebase deploy --only hosting
```

---

## 📊 Performance Benchmarks

| Metric                 | Value        |
| ---------------------- | ------------ |
| AI Query Response      | 2-4s average |
| Document Analysis      | 3-6s         |
| Case Analysis          | 5-15s        |
| Voice Transcription    | 1-3s         |
| Vector Search (Qdrant) | 1-10ms       |
| Frontend LCP           | <2s (PWA)    |

---

## 💸 Cost Comparison (Monthly)

| Scale         | Old (Vertex AI) | New (Qdrant) | Saving     |
| ------------- | --------------- | ------------ | ---------- |
| 1,000 users   | ~$220/mo        | ~$25/mo      | ~$195/mo   |
| 10,000 users  | ~$600/mo        | ~$100/mo     | ~$500/mo   |
| 100,000 users | ~$1,800/mo      | ~$400/mo     | ~$1,400/mo |

---

## ⚠️ Important Disclaimers

1. **Not Legal Advice**: HaqDar AI provides legal _information_, not legal _advice_. No attorney-client relationship is created.
2. **AI Limitations**: AI-generated documents require review by a licensed Pakistani advocate before use in any official proceeding.
3. **Law Changes**: Pakistani law changes frequently. Always verify current law with a qualified lawyer.
4. **No Guarantee**: HaqDar AI does not guarantee legal outcomes.

---

## 📄 License

Proprietary Software — All Rights Reserved  
© 2026 HaqDar AI

---

## 📞 Contact

- **Website**: [haqdar.pk](https://haqdar.pk)
- **Email**: contact@haqdar.pk
- **Legal**: legal@haqdar.pk
- **Privacy**: privacy@haqdar.pk
- **Support**: support@haqdar.pk
