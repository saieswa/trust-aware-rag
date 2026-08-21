# Deployment Guide

This guide covers local deployment (`docker compose up`), production
deployment, and the CI/CD pipeline that builds, tests, and publishes
images automatically.

---

## 1. Prerequisites

| Tool | Minimum version | Check with |
|---|---|---|
| Docker | 24.x | `docker --version` |
| Docker Compose | v2 (bundled with Docker Desktop, or `docker-compose-v2` on Linux) | `docker compose version` |
| Git | any recent version | `git --version` |

---

## 2. Local Deployment (`docker compose up`)

**Step 1 — Configure environment variables:**
```bash
cp .env.example .env
```
At minimum, set a real `GROQ_API_KEY` if you want the LLM-powered code
paths (query decomposition, contradiction detection, synthesis,
verification) to run instead of their heuristic fallbacks. Everything
works without one — you'll just see `"method": "heuristic"` in API
responses instead of `"llm"`.

**Step 2 — Build and start everything:**
```bash
docker compose build
docker compose up -d
```

This starts five containers: `postgres`, `redis`, `backend`, `frontend`,
`nginx` — wired together on an internal Docker network, with health
checks gating startup order (Postgres and Redis must report healthy
before the backend starts; the backend must report healthy before the
frontend and nginx start).

**Step 3 — Run database migrations** (one-time, or after any schema change):
```bash
docker compose exec backend alembic upgrade head
```

**Step 4 — Index the sample documents:**
```bash
curl -X POST http://localhost:8000/api/v1/retrieval/index \
  -H "Content-Type: application/json" \
  -d '{"directory": "data/sample_documents"}'
```

**Step 5 — Verify everything is healthy:**
```bash
docker compose ps
curl http://localhost:8000/api/v1/health
```

**Access points:**
- Frontend: http://localhost:3000 (or http://localhost:80 via nginx)
- API docs (Swagger): http://localhost:8000/docs
- Nginx (single entrypoint, routes both): http://localhost:80

**Stop everything:**
```bash
docker compose down          # keeps data volumes
docker compose down -v       # also destroys Postgres/Redis data — destructive
```

---

## 3. Production Deployment

Production uses the same `docker-compose.yml` with a `docker-compose.prod.yml`
overlay applied on top:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**What the production overlay changes:**
- Postgres and Redis no longer publish ports to the host — only reachable
  by other containers on the internal network (the default file exposes
  them for local `psql`/`redis-cli` debugging; production has no reason
  to accept external connections to the database directly).
- `restart: always` instead of `unless-stopped` — recovers from a host
  reboot without manual intervention.
- Resource limits on every container, so one runaway process can't
  starve the others on a shared host.
- Backend switches to `APP_ENV=production`, `LOG_JSON=true` (structured
  logs for aggregators like Datadog/ELK instead of colored dev output).

**Before deploying to production:**
1. Copy `.env.production.example` to `.env` on the production host and
   fill in **real, strong secrets** — `APP_SECRET_KEY`,
   `POSTGRES_PASSWORD`, `GROQ_API_KEY`. Never commit this file.
2. Set `NEXT_PUBLIC_API_URL` to your real public backend URL, not
   `localhost`.
3. Consider a managed PostgreSQL (RDS, Cloud SQL, etc.) instead of the
   bundled container for real production data durability and backups.
4. Put a real TLS certificate in front of nginx (see Section 5 below) —
   the bundled `nginx.conf` serves plain HTTP by default.

---

## 4. CI/CD Pipeline

Two GitHub Actions workflows, `.github/workflows/ci.yml` and `cd.yml`:

### CI (`ci.yml`) — runs on every push and PR
- **Backend:** `ruff` lint, byte-compile check, `pytest` (skips gracefully
  if no tests exist yet under `backend/tests/`).
- **Frontend:** `next lint`, `tsc --noEmit` type-check, production build.
- **Dockerfile lint:** `hadolint` against both Dockerfiles.

Fast (a couple of minutes), no Docker image builds — this is the quick
feedback loop for every commit.

### CD (`cd.yml`) — runs on every push to `main`
This is the step that actually proves the stack works, not just that it
*looks* correct:
1. Builds every image with `docker compose build`.
2. Starts the full stack with `docker compose up -d`.
3. **Waits for every container's healthcheck to report healthy** (up to
   3 minutes) before proceeding.
4. Runs the real Alembic migration against the real (containerized)
   Postgres.
5. Hits real endpoints and asserts on the real response: `/api/v1/health`
   returns `status: ok`, `/api/v1/retrieval/index` actually indexes
   chunks, `/api/v1/trust/score` returns a valid trust score, the
   frontend returns HTTP 200, and nginx correctly proxies both.
6. Dumps all container logs if anything fails, for debugging.
7. Tears the stack down.
8. **Only if every smoke test passed**, logs into GitHub Container
   Registry and pushes both images, tagged `latest` and with the commit
   SHA.

This is deliberately the mechanism that validates `docker compose up`
end-to-end — see the honesty note below for why.

### Using the published images

Once `cd.yml` has run successfully at least once, images are available at:
```
ghcr.io/<your-github-username>/<repo-name>/backend:latest
ghcr.io/<your-github-username>/<repo-name>/frontend:latest
```

---

## 5. Adding TLS/SSL (recommended for any real production deployment)

The bundled `deployment/nginx/nginx.conf` serves plain HTTP. For a real
public deployment, the standard approach is:

1. Get a certificate (e.g. via [Certbot](https://certbot.eff.org/) /
   Let's Encrypt, or your cloud provider's managed certificate).
2. Add a `listen 443 ssl;` server block to `nginx.conf` referencing your
   certificate and key paths, and mount them into the nginx container as
   read-only volumes.
3. Redirect port 80 to 443 with a small `return 301 https://$host$request_uri;`
   server block.

This project ships the HTTP-only config since certificate provisioning
is environment-specific (differs by cloud provider, domain registrar,
and whether you're behind an existing load balancer) — the guide above
covers the standard shape without prescribing a provider.

---

## 6. Monitoring & Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `backend` container unhealthy | Can't reach Postgres/Redis | Check `docker compose logs backend`; confirm `postgres`/`redis` are healthy first |
| `docker compose up` hangs waiting on a healthcheck | A dependency never became healthy | `docker compose ps` to see which; `docker compose logs <service>` for why |
| Frontend shows API errors | `NEXT_PUBLIC_API_URL` wrong, or backend actually down | Check the env var matches where the backend is really reachable from the browser |
| `alembic upgrade head` fails | Migration already applied, or DB not reachable | `docker compose exec backend alembic current` to check current revision |
| Nginx 502 | Backend/frontend container not yet healthy | Nginx's `depends_on: condition: service_healthy` should prevent this at startup — check if a container crashed after starting |

**Viewing logs:**
```bash
docker compose logs -f backend       # follow one service
docker compose logs --tail=200       # last 200 lines, all services
```

**Checking health directly:**
```bash
docker compose ps                          # shows health status per container
curl http://localhost:8000/api/v1/health   # backend's own dependency check
```

---

## 7. Honesty Note: What Was (and Wasn't) Verified Where

This project was developed in a sandboxed environment where Docker Hub
(`registry-1.docker.io`) is not reachable — the same class of network
restriction that blocked HuggingFace and OpenAI earlier in this project.
Here's exactly what that meant for verifying this deployment setup, and
what to expect on your own machine or in CI:

- **`docker compose config` and `docker compose -f ... -f ... config`**
  were run for real, against the actual Docker Compose v2 parser — both
  files are confirmed structurally valid, with variable interpolation
  and multi-file merging both checked.
- **`docker build` was run for real** against `Dockerfile.backend` — it
  parsed the Dockerfile completely and began executing the defined
  steps (`Step 1/25`), failing only at the `FROM python:3.11-slim` base
  image pull due to the registry block. This confirms the Dockerfile
  itself is syntactically correct; only the image pull was unavailable
  here.
- **`nginx.conf` was validated with the real nginx binary** (`nginx -t`),
  with the Docker Compose service hostnames swapped for a resolvable
  placeholder to isolate syntax validation from DNS resolution (which
  only works inside the actual Docker network) — syntax confirmed valid.
- **The backend and frontend applications themselves** were extensively
  built and run natively (outside Docker) throughout this project's
  development, including real PostgreSQL and Redis instances, real
  Alembic migrations, and a real `npm run build` producing the exact
  standalone output this Dockerfile copies — see the project's earlier
  steps for that verification history.
- **What genuinely could not be verified here:** an actual end-to-end
  `docker compose up` with real pulled images. This is exactly what
  `cd.yml`'s smoke-test job is for — it runs on GitHub's own runners,
  which have full registry access, and will give you a real pass/fail
  signal the first time you push to `main`.

If `docker compose up` doesn't work cleanly the first time you run it
outside this sandbox, that's a genuine bug worth reporting — everything
short of the actual image pull has been checked as thoroughly as this
environment allowed.
