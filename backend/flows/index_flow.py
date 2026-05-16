from __future__ import annotations

from typing import Any

from backend.db.supabase import get_supabase_client
from backend.db.vector import delete_document_chunks, upsert_document_chunk
from backend.tools.rag_tool import embed_text


DEFAULT_CHUNK_WORDS = 500
DEFAULT_OVERLAP_WORDS = 50


def chunk_text(
    text: str,
    size: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_OVERLAP_WORDS,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    return [" ".join(words[index : index + size]) for index in range(0, len(words), step)]


async def index_document(
    *,
    source_type: str,
    source_id: str,
    content: str,
    title: str | None = None,
    source_table: str | None = None,
    source_url: str | None = None,
    module_id: str | None = None,
    user_id: str | None = None,
    module_name: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    """Index any searchable document into document_chunks.

    source_type examples: course, timetable, news, admin_document, event, other.
    content can come from PDF/DOCX/PPTX/text extraction before this flow is called.
    """
    chunks = chunk_text(content)
    delete_document_chunks(source_type=source_type, source_id=source_id)

    for index, chunk in enumerate(chunks):
        upsert_document_chunk(
            source_type=source_type,
            source_id=source_id,
            source_table=source_table,
            source_url=source_url,
            module_id=module_id,
            user_id=user_id,
            chunk_index=index,
            content=chunk,
            embedding=embed_text(chunk),
            title=title,
            source_name=title,
            module_name=module_name,
            filiere=filiere,
            file_type=file_type,
            metadata=metadata or {},
        )

    return len(chunks)


async def trigger_index_course(course_id: str) -> int:
    """Compatibility wrapper for indexing rows from the courses table."""
    supabase = get_supabase_client()
    course = (
        supabase.table("courses")
        .select("*, modules(name, filieres(name))")
        .eq("id", course_id)
        .single()
        .execute()
        .data
    )
    if not course:
        return 0

    module = course.get("modules") or {}
    filiere = module.get("filieres") or {}
    content = f"{course.get('title', '')}. {course.get('description', '')}".strip()
    return await index_document(
        source_type="course",
        source_id=course_id,
        source_table="courses",
        source_url=course.get("file_url"),
        module_id=course.get("module_id"),
        content=content,
        title=course.get("title"),
        module_name=module.get("name"),
        filiere=filiere.get("name"),
        file_type=course.get("file_type"),
        metadata={"uploaded_by": course.get("uploaded_by")},
    )
