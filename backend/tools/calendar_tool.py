from __future__ import annotations

from datetime import date, datetime
from typing import Any

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **_: Any):
        if func is None:
            return lambda wrapped: wrapped
        return func


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None, **extra}


def _failure(error: Exception | str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": str(error), **extra}


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _date(value: Any) -> str:
    parsed = _parse_datetime(value)
    return parsed.strftime("%Y-%m-%d") if parsed else str(value or "")


def _time(value: Any) -> str:
    parsed = _parse_datetime(value)
    return parsed.strftime("%H:%M") if parsed else ""


def _module_name(event: dict[str, Any]) -> str:
    if event.get("module_name"):
        return str(event["module_name"])
    modules = event.get("modules")
    if isinstance(modules, dict):
        return str(modules.get("name") or "")
    return str(event.get("title") or "")


def format_emploi_table(events: list[dict[str, Any]]) -> str:
    if not events:
        return "_Aucune seance trouvee._"

    sorted_events = sorted(events, key=lambda event: str(event.get("start_date", "")))
    rows = [
        "| Date | Debut | Fin | Module | Type | Salle |",
        "|---|---:|---:|---|---|---|",
    ]
    for event in sorted_events:
        rows.append(
            "| "
            + " | ".join(
                [
                    _date(event.get("start_date")),
                    _time(event.get("start_date")),
                    _time(event.get("end_date")),
                    _module_name(event),
                    str(event.get("event_type") or ""),
                    str(event.get("location") or ""),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def format_events_list(events: list[dict[str, Any]]) -> str:
    if not events:
        return "_Aucun evenement a venir._"

    sorted_events = sorted(events, key=lambda event: str(event.get("start_date", "")))
    lines = []
    for event in sorted_events:
        event_type = str(event.get("event_type") or "event").capitalize()
        title = str(event.get("title") or "")
        start = f"{_date(event.get('start_date'))} {_time(event.get('start_date'))}".strip()
        location = str(event.get("location") or "A definir")
        lines.append(f"- **{event_type}** | {title} | {start} | {location}")
    return "\n".join(lines)


@tool
def format_schedule_table(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Format timetable-like events as a Markdown table."""
    try:
        markdown = format_emploi_table(events)
        return _success(markdown, chars=len(markdown))
    except Exception as exc:
        return _failure(exc, chars=0)


@tool
def format_events_markdown(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Format event records as a Markdown list."""
    try:
        markdown = format_events_list(events)
        return _success(markdown, chars=len(markdown))
    except Exception as exc:
        return _failure(exc, chars=0)


CALENDAR_TOOLS = [
    format_schedule_table,
    format_events_markdown,
]
