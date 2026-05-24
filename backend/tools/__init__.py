from backend.tools.calendar_tool import (
    CALENDAR_TOOLS,
    format_emploi_table,
    format_events_list,
)
from backend.tools.format_tool import (
    FORMAT_TOOLS,
    to_bullet_list,
    to_markdown_table,
    truncate_for_chat,
)
from backend.tools.pdf_tool import (
    PDF_TOOLS,
    build_bulletin_pdf,
    build_notes_pdf,
    build_timetable_pdf,
    render_dynamic_pdf,
)
from backend.tools.rag_tool import (
    RAG_TOOLS,
    embed_text,
    embed_texts,
    format_rag_context,
    search_document_content,
    vector_search,
)
from backend.tools.sql_tool import (
    SQL_TOOLS,
    query_absences,
    query_emploi,
    query_events,
    query_modules,
    query_notes,
    query_student_profile,
)


LANGGRAPH_TOOLS = [
    *SQL_TOOLS,
    *RAG_TOOLS,
    *PDF_TOOLS,
    *CALENDAR_TOOLS,
    *FORMAT_TOOLS,
]


__all__ = [
    "LANGGRAPH_TOOLS",
    "SQL_TOOLS",
    "RAG_TOOLS",
    "PDF_TOOLS",
    "CALENDAR_TOOLS",
    "FORMAT_TOOLS",
    "embed_text",
    "embed_texts",
    "vector_search",
    "format_rag_context",
    "search_document_content",
    "build_notes_pdf",
    "build_bulletin_pdf",
    "build_timetable_pdf",
    "render_dynamic_pdf",
    "format_emploi_table",
    "format_events_list",
    "to_markdown_table",
    "to_bullet_list",
    "truncate_for_chat",
    "query_notes",
    "query_emploi",
    "query_absences",
    "query_modules",
    "query_student_profile",
    "query_events",
]
