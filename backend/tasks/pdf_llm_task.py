"""PDF LLM Task.

Contains the report-type inference helper used by the PDF agent.
Imported by backend.agents.pdf_agent – keeps report-type logic isolated
from data-collection (SQL tools) and async-wrapping logic.

Note: PDF generation itself (``build_bulletin_pdf``, ``build_notes_pdf``) lives
in ``backend.tools.pdf_tool`` and is orchestrated by the agent.  This task
module holds only the *decision* logic (which report type?) so it can be
tested and updated independently.
"""

from __future__ import annotations

from typing import Any, Literal


ReportType = Literal["notes", "bulletin"]


# ---------------------------------------------------------------------------
# Public task entry-point
# ---------------------------------------------------------------------------


def infer_report_type_task(
    message: str,
    explicit_type: str | None = None,
) -> ReportType:
    """Determine the PDF report type from *message* or an explicit override.

    Parameters
    ----------
    message:
        The original user question (used for keyword matching).
    explicit_type:
        If ``"notes"`` or ``"bulletin"``, returned immediately without inspecting
        the message.

    Returns
    -------
    ``"notes"`` or ``"bulletin"``.
    """
    if explicit_type in ("notes", "bulletin"):
        return explicit_type  # type: ignore[return-value]
    lowered = message.lower()
    if any(word in lowered for word in ["bulletin", "absence", "absences"]):
        return "bulletin"
    return "notes"


def build_pdf_answer(
    selected_type: ReportType,
    file_path: str,
    student: dict[str, Any],
    notes: list[Any],
    absences: list[Any],
) -> dict[str, Any]:
    """Assemble the successful PDF agent response dict.

    Parameters
    ----------
    selected_type:
        ``"notes"`` or ``"bulletin"``.
    file_path:
        Absolute or relative path to the generated PDF file.
    student:
        Student profile dict.
    notes:
        List of note records.
    absences:
        List of absence records.

    Returns
    -------
    dict with keys ``ok``, ``answer``, ``artifact``, ``data``, ``error``.
    """
    return {
        "ok": True,
        "answer": f"Le PDF {selected_type} est pret: {file_path}",
        "artifact": {"type": selected_type, "file_path": file_path},
        "data": {"student": student, "notes": notes, "absences": absences},
        "error": None,
    }


def build_pdf_error(exc: Exception) -> dict[str, Any]:
    """Assemble the failed PDF agent response dict."""
    return {
        "ok": False,
        "answer": f"Je n'ai pas pu generer le PDF: {exc}",
        "artifact": None,
        "data": {},
        "error": str(exc),
    }
