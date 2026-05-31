"""Generic PDF report helpers.

This module turns whatever context the graph has into a report specification
that the PDF renderer can display. It intentionally avoids hard-coded report
templates like "notes" or "bulletin" as the default behavior.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


ReportType = str
NOISE_PATTERNS = (
    "je ne peux pas",
    "je n'ai pas pu",
    "données nécessaires",
    "donnees necessaires",
    "données manquantes",
    "donnees manquantes",
    "identifiant de l'étudiant",
    "identifiant de l'etudiant",
    "failed",
    "error",
    "erreur",
    "vector search",
    "rag",
    "sql",
    "agent",
    "pipeline",
    "database",
    "base de données",
    "base de donnees",
    "aucune donnee structuree",
    "aucune donnée structurée",
)


def infer_report_type_task(
    message: str,
    explicit_type: str | None = None,
) -> ReportType:
    """Return a loose report label, defaulting to a general report."""
    if explicit_type:
        return explicit_type
    lowered = message.lower()
    if any(word in lowered for word in ["resume", "résumé", "summarize", "summary", "synthese", "synthèse"]):
        return "summary"
    return "report"


def _student_name(student: dict[str, Any]) -> str:
    return " ".join(part for part in [student.get("first_name"), student.get("last_name")] if part).strip()


def _student_filiere(student: dict[str, Any]) -> str:
    return str(student.get("filiere_name") or student.get("filiere") or "")


def _student_level(student: dict[str, Any]) -> str:
    return str(student.get("level_name") or student.get("level") or "")


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, (str, int, float)) or value is None:
        return value
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    return str(value)


def _clean_text(text: str, max_chars: int = 9000) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
    return cleaned[:max_chars]


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _text_section(title: str, content: str, max_chars: int = 9000) -> dict[str, Any] | None:
    cleaned = _clean_text(content, max_chars=max_chars)
    if not cleaned:
        return None
    return {"title": title, "type": "text", "items": [cleaned]}


def _has_noise(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def _strip_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    return value.strip(" -")


def _is_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and set(stripped.replace(" ", "")) <= {"-", "_", "|", ":"}


def _clean_export_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("|") and line.endswith("|"):
            lines.append(raw_line)
            continue
        if not line or _is_separator(line):
            lines.append("")
            continue
        if "http://" in line or "https://" in line:
            continue
        if "lien vers" in line.lower() or "téléchargez" in line.lower() or "telechargez" in line.lower():
            continue
        if _has_noise(line):
            continue
        lines.append(raw_line)

    cleaned = "\n".join(lines).strip()
    useful_markers = [
        "voici",
        "emploi du temps",
        "résumé",
        "resume",
        "résumé",
        "synthese",
        "synthèse",
        "|",
        "lundi",
        "mardi",
        "mercredi",
        "cours",
        "francais",
    ]
    paragraphs = re.split(r"\n\s*\n", cleaned)
    while paragraphs and not any(_fold_text(marker) in _fold_text(paragraphs[0]) for marker in useful_markers):
        paragraphs.pop(0)
    return "\n\n".join(paragraphs).strip()


def _table_from_markdown(title: str, table_lines: list[str]) -> dict[str, Any] | None:
    if len(table_lines) < 2:
        return None
    header = [_strip_markdown(cell) for cell in table_lines[0].strip().strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        cells = [_strip_markdown(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) < len(header):
            cells.extend([""] * (len(header) - len(cells)))
        rows.append({key or f"col_{index}": cells[index] for index, key in enumerate(header)})
    columns = [{"key": key or f"col_{index}", "label": key or f"Colonne {index + 1}"} for index, key in enumerate(header)]
    return {"title": title, "type": "table", "columns": columns, "rows": rows}


def _flush_items(sections: list[dict[str, Any]], title: str, items: list[str]) -> None:
    cleaned_items = [_strip_markdown(item) for item in items if _strip_markdown(item)]
    if cleaned_items:
        sections.append({"title": title, "type": "list", "items": cleaned_items})


def _sections_from_answer(text: str) -> list[dict[str, Any]]:
    cleaned = _clean_export_text(text)
    if not cleaned:
        return []

    sections: list[dict[str, Any]] = []
    current_title = "Synthese"
    items: list[str] = []
    table_lines: list[str] = []

    def flush_table() -> None:
        nonlocal table_lines
        if table_lines:
            table = _table_from_markdown(current_title, table_lines)
            if table:
                sections.append(table)
            table_lines = []

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            flush_table()
            continue

        heading_match = re.match(r"^#{1,6}\s+(.+)$", line) or re.match(r"^\*\*(.+)\*\*:?\s*$", line)
        if heading_match:
            flush_table()
            _flush_items(sections, current_title, items)
            items = []
            current_title = _strip_markdown(heading_match.group(1))
            continue

        if line.startswith("|") and line.endswith("|"):
            _flush_items(sections, current_title, items)
            items = []
            table_lines.append(line)
            continue

        flush_table()
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        items.append(bullet.group(1) if bullet else line)

    flush_table()
    _flush_items(sections, current_title, items)
    return sections


def _table_section(title: str, rows: list[dict[str, Any]], max_columns: int = 6) -> dict[str, Any] | None:
    if not rows:
        return None

    keys: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            if key in keys or key in {"id", "embedding", "metadata"} or key.endswith("_id"):
                continue
            if isinstance(value, (dict, list)):
                continue
            keys.append(key)
            if len(keys) >= max_columns:
                break
        if len(keys) >= max_columns:
            break

    if not keys:
        return None

    return {
        "title": title,
        "type": "table",
        "columns": [{"key": key, "label": key.replace("_", " ").title()} for key in keys],
        "rows": [{key: _normalize_cell(row.get(key)) for key in keys} for row in rows if isinstance(row, dict)],
    }


def _source_section(sources: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = []
    for source in sources[:10]:
        if not isinstance(source, dict):
            continue
        rows.append(
            {
                "title": source.get("title") or source.get("source_name") or "-",
                "source_type": source.get("source_type") or source.get("file_type") or "-",
                "source": source.get("source_name") or source.get("source_url") or "-",
            }
        )
    return _table_section("Sources", rows, max_columns=3)


def _append_sql_sections(sections: list[dict[str, Any]], sql_context: dict[str, Any]) -> None:
    formatted = sql_context.get("formatted_context")
    if formatted:
        section = _text_section("Donnees structurees", str(formatted))
        if section:
            sections.append(section)

    for key, value in sql_context.items():
        if key == "formatted_context" or not isinstance(value, dict):
            continue
        data = value.get("data")
        if isinstance(data, list):
            section = _table_section(key.replace("_", " ").title(), data)
            if section:
                sections.append(section)
        elif isinstance(data, dict):
            section = _table_section(key.replace("_", " ").title(), [data])
            if section:
                sections.append(section)


def build_dynamic_report_spec(
    *,
    message: str,
    selected_type: ReportType,
    student: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
    absences: list[dict[str, Any]] | None = None,
    modules: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    data_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a generic report spec from conversation, RAG, SQL, and sources."""
    data_context = data_context or {}
    rag_context = data_context.get("rag") if isinstance(data_context.get("rag"), dict) else {}
    sql_context = data_context.get("sql") if isinstance(data_context.get("sql"), dict) else {}
    sources = data_context.get("sources") if isinstance(data_context.get("sources"), list) else []

    name = _student_name(student) or "Etudiant"
    subtitle_parts = [part for part in [_student_filiere(student), _student_level(student)] if part]
    sections: list[dict[str, Any]] = []

    answer_text = str(data_context.get("last_assistant_response") or data_context.get("current_response") or "")
    sections.extend(_sections_from_answer(answer_text))

    rag_text = str(rag_context.get("context") or "")
    section = _text_section("Contenu disponible", rag_text)
    if section and not sections:
        sections.append(section)

    _append_sql_sections(sections, sql_context)

    for title, rows in (
        ("Notes", notes or []),
        ("Absences", absences or []),
        ("Modules", modules or []),
        ("Evenements", events or []),
    ):
        section = _table_section(title, rows)
        if section:
            sections.append(section)

    source_section = _source_section(sources)
    if source_section:
        sections.append(source_section)

    if not sections:
        sections.append(
            {
                "title": "Rapport",
                "type": "list",
                "items": ["Aucun contexte exploitable n'a ete trouve pour generer ce rapport."],
            }
        )

    title = "Rapport PDF"
    if selected_type == "summary":
        title = "Synthese PDF"
    elif "emploi" in _fold_text(data_context.get("last_assistant_response") or ""):
        title = "Rapport - Emploi du temps"

    return {
        "type": selected_type or "report",
        "slug": "report",
        "title": title,
        "subtitle": " | ".join(part for part in [name, *subtitle_parts] if part),
        "request": message,
        "sections": sections,
    }


def build_pdf_answer(
    selected_type: ReportType,
    file_path: str,
    report_spec: dict[str, Any],
    student: dict[str, Any],
    data_context: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the successful PDF agent response dict."""
    return {
        "ok": True,
        "answer": f"Le PDF {selected_type or 'rapport'} est pret: {file_path}",
        "artifact": {"type": selected_type or "report", "file_path": file_path, "report_spec": report_spec},
        "data": {
            "report": report_spec,
            "student": student,
            "context": data_context,
        },
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
