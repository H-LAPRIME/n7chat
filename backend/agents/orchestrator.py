"""Orchestrator agent.

Thin async wrapper around the LLM task in ``backend.tasks.orchestrator_llm_task``.
Responsible for:
  - Building the async entry-point (``classify_intent`` / ``run_orchestrator_agent``).
  - Re-exporting shared types so the rest of the codebase (graph, routers) can
    import from a single known location.

All prompt constants, Mistral client logic, and fallback helpers live in
``backend.tasks.orchestrator_llm_task``.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from backend.tasks import orchestrator_llm_task as _task
from backend.tasks.orchestrator_llm_task import (
    Intent,
    OrchestratorDecision,
    STATIC_CAPABILITIES,
    VALID_INTENTS,
    classify_intent_task,
    _fallback_intent,
    _fallback_plan,
    _normalize_plan,
    _parse_decision,
    _tool_invoke,
)


@lru_cache(maxsize=1)
def get_orchestrator_context() -> dict[str, Any]:
    """Return schema/capability context used by the orchestrator prompt."""
    original_tool_invoke = _task._tool_invoke
    _task._tool_invoke = _tool_invoke
    try:
        _task.get_orchestrator_context.cache_clear()
        return _task.get_orchestrator_context()
    finally:
        _task._tool_invoke = original_tool_invoke


def classify_intent_sync(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> OrchestratorDecision:
    """Synchronous intent classification, delegated to the task layer."""
    return classify_intent_task(message, history, user_role)


async def classify_intent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> OrchestratorDecision:
    return await asyncio.to_thread(classify_intent_task, message, history, user_role)


async def run_orchestrator_agent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user: dict[str, Any] | None = None,
) -> OrchestratorDecision:
    return await classify_intent(
        message=message,
        history=history,
        user_role=(user or {}).get("role"),
    )
