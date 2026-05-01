"""
agents/faq_agent.py
─────────────────────
FAQ Agent — GROQ LLM + Redis cache
Answers frequently asked questions. Cache-first strategy.
"""

import hashlib
import os

import redis

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_groq_faq

_redis_client: redis.Redis | None = None
FAQ_TTL = 60 * 60 * 24  # 24 hours


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return _redis_client


def _cache_key(text: str) -> str:
    return "faq:" + hashlib.md5(text.lower().strip().encode()).hexdigest()


def faq_node(state: AgentState) -> AgentState:
    question = state["user_message"]
    key = _cache_key(question)

    # ── Cache hit ──────────────────────────────────────────────
    try:
        cached = _get_redis().get(key)
        if cached:
            return {
                **state,
                "agent_used": "faq (cache)",
                "response": cached.decode("utf-8"),
            }
    except Exception:
        pass  # Redis unavailable — fall through to LLM

    # ── LLM answer ────────────────────────────────────────────
    llm = get_langchain_groq_faq()
    response = llm.invoke([{"role": "user", "content": question}])
    answer = response.content.strip()

    # ── Store in cache ─────────────────────────────────────────
    try:
        _get_redis().setex(key, FAQ_TTL, answer)
    except Exception:
        pass

    return {
        **state,
        "agent_used": "faq",
        "response": answer,
    }
