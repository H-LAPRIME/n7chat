from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from backend.agents.orchestrator import run_orchestrator_agent
from backend.agents.pdf_agent import run_pdf_agent
from backend.agents.rag_agent import run_rag_agent
from backend.agents.sql_agent import run_sql_agent


Intent = Literal[
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "general",
]

SQL_INTENTS = {"emploi_du_temps", "notes", "absence"}
RAG_INTENTS = {"courses"}
PDF_INTENTS = {"pdf_report"}


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, Any]]
    user: dict[str, Any]
    intent: Intent
    route_reason: str
    response: str
    data: dict[str, Any]
    sources: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    error: str | None


async def orchestrator_node(state: AgentState) -> AgentState:
    decision = await run_orchestrator_agent(
        message=state.get("message", ""),
        history=state.get("history", []),
        user=state.get("user", {}),
    )
    return {
        **state,
        "intent": decision["intent"],
        "route_reason": decision.get("reason", ""),
    }


async def sql_node(state: AgentState) -> AgentState:
    result = await run_sql_agent(
        message=state.get("message", ""),
        intent=state.get("intent", "general"),
        user=state.get("user", {}),
    )
    return {
        **state,
        "response": result.get("answer", ""),
        "data": result.get("data", {}),
        "error": result.get("error"),
    }


async def rag_node(state: AgentState) -> AgentState:
    result = await run_rag_agent(
        message=state.get("message", ""),
        user=state.get("user", {}),
    )
    return {
        **state,
        "response": result.get("answer", ""),
        "data": {"rag_context": result.get("context", "")},
        "sources": result.get("sources", []),
        "error": result.get("error"),
    }


async def pdf_node(state: AgentState) -> AgentState:
    result = await run_pdf_agent(
        message=state.get("message", ""),
        user=state.get("user", {}),
    )
    artifact = result.get("artifact")
    return {
        **state,
        "response": result.get("answer", ""),
        "data": result.get("data", {}),
        "artifacts": [artifact] if artifact else [],
        "error": result.get("error"),
    }


async def general_node(state: AgentState) -> AgentState:
    return {
        **state,
        "response": (
            "Je peux t'aider avec les notes, absences, emploi du temps, cours, "
            "documents indexes et generation de PDF. Peux-tu preciser ta demande ?"
        ),
        "data": {},
        "error": None,
    }


def route_from_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent in SQL_INTENTS:
        return "sql"
    if intent in RAG_INTENTS:
        return "rag"
    if intent in PDF_INTENTS:
        return "pdf"
    return "general"


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("sql", sql_node)
    builder.add_node("rag", rag_node)
    builder.add_node("pdf", pdf_node)
    builder.add_node("general", general_node)

    builder.set_entry_point("orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_from_intent,
        {
            "sql": "sql",
            "rag": "rag",
            "pdf": "pdf",
            "general": "general",
        },
    )
    for node in ("sql", "rag", "pdf", "general"):
        builder.add_edge(node, END)
    return builder.compile()


graph = build_graph()


async def run_agent(
    message: str,
    history: list[dict[str, Any]] | None,
    user: dict[str, Any] | None,
) -> AsyncGenerator[str, None]:
    state: AgentState = {
        "message": message,
        "history": history or [],
        "user": user or {},
        "intent": "general",
        "route_reason": "",
        "response": "",
        "data": {},
        "sources": [],
        "artifacts": [],
        "error": None,
    }

    final_state = await graph.ainvoke(state)
    yield final_state.get("response", "")
