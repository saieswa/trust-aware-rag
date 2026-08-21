# Installation Guide

This guide sets up the project **structure and environment only** — no
agent logic exists yet at this step, so these instructions get you to a
point where the empty scaffold runs cleanly end-to-end (frontend loads,
backend health-checks, databases are reachable).

---

## Prerequisites

| Tool | Minimum version | Check with |
|---|---|---|
| Docker | 24.x | `docker --version` |
| Docker Compose | v2 (bundled with Docker Desktop) | `docker compose version` |
| Node.js | 20.x (only needed for local, non-Docker frontend dev) | `node --version` |
| Python | 3.11 (only needed for local, non-Docker backend dev) | `python3 --version` |
| Git | any recent version | `git --version` |

---

## Option A — Run everything with Docker (recommended)

1. **Clone / enter the project folder**
   ```bash
   cd trust-aware-rag
   ```

2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in:
   - `GROQ_API_KEY` — required for LLM calls.
   - `HUGGINGFACE_API_TOKEN` — optional, only needed for gated HF models.
   - Leave `POSTGRES_*`, `REDIS_*` as-is for local development.

3. **Build and start all services**
   ```bash
   docker compose build
   docker compose up
   ```

4. **Verify services are up**
   - Frontend: http://localhost:3000
   - Backend docs (FastAPI auto-generated): http://localhost:8000/docs
   - Nginx (unified entrypoint): http://localhost:80
   - PostgreSQL: `localhost:5432` (user/password from `.env`)
   - Redis: `localhost:6379`

5. **Stop everything**
   ```bash
   docker compose down
   ```
   Add `-v` to also remove database volumes (destructive):
   ```bash
   docker compose down -v
   ```

---

## Option B — Run services locally (no Docker), for active development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

You'll also need PostgreSQL and Redis running locally (or via Docker just
for those two services):
```bash
docker compose up postgres redis
```

Then run the API (once `backend/app/main.py` exists in a later step):
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000 and will call the
backend at the URL set in `NEXT_PUBLIC_API_URL` (`frontend/.env.local` or
inherited from the root `.env`).

---

## Environment variables reference

All variables are documented inline in `.env.example`. Key ones to double-check
before running anything:

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Powers all LLM-driven agents |
| `EMBEDDING_MODEL_NAME` | HuggingFace model used to embed text for FAISS |
| `DATABASE_URL` | Full PostgreSQL connection string used by SQLAlchemy |
| `REDIS_URL` | Redis connection string used for caching |
| `TRUST_THRESHOLD_HIGH` / `TRUST_THRESHOLD_LOW` | Decision thresholds for the trust score policy |
| `NEXT_PUBLIC_API_URL` | URL the frontend uses to reach the backend |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose build` fails on `faiss-cpu` | Missing build tools in base image | Already handled via `build-essential` in `Dockerfile.backend`; ensure Docker has enough memory (4GB+) |
| Backend can't reach Postgres | Wrong host in `DATABASE_URL` | Inside Docker, host must be the service name `postgres`, not `localhost` |
| Frontend shows CORS errors | Backend CORS not yet configured | Expected at this stage — CORS middleware is added when `backend/app/main.py` is implemented |
| `npm install` errors on lockfile | No `package-lock.json` committed yet | Run `npm install` once locally to generate it, then commit |

---

## What's NOT included yet

This step only creates structure. The following are intentionally empty and
will be filled in subsequent steps:
- Agent logic in `agents/*`
- FastAPI routes in `backend/app/api/routes/*`
- Trust scoring logic in `trust/*`
- Retrieval/embedding logic in `retrieval/*`
- Database models/migrations in `database/postgres/*`
- Frontend pages/components in `frontend/src/app/*` and `frontend/src/components/*`

Running the Docker stack now will start empty containers/services — that's
expected and confirms your environment is wired correctly before real logic
is added.
