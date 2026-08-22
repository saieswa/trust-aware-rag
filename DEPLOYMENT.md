# Deployment Guide

This guide covers deploying the **Trust-Aware Multi-Agent RAG** stack to production environments.

---

## Production Cloud Architecture

```
                       ┌──────────────────────┐
                       │  Users / Browsers    │
                       └──────────┬───────────┘
                                  │ HTTPS
                                  ▼
                       ┌──────────────────────┐
                       │ Nginx Reverse Proxy  │
                       └─────┬──────────┬─────┘
                             │          │
                 / (Next.js) │          │ /api/v1 (FastAPI)
                             ▼          ▼
                     ┌───────────┐  ┌───────────┐
                     │ Frontend  │  │  Backend  │
                     │ Next.js   │  │  FastAPI  │
                     └───────────┘  └─────┬─────┘
                                          │
                     ┌────────────────────┼────────────────────┐
                     │                    │                    │
                     ▼                    ▼                    ▼
             ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
             │   Supabase    │    │    Upstash    │    │  Groq Cloud   │
             │  PostgreSQL   │    │     Redis     │    │   LLM API     │
             └───────────────┘    └───────────────┘    └───────────────┘
```

---

## 1. Cloud Managed Services Setup

1. **Supabase PostgreSQL**:
   - Create a project at [supabase.com](https://supabase.com).
   - Obtain your database connection string in URI format (`postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres`).
   - Set as `DATABASE_URL` with `postgresql+asyncpg://` driver prefix.

2. **Upstash Redis**:
   - Create a serverless Redis database at [upstash.com](https://upstash.com).
   - Copy the TLS connection URL (`rediss://default:[TOKEN]@[ENDPOINT].upstash.io:6379`).
   - Set as `REDIS_URL`.

3. **Groq Cloud**:
   - Create an API key at [console.groq.com](https://console.groq.com).
   - Set as `GROQ_API_KEY`.

---

## 2. Containerized Deployment (Docker)

To deploy the Application containers (Backend, Frontend, Nginx) connected to cloud Supabase and Upstash:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 3. Serverless / PaaS Deployments

- **Frontend**: Deploy `frontend/` to **Vercel** or **Cloudflare Pages** with `NEXT_PUBLIC_API_URL` set to your backend domain.
- **Backend**: Deploy `backend/` as a Docker container to **Railway**, **Render**, **Fly.io**, **AWS ECS**, or **Google Cloud Run** with environment variables configured in their secrets dashboard.
