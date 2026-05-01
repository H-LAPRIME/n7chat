"""
agents/orchestrator.py
────────────────────────
LangGraph orchestration graph — classifies intent and routes
to the appropriate sub-agent node.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_groq_orchestrator

# ── Intent labels ─────────────────────────────────────────────
INTENTS = {
    "quick_answer",
    "perform_task",
    "save",
    "doc_search",
    "unknown_intent",
}

ORCHESTRATOR_SYSTEM_PROMPT = """You are an intent classifier for an educational AI assistant.
Given a user message and context, classify the intent as ONE of:
- quick_answer: Simple factual or general question
- perform_task: Request to do something (enroll, submit, create)
- save: Explicitly ask to remember/save something
- doc_search: Question requiring document search (PDFs, regulations, courses)
- unknown_intent: Unclear or out-of-scope

Respond ONLY with the intent label, nothing else."""


# ── Node: classify intent ─────────────────────────────────────

def classify_intent_node(state: AgentState) -> AgentState:
    llm = get_langchain_groq_orchestrator()
    response = llm.invoke(
        [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": state["user_message"]},
        ]
    )
    intent = response.content.strip().lower()
    if intent not in INTENTS:
        intent = "unknown_intent"
    return {**state, "intent": intent}


# ── Router ────────────────────────────────────────────────────

def route_intent(state: AgentState) -> str:
    routing = {
        "quick_answer": "faq",
        "perform_task": "planner",
        "save": "memory",
        "doc_search": "retrieval",
        "unknown_intent": "fallback",
    }
    return routing.get(state["intent"], "fallback")


# ── Stub nodes (implemented in individual agent files) ─────────

def _import_nodes():
    from agents.faq_agent import faq_node
    from agents.planner_agent import planner_node
    from agents.memory_agent import memory_node
    from agents.retrieval_agent import retrieval_node
    from agents.fallback_agent import fallback_node
    from agents.action_agent import action_node
    return faq_node, planner_node, memory_node, retrieval_node, fallback_node, action_node


# ── Build graph ───────────────────────────────────────────────

def build_graph() -> StateGraph:
    faq_node, planner_node, memory_node, retrieval_node, fallback_node, action_node = _import_nodes()

    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("faq", faq_node)
    graph.add_node("planner", planner_node)
    graph.add_node("memory", memory_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("action", action_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges("classify_intent", route_intent)

    # All agent nodes end the graph
    for node in ("faq", "planner", "memory", "retrieval", "fallback", "action"):
        graph.add_edge(node, END)

    return graph.compile()


# ── Public API ────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run(user_message: str, session_id: str, user: dict) -> dict:
    """Entry point called from Flask route."""
    initial_state: AgentState = {
        "session_id": session_id,
        "user_id": user.get("sub", ""),
        "role": user.get("role", "student"),
        "user_message": user_message,
        "intent": "",
        "short_term_history": [],
        "long_term_summary": "",
        "agent_used": "",
        "response": "",
        "sources": [],
        "messages": [HumanMessage(content=user_message)],
    }
    result = get_graph().invoke(initial_state)
    return {
        "response": result.get("response", ""),
        "agent_used": result.get("agent_used", ""),
        "sources": result.get("sources", []),
        "session_id": session_id,
    }
