"""
backend/config.py
─────────────────
Centralised configuration loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


class Config:
    # ── Flask ──────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev_secret_change_me")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"
    PORT: int = int(os.getenv("PORT", 5000))

    # ── JWT ───────────────────────────────────────────────────
    JWT_ACCESS_EXPIRES: int = int(os.getenv("JWT_ACCESS_EXPIRES", 3600))
    JWT_REFRESH_EXPIRES: int = int(os.getenv("JWT_REFRESH_EXPIRES", 604800))

    # ── LLM API Keys ──────────────────────────────────────────
    GROQ_API_KEY_ORCHESTRATOR: str = os.getenv("GROQ_API_KEY_ORCHESTRATOR", "")
    GROQ_API_KEY_FAQ: str = os.getenv("GROQ_API_KEY_FAQ", "")
    GROQ_API_KEY_RAG: str = os.getenv("GROQ_API_KEY_RAG", "")
    GROQ_API_KEY_ACTION: str = os.getenv("GROQ_API_KEY_ACTION", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # ── Databases ─────────────────────────────────────────────
    STRUCTURE_DATABASE_URL: str = (
        os.getenv("STRUCTURE_DATABASE_URL")
        or os.getenv("SUPABASE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or ""
    )
    VECTOR_DATABASE_URL: str = os.getenv("VECTOR_DATABASE_URL") or os.getenv("POSTGRES_URL", "")
    POSTGRES_URL: str = VECTOR_DATABASE_URL

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── Storage ───────────────────────────────────────────────
    DOCS_PATH: str = os.getenv("DOCS_PATH", "../storage/documents")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "documents")
    SUPABASE_DOCUMENTS_BUCKET: str = os.getenv("SUPABASE_DOCUMENTS_BUCKET", SUPABASE_BUCKET)
    SUPABASE_PROFILES_BUCKET: str = os.getenv("SUPABASE_PROFILES_BUCKET", "profiles")
    SUPABASE_LOGOS_BUCKET: str = os.getenv("SUPABASE_LOGOS_BUCKET", "logos")

    # ── CORS ──────────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ── Rate Limiting ─────────────────────────────────────────
    RATELIMIT_DEFAULT: str = "60 per minute"
    RATELIMIT_STORAGE_URL: str = os.getenv("REDIS_URL", "memory://")

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = STRUCTURE_DATABASE_URL or VECTOR_DATABASE_URL or "sqlite:///n7chat.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Mail / SMTP ───────────────────────────────────────────
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.getenv("MAIL_DEFAULT_SENDER", "noreply@n7chat.com")
