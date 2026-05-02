"""
backend/config.py
─────────────────
Centralised configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


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
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ── Storage ───────────────────────────────────────────────
    DOCS_PATH: str = os.getenv("DOCS_PATH", "../storage/documents")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "documents")

    # ── CORS ──────────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ── Rate Limiting ─────────────────────────────────────────
    RATELIMIT_DEFAULT: str = "60 per minute"
    RATELIMIT_STORAGE_URL: str = os.getenv("REDIS_URL", "memory://")

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///n7chat.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Mail / SMTP ───────────────────────────────────────────
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS: bool = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.getenv("MAIL_DEFAULT_SENDER", "noreply@n7chat.com")
