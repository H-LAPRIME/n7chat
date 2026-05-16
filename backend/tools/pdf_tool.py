from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from typing import Any
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **_: Any):
        if func is None:
            return lambda wrapped: wrapped
        return func


TEAL = colors.HexColor("#1D9E75")
LIGHT = colors.HexColor("#F1EFE8")
BORDER = colors.HexColor("#B4B2A9")


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None, **extra}


def _failure(error: Exception | str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": str(error), **extra}


def _pdf_path(prefix: str) -> str:
    return str(Path(gettempdir()) / f"{prefix}-{uuid4()}.pdf")


def _base_doc(filename: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _student_name(student: dict[str, Any]) -> str:
    return f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()


def _student_filiere(student: dict[str, Any]) -> str:
    if student.get("filiere_name"):
        return str(student["filiere_name"])
    filieres = student.get("filieres")
    if isinstance(filieres, dict):
        return str(filieres.get("name") or "")
    return ""


def _student_level(student: dict[str, Any]) -> str:
    if student.get("level_name"):
        return str(student["level_name"])
    levels = student.get("levels")
    if isinstance(levels, dict):
        return str(levels.get("name") or "")
    return ""


def _module_name(row: dict[str, Any]) -> str:
    if row.get("module_name"):
        return str(row["module_name"])
    modules = row.get("modules")
    if isinstance(modules, dict):
        return str(modules.get("name") or "")
    return ""


def _module_semester(row: dict[str, Any]) -> str:
    if row.get("semester"):
        return str(row["semester"])
    modules = row.get("modules")
    if isinstance(modules, dict):
        return str(modules.get("semester") or "")
    return ""


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )


def build_notes_pdf(student: dict[str, Any], notes: list[dict[str, Any]]) -> str:
    filename = _pdf_path("notes")
    doc = _base_doc(filename)
    styles = getSampleStyleSheet()
    story = []

    name = _student_name(student) or "Etudiant"
    story.append(Paragraph(f"Releve de notes - {name}", styles["Title"]))
    story.append(
        Paragraph(
            f"Filiere : {_student_filiere(student)} | Niveau : {_student_level(student)}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", color=TEAL, thickness=1))
    story.append(Spacer(1, 0.4 * cm))

    rows = [["Module", "Type", "Note", "Coeff.", "Date"]]
    rows.extend(
        [
            _module_name(note),
            str(note.get("exam_type", "")),
            str(note.get("score", "")),
            str(note.get("coefficient", "")),
            str(note.get("published_at", ""))[:10],
        ]
        for note in notes
    )

    table = Table(rows, colWidths=[6 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 3 * cm])
    table.setStyle(_table_style())
    story.append(table)
    doc.build(story)
    return filename


def build_bulletin_pdf(
    student: dict[str, Any],
    notes: list[dict[str, Any]],
    absences: list[dict[str, Any]],
) -> str:
    filename = _pdf_path("bulletin")
    doc = _base_doc(filename)
    styles = getSampleStyleSheet()
    story = []

    name = _student_name(student) or "Etudiant"
    story.append(Paragraph("Bulletin academique", styles["Title"]))
    story.append(
        Paragraph(
            f"{name} - {_student_filiere(student)} - {_student_level(student)}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Notes", styles["Heading2"]))
    note_rows = [["Module", "Type", "Note", "Semestre"]]
    note_rows.extend(
        [
            _module_name(note),
            str(note.get("exam_type", "")),
            str(note.get("score", "")),
            _module_semester(note),
        ]
        for note in notes
    )
    notes_table = Table(note_rows, colWidths=[7 * cm, 3 * cm, 2.5 * cm, 2.5 * cm])
    notes_table.setStyle(_table_style())
    story.append(notes_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Absences", styles["Heading2"]))
    absence_rows = [["Module", "Date", "Justifiee"]]
    absence_rows.extend(
        [
            _module_name(absence),
            str(absence.get("date", ""))[:10],
            "Oui" if absence.get("justified") else "Non",
        ]
        for absence in absences
    )
    absences_table = Table(absence_rows, colWidths=[8 * cm, 4 * cm, 3 * cm])
    absences_table.setStyle(_table_style())
    story.append(absences_table)

    doc.build(story)
    return filename


@tool
def build_notes_pdf_tool(
    student: dict[str, Any],
    notes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a notes PDF and return its local file path."""
    try:
        path = build_notes_pdf(student, notes)
        return _success({"file_path": path})
    except Exception as exc:
        return _failure(exc)


@tool
def build_bulletin_pdf_tool(
    student: dict[str, Any],
    notes: list[dict[str, Any]],
    absences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a bulletin PDF and return its local file path."""
    try:
        path = build_bulletin_pdf(student, notes, absences)
        return _success({"file_path": path})
    except Exception as exc:
        return _failure(exc)


PDF_TOOLS = [
    build_notes_pdf_tool,
    build_bulletin_pdf_tool,
]
