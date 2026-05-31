from __future__ import annotations

import html
import re
from pathlib import Path
from tempfile import gettempdir
from typing import Any
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
PDF_TEMPLATE = "pdf_report.html"

BLACKBOARD_BOLD = {
    "N": "ℕ",
    "Z": "ℤ",
    "Q": "ℚ",
    "R": "ℝ",
    "C": "ℂ",
    "K": "𝕂",
}
SUBSCRIPT_CHARS = str.maketrans("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ")
SUPERSCRIPT_CHARS = str.maketrans("0123456789+-=()in", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ")


def _translate_script(value: str, table: dict[int, str]) -> str:
    return value.translate(table)


def _format_matrix(match: re.Match[str]) -> str:
    body = match.group(1)
    rows = []
    for row in re.split(r"\\\\", body):
        cells = [cell.strip() for cell in row.split("&") if cell.strip()]
        if cells:
            rows.append("  ".join(cells))
    return "[" + "; ".join(rows) + "]"


def _latex_to_readable_text(value: Any) -> str:
    """Convert common LaTeX math fragments into readable PDF text."""
    if value is None:
        return ""
    text = _normalize_cell(value)
    text = re.sub(r"\\begin\{[bpv]?matrix\}([\s\S]*?)\\end\{[bpv]?matrix\}", _format_matrix, text)
    text = re.sub(r"\\mathbb\{([A-Z])\}", lambda m: BLACKBOARD_BOLD.get(m.group(1), m.group(1)), text)
    text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", text)
    replacements = {
        r"\(": "",
        r"\)": "",
        r"\[": "",
        r"\]": "",
        "$$": "",
        r"\times": "×",
        r"\cdot": "·",
        r"\dots": "…",
        r"\ldots": "…",
        r"\sum": "∑",
        r"\lambda": "λ",
        r"\neq": "≠",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\infty": "∞",
        r"\det": "det",
        r"\|": "‖",
        r"\_": "_",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"_\{([^{}]+)\}", lambda m: _translate_script(m.group(1), SUBSCRIPT_CHARS), text)
    text = re.sub(r"\^\\?\{([^{}]+)\}", lambda m: _translate_script(m.group(1), SUPERSCRIPT_CHARS), text)
    text = re.sub(r"_([0-9aehijklmnoprstuvx]+)", lambda m: _translate_script(m.group(1), SUBSCRIPT_CHARS), text)
    text = re.sub(r"\^([0-9in]+)", lambda m: _translate_script(m.group(1), SUPERSCRIPT_CHARS), text)
    text = text.replace("\\", "")
    return re.sub(r"[ \t]+", " ", text).strip()


def _pdf_text_html(value: Any) -> str:
    return html.escape(_latex_to_readable_text(value)).replace("\n", "<br>")


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None, **extra}


def _failure(error: Exception | str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": str(error), **extra}


def _pdf_path(prefix: str = "report") -> str:
    safe_prefix = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in prefix.lower())
    return str(Path(gettempdir()) / f"{safe_prefix or 'report'}-{uuid4()}.pdf")


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
    return str(row.get("name") or "")


def _module_semester(row: dict[str, Any]) -> str:
    if row.get("semester"):
        return str(row["semester"])
    modules = row.get("modules")
    if isinstance(modules, dict):
        return str(modules.get("semester") or "")
    return ""


def _teacher_name(row: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [row.get("teacher_first_name"), row.get("teacher_last_name")]
        if part
    )


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


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    return str(value)


def _fallback_reportlab_render(report_spec: dict[str, Any], filename: str) -> None:
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph(html.escape(_latex_to_readable_text(report_spec.get("title") or "Rapport")), styles["Title"]))
    subtitle = report_spec.get("subtitle")
    if subtitle:
        story.append(Paragraph(html.escape(_latex_to_readable_text(subtitle)), styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    for section in report_spec.get("sections", []):
        if not isinstance(section, dict):
            continue
        story.append(Paragraph(html.escape(_latex_to_readable_text(section.get("title") or "Section")), styles["Heading2"]))
        if section.get("summary"):
            story.append(Paragraph(html.escape(_latex_to_readable_text(section["summary"])), styles["Normal"]))
            story.append(Spacer(1, 0.2 * cm))

        if section.get("type") == "table":
            columns = section.get("columns") or []
            rows = section.get("rows") or []
            table_data = [[_latex_to_readable_text(column.get("label") or column.get("key") or "") for column in columns]]
            for row in rows:
                if isinstance(row, dict):
                    table_data.append([_latex_to_readable_text(row.get(str(column.get("key")))) for column in columns])
                elif isinstance(row, list):
                    table_data.append([_latex_to_readable_text(cell) for cell in row])

            if len(table_data) == 1:
                table_data.append(["Aucune donnee"] + [""] * max(len(table_data[0]) - 1, 0))
            table = Table(table_data, repeatRows=1)
            table.setStyle(_table_style())
            story.append(table)
        elif section.get("type") == "text":
            for item in section.get("items") or []:
                for paragraph in str(item).splitlines():
                    if paragraph.strip():
                        story.append(Paragraph(html.escape(_latex_to_readable_text(paragraph.strip())), styles["Normal"]))
        else:
            for item in section.get("items") or []:
                story.append(Paragraph(f"- {html.escape(_latex_to_readable_text(item))}", styles["Normal"]))
        story.append(Spacer(1, 0.5 * cm))

    doc.build(story)


def render_dynamic_pdf(report_spec: dict[str, Any]) -> str:
    """Render a dynamic report JSON spec to PDF.

    Preferred path is Jinja2 HTML -> WeasyPrint PDF. If WeasyPrint is not
    installed or native libraries are missing, ReportLab renders the same spec.
    """
    filename = _pdf_path(str(report_spec.get("slug") or report_spec.get("type") or "report"))
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from weasyprint import HTML

        env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.filters["pdf_text"] = _pdf_text_html
        template = env.get_template(PDF_TEMPLATE)
        html_content = template.render(report=report_spec)
        HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(filename)
    except Exception:
        _fallback_reportlab_render(report_spec, filename)
    return filename


def build_notes_report_spec(student: dict[str, Any], notes: list[dict[str, Any]]) -> dict[str, Any]:
    name = _student_name(student) or "Etudiant"
    return {
        "type": "notes",
        "slug": "notes",
        "title": f"Releve de notes - {name}",
        "subtitle": f"Filiere : {_student_filiere(student)} | Niveau : {_student_level(student)}",
        "sections": [
            {
                "title": "Notes",
                "type": "table",
                "columns": [
                    {"key": "module", "label": "Module"},
                    {"key": "exam_type", "label": "Type"},
                    {"key": "score", "label": "Note"},
                    {"key": "coefficient", "label": "Coeff."},
                    {"key": "published_at", "label": "Date"},
                ],
                "rows": [
                    {
                        "module": _module_name(note),
                        "exam_type": note.get("exam_type"),
                        "score": note.get("score"),
                        "coefficient": note.get("coefficient"),
                        "published_at": str(note.get("published_at") or "")[:10],
                    }
                    for note in notes
                ],
            }
        ],
    }


def build_bulletin_report_spec(
    student: dict[str, Any],
    notes: list[dict[str, Any]],
    absences: list[dict[str, Any]],
) -> dict[str, Any]:
    name = _student_name(student) or "Etudiant"
    return {
        "type": "bulletin",
        "slug": "bulletin",
        "title": "Bulletin academique",
        "subtitle": f"{name} - {_student_filiere(student)} - {_student_level(student)}",
        "sections": [
            build_notes_report_spec(student, notes)["sections"][0],
            {
                "title": "Absences",
                "type": "table",
                "columns": [
                    {"key": "module", "label": "Module"},
                    {"key": "date", "label": "Date"},
                    {"key": "justified", "label": "Justifiee"},
                ],
                "rows": [
                    {
                        "module": _module_name(absence),
                        "date": str(absence.get("date") or "")[:10],
                        "justified": bool(absence.get("justified")),
                    }
                    for absence in absences
                ],
            },
        ],
    }


def build_timetable_report_spec(
    student: dict[str, Any],
    modules: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    name = _student_name(student) or "Etudiant"
    return {
        "type": "timetable",
        "slug": "timetable",
        "title": f"Emploi du temps - {name}",
        "subtitle": f"Filiere : {_student_filiere(student)} | Niveau : {_student_level(student)}",
        "sections": [
            {
                "title": "Modules",
                "type": "table",
                "columns": [
                    {"key": "module", "label": "Module"},
                    {"key": "code", "label": "Code"},
                    {"key": "semester", "label": "Semestre"},
                    {"key": "teacher", "label": "Enseignant"},
                ],
                "rows": [
                    {
                        "module": _module_name(module),
                        "code": module.get("module_code") or module.get("code"),
                        "semester": _module_semester(module),
                        "teacher": _teacher_name(module),
                    }
                    for module in modules
                ],
            },
            {
                "title": "Evenements a venir",
                "type": "table",
                "columns": [
                    {"key": "title", "label": "Titre"},
                    {"key": "event_type", "label": "Type"},
                    {"key": "start_date", "label": "Debut"},
                    {"key": "end_date", "label": "Fin"},
                    {"key": "location", "label": "Lieu"},
                ],
                "rows": [
                    {
                        "title": event.get("title"),
                        "event_type": event.get("event_type"),
                        "start_date": str(event.get("start_date") or "")[:16],
                        "end_date": str(event.get("end_date") or "")[:16],
                        "location": event.get("location"),
                    }
                    for event in events
                ],
            },
        ],
    }


def build_notes_pdf(student: dict[str, Any], notes: list[dict[str, Any]]) -> str:
    return render_dynamic_pdf(build_notes_report_spec(student, notes))


def build_bulletin_pdf(
    student: dict[str, Any],
    notes: list[dict[str, Any]],
    absences: list[dict[str, Any]],
) -> str:
    return render_dynamic_pdf(build_bulletin_report_spec(student, notes, absences))


def build_timetable_pdf(
    student: dict[str, Any],
    modules: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> str:
    return render_dynamic_pdf(build_timetable_report_spec(student, modules, events))


@tool
def render_dynamic_pdf_tool(report_spec: dict[str, Any]) -> dict[str, Any]:
    """Render any dynamic report JSON spec and return its local PDF path."""
    try:
        path = render_dynamic_pdf(report_spec)
        return _success({"file_path": path})
    except Exception as exc:
        return _failure(exc)


PDF_TOOLS = [
    render_dynamic_pdf_tool,
]
