from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **_: Any):
        if func is None:
            return lambda wrapped: wrapped
        return func


DEFAULT_MAX_CHARS = 3000


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None, **extra}


def _failure(error: Exception | str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": str(error), **extra}


def to_markdown_table(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str] | None = None,
    empty_message: str = "_Aucune donnee._",
) -> str:
    if not rows:
        return empty_message

    selected_columns = list(columns or rows[0].keys())
    header = "| " + " | ".join(selected_columns) + " |"
    sep = "| " + " | ".join(["---"] * len(selected_columns)) + " |"
    lines = [header, sep]

    for row in rows:
        values = [_stringify(row.get(column, "")) for column in selected_columns]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def to_bullet_list(
    rows: Sequence[Mapping[str, Any]],
    title_key: str,
    detail_keys: Sequence[str] | None = None,
    empty_message: str = "_Aucune donnee._",
) -> str:
    if not rows:
        return empty_message

    details = list(detail_keys or [])
    lines = []
    for row in rows:
        title = _stringify(row.get(title_key, ""))
        suffix = " | ".join(
            _stringify(row.get(key, "")) for key in details if row.get(key) is not None
        )
        lines.append(f"- **{title}**" + (f" | {suffix}" if suffix else ""))
    return "\n".join(lines)


def truncate_for_chat(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    if len(text) <= max_chars:
        return text
    overflow = len(text) - max_chars
    return text[:max_chars].rstrip() + f"\n\n_[... truncated: {overflow} more chars]_"


@tool
def markdown_table_tool(
    rows: list[dict[str, Any]],
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Format records as a Markdown table for chat output."""
    try:
        table = to_markdown_table(rows, columns)
        return _success(table, chars=len(table))
    except Exception as exc:
        return _failure(exc, chars=0)


@tool
def bullet_list_tool(
    rows: list[dict[str, Any]],
    title_key: str,
    detail_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Format records as a compact Markdown bullet list."""
    try:
        text = to_bullet_list(rows, title_key, detail_keys)
        return _success(text, chars=len(text))
    except Exception as exc:
        return _failure(exc, chars=0)


@tool
def truncate_text_tool(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:
    """Trim long text to a chat-safe length."""
    try:
        truncated = truncate_for_chat(text, max_chars=max_chars)
        return _success(truncated, chars=len(truncated), truncated=len(truncated) < len(text))
    except Exception as exc:
        return _failure(exc, chars=0, truncated=False)


FORMAT_TOOLS = [
    markdown_table_tool,
    bullet_list_tool,
    truncate_text_tool,
]
