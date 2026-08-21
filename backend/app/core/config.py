"""
Centralized application configuration.

Every setting the app needs is declared here as a typed field, and pydantic-settings
loads values from environment variables (or a `.env` file in development) and
validates them at startup. This means a missing or malformed environment
variable fails fast, with a clear error, instead of crashing later inside
some unrelated request handler.

Usage elsewhere in the app:

    from app.core.config import get_settings
    settings = get_settings()
    settings.DATABASE_URL
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------- App ----------
    APP_NAME: str = "Trust-Aware Multi-Agent RAG API"
    APP_ENV: str = Field(default="development")  # development | staging | production
    APP_DEBUG: bool = Field(default=True)
    APP_SECRET_KEY: str = Field(default="change-me-in-production")
    APP_VERSION: str = "0.1.0"

    # ---------- API ----------
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # ---------- LLM provider: Groq Cloud ----------
    # Groq Cloud's API is deliberately OpenAI-compatible (same
    # request/response shape), so agents/llm_client.py reuses
    # langchain_openai.ChatOpenAI pointed at GROQ_BASE_URL instead of
    # needing a separate LangChain integration package.
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama3-8b-8192")
    GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1")
    HUGGINGFACE_API_TOKEN: str = Field(default="")
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # ---------- Vector store (referenced by config only, not used yet) ----------
    VECTOR_STORE_PROVIDER: str = Field(default="faiss")
    FAISS_INDEX_PATH: str = Field(default="./models/embeddings_cache/faiss_index")

    # ---------- PostgreSQL ----------
    POSTGRES_USER: str = Field(default="trag_user")
    POSTGRES_PASSWORD: str = Field(default="trag_password")
    POSTGRES_DB: str = Field(default="trust_aware_rag")
    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: str = Field(default="")

    # ---------- Redis ----------
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_URL: str = Field(default="")
    REDIS_CACHE_TTL_SECONDS: int = Field(default=300)

    # ---------- Trust model (referenced by config only, not used yet) ----------
    TRUST_THRESHOLD_HIGH: float = Field(default=0.75)
    TRUST_THRESHOLD_LOW: float = Field(default=0.5)
    TRUST_MODEL_PATH: str = Field(default="./models/trust_classifier/trust_xgb.json")

    # ---------- Logging ----------
    LOG_LEVEL: str = Field(default="INFO")
    LOG_JSON: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str, info) -> str:
        """Build DATABASE_URL from parts if not explicitly provided, and ensure async driver prefix."""
        if v:
            # Automap standard Postgres URIs (like those from Supabase) to use asyncpg
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            return v
        data = info.data
        user = data.get("POSTGRES_USER", "trag_user")
        password = data.get("POSTGRES_PASSWORD", "trag_password")
        host = data.get("POSTGRES_HOST", "postgres")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "trust_aware_rag")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, v: str, info) -> str:
        """Build REDIS_URL from parts if not explicitly provided."""
        if v:
            return v
        data = info.data
        host = data.get("REDIS_HOST", "redis")
        port = data.get("REDIS_PORT", 6379)
        return f"redis://{host}:{port}/0"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    lru_cache ensures the .env file and environment are only parsed once per
    process, and every part of the app shares the exact same settings object.
    """
    return Settings()
