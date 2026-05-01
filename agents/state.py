"""
agents/state.py
────────────────
Shared AgentState TypedDict used across all LangGraph nodes.
"""

from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Core ──────────────────────────────────────────────────
    session_id: str
    user_id: str
    role: str                           # "student" | "admin"
    user_message: str
    intent: str                         # classified intent label

    # ── Memory ────────────────────────────────────────────────
    short_term_history: list[dict]      # last N conversation turns
    long_term_summary: str              # compressed user profile/history

    # ── Agent Results ─────────────────────────────────────────
    agent_used: str
    response: str
    sources: list[dict]                 # [{"doc": str, "page": int}, ...]

    # ── LangGraph messages (required by add_messages reducer) ─
    messages: Annotated[list, add_messages]
