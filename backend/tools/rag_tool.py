from __future__ import annotations

from collections.abc import Sequence
from os import environ
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.db.vector import search_document_chunks

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **_: Any):
        if func is None:
            return lambda wrapped: wrapped
        return func


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")

DEFAULT_TOP_K = 4
MAX_TOP_K = 12
EMBEDDING_MODEL = "mistral-embed"


def _success(data: Any, **extra: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None, **extra}


def _failure(error: Exception | str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": str(error), **extra}


def _top_k(value: int) -> int:
    return max(1, min(int(value), MAX_TOP_K))


def _mistral_client():
    api_key = environ.get("MISTRAL_KEY_RAG")
    if not api_key:
        raise RuntimeError("MISTRAL_KEY_RAG is missing from backend/.env")

    try:
        try:
            from mistralai import Mistral
        except ImportError:
            from mistralai.client import Mistral
    except ImportError as exc:
        raise RuntimeError("mistralai is not installed. Add it to requirements.") from exc

    return Mistral(api_key=api_key)


def embed_text(text: str) -> list[float]:
    """Create a 1024-dim embedding for one text using the RAG Mistral key."""
    if not text.strip():
        raise ValueError("text cannot be empty")
    response = _mistral_client().embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=[text],
    )
    return list(response.data[0].embedding)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Create embeddings for multiple texts in one provider request."""
    clean_texts = [text for text in texts if text and text.strip()]
    if not clean_texts:
        raise ValueError("texts cannot be empty")
    response = _mistral_client().embeddings.create(
        model=EMBEDDING_MODEL,
        inputs=clean_texts,
    )
    return [list(item.embedding) for item in response.data]


def vector_search(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = None,
    source_id: str | None = None,
    module_id: str | None = None,
    course_id: str | None = None,
    filiere_id: str | None = None,
    visibility_scope: str | None = None,
    accessible_filiere_id: str | None = None,
    accessible_teacher_id: str | None = None,
    user_id: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
) -> list[dict[str, Any]]:
    """Embed a query and search matching document chunks in pgvector."""
    embedding = embed_text(query)
    if course_id and not source_id:
        source_type = "course"
        source_id = course_id
    return search_document_chunks(
        embedding,
        match_count=_top_k(top_k),
        source_type=source_type,
        source_id=source_id,
        module_id=module_id,
        filiere_id=filiere_id,
        visibility_scope=visibility_scope,
        accessible_filiere_id=accessible_filiere_id,
        accessible_teacher_id=accessible_teacher_id,
        user_id=user_id,
        filiere=filiere,
        file_type=file_type,
    )


def format_rag_context(chunks: list[dict[str, Any]], max_chars: int = 6000) -> str:
    """Format retrieved chunks into compact source-aware context."""
    if not chunks:
        return ""

    parts = []
    used = 0
    for chunk in chunks:
        title = chunk.get("title") or chunk.get("source_name") or "Untitled"
        source_type = chunk.get("source_type") or "document"
        metadata = chunk.get("metadata") or {}
        module = chunk.get("module_name") or chunk.get("filiere") or "general"
        uploader = metadata.get("uploader_name") or chunk.get("uploader_name") or "unknown uploader"
        uploader_role = metadata.get("uploader_role") or chunk.get("uploader_role") or "unknown role"
        accessibility = metadata.get("accessibility") or chunk.get("visibility_scope") or "unknown access"
        similarity = chunk.get("similarity")
        score = f" | score={similarity:.3f}" if isinstance(similarity, float) else ""
        content = str(chunk.get("content") or "").strip()
        part = (
            f"[{source_type}: {title} | {module} | uploaded_by={uploader} "
            f"({uploader_role}) | access={accessibility}{score}]\n{content}"
        )
        if used + len(part) > max_chars:
            break
        parts.append(part)
        used += len(part)

    return "\n\n---\n\n".join(parts)


def _search_documents_payload(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = None,
    source_id: str | None = None,
    module_id: str | None = None,
    course_id: str | None = None,
    filiere_id: str | None = None,
    visibility_scope: str | None = None,
    accessible_filiere_id: str | None = None,
    accessible_teacher_id: str | None = None,
    user_id: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    chunks = vector_search(
        query,
        top_k=top_k,
        source_type=source_type,
        source_id=source_id,
        module_id=module_id,
        course_id=course_id,
        filiere_id=filiere_id,
        visibility_scope=visibility_scope,
        accessible_filiere_id=accessible_filiere_id,
        accessible_teacher_id=accessible_teacher_id,
        user_id=user_id,
        filiere=filiere,
        file_type=file_type,
    )
    return _success(
        chunks,
        row_count=len(chunks),
        context=format_rag_context(chunks),
    )


@tool
def embed_text_for_rag(text: str) -> dict[str, Any]:
    """Create an embedding for a query or document chunk."""
    try:
        embedding = embed_text(text)
        return _success(
            {"embedding": embedding},
            dimensions=len(embedding),
            model=EMBEDDING_MODEL,
        )
    except Exception as exc:
        return _failure(exc, dimensions=0, model=EMBEDDING_MODEL)


@tool
def search_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = None,
    source_id: str | None = None,
    module_id: str | None = None,
    course_id: str | None = None,
    user_id: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Search indexed documents semantically and return matching content."""
    try:
        return _search_documents_payload(
            query,
            top_k=top_k,
            source_type=source_type,
            source_id=source_id,
            module_id=module_id,
            course_id=course_id,
            user_id=user_id,
            filiere=filiere,
            file_type=file_type,
        )
    except Exception as exc:
        return _failure(exc, row_count=0, context="")


@tool
def search_course_content(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    module_id: str | None = None,
    course_id: str | None = None,
    filiere_id: str | None = None,
    accessible_filiere_id: str | None = None,
    accessible_teacher_id: str | None = None,
    filiere: str | None = None,
) -> dict[str, Any]:
    """Compatibility tool: search only indexed course documents."""
    try:
        return _search_documents_payload(
            query=query,
            top_k=top_k,
            source_type="course",
            source_id=course_id,
            module_id=module_id,
            filiere_id=filiere_id,
            accessible_filiere_id=accessible_filiere_id,
            accessible_teacher_id=accessible_teacher_id,
            filiere=filiere,
        )
    except Exception as exc:
        return _failure(exc, row_count=0, context="")


def search_document_content(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    source_type: str | None = None,
    source_id: str | None = None,
    module_id: str | None = None,
    filiere_id: str | None = None,
    visibility_scope: str | None = None,
    accessible_filiere_id: str | None = None,
    accessible_teacher_id: str | None = None,
    user_id: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
) -> dict[str, Any]:
    """Runtime helper for semantic document search."""
    return _search_documents_payload(
        query=query,
        top_k=top_k,
        source_type=source_type,
        source_id=source_id,
        module_id=module_id,
        filiere_id=filiere_id,
        visibility_scope=visibility_scope,
        accessible_filiere_id=accessible_filiere_id,
        accessible_teacher_id=accessible_teacher_id,
        user_id=user_id,
        filiere=filiere,
        file_type=file_type,
    )


@tool
def format_rag_context_tool(chunks: list[dict[str, Any]], max_chars: int = 6000) -> dict[str, Any]:
    """Format retrieved RAG chunks into a prompt-ready context block."""
    try:
        context = format_rag_context(chunks, max_chars=max_chars)
        return _success(context, chars=len(context))
    except Exception as exc:
        return _failure(exc, chars=0)


RAG_TOOLS = [
    embed_text_for_rag,
    search_documents,
    search_course_content,
    format_rag_context_tool,
]
