# HaqDar AI — Pakistan's Legal Rights Companion

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/haqdar)
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
│   │   │   └── query.py        # All API endpoints
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
│   │   │   └── transcription_service.py   # Groq Whisper ASR
│   │   └── main.py             # FastAPI app with middleware
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
    │   │   └── DocumentationPage.jsx # Built-in app documentation
    │   ├── components/
    │   │   └── Sidebar.jsx         # Navigation sidebar
    │   ├── context/
    │   │   └── AuthContext.jsx     # Firebase Auth context
    │   └── App.jsx                 # Router with lazy-loading
    └── .env                        # Frontend env vars
```

---

## ⚡ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI** | Google Gemini 2.5 Flash (with Google Search Grounding) |
| **Vector Search** | Google Vertex AI Vector Search |
| **Embeddings** | text-embedding-005 |
| **ASR** | Groq Whisper (6 languages) |
| **Backend** | Python 3.12, FastAPI 0.115, Uvicorn |
| **Database** | Google Cloud Firestore |
| **Auth** | Firebase Authentication (Google OAuth + Phone) |
| **Frontend** | React 19, Vite 6, Tailwind CSS |
| **PWA** | Service Worker, Web App Manifest |
| **Hosting** | Google Cloud Run (backend) + Firebase Hosting (frontend) |
| **Payments** | Stripe (international) + JazzCash/Easypaisa (local) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Google Cloud project with Vertex AI enabled
- Firebase project
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

# Google Cloud
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
INDEX_ENDPOINT_ID=your-vertex-ai-index-endpoint-id
DEPLOYED_INDEX_ID=your-deployed-index-id

# Firebase
FIREBASE_SERVICE_ACCOUNT_PATH=haqdar-key.json

# App Settings
ENVIRONMENT=development  # development | production
DEBUG=true               # false in production

# Groq (for ASR)
GROQ_API_KEY=your-groq-api-key
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

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | System health check | None |
| POST | `/query` | AI legal Q&A with RAG | Required |
| POST | `/case-analyze` | Case strength analysis | Required |
| POST | `/draft-legal` | Universal document drafting | Required |
| POST | `/draft-template` | Template-based document gen | Required |
| GET | `/templates` | List available templates | None |
| POST | `/document` | Upload document for analysis | Required |
| POST | `/peca` | Cybercrime/PECA specialist | Required |
| POST | `/draft` | Complaint letter (Word) | Required |
| POST | `/transcribe` | Speech-to-text | Optional |
| GET | `/referral` | Legal aid by city | None |
| GET | `/referral/autocomplete` | City autocomplete | None |
| GET | `/user/profile` | Get user profile + usage | Required |
| POST | `/user/profile` | Update user profile | Required |
| GET | `/news` | Legal news feed | Optional |

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

| Feature | Free | Pro (PKR 999/mo) | Firm (PKR 9,999/mo) |
|---------|------|-----------------|---------------------|
| AI Queries/Day | 10 | 500 | Unlimited |
| Document Drafts/Month | 2 | 50 | Unlimited |
| Document Analysis/Month | 1 | 20 | Unlimited |
| PDF Upload | ❌ | ✅ | ✅ |
| Case Analyzer | ✅ | ✅ | ✅ |
| Chat Export | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ |
| API Access | ❌ | ❌ | ✅ |

---

## 🌍 Supported Languages

| Code | Language | Script | Voice Input |
|------|----------|--------|-------------|
| `ur` | Urdu | Nastaliq (Arabic) | ✅ |
| `en` | English | Latin | ✅ |
| `ps` | Pashto | Arabic | ✅ |
| `pa` | Punjabi | Shahmukhi | ✅ |
| `sd` | Sindhi | Arabic | ✅ |
| `bal` | Balochi | Arabic | ✅ |

---

## 🔒 Security

- **CORS**: Restricted to known production domains (no `*` wildcard)
- **Authentication**: All write endpoints require Firebase JWT verification
- **Rate Limiting**: Per-user quota enforcement (free: 10 queries/day)
- **Input Validation**: Pydantic models with min/max length constraints
- **Audit Log**: Immutable Firestore audit trail for all operations
- **HTTPS**: Required in production (TLS 1.3)
- **No Data Selling**: User queries never shared with third parties

---

## 📜 Legal Categories (80+)

Criminal, Civil, Family, Property, Labour, Constitutional, Consumer, Taxation, Corporate, Banking, Intellectual Property, Rent/Tenancy, Inheritance, Domestic Violence, PECA/Cybercrime, Juvenile Justice, Environmental, Arbitration, Immigration, Maritime, Energy, Aviation, Insurance, Election, Defamation, Media/Telecom, Medical Negligence, Service Law, Trust/Waqf, Food Safety, Disability, Competition, Anti-Corruption, Data Privacy, Hudood/Qisas, Education, Agricultural, Motor Vehicle, Prison/Detention, Refugee, Religious Offences, Microfinance, Human Rights, Mining, Water Resources, Securities, Overseas Pakistanis, Human Trafficking, Social Security, Workplace Harassment, Child Protection, Local Government, Real Estate Regulatory, Zakat/Ushr, Military, International Trade, and more.

---

## 📚 Adding New Laws to the Vector Database

To add new legal PDFs to the HaqDar knowledge base and index them for the AI:

1. **Place PDFs**: Put your new raw `.pdf` files in the `raw_laws` (or `real_laws`) directory.
2. **Process and Parse PDFs**:
   ```bash
   venv\Scripts\activate
   
   python process_real_laws_ocr.py

   python scratch/verify_embeddings.py

   ```
   This script extracts text from the PDFs and breaks them down into usable chunks.
3. **Generate Embeddings**:
   Ensure `law-embeddings.json` is updated with the new chunks using the embedding generation script.
4. **Upload to Vector Database & Firestore**:
   ```bash
   python upload_real_laws_to_firestore.py
   ```
   This will sync the newly generated text chunks and their embeddings to the Firestore `law_corpus` collection and the Vertex AI Vector Search index.

---

## 🛠️ Real Backend Integrations (v2.1.0)

HaqDar v2.1.0 has moved from mock interfaces to fully functional, database-driven features.

### 🏛️ Lawyer Marketplace & Lead Gen
- **Persistence**: Lawyers are fetched from the Firestore `lawyers` collection.
- **Workflow**: 
  - **Consultation Requests**: Saved to `consultation_requests` in Firestore.
  - **Notifications**: Structured for instant WhatsApp/Email forwarding to the lawyer.
  - **Verification**: New lawyers enter a "Pending" state and require Admin approval to go live.

### 💬 Community Forum
- **Posts & Replies**: Stored in global `forum_posts` and `forum_replies` collections.
- **Moderation**: Admin-level users can flag or remove posts directly.
- **Language**: Supports RTL (Urdu/Pashto) and LTR (English) scripts natively.

### 🏢 Firm Dashboard (Multi-Tenant)
- **Architecture**: Multi-tenant data isolation.
- **Team Management**: Real-time member invitation and role assignment (Admin, Associate, Paralegal).
- **Usage Tracking**: Aggregated AI query counts for firm-wide quota management.

---

## 🗺️ Roadmap

### ✅ Completed (v2.0.0)
- [x] Production CORS configuration
- [x] Centralized config with Settings class
- [x] Usage tracking & quota enforcement
- [x] Case Strength Analyzer (AI scoring 0-100)
- [x] PDF document analysis (multi-page)
- [x] 20 document templates with form builder (Real Backend Integration)
- [x] Admin analytics dashboard (Real-time Firestore Stats)
- [x] Chat history export (JSON)
- [x] Streaming AI responses (Server-Sent Events)
- [x] Lawyer Marketplace (Real Firestore Backend + Lead Generation)
- [x] Community Legal Forum (Real Multilingual Posts & Replies)
- [x] Multi-tenant Firm Dashboard (Real Team Management)
- [x] WhatsApp Bot integration (Voice notes → Legal advice)
- [x] Vertex AI Vector Search migration
- [x] Multi-turn conversation memory
- [x] 80-category legal taxonomy (was 8)
- [x] Terms of Service page
- [x] Privacy Policy (PDPB compliant)
- [x] PWA manifest + Service Worker v2
- [x] SEO-optimized index.html
- [x] API environment variable (no hardcoded localhost)
- [x] Global error handling middleware
- [x] Request timing/logging middleware
- [x] Health check endpoint
- [x] Audit log for compliance
- [x] Legal news feed (Gemini + Google Search)

### 🔄 In Progress (v2.1)
- [ ] Subscription billing (Stripe + JazzCash integration)

### 📅 Planned (v3.0)
- [ ] Mobile apps (React Native)

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

| Metric | Value |
|--------|-------|
| AI Query Response | 2-4s average |
| Document Analysis | 3-6s |
| Case Analysis | 5-15s |
| Voice Transcription | 1-3s |
| Vector Search | <500ms |
| Frontend LCP | <2s (PWA) |

---

## ⚠️ Important Disclaimers

1. **Not Legal Advice**: HaqDar AI provides legal *information*, not legal *advice*. No attorney-client relationship is created.
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
