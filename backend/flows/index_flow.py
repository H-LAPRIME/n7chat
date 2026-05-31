from __future__ import annotations

from typing import Any
from uuid import uuid5, NAMESPACE_URL

from backend.db.supabase import execute, fetch_one
from backend.db.vector import delete_document_chunks, upsert_document_chunk
from backend.tools.rag_tool import embed_text


DEFAULT_CHUNK_WORDS = 500
DEFAULT_OVERLAP_WORDS = 50
ADMIN_DOCUMENT_SOURCE_TYPES = {
    "admin_document",
    "timetable",
    "emploi_du_temps",
    "news",
    "event",
    "other",
}


def resolve_admin_document_source_type(document_category: str | None) -> str:
    """Map an admin upload category to a document_chunks source_type."""
    category = (document_category or "admin_document").strip().lower()
    if category == "emploi_du_temps":
        return "timetable"
    if category in {"timetable", "news", "event", "other"}:
        return category
    return "admin_document"


def _audience_label(visibility_scope: str | None, filiere: str | None = None, module_name: str | None = None) -> str:
    scope = visibility_scope or "public"
    if scope == "public":
        return "Public"
    if scope == "module":
        return f"Module: {module_name}" if module_name else "Specific module"
    if scope == "filiere":
        return f"Class: {filiere}" if filiere else "Specific class"
    return scope


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
    filiere_id: str | None = None,
    visibility_scope: str = "public",
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
            filiere_id=filiere_id,
            visibility_scope=visibility_scope,
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
    course = fetch_one(
        """
        SELECT
          c.*,
          m.name AS module_name,
          m.filiere_id AS module_filiere_id,
          f.name AS filiere_name,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name,
          e.teacher_code
        FROM courses c
        LEFT JOIN modules m ON m.id = c.module_id
        LEFT JOIN filieres f ON f.id = COALESCE(c.filiere_id, m.filiere_id)
        LEFT JOIN enseignants e ON e.id = c.uploaded_by
        WHERE c.id = %(id)s
        """,
        {"id": course_id},
    )
    if not course:
        return 0

    course = dict(course)
    visibility_scope = course.get("visibility_scope") or ("filiere" if course.get("module_filiere_id") else "public")
    filiere_id = course.get("filiere_id") or course.get("module_filiere_id")
    uploader_name = " ".join(part for part in [course.get("teacher_first_name"), course.get("teacher_last_name")] if part).strip()
    content = f"{course.get('title', '')}. {course.get('description', '')}".strip()
    try:
        count = await index_document(
            source_type="course",
            source_id=course_id,
            source_table="courses",
            source_url=course.get("file_url"),
            module_id=course.get("module_id"),
            filiere_id=filiere_id,
            visibility_scope=visibility_scope,
            content=content,
            title=course.get("title"),
            module_name=course.get("module_name"),
            filiere=course.get("filiere_name"),
            file_type=course.get("file_type"),
            metadata={
                "uploaded_by": str(course.get("uploaded_by")) if course.get("uploaded_by") else None,
                "uploader_name": uploader_name,
                "uploader_role": "teacher",
                "teacher_code": course.get("teacher_code"),
                "accessibility": _audience_label(visibility_scope, course.get("filiere_name"), course.get("module_name")),
            },
        )
        execute("UPDATE courses SET index_status = 'indexed' WHERE id = %(id)s", {"id": course_id})
        return count
    except Exception:
        execute("UPDATE courses SET index_status = 'failed' WHERE id = %(id)s", {"id": course_id})
        raise


async def index_course_content(course_id: str, content: str) -> int:
    """Index extracted course-file text for an existing course row."""
    course = fetch_one(
        """
        SELECT
          c.*,
          m.name AS module_name,
          m.filiere_id AS module_filiere_id,
          f.name AS filiere_name,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name,
          e.teacher_code
        FROM courses c
        LEFT JOIN modules m ON m.id = c.module_id
        LEFT JOIN filieres f ON f.id = COALESCE(c.filiere_id, m.filiere_id)
        LEFT JOIN enseignants e ON e.id = c.uploaded_by
        WHERE c.id = %(id)s
        """,
        {"id": course_id},
    )
    if not course:
        return 0

    course = dict(course)
    visibility_scope = course.get("visibility_scope") or ("filiere" if course.get("module_filiere_id") else "public")
    filiere_id = course.get("filiere_id") or course.get("module_filiere_id")
    uploader_name = " ".join(part for part in [course.get("teacher_first_name"), course.get("teacher_last_name")] if part).strip()
    fallback = f"{course.get('title', '')}. {course.get('description', '')}".strip()
    searchable = "\n\n".join(part for part in [fallback, content.strip()] if part)
    try:
        count = await index_document(
            source_type="course",
            source_id=course_id,
            source_table="courses",
            source_url=course.get("file_url"),
            module_id=course.get("module_id"),
            filiere_id=filiere_id,
            visibility_scope=visibility_scope,
            content=searchable,
            title=course.get("title"),
            module_name=course.get("module_name"),
            filiere=course.get("filiere_name"),
            file_type=course.get("file_type"),
            metadata={
                "uploaded_by": str(course.get("uploaded_by")) if course.get("uploaded_by") else None,
                "uploader_name": uploader_name,
                "uploader_role": "teacher",
                "teacher_code": course.get("teacher_code"),
                "accessibility": _audience_label(visibility_scope, course.get("filiere_name"), course.get("module_name")),
                "indexed_content": "uploaded_file",
            },
        )
        execute("UPDATE courses SET index_status = 'indexed' WHERE id = %(id)s", {"id": course_id})
        return count
    except Exception:
        execute("UPDATE courses SET index_status = 'failed' WHERE id = %(id)s", {"id": course_id})
        raise


async def index_admin_document_upload(
    *,
    storage_path: str,
    public_url: str,
    title: str,
    content: str,
    file_type: str | None = None,
    uploaded_by: str | None = None,
    uploader_name: str | None = None,
    description: str | None = None,
    document_category: str | None = None,
    visibility_scope: str = "public",
    filiere_id: str | None = None,
    module_id: str | None = None,
) -> int:
    """Index an uploaded administrative document stored in the documents bucket."""
    searchable = "\n\n".join(part for part in [title, description or "", content.strip()] if part)
    source_type = resolve_admin_document_source_type(document_category)
    source_id = str(uuid5(NAMESPACE_URL, f"n7chat:{source_type}:{storage_path}"))
    return await index_document(
        source_type=source_type,
        source_id=source_id,
        source_table="storage.documents",
        source_url=public_url,
        module_id=module_id,
        filiere_id=filiere_id,
        visibility_scope=visibility_scope,
        content=searchable,
        title=title,
        file_type=file_type,
        metadata={
            "storage_path": storage_path,
            "uploaded_by": uploaded_by,
            "uploader_name": uploader_name or "Admin",
            "uploader_role": "admin",
            "description": description,
            "document_category": document_category or "admin_document",
            "visibility_scope": visibility_scope,
            "filiere_id": filiere_id,
            "module_id": module_id,
            "accessibility": _audience_label(visibility_scope),
            "indexed_content": "uploaded_file",
        },
    )
