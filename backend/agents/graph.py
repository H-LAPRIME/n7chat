from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from backend.agents.orchestrator import run_orchestrator_agent
from backend.agents.rag_agent import run_rag_agent
from backend.agents.sql_agent import run_sql_agent
from backend.agents.general_agent import run_general_agent
from backend.flows.pdf_flow import build_pdf_report_flow


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
    if intent == "emploi_du_temps":
        return [
            {
                "agent": "hybrid",
                "purpose": "Combine structured timetable data with uploaded timetable/admin documents.",
            }
        ]
    if intent in SQL_INTENTS:
        return [{"agent": "sql", "purpose": f"Fetch structured data for {intent}."}]
    if intent in RAG_INTENTS:
        return [{"agent": "rag", "purpose": "Search indexed documents."}]
    if intent in PDF_INTENTS:
        return [{"agent": "pdf", "purpose": "Generate a PDF report from the available context."}]
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
    print("[GRAPH] 🧠 Orchestrateur → classification du message...")
    t0 = time.perf_counter()
    decision = await run_orchestrator_agent(
        message=state.get("message", ""),
        history=state.get("history", []),
        user=state.get("user", {}),
    )
    elapsed = time.perf_counter() - t0
    intent = decision["intent"]
    plan = decision.get("plan") or _default_plan(intent)
    reason = decision.get("reason", "(aucune raison fournie)")
    plan_steps = " → ".join(s.get("agent", "?") for s in plan)
    print(f"[GRAPH] ✅ Orchestrateur terminé en {elapsed:.2f}s")
    print(f"[GRAPH]    🎯 Intent détecté  : {intent}")
    print(f"[GRAPH]    💡 Raison          : {reason}")
    print(f"[GRAPH]    📋 Plan d'exécution: {plan_steps}")
    print(f"[GRAPH]    📄 Suggest PDF     : {bool(decision.get('suggest_pdf', False))}")
    return {
        **state,
        "intent": intent,
        "route_reason": reason,
        "plan": plan,
        "suggest_pdf": bool(decision.get("suggest_pdf", False)),
        "executed_agents": [],
    }


async def sql_node(state: AgentState) -> AgentState:
    print(f"[GRAPH] 🗄️  Agent SQL → intent='{state.get('intent')}' en cours...")
    t0 = time.perf_counter()
    result = await run_sql_agent(
        message=state.get("message", ""),
        intent=state.get("intent", "general"),
        user=state.get("user", {}),
    )
    elapsed = time.perf_counter() - t0
    error = result.get("error")
    answer_preview = (result.get("answer") or "")[:80]
    print(f"[GRAPH] ✅ Agent SQL terminé en {elapsed:.2f}s")
    if error:
        print(f"[GRAPH]    ❌ Erreur SQL : {error}")
    else:
        print(f"[GRAPH]    📊 Réponse   : {answer_preview}{'...' if len(result.get('answer','')) > 80 else ''}")
    data = dict(state.get("data", {}))
    data["sql"] = result.get("data", {})
    return {
        **state,
        "response": result.get("answer", ""),
        "data": data,
        "error": error,
        "executed_agents": [*state.get("executed_agents", []), "sql"],
    }


async def rag_node(state: AgentState) -> AgentState:
    print("[GRAPH] 📚 Agent RAG → recherche documentaire en cours...")
    t0 = time.perf_counter()
    result = await run_rag_agent(
        message=state.get("message", ""),
        user=state.get("user", {}),
    )
    elapsed = time.perf_counter() - t0
    error = result.get("error")
    sources = result.get("sources") or []
    answer_preview = (result.get("answer") or "")[:80]
    print(f"[GRAPH] ✅ Agent RAG terminé en {elapsed:.2f}s")
    if error:
        print(f"[GRAPH]    ❌ Erreur RAG : {error}")
    else:
        print(f"[GRAPH]    🔍 Sources trouvées : {len(sources)}")
        print(f"[GRAPH]    📖 Réponse          : {answer_preview}{'...' if len(result.get('answer','')) > 80 else ''}")
    data = dict(state.get("data", {}))
    data["rag"] = {"context": result.get("context", "")}
    return {
        **state,
        "response": result.get("answer", ""),
        "data": data,
        "sources": [*state.get("sources", []), *(sources)],
        "error": error,
        "executed_agents": [*state.get("executed_agents", []), "rag"],
    }


async def hybrid_node(state: AgentState) -> AgentState:
    print("[GRAPH] 🔀 Agent HYBRID → SQL + RAG en parallèle...")
    t0 = time.perf_counter()
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
    elapsed = time.perf_counter() - t0
    print(f"[GRAPH] ✅ Agent HYBRID terminé en {elapsed:.2f}s")
    print(f"[GRAPH]    🗄️  SQL error  : {sql_result.get('error') or 'aucune'}")
    print(f"[GRAPH]    📚 RAG sources: {len(rag_result.get('sources') or [])}")
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
    print("[GRAPH] 📄 Agent PDF → génération du rapport...")
    t0 = time.perf_counter()
    result = await build_pdf_report_flow(
        message=state.get("message", ""),
        user=state.get("user", {}),
        history=state.get("history", []),
        data_context={
            **state.get("data", {}),
            "sources": state.get("sources", []),
            "current_response": state.get("response", ""),
        },
    )
    elapsed = time.perf_counter() - t0
    artifact = result.get("artifact")
    print(f"[GRAPH] ✅ Agent PDF terminé en {elapsed:.2f}s")
    if artifact:
        print(f"[GRAPH]    📎 Artifact : {artifact.get('filename', '?')}")
    else:
        print(f"[GRAPH]    ⚠️  Aucun artifact généré. Erreur: {result.get('error')}")
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
    print("[GRAPH] 💬 Agent GENERAL → réponse conversationnelle...")
    t0 = time.perf_counter()
    result = await run_general_agent(
        message=state.get("message", ""),
        history=state.get("history", []),
        user=state.get("user", {}),
    )
    elapsed = time.perf_counter() - t0
    answer_preview = (result.get("answer") or "")[:80]
    print(f"[GRAPH] ✅ Agent GENERAL terminé en {elapsed:.2f}s")
    if result.get("error"):
        print(f"[GRAPH]    ❌ Erreur : {result.get('error')}")
    else:
        print(f"[GRAPH]    💬 Réponse : {answer_preview}{'...' if len(result.get('answer','')) > 80 else ''}")
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
) -> AsyncGenerator[str | dict[str, Any], None]:
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

    print("[GRAPH] 🚀 Exécution du graph LangGraph...")
    t_total = time.perf_counter()
    final_state = await graph.ainvoke(state)
    total_elapsed = time.perf_counter() - t_total

    executed = final_state.get("executed_agents", [])
    pipeline_str = " → ".join(["orchestrator"] + executed)
    response = final_state.get("response", "")

    print(f"[GRAPH] 🏁 Graph terminé en {total_elapsed:.2f}s")
    print(f"[GRAPH]    🔗 Pipeline exécuté : {pipeline_str}")
    print(f"[GRAPH]    📝 Taille réponse   : {len(response)} caractères")
    if final_state.get("error"):
        print(f"[GRAPH]    ❌ Erreur finale   : {final_state.get('error')}")
    if final_state.get("artifacts"):
        print(f"[GRAPH]    📎 Artifacts       : {len(final_state.get('artifacts', []))}")

    # Append PDF offer when orchestrator signalled it and we haven't generated
    # a PDF already (artifacts list would be non-empty in that case).
    if final_state.get("suggest_pdf") and not final_state.get("artifacts"):
        response = response + _PDF_OFFER

    yield response

    for artifact in final_state.get("artifacts", []) or []:
        if artifact:
            yield {"artifact": artifact}
