from __future__ import annotations

import asyncio
import json
import re
from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv

from backend.tools.sql_tool import get_database_schema


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

VALID_INTENTS: set[str] = {
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "general",
}

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")

STATIC_CAPABILITIES = {
    "intents": {
        "emploi_du_temps": {
            "route": "sql",
            "tables": ["events", "modules", "filieres", "enseignants"],
            "description": "Use structured timetable/event/module data.",
        },
        "notes": {
            "route": "sql",
            "tables": ["notes", "students", "modules", "enseignants"],
            "description": "Use structured grades and module data.",
        },
        "absence": {
            "route": "sql",
            "tables": ["absences", "students", "modules", "enseignants"],
            "description": "Use structured absence and justification data.",
        },
        "courses": {
            "route": "rag",
            "tables": ["document_chunks", "courses", "events"],
            "description": (
                "Use semantic search over indexed documents: courses, timetables, "
                "news, administrative documents, events, and other files."
            ),
        },
        "pdf_report": {
            "route": "pdf",
            "tables": ["students", "notes", "absences", "generated_reports"],
            "description": "Generate notes or bulletin PDF reports.",
        },
        "general": {
            "route": "general",
            "tables": [],
            "description": "Use when the request is unclear or outside system data.",
        },
    },
    "document_source_types": [
        "course",
        "timetable",
        "news",
        "admin_document",
        "event",
        "other",
    ],
}


class OrchestratorDecision(TypedDict):
    intent: Intent
    confidence: float
    reason: str
    plan: list[dict[str, str]]


SYSTEM_PROMPT = """
You are the n7chat orchestrator.

Classify the user's message into exactly one intent:
- emploi_du_temps: timetable, schedule, sessions, classes, calendar.
- notes: grades, marks, scores, averages, exams results.
- courses: course content, lessons, uploaded documents, news, administrative docs, RAG search.
- absence: absences, justification, attendance.
- pdf_report: generate/download PDF report, bulletin, notes report.
- general: greetings, unclear request, or anything outside the above.

Use the provided database schema and system capabilities to decide whether the
request needs structured SQL data, semantic document retrieval, PDF generation,
or a general answer.

Important routing rules:
- If the user asks for a specific structured record already represented in SQL
  tables (notes, absences, events, modules, profile), prefer SQL intents.
- If the user asks about the content of a document, course support, news,
  timetable document, or administrative document, prefer courses/RAG even if
  the text also mentions absences or exams.
- If the user asks to generate, download, print, or export a PDF report, prefer
  pdf_report.

Return only JSON:
{
  "intent":"...",
  "confidence":0.0,
  "reason":"short reason",
  "plan":[
    {"agent":"sql|rag|pdf|general", "purpose":"short purpose"}
  ]
}

Planning rules:
- notes, absence, emploi_du_temps: plan with sql.
- courses/document questions: plan with rag.
- pdf_report: plan with sql first, then pdf. The SQL step gathers structured
  student notes/absences/profile, then the PDF step uses that context to build
  the report.
- If a request needs both structured data and document context, include both
  sql and rag before the final answer/PDF step.
"""


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_ORCHESTRATOR")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_ORCHESTRATOR is missing from backend/.env")

    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral

    return Mistral(api_key=api_key)


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _tool_invoke(tool_obj: Any, payload: dict[str, Any] | None = None) -> Any:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload or {})
    return tool_obj(**(payload or {}))


def _compact_schema(schema: dict[str, Any], max_columns_per_table: int = 12) -> dict[str, Any]:
    tables = schema.get("tables") or {}
    compact_tables = {}
    for table_name, columns in tables.items():
        compact_tables[table_name] = [
            f"{column.get('name')}:{column.get('type')}"
            for column in columns[:max_columns_per_table]
        ]
    return {
        "ok": bool(schema.get("ok")),
        "tables": compact_tables,
        "error": schema.get("error"),
    }


@lru_cache(maxsize=1)
def get_orchestrator_context() -> dict[str, Any]:
    """Return schema/capability context used by the orchestrator prompt.

    Cached per process because schema changes rarely, while classification is hot.
    """
    try:
        schema = _tool_invoke(get_database_schema)
        compact_schema = _compact_schema(schema if isinstance(schema, dict) else {})
    except Exception as exc:
        compact_schema = {"ok": False, "tables": {}, "error": str(exc)}

    return {
        "capabilities": STATIC_CAPABILITIES,
        "database_schema": compact_schema,
    }


def _fallback_intent(message: str) -> Intent:
    text = message.lower()
    if any(word in text for word in ["pdf", "rapport", "bulletin", "releve"]):
        return "pdf_report"
    if any(
        word in text
        for word in ["cours", "document", "support", "chapitre", "news", "administratif"]
    ):
        return "courses"
    if any(word in text for word in ["note", "score", "moyenne", "exam", "controle"]):
        return "notes"
    if any(word in text for word in ["absence", "absent", "justification", "justifie"]):
        return "absence"
    if any(word in text for word in ["emploi", "planning", "horaire", "seance"]):
        return "emploi_du_temps"
    return "general"


def _fallback_plan(intent: str, message: str) -> list[dict[str, str]]:
    text = message.lower()
    if intent == "pdf_report":
        return [
            {"agent": "sql", "purpose": "Collect student profile, notes, and absences."},
            {"agent": "pdf", "purpose": "Generate the requested PDF report."},
        ]
    if intent in {"notes", "absence", "emploi_du_temps"}:
        return [{"agent": "sql", "purpose": f"Fetch structured data for {intent}."}]
    if intent == "courses":
        plan = []
        if any(word in text for word in ["note", "absence", "emploi", "planning"]):
            plan.append(
                {
                    "agent": "sql",
                    "purpose": "Fetch related structured school data before document search.",
                }
            )
        plan.append(
            {
                "agent": "rag",
                "purpose": "Search indexed documents and course/admin content.",
            }
        )
        return plan
    return [{"agent": "general", "purpose": "Answer or ask for clarification."}]


def _parse_decision(raw: str, message: str) -> OrchestratorDecision:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    payload = json.loads(match.group(0) if match else raw)
    intent = payload.get("intent", "general")
    if intent not in VALID_INTENTS:
        intent = _fallback_intent(message)

    confidence = payload.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(float(confidence), 1.0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "intent": intent,
        "confidence": confidence,
        "reason": str(payload.get("reason") or ""),
        "plan": _normalize_plan(payload.get("plan"), intent, message),
    }  # type: ignore[typeddict-item]


def _normalize_plan(plan: Any, intent: str, message: str) -> list[dict[str, str]]:
    valid_agents = {"sql", "rag", "pdf", "general"}
    normalized = []
    if isinstance(plan, list):
        for step in plan:
            if not isinstance(step, dict):
                continue
            agent = str(step.get("agent") or "").lower()
            if agent not in valid_agents:
                continue
            normalized.append(
                {
                    "agent": agent,
                    "purpose": str(step.get("purpose") or f"Run {agent} agent."),
                }
            )

    if not normalized:
        return _fallback_plan(intent, message)

    if intent == "pdf_report":
        agents = [step["agent"] for step in normalized]
        if "sql" not in agents:
            normalized.insert(
                0,
                {
                    "agent": "sql",
                    "purpose": "Collect structured data needed for the PDF report.",
                },
            )
        if "pdf" not in agents:
            normalized.append({"agent": "pdf", "purpose": "Generate the PDF report."})

    return normalized


def classify_intent_sync(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> OrchestratorDecision:
    prompt = json.dumps(
        {
            "user_role": user_role or "unknown",
            "history": (history or [])[-6:],
            "message": message,
            "system_context": get_orchestrator_context(),
        },
        ensure_ascii=False,
        default=str,
    )

    try:
        response = _mistral_client().chat.complete(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return _parse_decision(_extract_content(response), message)
    except Exception as exc:
        return {
            "intent": _fallback_intent(message),
            "confidence": 0.35,
            "reason": f"fallback classifier used: {exc}",
            "plan": _fallback_plan(_fallback_intent(message), message),
        }


async def classify_intent(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> OrchestratorDecision:
    return await asyncio.to_thread(classify_intent_sync, message, history, user_role)


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
