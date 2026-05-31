"""RAG agent.

Thin async wrapper around the LLM task in ``backend.tasks.rag_llm_task``.
Responsible for:
  - Running the pgvector semantic search via ``search_document_content``.
  - Passing the search result to ``answer_from_documents_task`` for the
    Mistral answer.
  - Exposing the async ``run_rag_agent`` entry-point consumed by the graph.

All Mistral client logic and prompts live in ``backend.tasks.rag_llm_task``.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from typing import Any
from urllib.parse import unquote, urlparse

from backend.db.supabase import fetch_all
from backend.flows.document_extract_flow import extract_text_from_bytes
from backend.flows.index_flow import index_course_content
from backend.flows.storage_flow import COURSE_BUCKET, download_storage_file
from backend.tasks import rag_llm_task as _task
from backend.tasks.rag_llm_task import answer_from_documents_task
from backend.tools.rag_tool import search_document_content
from backend.tools.sql_tool import get_filiere_modules
import json

_mistral_client = _task._mistral_client
PUBLIC_FALLBACK_SOURCE_TYPES = ("admin_document", "timetable", "news", "event")
COURSE_MATERIAL_KEYWORDS = (
    "cours",
    "cour",
    "course",
    "support",
    "supports",
    "document",
    "documents",
    "uploaded",
    "upload",
    "uploade",
    "db",
    "base de donnees",
)
COURSE_LIST_KEYWORDS = ("existe", "existes", "liste", "quels", "quelles", "deja", "available", "disponible")
FOLLOWUP_CONTENT_KEYWORDS = (
    "contient",
    "contenu",
    "quoi",
    "qoui",
    "dedans",
    "inside",
    "resume",
    "resumer",
    "resme",
    "resmer",
    "résumé",
    "explique",
)
PREVIOUS_ANSWER_REFERENCE_KEYWORDS = (
    "dernier",
    "precedent",
    "precedente",
    "ce dernier",
    "cette derniere",
    "ca",
    "cela",
    "cette reponse",
    "ce resume",
)
COURSE_STOPWORDS = {
    "cours",
    "cour",
    "course",
    "support",
    "supports",
    "document",
    "documents",
    "uploaded",
    "upload",
    "uploade",
    "dans",
    "base",
    "donnees",
    "existe",
    "existes",
    "quels",
    "quelles",
    "quel",
    "quelle",
    "deja",
    "est",
    "que",
    "qui",
    "des",
    "les",
    "une",
    "un",
    "the",
    "there",
    "are",
    "of",
}
TIMETABLE_KEYWORDS = ("emploi", "planning", "horaire", "seance", "séance", "timetable", "schedule")


# ---------------------------------------------------------------------------
# Sync runner (calls retrieval tool then task layer)
# ---------------------------------------------------------------------------


def _is_timetable_query(message: str, filters: dict[str, Any]) -> bool:
    source_type = (filters.get("source_type") or "").lower()
    if source_type in {"timetable", "emploi_du_temps"}:
        return True
    normalized = message.lower()
    return any(keyword in normalized for keyword in TIMETABLE_KEYWORDS)


def _fold_text(value: Any) -> str:
    text = str(value or "").lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _course_query_terms(message: str) -> list[str]:
    folded = _fold_text(message)
    tokens = re.findall(r"[a-z0-9]+", folded)
    return [token for token in tokens if len(token) > 2 and token not in COURSE_STOPWORDS]


def _is_uploaded_course_lookup(message: str, filters: dict[str, Any]) -> bool:
    if (filters.get("source_type") or "").lower() == "course":
        return False
    folded = _fold_text(message)
    has_course_word = any(keyword in folded for keyword in COURSE_MATERIAL_KEYWORDS)
    has_lookup_word = any(keyword in folded for keyword in COURSE_LIST_KEYWORDS)
    return has_course_word and (has_lookup_word or "db" in folded or "base" in folded)


def _is_course_material_request(message: str, filters: dict[str, Any]) -> bool:
    if (filters.get("source_type") or "").lower() == "course":
        return True
    folded = _fold_text(message)
    return any(keyword in folded for keyword in COURSE_MATERIAL_KEYWORDS) and bool(_course_query_terms(message))


def _accessible_courses(user: dict[str, Any], message: str, limit: int = 50) -> list[dict[str, Any]]:
    role = (user.get("role") or "student").lower()
    rows = fetch_all(
        """
        SELECT
          c.id,
          c.title,
          c.description,
          c.file_url,
          c.file_type,
          COALESCE(c.visibility_scope, 'module') AS visibility_scope,
          c.filiere_id,
          c.module_id,
          c.index_status,
          c.created_at,
          m.name AS module_name,
          m.code AS module_code,
          COALESCE(cf.name, f.name) AS filiere_name,
          COALESCE(cf.code, f.code) AS filiere_code,
          e.first_name AS teacher_first_name,
          e.last_name AS teacher_last_name,
          e.teacher_code AS teacher_code,
          CONCAT_WS(' ', e.first_name, e.last_name) AS uploader_name
        FROM courses c
        LEFT JOIN modules m ON m.id = c.module_id
        LEFT JOIN filieres f ON f.id = m.filiere_id
        LEFT JOIN filieres cf ON cf.id = c.filiere_id
        LEFT JOIN enseignants e ON e.id = c.uploaded_by
        WHERE (
          %(role)s = 'admin'
          OR COALESCE(c.visibility_scope, 'module') = 'public'
          OR (%(role)s = 'teacher' AND c.uploaded_by = %(teacher_id)s::uuid)
          OR (
            %(role)s = 'teacher'
            AND (
              m.teacher_id = %(teacher_id)s::uuid
              OR c.filiere_id IN (
                SELECT DISTINCT filiere_id
                FROM modules
                WHERE teacher_id = %(teacher_id)s::uuid
                  AND filiere_id IS NOT NULL
              )
            )
          )
          OR (
            %(role)s = 'student'
            AND (
              c.filiere_id = %(filiere_id)s::uuid
              OR m.filiere_id = %(filiere_id)s::uuid
            )
          )
        )
        ORDER BY c.created_at DESC
        LIMIT %(limit)s
        """,
        {
            "role": role,
            "teacher_id": user.get("teacher_id"),
            "filiere_id": user.get("filiere_id"),
            "limit": limit,
        },
    )
    terms = _course_query_terms(message)
    courses = [dict(row) for row in rows]
    if not terms:
        return courses

    filtered = []
    for course in courses:
        haystack = _fold_text(
            " ".join(
                str(course.get(key) or "")
                for key in (
                    "title",
                    "description",
                    "file_type",
                    "module_name",
                    "module_code",
                    "filiere_name",
                    "filiere_code",
                    "uploader_name",
                    "teacher_code",
                )
            )
        )
        if any(term in haystack for term in terms):
            filtered.append(course)
    return filtered


def _course_access_label(course: dict[str, Any]) -> str:
    scope = course.get("visibility_scope") or "module"
    if scope == "public":
        return "Public"
    if scope == "filiere":
        filiere = course.get("filiere_name") or course.get("filiere_code")
        return f"Classe: {filiere}" if filiere else "Classe specifique"
    module = course.get("module_name") or course.get("module_code")
    return f"Module: {module}" if module else "Module specifique"


def _format_accessible_courses_answer(message: str, courses: list[dict[str, Any]]) -> dict[str, Any]:
    terms = _course_query_terms(message)
    if not courses:
        subject = " ".join(terms) if terms else "demandes"
        return {
            "ok": True,
            "answer": (
                f"Je n'ai trouve aucun support de cours uploade accessible pour {subject}. "
                "Les emplois du temps peuvent contenir des modules programmes, mais aucun fichier de cours correspondant n'est indexe pour ton acces."
            ),
            "context": "",
            "sources": [],
            "error": None,
        }

    lines = ["Voici les supports de cours uploades auxquels tu as acces :"]
    for index, course in enumerate(courses[:12], start=1):
        uploader = course.get("uploader_name") or "Enseignant non renseigne"
        teacher_code = f" ({course.get('teacher_code')})" if course.get("teacher_code") else ""
        module = course.get("module_name") or course.get("module_code") or "module non renseigne"
        file_type = course.get("file_type") or "fichier"
        access = _course_access_label(course)
        line = f"{index}. **{course.get('title') or 'Sans titre'}** - {module} - {uploader}{teacher_code} - {access} - {file_type}"
        if course.get("file_url"):
            line += f"\n   [Ouvrir le {file_type.upper()}]({course['file_url']})"
        lines.append(line)

    if len(courses) > 12:
        lines.append(f"\n{len(courses) - 12} autre(s) support(s) accessible(s) non affiche(s).")
    lines.append("\nSi plusieurs profs ont uploade un cours similaire, choisis le support par nom d'enseignant.")
    return {
        "ok": True,
        "answer": "\n".join(lines),
        "context": "",
        "sources": courses[:12],
        "error": None,
    }


def _last_assistant_message(history: list[dict[str, Any]] | None) -> str:
    return next(
        (str(item.get("content") or "") for item in reversed(history or []) if item.get("role") == "assistant"),
        "",
    )


def _is_course_content_followup(message: str, history: list[dict[str, Any]] | None) -> bool:
    folded = _fold_text(message)
    if not any(keyword in folded for keyword in FOLLOWUP_CONTENT_KEYWORDS):
        return False
    previous = _last_assistant_message(history)
    previous_folded = _fold_text(previous)
    return (
        "voici les supports de cours" in previous_folded
        or "lien:" in previous_folded
        or "ouvrir le" in previous_folded
    )


def _is_previous_answer_followup(message: str, history: list[dict[str, Any]] | None) -> bool:
    if not _last_assistant_message(history):
        return False
    folded = _fold_text(message)
    has_action = any(keyword in folded for keyword in FOLLOWUP_CONTENT_KEYWORDS)
    has_reference = any(keyword in folded for keyword in PREVIOUS_ANSWER_REFERENCE_KEYWORDS)
    return has_action and has_reference


def _answer_from_previous_response(
    message: str,
    previous: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    original_client = _task._mistral_client
    _task._mistral_client = _mistral_client
    try:
        return answer_from_documents_task(
            message,
            {"conversation_context": "last_assistant_response"},
            {
                "ok": True,
                "context": previous,
                "data": [
                    {
                        "source_type": "conversation",
                        "title": "Derniere reponse assistant",
                        "content": previous,
                    }
                ],
                "row_count": 1,
                "error": None,
            },
            user,
        )
    finally:
        _task._mistral_client = original_client


def _resolve_followup_course(user: dict[str, Any], history: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    previous = _last_assistant_message(history)
    if not previous:
        return None
    courses = _accessible_courses(user, "", limit=50)
    if not courses:
        return None

    urls = re.findall(r"https?://\S+", previous)
    for url in urls:
        clean_url = url.rstrip(").,;")
        for course in courses:
            if course.get("file_url") and str(course["file_url"]).rstrip(").,;") == clean_url:
                return course

    titles = re.findall(r"\*\*(.+?)\*\*", previous)
    for title in titles:
        folded_title = _fold_text(title)
        for course in courses:
            if _fold_text(course.get("title")) == folded_title:
                return course
    return courses[0] if len(courses) == 1 else None


def _storage_path_from_public_course_url(file_url: str | None) -> str | None:
    if not file_url:
        return None
    parsed = urlparse(file_url)
    marker = f"/storage/v1/object/public/{COURSE_BUCKET}/"
    if marker not in parsed.path:
        return None
    return unquote(parsed.path.split(marker, 1)[1])


def _filename_from_storage_path(storage_path: str | None) -> str:
    if not storage_path:
        return "course-upload"
    return storage_path.rsplit("/", 1)[-1] or "course-upload"


def _ensure_course_indexed(course: dict[str, Any]) -> bool:
    storage_path = _storage_path_from_public_course_url(course.get("file_url"))
    if not storage_path:
        return False
    content = download_storage_file(COURSE_BUCKET, storage_path)
    text = extract_text_from_bytes(
        filename=_filename_from_storage_path(storage_path),
        content=content,
        content_type="application/pdf" if storage_path.lower().endswith(".pdf") else None,
    )
    if not text.strip():
        return False
    asyncio.run(index_course_content(str(course["id"]), text))
    return True


def _tool_result(tool_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def answer_from_documents_sync(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    user = user or {}
    filters = filters or {}
    scoped_filiere_id = filters.get("filiere_id") or user.get("filiere_id")
    scoped_filiere = filters.get("filiere")
    is_timetable_query = _is_timetable_query(message, filters)
    is_course_material_request = _is_course_material_request(message, filters) and not is_timetable_query
    explicit_source_type = filters.get("source_type")
    requested_source_type = explicit_source_type or ("timetable" if is_timetable_query else "course" if is_course_material_request else None)
    allow_public_fallback = (
        not explicit_source_type
        or str(explicit_source_type).lower() in PUBLIC_FALLBACK_SOURCE_TYPES
    )
    if is_course_material_request:
        allow_public_fallback = False
    role = (user.get("role") or "student").lower()
    teacher_id = user.get("teacher_id") if role == "teacher" else None
    is_course_lookup = _is_uploaded_course_lookup(message, filters)
    followup_course = (
        _resolve_followup_course(user, history)
        if _is_course_content_followup(message, history)
        else None
    )
    if not followup_course and _is_previous_answer_followup(message, history):
        return _answer_from_previous_response(message, _last_assistant_message(history), user)

    if is_course_lookup:
        try:
            courses = _accessible_courses(user, message, limit=int(filters.get("top_k", 50)))
            return _format_accessible_courses_answer(message, courses)
        except Exception as exc:
            print(f"[RAG Course Lookup Error] {exc}")
    if followup_course:
        filters = {
            **filters,
            "source_type": "course",
            "source_id": str(followup_course["id"]),
            "top_k": filters.get("top_k", 5),
        }
        requested_source_type = "course"
        allow_public_fallback = False

    # --- vector search ---
    try:
        search_result = search_document_content(
            query=message,
            top_k=int(filters.get("top_k", 5)),
            source_type="course" if is_course_lookup else requested_source_type,
            source_id=filters.get("source_id"),
            module_id=filters.get("module_id") or user.get("module_id"),
            filiere_id=filters.get("filiere_id"),
            accessible_filiere_id=scoped_filiere_id if role not in {"teacher", "admin"} else None,
            accessible_teacher_id=teacher_id,
            # Do NOT fallback to user.get("sub") because courses are uploaded by teachers,
            # so filtering by student's user_id would yield 0 results.
            user_id=filters.get("user_id"),
            filiere=scoped_filiere,
            file_type=filters.get("file_type"),
        )
        if followup_course and not (search_result.get("data") or []):
            try:
                if _ensure_course_indexed(followup_course):
                    search_result = search_document_content(
                        query=message,
                        top_k=int(filters.get("top_k", 5)),
                        source_type="course",
                        source_id=filters.get("source_id"),
                        module_id=None,
                        filiere_id=None,
                        accessible_filiere_id=scoped_filiere_id if role not in {"teacher", "admin"} else None,
                        accessible_teacher_id=teacher_id,
                        user_id=filters.get("user_id"),
                        filiere=None,
                        file_type=filters.get("file_type"),
                    )
            except Exception as exc:
                print(f"[RAG Followup Reindex Error] {exc}")
        if followup_course and not (search_result.get("data") or []):
            return {
                "ok": True,
                "answer": (
                    f"J'ai bien retrouve le support **{followup_course.get('title') or 'cours'}**, "
                    "mais son contenu textuel n'est pas encore disponible dans l'index. "
                    "Tu peux l'ouvrir avec le lien du cours pour consulter le fichier."
                ),
                "context": "",
                "sources": [followup_course],
                "error": None,
            }
        if is_timetable_query and not is_course_lookup and not followup_course and not (search_result.get("data") or []):
            search_result = search_document_content(
                query=message,
                top_k=int(filters.get("top_k", 5)),
                source_type="admin_document",
                source_id=filters.get("source_id"),
                module_id=None,
                filiere_id=None,
                visibility_scope=None,
                accessible_filiere_id=scoped_filiere_id if role not in {"teacher", "admin"} else None,
                accessible_teacher_id=teacher_id,
                user_id=filters.get("user_id"),
                filiere=None,
                file_type=filters.get("file_type"),
            )
        if scoped_filiere_id and not is_course_lookup and not followup_course and not (search_result.get("data") or []) and allow_public_fallback:
            public_rows = []
            public_context_parts = []
            for source_type in PUBLIC_FALLBACK_SOURCE_TYPES:
                public_result = search_document_content(
                    query=message,
                    top_k=max(1, int(filters.get("top_k", 5)) // 2),
                    source_type=source_type,
                    source_id=filters.get("source_id"),
                    module_id=None,
                    filiere_id=None,
                    visibility_scope="public",
                    accessible_filiere_id=scoped_filiere_id if role not in {"teacher", "admin"} else None,
                    accessible_teacher_id=teacher_id,
                    user_id=filters.get("user_id"),
                    filiere=None,
                    file_type=filters.get("file_type"),
                )
                rows = public_result.get("data") or []
                if rows:
                    public_rows.extend(rows)
                    if public_result.get("context"):
                        public_context_parts.append(public_result["context"])
            if public_rows:
                search_result = {
                    "ok": True,
                    "data": public_rows[: int(filters.get("top_k", 5))],
                    "row_count": min(len(public_rows), int(filters.get("top_k", 5))),
                    "context": "\n\n---\n\n".join(public_context_parts),
                    "error": None,
                }
    except Exception as exc:
        print(f"[RAG Agent Error] {exc}")
        search_result = {"context": f"Vector search failed: {exc}", "data": []}

    # --- Inject structured modules (Graceful Fallback) ---
    filiere_id = user.get("filiere_id") or user.get("student", {}).get("filiere_id")
    if filiere_id and requested_source_type != "course" and not followup_course:
        try:
            modules_data = _tool_result(
                get_filiere_modules,
                {"filiere_id": filiere_id, "semester": user.get("semester")},
            )
            structured_context = "\n--- Structured Modules Data ---\n" + json.dumps(modules_data, ensure_ascii=False)
            search_result["context"] = search_result.get("context", "") + structured_context
        except Exception as e:
            print(f"[RAG Modules Error] {e}")

    # --- LLM answer (task layer) ---
    original_client = _task._mistral_client
    _task._mistral_client = _mistral_client
    try:
        return answer_from_documents_task(message, filters, search_result, user)
    finally:
        _task._mistral_client = original_client


# ---------------------------------------------------------------------------
# Async entry-point (used by graph nodes and routers)
# ---------------------------------------------------------------------------


async def run_rag_agent(
    message: str,
    user: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        answer_from_documents_sync, message, user or {}, filters or {}, history or []
    )
