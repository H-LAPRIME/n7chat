"""Orchestrator LLM Task.

Contains every piece of the intent-classification LLM call:
  - prompt constants
  - Mistral client factory
  - response parsing / fallback helpers
  - the synchronous ``classify_intent_task`` entry-point

``backend.agents.orchestrator`` imports ``classify_intent_task`` (plus the
shared types it needs) from here, keeping the LLM interaction isolated from
routing / async-wrapping logic.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Intent = Literal[
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "profile",
    "general",
]

VALID_INTENTS: set[str] = {
    "emploi_du_temps",
    "notes",
    "courses",
    "absence",
    "pdf_report",
    "profile",
    "general",
}


class OrchestratorDecision(TypedDict):
    intent: Intent
    confidence: float
    reason: str
    plan: list[dict[str, str]]
    suggest_pdf: bool  # True → answer normally, then offer PDF generation to the user


# ---------------------------------------------------------------------------
# Static capability catalogue (no DB hit)
# ---------------------------------------------------------------------------

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
        "profile": {
            "route": "sql",
            "tables": ["students", "enseignants", "filieres", "departments"],
            "description": "Use structured data for user profiles, filieres, teachers, and departments.",
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

# ---------------------------------------------------------------------------
# LLM system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are the n7chat orchestrator.

═══════════════════════════════════════════════════════
 STEP 1 – CLASSIFY INTENT
═══════════════════════════════════════════════════════
Classify the user's message into exactly one intent:
- emploi_du_temps : timetable, schedule, sessions, classes, calendar.
- notes           : grades, marks, scores, averages, exam results.
- courses         : course content, lessons, uploaded documents, news,
                    administrative docs, RAG search.
- absence         : absences, justification, attendance.
- pdf_report      : user EXPLICITLY asks to generate / download / print /
                    export a PDF report or bulletin.
- profile         : user asks about their profile, filiere, department, or teachers.
- general         : greetings, unclear request, or anything outside the above.

Routing rules:
- SQL-backed intents (notes, absence, emploi_du_temps, profile): prefer sql.
- Document / semantic content: prefer courses → rag.
- ONLY route to pdf_report when the user *explicitly* requests PDF generation.
  A question like "show me my notes" is intent=notes, NOT pdf_report.

═══════════════════════════════════════════════════════
 STEP 2 – PDF ACCEPTANCE CHECK (check history first)
═══════════════════════════════════════════════════════
Look at the last assistant message in history:
  - If it contains a PDF offer (e.g. "Souhaitez-vous un rapport PDF ?") AND
    the current user message is an acceptance (oui, yes, ok, génère, generate,
    allez-y, vas-y, s'il te plaît, please, go ahead, d'accord, sure, bien sûr)
    → set intent="pdf_report" and suggest_pdf=false.
  - Otherwise do NOT route to pdf_report based on history alone.

═══════════════════════════════════════════════════════
 STEP 3 – SHOULD WE OFFER A PDF? (suggest_pdf flag)
═══════════════════════════════════════════════════════
After classifying intent, decide whether the response is complex/structured
enough to deserve a PDF offer. Set suggest_pdf=true when ALL of:
  1. intent is notes, absence, or pdf_report-adjacent (but NOT pdf_report itself)
  2. The data will be a multi-row table (all notes, full absence list, bulletin)
  3. The user did NOT already receive a PDF offer in the last assistant message
     (avoid repeating the offer).
Set suggest_pdf=false when:
  - intent is emploi_du_temps, courses, or general
  - The question is narrow (e.g. "what is my average in Maths?")
  - The last assistant message already offered a PDF
  - intent is pdf_report (we are already generating it)

═══════════════════════════════════════════════════════
 OUTPUT – return ONLY JSON
═══════════════════════════════════════════════════════
{
  "intent": "...",
  "confidence": 0.0,
  "reason": "short reason",
  "suggest_pdf": false,
  "plan": [
    {"agent": "sql|rag|pdf|general", "purpose": "short purpose"}
  ]
}

Planning rules:
- notes, absence, emploi_du_temps, profile → sql.
- courses → rag.
- pdf_report → sql first, then pdf.
- Mixed data+docs → sql + rag.
"""

DEFAULT_MODEL = environ.get("MISTRAL_MODEL", "mistral-large-latest")

# ---------------------------------------------------------------------------
# Mistral client
# ---------------------------------------------------------------------------


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_ORCHESTRATOR")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_ORCHESTRATOR is missing from backend/.env")

    try:
        from mistralai import Mistral
    except ImportError:
        from mistralai.client import Mistral  # type: ignore[no-redef]

    return Mistral(api_key=api_key)


# ---------------------------------------------------------------------------
# Schema helper (cached)
# ---------------------------------------------------------------------------


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


def _tool_invoke(tool_obj: Any, payload: dict[str, Any] | None = None) -> Any:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload or {})
    return tool_obj(**(payload or {}))


@lru_cache(maxsize=1)
def get_orchestrator_context() -> dict[str, Any]:
    """Return schema/capability context used by the orchestrator prompt.

    Cached per process because schema changes rarely, while classification is hot.
    """
    from backend.tools.sql_tool import get_database_schema  # local import avoids cycle

    try:
        schema = _tool_invoke(get_database_schema)
        compact_schema = _compact_schema(schema if isinstance(schema, dict) else {})
    except Exception as exc:
        compact_schema = {"ok": False, "tables": {}, "error": str(exc)}

    return {
        "capabilities": STATIC_CAPABILITIES,
        "database_schema": compact_schema,
    }


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


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


def _fallback_suggest_pdf(intent: str, message: str, history: list[dict[str, Any]] | None) -> bool:
    """Heuristic fallback: should we offer a PDF after a normal answer?"""
    if intent not in {"notes", "absence"}:
        return False
    # Don't repeat the offer if the last assistant message already had one
    last_assistant = next(
        (m.get("content", "") for m in reversed(history or []) if m.get("role") == "assistant"),
        "",
    )
    if "pdf" in last_assistant.lower() or "rapport" in last_assistant.lower():
        return False
    # Broad request → worth offering
    text = message.lower()
    broad_keywords = ["toutes", "tous", "all", "mes notes", "my notes", "liste", "bilan"]
    return any(kw in text for kw in broad_keywords) or intent == "absence"


def _parse_decision(
    raw: str,
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> OrchestratorDecision:
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

    # suggest_pdf: trust the LLM; fall back to heuristic if missing/invalid
    suggest_pdf_raw = payload.get("suggest_pdf")
    if isinstance(suggest_pdf_raw, bool):
        suggest_pdf = suggest_pdf_raw
    else:
        suggest_pdf = _fallback_suggest_pdf(intent, message, history)

    # Never suggest PDF when we are already generating one
    if intent == "pdf_report":
        suggest_pdf = False

    return {
        "intent": intent,
        "confidence": confidence,
        "reason": str(payload.get("reason") or ""),
        "plan": _normalize_plan(payload.get("plan"), intent, message),
        "suggest_pdf": suggest_pdf,
    }  # type: ignore[typeddict-item]


# ---------------------------------------------------------------------------
# Public task entry-point
# ---------------------------------------------------------------------------


def classify_intent_task(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> OrchestratorDecision:
    """Call Mistral to classify *message* and return an :class:`OrchestratorDecision`.

    This is the pure LLM task — no side-effects beyond the API call.
    Falls back to keyword heuristics when the API is unavailable.

    The decision now includes ``suggest_pdf`` which signals that the normal
    text answer should be followed by a PDF generation offer.
    """
    prompt = json.dumps(
        {
            "current_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        return _parse_decision(_extract_content(response), message, history)
    except Exception as exc:
        fallback_intent = _fallback_intent(message)
        return {
            "intent": fallback_intent,
            "confidence": 0.35,
            "reason": f"fallback classifier used: {exc}",
            "plan": _fallback_plan(fallback_intent, message),
            "suggest_pdf": _fallback_suggest_pdf(fallback_intent, message, history),
        }
