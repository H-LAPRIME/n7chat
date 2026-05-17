"""General Agent.

Thin async wrapper around the LLM task in ``backend.tasks.general_llm_task``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.tasks.general_llm_task import answer_general_task


async def run_general_agent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the general agent async."""
    return await asyncio.to_thread(
        answer_general_task,
        message,
        history,
        user,
    )
