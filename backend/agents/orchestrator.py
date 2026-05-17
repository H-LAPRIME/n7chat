from __future__ import annotations

import asyncio
import json
import re
from os import environ
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv


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


class OrchestratorDecision(TypedDict):
    intent: Intent
    confidence: float
    reason: str


SYSTEM_PROMPT = """
You are the n7chat orchestrator.

Classify the user's message into exactly one intent:
- emploi_du_temps: timetable, schedule, sessions, classes, calendar.
- notes: grades, marks, scores, averages, exams results.
- courses: course content, lessons, uploaded documents, news, administrative docs, RAG search.
- absence: absences, justification, attendance.
- pdf_report: generate/download PDF report, bulletin, notes report.
- general: greetings, unclear request, or anything outside the above.

Return only JSON:
{"intent":"...", "confidence":0.0, "reason":"short reason"}
"""


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_ORCHESTRATOR")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_ORCHESTRATOR is missing from backend/.env")

    from mistralai import Mistral

    return Mistral(api_key=api_key)


def _extract_content(response: Any) -> str:
    try:
        return response.choices[0].message.content or ""
    except Exception:
        return str(response)


def _fallback_intent(message: str) -> Intent:
    text = message.lower()
    if any(word in text for word in ["pdf", "rapport", "bulletin", "releve"]):
        return "pdf_report"
    if any(word in text for word in ["note", "score", "moyenne", "exam", "controle"]):
        return "notes"
    if any(word in text for word in ["absence", "absent", "justification", "justifie"]):
        return "absence"
    if any(word in text for word in ["emploi", "planning", "horaire", "seance"]):
        return "emploi_du_temps"
    if any(
        word in text
        for word in ["cours", "document", "support", "chapitre", "news", "administratif"]
    ):
        return "courses"
    return "general"


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
    }  # type: ignore[typeddict-item]


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
