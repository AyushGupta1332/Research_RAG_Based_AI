# Research Agent — Project Memory

> **Last Updated:** 2026-05-13T19:18 IST
> **Current Phase:** Phase 6 Complete — Skipped Phase 5 (optional)

---

## Project Overview

Building an **Autonomous Multi-Agent Research System** — a production-grade AI research platform that ingests research papers, extracts structured knowledge, performs hybrid retrieval, orchestrates specialized agents, and generates grounded, citation-backed research outputs.

**This is NOT a chatbot or basic RAG app. This IS a scalable AI research operating system.**

---

## Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Backend Framework | **Flask** (pure Python) | Simpler than FastAPI, no Docker needed |
| Frontend | **HTML + CSS + JS + Tailwind CSS** (CDN) | No framework overhead, fast iteration |
| Database | **SQLite** (dev) → PostgreSQL (prod later) | Zero setup, local file-based |
| Docker | **Not using Docker** for now | Reduces complexity, everything runs locally |
| Task Queue | **Python threading** (background threads) | No Redis/Celery needed for dev |
| LLM Provider | **Groq API** (decided, not yet implemented) | Free tier, fast inference |
| Embeddings | **BAAI/bge-m3** local GPU (RTX 3050) | Implemented in Phase 3, lazy-loads on first use |
| Reranker | **BAAI/bge-reranker-large** local GPU | Implemented in Phase 3, lazy-loads on first use |
| Vector DB | **ChromaDB** (pip install, persistent) | Implemented in Phase 3, cosine similarity |
| Sparse Search | **rank-bm25** | Implemented in Phase 3, BM25Okapi |
| Fusion Method | **Reciprocal Rank Fusion (RRF)** | k=60, configurable weights |

---

## Conversation History

### Conversation 1 — Planning (2026-05-11, morning)
- ID: `da4d3359-0efd-4207-8abf-69fddfb4ff2e`
- Created the initial `Instructions.md` blueprint (8 phases)
- Created the initial `implementation_plan.md` (FastAPI + Docker approach)
- Decided on tech stack: Groq API, local GPU embeddings, Docker infra

### Conversation 2 — First Phase 1 Attempt (2026-05-11, morning)
- ID: `2097cc5e-6ad5-43d4-ad20-827156ad7985`
- Started Phase 1 with FastAPI + Docker Compose
- Set up project structure, installed dependencies
- Got the basic FastAPI skeleton running

### Conversation 3 — Debugging Phase 1 (2026-05-11, morning)
- ID: `cea75a48-bc36-45c7-81c4-bd29a3f4f6ea`
- Hit 500 errors during user registration
- Debugging database connection issues with containerized PostgreSQL
- **This approach was abandoned** in favor of the simplified stack

### Conversation 4 — Phase 1 & 2 (2026-05-11, afternoon)
- ID: `4391e162-975a-418f-b4cb-41a13fb86b1b`
- **Pivoted approach:** No Docker, Flask backend, HTML/Tailwind frontend, SQLite
- Updated `implementation_plan.md` to reflect new approach
- **Completed Phase 1** — Infrastructure Foundation
- **Completed Phase 2** — Research Ingestion Pipeline
- Created `main.py` in project root for one-command startup

### Conversation 5 — Phase 3 + 4 (2026-05-13, evening)
- ID: `322a34d5-fc55-4df5-bdeb-dc783e5f113a`
- **Completed Phase 3** — Embedding & Retrieval System
- Built 5 new backend services (embedding, vector store, BM25, reranker, search orchestrator)
- Updated Query API with full hybrid search endpoint
- Built search frontend page with advanced options
- Auto-embed on ingestion completion (Phase 2 → Phase 3 bridge)
- Installed: sentence-transformers, chromadb, rank-bm25, torch, numpy
- **Completed Phase 4** — Structured Knowledge Extraction
- Built LLM abstraction layer (Groq provider, Llama 3.3 70B)
- Built extraction service with structured prompts + validation
- Added PaperExtraction model, 3 new API endpoints
- Updated paper_detail.html with Extraction tab (AI summary, methods, metrics, etc.)
- Installed: groq SDK

---

## Phase 1 — Infrastructure Foundation ✅ COMPLETE

**What was built:**

### Backend (Flask)
- `backend/app/__init__.py` — Flask app factory with blueprints, CORS, error handlers
- `backend/app/config.py` — Environment-specific config classes (dev/test/prod)
- `backend/app/extensions.py` — SQLAlchemy, JWT, Migrate extension instances
- `backend/app/models/user.py` — User model with bcrypt password hashing
- `backend/app/api/auth.py` — Auth blueprint: register, login, token refresh, profile
- `backend/app/api/pages.py` — Pages blueprint serving HTML templates
- `backend/app/api/papers.py` — Papers blueprint (was placeholder, now full in Phase 2)
- `backend/app/api/query.py` — Query blueprint (was placeholder, now full in Phase 3)
- `backend/app/services/auth_service.py` — Auth business logic layer
- `backend/app/middleware/logging_middleware.py` — Structured logging + request tracing
- `backend/app/utils/responses.py` — Standardized API response helpers
- `backend/run.py` — Backend entry point
- `backend/requirements.txt` — All Python dependencies
- `backend/.env` / `.env.example` — Environment configuration
- `backend/migrations/` — Flask-Migrate (Alembic) initialized

### Frontend (HTML + Tailwind CSS)
- `frontend/templates/base.html` — Base layout with Tailwind CDN, design system, Google Fonts
- `frontend/templates/index.html` — Landing page with gradient hero, feature cards
- `frontend/templates/login.html` — Login page with split-panel design
- `frontend/templates/register.html` — Registration page
- `frontend/templates/dashboard.html` — Dashboard with stats and quick actions
- `frontend/static/js/api.js` — API client with auto token injection and refresh
- `frontend/static/js/auth.js` — Auth module (login/register/logout/localStorage)
- `frontend/static/js/app.js` — Form handlers, toast notifications
- `frontend/static/css/styles.css` — Custom CSS (scrollbars, glassmorphism, gradients)

---

## Phase 2 — Research Ingestion Pipeline ✅ COMPLETE

**What was built:**

### Backend — Ingestion Pipeline
- `backend/app/models/paper.py` — Paper, PaperSection, Chunk models with relationships + cascade deletes
- `backend/app/services/pdf_parser.py` — PyMuPDF parser: title extraction (font-size analysis), author detection, section detection (20+ regex patterns for research paper headings)
- `backend/app/services/chunking_service.py` — Section-aware semantic chunking: sentence splitting, 12% overlap, tiktoken token counting, configurable target (600) and max (768) tokens
- `backend/app/services/ingestion_service.py` — Orchestrator: upload → parse → sections → chunk → store → **auto-embed (Phase 3)**

### Frontend — Paper Management
- `frontend/templates/upload.html` — Drag-and-drop upload with XHR progress bar
- `frontend/templates/papers.html` — Paper library with filter tabs, card grid, pagination
- `frontend/templates/paper_detail.html` — Paper detail with metadata, sections, chunks, reprocess/delete

---

## Phase 3 — Embedding & Retrieval System ✅ COMPLETE

**What was built:**

### Backend — Retrieval Pipeline
- `backend/app/services/embedding_service.py` — GPU-aware embedding with BAAI/bge-m3 (fallback: bge-small-en-v1.5), lazy loading, batch encoding, L2-normalized embeddings
- `backend/app/services/vector_store.py` — ChromaDB persistent vector store, cosine similarity, upsert semantics, per-paper deletion, metadata filtering
- `backend/app/services/bm25_service.py` — BM25Okapi sparse search, tokenization with stop word removal, in-memory index built from DB
- `backend/app/services/reranker_service.py` — Cross-encoder reranking (bge-reranker-large → bge-reranker-base → ms-marco-MiniLM fallback chain), lazy loading
- `backend/app/services/search_service.py` — Hybrid search orchestrator: BM25 + Dense → RRF fusion (k=60) → cross-encoder reranking → final results

### API Endpoints (Phase 3)
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/query/` | Full hybrid search (BM25 + dense + reranker) |
| POST | `/api/query/embed/<id>` | Trigger embedding for a paper |
| GET | `/api/query/stats` | Retrieval system statistics |
| POST | `/api/query/reindex` | Rebuild all search indices |

### Frontend — Search Interface
- `frontend/templates/search.html` — Full search page with:
  - Search input with gradient glow effect
  - Advanced options (top-k, BM25/dense weight sliders, reranker toggle)
  - Result cards with scores (rerank, RRF, BM25, dense), section badges, paper links
  - Search metadata bar (timing, method, result count)
  - System stats panel (embedding model, vector store, BM25 index, reranker status)
- Updated `frontend/templates/dashboard.html` — Added "Search Knowledge" quick action card

### Retrieval Pipeline Architecture
```
User Query
    │
    ├──► BM25 Search (top 20)
    │
    ├──► Dense Retrieval via ChromaDB (top 20)
    │         (bge-m3 embeddings, cosine similarity)
    │
    ▼
Reciprocal Rank Fusion (k=60, configurable weights)
    │
    ▼
Cross-Encoder Reranking (bge-reranker-large)
    │
    ▼
Top-K Final Chunks (with scores + citations)
```

### Key Design Decisions
- **Lazy model loading** — embedding model and reranker load on first use, not at server startup
- **GPU auto-detection** — CUDA if available, CPU fallback
- **Auto-embed on ingestion** — when a paper finishes processing, chunks are automatically embedded and indexed
- **Fallback model chains** — if bge-m3 fails to load, falls back to bge-small; reranker has 3 fallback options
- **Thread-safe** — all model loading uses threading locks

### Verification
- `/api/health` → 200 OK
- `/api/query/stats` → returns system stats (models not-loaded, 0 vectors, 0 BM25 docs)
- Search page renders with all UI elements
- Auto-embedding wired into ingestion pipeline

---

## Phase 4 — Structured Knowledge Extraction ✅ COMPLETE

**What was built:**

### Backend — LLM & Extraction Pipeline
- `backend/app/services/llm_provider.py` — LLM abstraction layer: ABC base class, Groq provider (Llama 3.3 70B Versatile), retry logic (3 attempts), token tracking, JSON mode, singleton factory
- `backend/app/services/extraction_prompts.py` — Structured prompts: full extraction (title, authors, datasets, architectures, methods, metrics, findings, limitations, future work, training details), methodology-specific, results-specific, and summary prompts
- `backend/app/services/extraction_service.py` — Extraction orchestrator: builds context from priority-sorted sections (abstract → intro → methodology → results), sends to LLM, validates schema, stores results. Runs in background thread.
- `backend/app/models/extraction.py` — PaperExtraction model: extracted_data JSON, summary_data JSON, LLM metadata (model, tokens, latency, confidence)

### API Endpoints (Phase 4)
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/papers/<id>/extract` | Trigger LLM extraction (background) |
| GET | `/api/papers/<id>/extraction` | Get extraction results |
| DELETE | `/api/papers/<id>/extract` | Delete extraction (for re-extraction) |

### Frontend — Extraction UI
- Updated `paper_detail.html` with **Extraction tab**:
  - "Extract Knowledge" button with AI icon
  - Auto-refresh during processing
  - AI Summary card (one-liner, detailed summary, key contributions)
  - Paper metadata grid (domain, type, references)
  - Methods list with "Novel" badge
  - Metrics table (metric, value, dataset, baseline comparison)
  - Datasets and Architectures cards
  - Key Findings, Limitations, Future Work lists
  - LLM metadata bar (model, tokens, latency, confidence %)
  - Error state with retry button

### Key Design Decisions
- **Groq + Llama 3.3 70B** — fast inference, free tier
- **JSON mode** — forces structured output from LLM
- **Priority-sorted context** — sends most important sections first, truncates at ~28k chars
- **Confidence scoring** — LLM self-reports extraction confidence (0-1)
- **Retry logic** — 3 attempts with exponential backoff
- **Background processing** — extraction runs in daemon thread

---

## Phase 6 — Multi-Agent Architecture ✅ COMPLETE

**What was built:**

### Backend — Agent Framework
- `backend/app/agents/__init__.py` — BaseAgent ABC: execute/run pattern, timing, error handling, built-in LLM calls
- `backend/app/agents/planner.py` — PlannerAgent: decomposes queries into task plans (retrieval/analysis/summarization/critic)
- `backend/app/agents/retrieval.py` — RetrievalAgent: wraps hybrid search, returns structured passages
- `backend/app/agents/analysis.py` — AnalysisAgent: deep research Q&A with citations and confidence scores
- `backend/app/agents/summarization.py` — SummarizationAgent: generates markdown research reports
- `backend/app/agents/critic.py` — CriticAgent: hallucination detection, grounding verification
- `backend/app/agents/orchestrator.py` — Coordinates: Planner → Retrieval → Analysis → Summarization → Critic

### API Endpoint
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/query/research` | Full multi-agent research query |

### Frontend — AI Research Assistant
- `frontend/templates/research.html` — Research page with:
  - Multi-line query textarea with Ctrl+Enter submit
  - Preset query buttons for common research questions
  - Agent execution trace bar (shows each agent's success/timing)
  - AI-generated markdown report display
  - Collapsible analysis section with key points + citations
  - Critic review card with verdict badge + grounding score
  - Source passages list
  - Loading state with pipeline progress

### Also Fixed
- Rerank scores normalized to 0-1 via sigmoid (display as percentages)
- Color-coded relevance: green >50%, amber 20-50%, red <20%

---

## What's NOT Built Yet

| Feature | Phase | Status |
|---|---|---|
| Knowledge graph (Neo4j) | Phase 5 | Skipped (optional for MVP) |
| Memory architecture | Phase 7 | Not started |
| Evaluation framework | Phase 8 | Not started |

---

## Project File Structure (Current)

```
Research Agent/
├── main.py                          # One-command startup (python main.py)
├── implementation_plan.md           # Full 8-phase plan
├── Instructions.md                  # Original system blueprint
├── memory.md                        # This file
├── .gitignore
│
├── backend/
│   ├── run.py                       # Flask entry point
│   ├── requirements.txt             # Python dependencies
│   ├── .env / .env.example          # Environment config
│   ├── migrations/                  # Alembic migrations
│   ├── instance/
│   │   ├── research_agent.db        # SQLite database
│   │   └── chromadb/                # ChromaDB persistent storage
│   ├── venv/                        # Virtual environment
│   └── app/
│       ├── __init__.py              # App factory
│       ├── config.py                # Config classes
│       ├── extensions.py            # SQLAlchemy, JWT, Migrate
│       ├── models/
│       │   ├── user.py              # User model
│       │   ├── paper.py             # Paper, PaperSection, Chunk
│       │   └── extraction.py        # PaperExtraction model (Phase 4)
│       ├── api/
│       │   ├── auth.py              # Auth endpoints
│       │   ├── papers.py            # Papers + extraction endpoints
│       │   ├── query.py             # Search/query endpoints (Phase 3)
│       │   └── pages.py             # HTML page routes
│       ├── services/
│       │   ├── auth_service.py      # Auth business logic
│       │   ├── pdf_parser.py        # PyMuPDF PDF parsing
│       │   ├── chunking_service.py  # Semantic chunking
│       │   ├── ingestion_service.py # Pipeline orchestrator + auto-embed
│       │   ├── embedding_service.py # bge-m3 embeddings (GPU)
│       │   ├── vector_store.py      # ChromaDB vector storage
│       │   ├── bm25_service.py      # BM25 sparse search
│       │   ├── reranker_service.py  # Cross-encoder reranking
│       │   ├── search_service.py    # Hybrid search orchestrator
│       │   ├── llm_provider.py      # Groq LLM abstraction (Phase 4)
│       │   ├── extraction_prompts.py # Structured extraction prompts
│       │   └── extraction_service.py # Knowledge extraction pipeline
│       ├── middleware/
│       │   └── logging_middleware.py # Request logging
│       └── utils/
│           └── responses.py         # API response helpers
│
├── frontend/
│   ├── templates/
│   │   ├── base.html                # Base layout + Tailwind
│   │   ├── index.html               # Landing page
│   │   ├── login.html               # Login
│   │   ├── register.html            # Register
│   │   ├── dashboard.html           # Dashboard
│   │   ├── upload.html              # PDF upload
│   │   ├── papers.html              # Papers library
│   │   ├── paper_detail.html        # Paper detail view
│   │   └── search.html              # Search interface (Phase 3)
│   └── static/
│       ├── css/styles.css           # Custom styles
│       └── js/
│           ├── api.js               # API client
│           ├── auth.js              # Auth module
│           └── app.js               # App logic
│
└── uploads/                         # Uploaded PDFs (gitignored)
```

---

## How to Run

```bash
cd "e:\Year Project\Extra Projects\Research Agent"
python main.py
# Server starts at http://localhost:5000
```

---

## Next Up: Phase 4 — Structured Knowledge Extraction

**Goal:** LLM-powered extraction of structured research knowledge from papers.

**Will implement:**
1. LLM abstraction layer (Groq API provider)
2. Structured extraction prompts (title, authors, datasets, architectures, metrics, etc.)
3. Extraction pipeline: Paper → LLM → Structured JSON → Validated → Stored
4. Validation layer with schema checks and confidence scores
5. API endpoint: `POST /api/papers/{id}/extract`
6. Frontend extraction UI

**Prerequisites:**
- Groq API key (set in `.env`)
- Decision on which Groq model (Llama 3, Mixtral, or Gemma)

---

## Known Issues / Notes

1. **Windows encoding:** Fixed by adding `sys.stdout.reconfigure(encoding='utf-8')` in run.py
2. **SQLite limitations:** Single-writer at a time; fine for dev, switch to PostgreSQL for prod
3. **Background threads:** Using daemon threads for processing — not production-grade but works for dev. Will switch to Celery + Redis later if needed.
4. **Model download on first use:** Embedding model (~2GB) and reranker model will download from HuggingFace on first search. This can take several minutes on first run.
5. **GPU VRAM:** bge-m3 requires ~2GB VRAM. If GPU memory is insufficient, models will fall back to lighter alternatives.
6. **Database location:** `backend/instance/research_agent.db` (SQLite file)
7. **ChromaDB location:** `backend/instance/chromadb/` (persistent vector storage)
8. **Test user:** Register a new user via the UI or API — `POST /api/auth/register`
