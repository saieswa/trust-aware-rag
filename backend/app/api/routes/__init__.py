"""
Top-level API router.

Every route module (health.py now; chat.py, evidence.py, admin.py, etc. in
later steps) gets included here exactly once. app/main.py then mounts this
single `api_router` under the versioned prefix (`/api/v1`), so individual
route files never need to know or hard-code their own prefix.
"""

from fastapi import APIRouter

from app.api.routes import agents, documents, health, retrieval, trust

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(retrieval.router)
api_router.include_router(documents.router)
api_router.include_router(agents.router)
api_router.include_router(trust.router)

# Future route modules will be added the same way, e.g.:
# from app.api.routes import chat, evidence, admin
# api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
# api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence"])
# api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
