from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from backend.agents.orchestrator import run_orchestrator_agent
from backend.agents.pdf_agent import run_pdf_agent
from backend.agents.rag_agent import run_rag_agent
from backend.agents.sql_agent import run_sql_agent
from backend.agents.general_agent import run_general_agent


Intent = Literal[
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "profile",
    "general",
]

SQL_INTENTS = {"emploi_du_temps", "notes", "absence", "profile"}
RAG_INTENTS = {"courses"}
PDF_INTENTS = {"pdf_report"}


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, Any]]
    user: dict[str, Any]
    intent: Intent
    route_reason: str
    plan: list[dict[str, str]]
    executed_agents: list[str]
    response: str
    data: dict[str, Any]
    sources: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    suggest_pdf: bool   # orchestrator sets True → append PDF offer to response
    error: str | None


def _default_plan(intent: str) -> list[dict[str, str]]:
    if intent in SQL_INTENTS:
        return [{"agent": "sql", "purpose": f"Fetch structured data for {intent}."}]
    if intent in RAG_INTENTS:
        return [{"agent": "rag", "purpose": "Search indexed documents."}]
    if intent in PDF_INTENTS:
        return [
            {"agent": "sql", "purpose": "Collect profile, notes, and absences."},
            {"agent": "pdf", "purpose": "Generate the requested PDF report."},
        ]
    return [{"agent": "general", "purpose": "Answer or ask for clarification."}]


def _next_agent(state: AgentState) -> str:
    executed = state.get("executed_agents", [])
    plan = state.get("plan") or _default_plan(state.get("intent", "general"))
    for step in plan:
        agent = step.get("agent", "general")
        if agent not in executed:
            return agent
    return "done"


def route_from_intent(state: AgentState) -> str:
    return _next_agent(state)


async def orchestrator_node(state: AgentState) -> AgentState:
    decision = await run_orchestrator_agent(
        message=state.get("message", ""),
        history=state.get("history", []),
        user=state.get("user", {}),
    )
    intent = decision["intent"]
    plan = decision.get("plan") or _default_plan(intent)
    return {
        **state,
        "intent": intent,
        "route_reason": decision.get("reason", ""),
        "plan": plan,
        "suggest_pdf": bool(decision.get("suggest_pdf", False)),
        "executed_agents": [],
    }


async def sql_node(state: AgentState) -> AgentState:
    result = await run_sql_agent(
        message=state.get("message", ""),
        intent=state.get("intent", "general"),
        user=state.get("user", {}),
    )
    data = dict(state.get("data", {}))
    data["sql"] = result.get("data", {})
    return {
        **state,
        "response": result.get("answer", ""),
        "data": data,
        "error": result.get("error"),
        "executed_agents": [*state.get("executed_agents", []), "sql"],
    }


async def rag_node(state: AgentState) -> AgentState:
    result = await run_rag_agent(
        message=state.get("message", ""),
        user=state.get("user", {}),
    )
    data = dict(state.get("data", {}))
    data["rag"] = {"context": result.get("context", "")}
    return {
        **state,
        "response": result.get("answer", ""),
        "data": data,
        "sources": [*state.get("sources", []), *(result.get("sources", []) or [])],
        "error": result.get("error"),
        "executed_agents": [*state.get("executed_agents", []), "rag"],
    }


async def hybrid_node(state: AgentState) -> AgentState:
    sql_result, rag_result = await asyncio.gather(
        run_sql_agent(
            message=state.get("message", ""),
            intent=state.get("intent", "general"),
            user=state.get("user", {}),
        ),
        run_rag_agent(
            message=state.get("message", ""),
            user=state.get("user", {}),
        ),
    )
    data = dict(state.get("data", {}))
    data["sql"] = sql_result.get("data", {})
    data["rag"] = {"context": rag_result.get("context", "")}
    sql_answer = (sql_result.get("answer") or "").strip()
    rag_answer = (rag_result.get("answer") or "").strip()
    response = "\n\n---\n\n".join(part for part in [sql_answer, rag_answer] if part)
    return {
        **state,
        "response": response,
        "data": data,
        "sources": [*state.get("sources", []), *(rag_result.get("sources", []) or [])],
        "error": sql_result.get("error") or rag_result.get("error"),
        "executed_agents": [*state.get("executed_agents", []), "hybrid"],
    }


async def pdf_node(state: AgentState) -> AgentState:
    result = await run_pdf_agent(
        message=state.get("message", ""),
        user=state.get("user", {}),
        data_context=state.get("data", {}),
    )
    artifact = result.get("artifact")
    data = dict(state.get("data", {}))
    data["pdf"] = result.get("data", {})
    return {
        **state,
        "response": result.get("answer", ""),
        "data": data,
        "artifacts": [*state.get("artifacts", []), *([artifact] if artifact else [])],
        "error": result.get("error"),
        "executed_agents": [*state.get("executed_agents", []), "pdf"],
    }


async def general_node(state: AgentState) -> AgentState:
    result = await run_general_agent(
        message=state.get("message", ""),
        history=state.get("history", []),
        user=state.get("user", {}),
    )
    return {
        **state,
        "response": result.get("answer", ""),
        "data": state.get("data", {}),
        "error": result.get("error"),
        "executed_agents": [*state.get("executed_agents", []), "general"],
    }


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("sql", sql_node)
    builder.add_node("rag", rag_node)
    builder.add_node("hybrid", hybrid_node)
    builder.add_node("pdf", pdf_node)
    builder.add_node("general", general_node)

    builder.set_entry_point("orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_from_intent,
        {
            "sql": "sql",
            "rag": "rag",
            "hybrid": "hybrid",
            "pdf": "pdf",
            "general": "general",
            "done": END,
        },
    )
    for node in ("sql", "rag", "hybrid", "pdf", "general"):
        builder.add_conditional_edges(
            node,
            route_from_intent,
            {
                "sql": "sql",
                "rag": "rag",
                "hybrid": "hybrid",
                "pdf": "pdf",
                "general": "general",
                "done": END,
            },
        )
    return builder.compile()


graph = build_graph()


# ---------------------------------------------------------------------------
# PDF-offer sentence (appended after normal answer when suggest_pdf=True)
# ---------------------------------------------------------------------------

_PDF_OFFER = (
    "\n\n---\n"
    "📎 Souhaitez-vous que je génère un **rapport PDF** à partir de ces données ? "
    "Répondez simplement *oui* ou *génère le rapport* et je m'en occupe."
)


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
        "plan": [],
        "executed_agents": [],
        "response": "",
        "data": {},
        "sources": [],
        "artifacts": [],
        "suggest_pdf": False,
        "error": None,
    }

    final_state = await graph.ainvoke(state)
    response = final_state.get("response", "")

    # Append PDF offer when orchestrator signalled it and we haven’t generated
    # a PDF already (artifacts list would be non-empty in that case).
    if final_state.get("suggest_pdf") and not final_state.get("artifacts"):
        response = response + _PDF_OFFER

    yield response
