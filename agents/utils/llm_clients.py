"""
agents/utils/llm_clients.py
─────────────────────────────
Lazy-initialised LLM client instances.
Each client is only created once and reused across the process.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


# ── LangChain wrappers (for LangGraph nodes) ──────────────────

@lru_cache(maxsize=1)
def get_langchain_groq_orchestrator():
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY_ORCHESTRATOR", ""),
        model="llama3-70b-8192",
        temperature=0.2,
    )

@lru_cache(maxsize=1)
def get_langchain_groq_faq():
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY_FAQ", ""),
        model="llama3-70b-8192",
        temperature=0.2,
    )

@lru_cache(maxsize=1)
def get_langchain_openrouter_rag():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        model="deepseek/deepseek-chat:free",
        temperature=0.2,
    )

@lru_cache(maxsize=1)
def get_langchain_groq_action():
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY_ACTION", ""),
        model="llama3-70b-8192",
        temperature=0.2,
    )


@lru_cache(maxsize=1)
def get_langchain_gemini():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.3,
    )
