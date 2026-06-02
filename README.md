# 🚀 Autonomous Multi-Agent Research System (Research OS)

An advanced, production-grade autonomous AI research operating system designed to ingest academic/scientific research papers, extract structured knowledge, perform local high-performance hybrid retrieval, and coordinate a multi-agent framework to generate grounded, citation-backed conversational reports.

**This is NOT a simple "chat with PDF" app. This IS a scalable local Research Operating System.**

---

## 💡 Conceptual Project Overview: How it Works

Rather than treating documents as unformatted text blobs or using simple single-turn chatbot lookups, the **Research OS** functions like a team of dedicated academic researchers working alongside you. Here is the simplified flow of how the system transforms complex PDF documents into highly structured, conversational research:

### 1. Ingestion & Indexing (Reading & Storing)
When you upload a scientific paper, the system doesn't just read it line-by-line. It performs **structural layout analysis** (like a human skimming headers). It identifies where the *Abstract*, *Methodology*, *Experimental Results*, and *Conclusions* begin and end. 
*   **Logical Chunking:** It slices the document precisely along these section boundaries so that concepts never get mixed up.
*   **Dual Indexing:** It indexes the text using two search strategies: **Dense Vector Search** (matching concepts and meanings) and **Sparse Keyword Search** (matching exact numbers, terms, or model names).

### 2. Knowledge Extraction (Deep Understanding)
As soon as a paper is ingested, a background processor (LLM) extracts structured knowledge immediately. It builds a permanent fact-sheet of the paper:
*   What **novel methodologies** were proposed?
*   What **evaluation metrics** and **datasets** were used?
*   What are the exact **results**, **limitations**, and **future work** items?
This structured sheet is kept in a separate tab, so you can inspect the core contributions of a paper at a glance without reading the whole PDF.

### 3. The Multi-Agent Research Team (Conversational Q&A)
When you ask a question (e.g. *"How does the accuracy of this model compare to previous baselines?"*), the system activates a specialized team of autonomous agents to draft your answer:

```
               ┌───────────────────────┐
               │    User Submits Query  │
               └───────────┬───────────┘
                           ▼
               ┌───────────────────────┐
               │     PLANNER AGENT     │ <─── Analyzes chat history & resolves pronouns
               └───────────┬───────────┘
                           ▼
               ┌───────────────────────┐
               │    RETRIEVAL AGENT    │ <─── Conducts hybrid vector & keyword search
               └───────────┬───────────┘
                           ▼
               ┌───────────────────────┐
               │    ANALYSIS AGENT     │ <─── Cross-references retrieved chunks with facts
               └───────────┬───────────┘
                           ▼
               ┌───────────────────────┐
               │  SUMMARIZATION AGENT  │ <─── Drafts a beautifully formatted Markdown report
               └───────────┬───────────┘
                           ▼
               ┌───────────────────────┐
               │     CRITIC AGENT      │ <─── Audits claims, detects hallucinations, grades factuality
               └───────────────────────┘
```

*   **The Planner Agent:** Takes your query, reads your chat history, and rewrites any ambiguous references (e.g. converting *"its baseline"* into *"the baseline metrics of Aegis DLP"*).
*   **The Retrieval Agent:** Performs hybrid search and merges vector results with keyword matches to pull the most relevant academic passages.
*   **The Analysis Agent:** Carefully cross-references your question against the retrieved passages and structured fact-sheets to construct a grounded response.
*   **The Summarization Agent:** Packages the final answer into a clean, comprehensive, professional Markdown report.
*   **The Critic Agent (The Gatekeeper):** Independent from the rest of the team, the Critic audits the generated answer word-by-word against the physical citations. It assigns an **Average Grounding Score (0-100%)** and flags any unsubstantiated claims before the response is shown to you.

### 4. The Quality & Latency Dashboard
To keep the search and LLM output quality at peak performance, a built-in **Performance Evaluation Dashboard** measures and plots key technical metrics:
*   **Accuracy Gauges:** Computes Precision, Recall, and Ranking decay metrics against a ground-truth dataset.
*   **Speed Profiler:** Breaks down the milliseconds taken by each retrieval component (Dense, Sparse, Fusion, Reranking).
*   **Audit Metrics:** Visualizes historical factual reliability distributions to ensure the agents remain grounded and hallucination-free.

---

## 🏛️ Theoretical Architecture & Core Frameworks

The system is engineered as a unified research processing stack composed of four distinct engineering layers:

```
[ PDF Upload ] ──► 1. INGESTION PIPELINE (Section-Aware Parse & Chunk)
                         │
                         ├──► 2a. HYBRID RETRIEVAL (bge-m3 Dense + BM25 Sparse)
                         └──► 2b. STRUCTURED KNOWLEDGE EXTRACTION (Llama 3.3 Background Process)
                                      │
[ User Query ] ──► 3. CONVERSATIONAL MULTI-AGENT ORCHESTRATION:
                         Planner (Query Rewriter) ➔ Retrieval ➔ Analysis ➔ Summarizer ➔ Critic
                                      │
                         [ Grounded Report + Audit Trace ]
```

### 1. Ingestion & Preprocessing Pipeline
*   **Section-Aware PDF Parsing:** Leveraging `PyMuPDF`, the system parses PDF documents and applies font-size statistics combined with heuristic regex pattern matchers to reconstruct the structural layout hierarchy of academic papers (e.g., Abstract, Introduction, Methodology, Experimental Setup, Results).
*   **Semantic Chunking:** Documents are chunked section-by-section to ensure passages never span logical boundaries. Chunks are sentence-split, utilizing `tiktoken` to target ~600 tokens (max 768 tokens) with a 12% sliding overlap to maintain semantic continuity.

### 2. High-Performance Hybrid Retrieval Framework
To achieve state-of-the-art context matching, the system implements a dual-retrieve, fuse, and rerank pipeline:
*   **Dense Semantic Indexing:** Text chunks are vectorized locally using `BAAI/bge-m3` (1024-dimension embeddings, L2 normalized) via `sentence-transformers` on GPU (CUDA) with CPU fallbacks, stored in a persistent local `ChromaDB` collection.
*   **Sparse Keyword Indexing:** Concurrently, an in-memory `BM25Okapi` index is generated using tokenized, stopword-filtered versions of the chunks via `rank-bm25` to capture exact terms (e.g., model acronyms, datasets, specific numbers).
*   **Reciprocal Rank Fusion (RRF):** Rankings from Dense and Sparse queries are fused mathematically using RRF ($k=60$) weighted by configurable sliders:
    $$\text{RRF\_Score}(d) = w_{\text{sparse}} \cdot \frac{1}{60 + \text{Rank}_{\text{sparse}}(d)} + w_{\text{dense}} \cdot \frac{1}{60 + \text{Rank}_{\text{dense}}(d)}$$
*   **Cross-Encoder Reranking:** The top merged candidates are fed into a local cross-encoder (`BAAI/bge-reranker-large`), which computes exact query-chunk matching scores, normalized to $0\text{--}100\%$ relevance bounds.

### 3. Structured Knowledge Extraction
*   **Background LLM Extraction:** Upon completion of paper ingestion, a background daemon thread isolates key sections and runs a multi-prompt schema extractor using **Groq JSON Mode** (`Llama-3.3-70b-versatile`).
*   **Metadata Schema:** Generates fully validated structured JSON objects storing key contributions, methods (novel vs. standard), evaluation metrics (metric, value, dataset, baseline), model architectures, limitations, and future work.

### 4. Conversational Multi-Agent Orchestrator
When a research query is submitted, a loosely coupled, zero-dependency custom agent system coordinates the response:
*   **Planner Agent:** Parses user queries and formulates structured sub-tasks. **Includes Conversational Memory Query Rewriting**—resolving pronouns/context references (e.g., *"Compare its accuracy with the other model"*) using chat history to create a self-contained search query.
*   **Retrieval Agent:** Fetches citation-grounded passages using the Hybrid Retrieval service.
*   **Research Analysis Agent:** Synthesizes retrieved chunks and structured extractions, performing benchmarks, methodology comparisons, and limitation studies in the context of the chat log.
*   **Summarization Agent:** Compiles comprehensive, beautifully structured academic reports in Markdown.
*   **Critic Agent (Grounding Auditor):** Acts as an independent auditor. It verifies every claim in the report against the retrieved chunks, computes a **Grounding Score (0–100%)**, flags hallucinations, and details contradictions/unsupported claims.

### 5. Automated Performance Evaluation Framework (Phase 8)
To guarantee the empirical quality of vector retrieval and the semantic fidelity of the multi-agent outputs, the system runs an automated end-to-end evaluation suite:
*   **Vector Retrieval Benchmarking:** Tests the system against a ground-truth dataset (`evaluation_dataset.json`) consisting of common query vectors and their corresponding paper/section targets.
*   **Component Latency Profiling:** Measures fine-grained timing metrics (in milliseconds) across each pipeline step—BM25 search, dense retrieval, RRF fusion, and cross-encoder reranking.
*   **Factual Grounding Audits:** Periodically queries database history to aggregate the Critic Agent's auditing reviews, calculating the running average grounding index and historical verdict distributions.

---

## 📁 Technical Directory Structure

```
research-agent/
├── main.py                          # Bootstrapper (auto-setup venv, installs requirements, boots Flask)
├── implementation_plan.md           # Engineering implementation phases
├── Instructions.md                  # Conceptual system design blueprint
├── memory.md                        # Active session progress journal
├── README.md                        # This file
│
├── backend/
│   ├── run.py                       # Flask application entry point
│   ├── requirements.txt             # Python packages (sentence-transformers, chromadb, groq, rank-bm25)
│   ├── .env / .env.example          # API keys & configuration environment
│   ├── migrations/                  # Alembic DB migration schemas
│   ├── instance/
│   │   ├── research_agent.db        # SQLite relational database
│   │   └── chromadb/                # Local persistent vector store
│   └── app/
│       ├── __init__.py              # Application factory pattern
│       ├── config.py                # Environment-specific configuration
│       ├── extensions.py            # Extensions init (SQLAlchemy, JWT, Migrate)
│       ├── models/
│       │   ├── user.py              # User account authentication models
│       │   ├── paper.py             # Paper, Section, Chunk tables
│       │   ├── extraction.py        # Structured paper knowledge extractions
│       │   └── memory.py            # Persistent ResearchSession and ResearchMessage
│       ├── api/
│       │   ├── auth.py              # User authentication REST endpoints
│       │   ├── papers.py            # Paper library uploads & extractions
│       │   ├── query.py             # Conversational agent & performance benchmarking endpoints
│       │   └── sessions.py          # Session management & conversation thread APIs
│       ├── utils/
│       │   ├── responses.py         # Standardized API response formatters
│       │   └── evaluation_dataset.json # Ground-truth retrieval test cases (Phase 8)
│       └── services/
│           ├── auth_service.py      # Authentication workflows
│           ├── pdf_parser.py        # PDF layouts section extractor
│           ├── chunking_service.py  # Section-aware sentence chunker
│           ├── ingestion_service.py # Parallel background pipeline orchestrator
│           ├── embedding_service.py # Local BAAI/bge-m3 dense vector encoder
│           ├── vector_store.py      # ChromaDB client connector
│           ├── bm25_service.py      # Sparse search index builder
│           ├── reranker_service.py  # Cross-Encoder rank filters
│           ├── search_service.py    # Hybrid retrieval coordinator
│           ├── llm_provider.py      # Groq LLM singleton abstraction
│           ├── extraction_prompts.py# Structured JSON schemas for analysis
│           ├── extraction_service.py# Background metadata extraction engine
│           └── evaluation_service.py# Benchmarks precision & grounding auditor (Phase 8)
│
└── frontend/
    ├── templates/
    │   ├── base.html                # Shared layout context with Tailwind CSS CDN
    │   ├── index.html               # Sleek glassmorphic landing deck
    │   ├── login.html / register.html# User validation portals
    │   ├── dashboard.html           # System analytics & quick actions hub
    │   ├── upload.html              # Drag-and-drop file ingestion portal
    │   ├── papers.html              # Indexed papers index
    │   ├── paper_detail.html        # Detailed section chunks & AI extraction tab
    │   ├── research.html            # Conversational Agent workspace (split-view chat)
    │   └── evaluation.html          # Performance Dashboard UI with SVG gauges (Phase 8)
    └── static/
        ├── css/styles.css           # Brand scrollbar customizations and custom CSS
        └── js/
            ├── api.js               # Dynamic API fetch wrappers (token interceptors)
            ├── auth.js              # State authorization locks
            └── app.js               # Common form helpers
```

---

## 🛠️ Installation & Setup

Ensure you have **Python 3.10+** and **Git** installed on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/AyushGupta1332/Research_RAG_Based_AI.git
cd Research_RAG_Based_AI
```

### 2. Configure Environment Variables
Inside the `backend/` directory, create a `.env` file using the example template:
```bash
cp backend/.env.example backend/.env
```
Open `backend/.env` and insert your **Groq API Key**:
```text
GROQ_API_KEY=gsk_your_actual_groq_api_key_goes_here
SECRET_KEY=generate_a_random_jwt_signing_key_here
```

### 3. Start the Application
Bootstrapping is completely automated. Run the root script:
```bash
python main.py
```
This script will:
1. Create a local virtual environment (`backend/venv/`).
2. Install all required dependencies (sentence-transformers, chromadb, rank-bm25, PyMuPDF, groq, etc.).
3. Initialize the SQLite relational database schema.
4. Launch the local Flask server on `http://localhost:5000`.

### 4. First Run Indexing Notice
*   **Model Downloads:** On your very first query or search, the system will download the embedding model (`bge-m3`, ~2GB) and reranker (`bge-reranker-large`) from HuggingFace to your local cache. This can take several minutes depending on your internet connection speed.
*   **Hardware Acceleration:** The embedding service automatically detects CUDA-capable GPUs (e.g., RTX 3050/4060) to run vector encoding with hardware acceleration. If no GPU is available, it gracefully falls back to CPU execution.
