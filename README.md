# Trust-Aware Multi-Agent RAG

> **A research-grade, hallucination-resistant Multi-Agent Retrieval-Augmented Generation (RAG) framework with calibrated trust scoring, multi-source contradiction detection, sentence-level verification, and dynamic knowledge ingestion.**

---

## Overview

Standard RAG pipelines blindly pass retrieved snippets to an LLM in a single pass without evaluating evidence sufficiency, agreement, or factual reliability. **Trust-Aware Multi-Agent RAG** introduces an auditable, multi-agent evaluation pipeline:

- **Retriever Agent** decomposes queries and searches vector indices.
- **Critic Agent** audits evidence quality, identifies contradictions between sources, and labels chunks (`support`, `contradict`, `neutral`).
- **Trust Scoring Engine** computes a calibrated trust score (0.0 to 1.0) based on source agreement, contradiction ratios, and semantic relevance, enforcing strict abstention policies when evidence is insufficient.
- **Synthesizer Agent** writes answers conditioned strictly on verified `support` evidence.
- **Verifier Agent** audits each sentence in the drafted answer, forcing revisions if unsupported claims or hallucinations are detected.

---

## High-Level Architecture

```
                                    User Question
                                          │
                                          ▼
                                ┌───────────────────┐
                                │  Retriever Agent  │ (Query Decomposition & Multi-Search)
                                └─────────┬─────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        │   FAISS Vector Store (Embeddings) │
                        │   Supabase PostgreSQL (Metadata)  │
                        └─────────────────┬─────────────────┘
                                          │
                                          ▼
                                ┌───────────────────┐
                                │   Critic Agent    │ (Evidence Quality & Contradiction Detection)
                                └─────────┬─────────┘
                                          │
                                          ▼
                                ┌───────────────────┐
                                │   Trust Engine    │ (Calibrated Trust Score & Decision Policy)
                                └─────────┬─────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
      Trust Score >= 0.75                          Trust Score < 0.50
   (High Confidence Answer)                       (Honest Abstention)
                   │                                             │
                   ▼                                             ▼
        ┌───────────────────┐                       "I don't have enough verified
        │ Synthesizer Agent │ (Citation-backed)      evidence to answer this."
        └──────────┬────────┘
                   │
                   ▼
        ┌───────────────────┐
        │  Verifier Agent   │ (Sentence Verification & Hallucination Checks)
        └──────────┬────────┘
                   │
                   ▼
       Final Verified Answer + Auditable Evidence + Trust Diagnostics
```

---

## Key Features

- **Multi-Agent Orchestration**: Modular LangGraph agents coordinating evidence retrieval, critique, synthesis, and verification.
- **Dynamic Knowledge Ingestion**:
  - **PDF Documents**: Page-by-page text extraction with page metadata preservation.
  - **DOCX / Word**: Paragraph and tabular data extraction.
  - **TXT / Markdown**: Clean document segmentation.
  - **CSV & XLSX Datasets**: Semantic row-to-sentence transformation (`Row 1: ColA: ValA, ColB: ValB.`).
  - **JSON Records**: Structured key-value extraction.
  - **Websites & URLs**: Live webpage fetching, DOM script/style stripping, and article extraction.
- **Incremental FAISS Vector Search**: Instant vector indexing, search, and zero-orphan vector deletion.
- **Auditable Source Citations**: Every sentence in the answer links to its exact source file, URL, page number, and chunk ID.
- **Contradiction Detection**: Explicitly identifies and visualizes conflicting claims across different sources on the Evidence page.
- **Trust Dashboard**: Tracks query volumes, average trust scores, decision distributions, and hallucination ratios.
- **Cloud-Native Database Infrastructure**:
  - **Supabase PostgreSQL**: Persistent relational storage for documents, chunks, and trust audit logs.
  - **Upstash Redis**: Fast caching and pipeline state management.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14, React 18, TypeScript, TailwindCSS, Lucide Icons |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, Pydantic, Alembic |
| **Orchestration** | LangGraph, LangChain Core |
| **LLM Inference** | Groq Cloud API (`llama3-8b-8192` / `llama3-70b-8192`) |
| **Embeddings** | HuggingFace Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`) |
| **Vector Store** | FAISS (`faiss-cpu`) |
| **Cloud PostgreSQL** | Supabase |
| **Cloud Cache** | Upstash Redis |

---

## Local Setup & Installation

### Prerequisites
- **Python 3.10 or 3.11** installed
- **Node.js 18+ or 20+** installed
- Free accounts on **[Supabase](https://supabase.com)**, **[Upstash](https://upstash.com)**, and **[Groq](https://console.groq.com)**

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/saieswa/trust-aware-rag.git
cd trust-aware-rag
```

---

### Step 2: Backend Setup (Python)

1. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

### Step 3: Frontend Setup (Next.js)

1. Open a new terminal in the `frontend` folder:
   ```bash
   cd frontend
   npm install
   ```

---

### Step 4: Configure Cloud Environment Variables (`.env`)

Create your `.env` file in the root `trust-aware-rag/` directory by copying `.env.example`:

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
# ---------- App ----------
APP_ENV=development
APP_DEBUG=true
APP_SECRET_KEY=generate-a-secure-random-key

# ---------- LLM Provider (Groq) ----------
GROQ_API_KEY=gsk_your_actual_groq_api_key
GROQ_MODEL=llama3-8b-8192
GROQ_BASE_URL=https://api.groq.com/openai/v1

# ---------- Embeddings ----------
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# ---------- Vector Store (FAISS) ----------
VECTOR_STORE_PROVIDER=faiss
FAISS_INDEX_PATH=./models/embeddings_cache/faiss_index

# ---------- Cloud PostgreSQL (Supabase) ----------
# Replace with your Supabase connection string:
DATABASE_URL=postgresql://postgres.your_project_id:your_password@aws-0-your-region.pooler.supabase.com:6543/postgres

# ---------- Cloud Redis (Upstash) ----------
# Replace with your Upstash TLS connection string:
REDIS_URL=rediss://default:your_upstash_token@your-upstash-host.upstash.io:6379/0

# ---------- Trust Policy Thresholds ----------
TRUST_THRESHOLD_HIGH=0.75
TRUST_THRESHOLD_LOW=0.5
TRUST_MODEL_PATH=./models/trust_classifier/trust_xgb.json

# ---------- Frontend API Target ----------
NEXT_PUBLIC_API_URL=http://localhost:8000
LOG_LEVEL=INFO
```

---

### Step 5: Run Database Migrations (Supabase)

Initialize the database schema (`trust_score_logs`, `documents`, `document_chunks`):

- **Windows (PowerShell)**:
  ```powershell
  $env:PYTHONPATH="backend"
  alembic upgrade head
  ```
- **Linux / macOS**:
  ```bash
  PYTHONPATH=backend alembic upgrade head
  ```

---

### Step 6: Start the Application

1. **Start the FastAPI Backend** (in your Python terminal):
   - **Windows (PowerShell)**:
     ```powershell
     $env:PYTHONPATH="backend"
     uvicorn app.main:app --reload --port 8000
     ```
   - **Linux / macOS**:
     ```bash
     PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
     ```
   * Swagger OpenAPI docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**

2. **Start the Next.js Frontend** (in your frontend terminal):
   ```bash
   cd frontend
   npm run dev
   ```
   * Web Application: **[http://localhost:3000](http://localhost:3000)**

---

## Supabase & Upstash Configuration Guide

### 1. Supabase PostgreSQL
1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Project Settings** → **Database** → **Connection String** → **URI**.
3. Select either the **Session pooler** (port `5432`) or **Transaction pooler** (port `6543`).
4. Copy the connection string into `DATABASE_URL` in `.env`.
   * *Note:* The backend automatically configures `asyncpg` async driver adapters.

### 2. Upstash Redis
1. Create a Redis database at [upstash.com](https://upstash.com).
2. Under the **Connect** tab, copy the **`rediss://`** connection string (TLS enabled).
3. Paste it into `REDIS_URL` in `.env`.

---

## Verification & Testing Workflows

### Test 1: Upload a PDF / Document
1. Navigate to **[http://localhost:3000/admin](http://localhost:3000/admin)**.
2. Drag and drop any PDF, DOCX, CSV, JSON, or TXT file into the upload zone.
3. Click **Upload & Index**.
4. Observe the file appearing in the **Knowledge Sources** table with its chunk count and status `Indexed`.

### Test 2: Ingest a Website URL
1. On the Admin page, enter a documentation URL (e.g. `https://example.com`).
2. Click **Add URL & Index**.
3. The page text is fetched, cleaned, chunked, and indexed into FAISS and Supabase.

### Test 3: Chat with Verified Evidence
1. Navigate to **[http://localhost:3000/chat](http://localhost:3000/chat)**.
2. Ask a question regarding the uploaded document or website.
3. Observe:
   - The multi-agent progress status (`Retrieving` → `Critiquing` → `Scoring` → `Synthesizing` → `Verifying`).
   - The verified answer, trust score gauge, and citation links.

### Test 4: Evidence & Contradiction Viewer
1. Click **View Evidence** on any citation or navigate to **[http://localhost:3000/evidence](http://localhost:3000/evidence)**.
2. Inspect individual chunk relevance, critic labels (`support` / `contradict`), and contradiction reports.

### Test 5: Automated Integration Tests
Run the backend test suite:

```bash
.venv\Scripts\pytest tests/integration/test_documents.py -v
```

---

## Safe GitHub Publishing

Your `.gitignore` is pre-configured to strictly exclude all local secrets (`.env`), virtual environments (`.venv/`), and compiled assets.

To push safely to GitHub:

```bash
git add .
git commit -m "Feature: Add dynamic knowledge ingestion and multi-format document support"
git push origin main
```

---

## License

MIT License. Designed for verifiable, hallucination-resistant LLM applications.
