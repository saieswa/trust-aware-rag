# Installation & Setup Guide

This guide walks you through setting up and running **Trust-Aware Multi-Agent RAG** locally.

---

## Architecture Overview

- **Backend API**: FastAPI (Python 3.10+)
- **Frontend App**: Next.js 14 / React 18 / Tailwind CSS (Node.js 18+)
- **Multi-Agent Pipeline**: LangGraph (Retriever, Critic, Synthesizer, Verifier)
- **Vector Store**: FAISS with in-engine document filtering (`IDSelectorArray`)
- **Database**: Supabase PostgreSQL (managed cloud database)
- **Cache**: Upstash Redis (managed cloud Redis)
- **LLM Provider**: Groq Cloud (`llama3-8b-8192`)
- **Embeddings**: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`

---

## Prerequisites

| Requirement | Minimum version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend API and Multi-Agent Pipeline |
| Node.js | 18+ | Next.js Frontend Application |
| Supabase | Cloud project | PostgreSQL database for metadata and chunks |
| Upstash | Cloud database | Redis for document-scoped caching |
| Groq API Key | Cloud account | Fast LLM generation for Agents |

---

## 1. Configure Environment Variables

Create your `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Groq LLM
GROQ_API_KEY=gsk_your_groq_api_key_here

# Supabase PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# Upstash Redis
REDIS_URL=rediss://default:YOUR_TOKEN@YOUR_ENDPOINT.upstash.io:6379

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 2. Backend Setup & Run

1. **Create and activate a Python virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the FastAPI backend server**:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

4. **Verify Backend Health**:
   Open http://localhost:8000/api/v1/health in your browser. Both `postgresql` (Supabase) and `redis` (Upstash) should show `healthy: true`.

---

## 3. Frontend Setup & Run

1. **Install Node dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Next.js development server**:
   ```bash
   npm run dev
   ```

3. **Access the application**:
   Open http://localhost:3000 in your browser.

---

## 4. Run Automated Tests

To execute all unit and integration test suites:

```bash
pytest
```
