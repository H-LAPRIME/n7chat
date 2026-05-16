from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from os import environ
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from backend.tools.pdf_tool import build_bulletin_pdf, build_notes_pdf
from backend.tools.rag_tool import search_document_content
from backend.tools.sql_tool import (
    get_filiere_modules,
    get_student_absences,
    get_student_notes,
    get_student_profile,
    get_upcoming_events,
)


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

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
VALID_INTENTS: set[str] = {
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "general",
}

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, Any]]
    user: dict[str, Any]
    intent: Intent
    response: str
    data: dict[str, Any]
    sources: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    error: str | None


def _mistral_client(agent: str):
    api_key_name = f"MISTRAL_KEY_{agent.upper()}"
    api_key = environ.get(api_key_name)
    if not api_key:
        raise RuntimeError(f"{api_key_name} is missing from backend/.env")

    from mistralai import Mistral

    return Mistral(api_key=api_key)


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _chat_sync(
    *,
    agent: str,
    system: str,
    user: str,
    temperature: float = 0.2,
) -> str:
    response = _mistral_client(agent).chat.complete(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return _extract_content(response).strip()


async def _chat(
    *,
    agent: str,
    system: str,
    user: str,
    temperature: float = 0.2,
) -> str:
    return await asyncio.to_thread(
        _chat_sync,
        agent=agent,
        system=system,
        user=user,
        temperature=temperature,
    )


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)


def _fallback_intent(message: str) -> Intent:
    text = message.lower()
    if any(word in text for word in ["pdf", "rapport", "bulletin", "releve"]):
        return "pdf_report"
    if any(word in text for word in ["note", "score", "moyenne", "exam"]):
        return "notes"
    if any(word in text for word in ["absence", "absent", "justifie"]):
        return "absence"
    if any(word in text for word in ["emploi", "planning", "horaire", "seance"]):
        return "emploi_du_temps"
    if any(word in text for word in ["cours", "course", "document", "support", "chapitre"]):
        return "courses"
    return "general"


async def orchestrator_node(state: AgentState) -> AgentState:
    message = state.get("message", "")
    role = state.get("user", {}).get("role", "unknown")
    history = state.get("history", [])[-6:]

    system = """
You are the n7chat orchestrator. Classify the user's intent into exactly one:
emploi_du_temps, notes, courses, absence, pdf_report, general.

Return only JSON in this shape:
{"intent": "..."}
"""
    prompt = f"User role: {role}\nHistory: {_json_dump(history)}\nMessage: {message}"

    try:
        raw = await _chat(agent="orchestrator", system=system, user=prompt, temperature=0)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw)
        intent = parsed.get("intent", "general")
        if intent not in VALID_INTENTS:
            intent = _fallback_intent(message)
    except Exception:
        intent = _fallback_intent(message)

    return {**state, "intent": intent}  # type: ignore[typeddict-item]


async def sql_node(state: AgentState) -> AgentState:
    user = state.get("user", {})
    intent = state.get("intent", "general")
    data: dict[str, Any] = {}

    if intent == "notes":
        student_id = user.get("student_id") or user.get("student", {}).get("id")
        if student_id:
            data["notes"] = _tool_result(get_student_notes, {"student_id": student_id})
        else:
            data["error"] = "student_id is required for notes intent"

    elif intent == "absence":
        student_id = user.get("student_id") or user.get("student", {}).get("id")
        if student_id:
            data["absences"] = _tool_result(get_student_absences, {"student_id": student_id})
        else:
            data["error"] = "student_id is required for absence intent"

    elif intent == "emploi_du_temps":
        filiere_id = user.get("filiere_id") or user.get("student", {}).get("filiere_id")
        semester = user.get("semester")
        if filiere_id:
            data["modules"] = _tool_result(
                get_filiere_modules,
                {"filiere_id": filiere_id, "semester": semester},
            )
        data["events"] = _tool_result(get_upcoming_events, {"limit": 20})

    system = """
You are the n7chat SQL agent. Answer the user in clear French using only the
provided Supabase data. If data is missing, say exactly what is missing.
Keep the answer concise and student-friendly.
"""
    prompt = f"Intent: {intent}\nUser question: {state.get('message', '')}\nData:\n{_json_dump(data)}"

    try:
        response = await _chat(agent="sql", system=system, user=prompt)
    except Exception as exc:
        response = f"Je n'ai pas pu interroger l'agent SQL: {exc}"

    return {**state, "data": data, "response": response}


async def rag_node(state: AgentState) -> AgentState:
    message = state.get("message", "")
    user = state.get("user", {})
    search = search_document_content(
        query=message,
        top_k=5,
        module_id=user.get("module_id"),
        user_id=user.get("sub") or user.get("id"),
        filiere=user.get("filiere_name"),
    )

    system = """
You are the n7chat RAG agent. Answer from the retrieved document context only.
Documents can be courses, timetable entries, news, administrative documents, or
other indexed material. If context is insufficient, say that clearly.
"""
    prompt = (
        f"Question: {message}\n"
        f"Retrieved context:\n{search.get('context', '')}\n"
        f"Raw matches:\n{_json_dump(search.get('data', []))}"
    )

    try:
        response = await _chat(agent="rag", system=system, user=prompt)
    except Exception as exc:
        response = f"Je n'ai pas pu interroger l'agent RAG: {exc}"

    return {
        **state,
        "data": {"rag": search},
        "sources": search.get("data") or [],
        "response": response,
    }


async def pdf_node(state: AgentState) -> AgentState:
    user = state.get("user", {})
    student_id = user.get("student_id") or user.get("student", {}).get("id")
    user_id = user.get("sub") or user.get("id")
    artifacts: list[dict[str, Any]] = []

    try:
        profile_result = None
        if user_id:
            profile_result = _tool_result(get_student_profile, {"user_id": user_id})
        student = profile_result.get("data") if isinstance(profile_result, dict) else None
        student = student or user.get("student") or user

        notes_result = (
            _tool_result(get_student_notes, {"student_id": student_id})
            if student_id
            else {"data": []}
        )
        absences_result = (
            _tool_result(get_student_absences, {"student_id": student_id})
            if student_id
            else {"data": []}
        )

        notes = notes_result.get("data") or []
        absences = absences_result.get("data") or []
        wants_bulletin = any(
            word in state.get("message", "").lower()
            for word in ["bulletin", "absence", "absences"]
        )
        if wants_bulletin:
            file_path = build_bulletin_pdf(student, notes, absences)
            report_type = "bulletin"
        else:
            file_path = build_notes_pdf(student, notes)
            report_type = "notes"

        artifacts.append({"type": report_type, "file_path": file_path})
        response = f"Le PDF {report_type} est pret: {file_path}"
        data = {"student": student, "notes": notes, "absences": absences}
    except Exception as exc:
        response = f"Je n'ai pas pu generer le PDF: {exc}"
        data = {"error": str(exc)}

    return {**state, "data": data, "artifacts": artifacts, "response": response}


async def general_node(state: AgentState) -> AgentState:
    system = """
You are n7chat, a concise university assistant. Answer general questions in
French. Do not invent private student data. Ask for clarification if needed.
"""
    try:
        response = await _chat(
            agent="orchestrator",
            system=system,
            user=f"Question: {state.get('message', '')}",
            temperature=0.4,
        )
    except Exception:
        response = (
            "Je peux t'aider avec les notes, absences, emploi du temps, cours, "
            "documents indexes et generation de PDF. Peux-tu preciser ta demande ?"
        )
    return {**state, "response": response}


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
        "response": "",
        "data": {},
        "sources": [],
        "artifacts": [],
        "error": None,
    }

    final_state = await graph.ainvoke(state)
    yield final_state.get("response", "")
