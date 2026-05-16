from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.db.supabase import get_database_url


EMBEDDING_DIMENSIONS = 1024
DEFAULT_SOURCE_TYPE = "other"


def _format_vector(embedding: Sequence[float]) -> str:
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"embedding must contain {EMBEDDING_DIMENSIONS} values, "
            f"got {len(embedding)}"
        )
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def upsert_document_chunk(
    *,
    source_type: str = DEFAULT_SOURCE_TYPE,
    source_id: str | None = None,
    source_table: str | None = None,
    source_url: str | None = None,
    module_id: str | None = None,
    user_id: str | None = None,
    chunk_index: int,
    content: str,
    embedding: Sequence[float],
    title: str | None = None,
    source_name: str | None = None,
    module_name: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_chunks (
                  id, source_type, source_id, source_table, source_url,
                  module_id, user_id, chunk_index, content, embedding,
                  title, source_name, module_name, filiere, file_type, metadata
                )
                VALUES (
                  COALESCE(%(id)s, uuid_generate_v4()), %(source_type)s,
                  %(source_id)s, %(source_table)s, %(source_url)s,
                  %(module_id)s, %(user_id)s, %(chunk_index)s, %(content)s,
                  %(embedding)s::vector, %(title)s, %(source_name)s,
                  %(module_name)s, %(filiere)s, %(file_type)s,
                  %(metadata)s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_type = EXCLUDED.source_type,
                  source_id = EXCLUDED.source_id,
                  source_table = EXCLUDED.source_table,
                  source_url = EXCLUDED.source_url,
                  module_id = EXCLUDED.module_id,
                  user_id = EXCLUDED.user_id,
                  chunk_index = EXCLUDED.chunk_index,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  title = EXCLUDED.title,
                  source_name = EXCLUDED.source_name,
                  module_name = EXCLUDED.module_name,
                  filiere = EXCLUDED.filiere,
                  file_type = EXCLUDED.file_type,
                  metadata = EXCLUDED.metadata
                RETURNING *
                """,
                {
                    "id": chunk_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "source_table": source_table,
                    "source_url": source_url,
                    "module_id": module_id,
                    "user_id": user_id,
                    "chunk_index": chunk_index,
                    "content": content,
                    "embedding": _format_vector(embedding),
                    "title": title,
                    "source_name": source_name or title,
                    "module_name": module_name,
                    "filiere": filiere,
                    "file_type": file_type,
                    "metadata": Jsonb(dict(metadata or {})),
                },
            )
            row = cur.fetchone()
        conn.commit()
    return dict(row)


def upsert_document_chunks(chunks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [upsert_document_chunk(**chunk) for chunk in chunks]


def search_document_chunks(
    embedding: Sequence[float],
    *,
    match_count: int = 5,
    source_type: str | None = None,
    source_id: str | None = None,
    module_id: str | None = None,
    user_id: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
) -> list[dict[str, Any]]:
    filters = []
    params: dict[str, Any] = {
        "embedding": _format_vector(embedding),
        "match_count": match_count,
    }

    if source_type:
        filters.append("source_type = %(source_type)s")
        params["source_type"] = source_type
    if source_id:
        filters.append("source_id = %(source_id)s")
        params["source_id"] = source_id
    if module_id:
        filters.append("module_id = %(module_id)s")
        params["module_id"] = module_id
    if user_id:
        filters.append("user_id = %(user_id)s")
        params["user_id"] = user_id
    if filiere:
        filters.append("filiere = %(filiere)s")
        params["filiere"] = filiere
    if file_type:
        filters.append("file_type = %(file_type)s")
        params["file_type"] = file_type

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                  id,
                  source_type,
                  source_id,
                  source_table,
                  source_url,
                  module_id,
                  user_id,
                  chunk_index,
                  content,
                  title,
                  source_name,
                  module_name,
                  filiere,
                  file_type,
                  metadata,
                  1 - (embedding <=> %(embedding)s::vector) AS similarity
                FROM document_chunks
                {where_sql}
                ORDER BY embedding <=> %(embedding)s::vector
                LIMIT %(match_count)s
                """,
                params,
            )
            return [dict(row) for row in cur.fetchall()]


def delete_document_chunks(
    *,
    source_type: str | None = None,
    source_id: str | None = None,
) -> int:
    if not source_type and not source_id:
        raise ValueError("source_type or source_id is required")

    filters = []
    params: dict[str, Any] = {}
    if source_type:
        filters.append("source_type = %(source_type)s")
        params["source_type"] = source_type
    if source_id:
        filters.append("source_id = %(source_id)s")
        params["source_id"] = source_id

    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM document_chunks WHERE {' AND '.join(filters)}",
                params,
            )
            deleted = cur.rowcount
        conn.commit()
    return deleted


def upsert_course_chunk(
    *,
    course_id: str,
    module_id: str | None,
    chunk_index: int,
    content: str,
    embedding: Sequence[float],
    title: str | None = None,
    module_name: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    return upsert_document_chunk(
        chunk_id=chunk_id,
        source_type="course",
        source_id=course_id,
        source_table="courses",
        module_id=module_id,
        chunk_index=chunk_index,
        content=content,
        embedding=embedding,
        title=title,
        source_name=title,
        module_name=module_name,
        filiere=filiere,
        file_type=file_type,
        metadata={"legacy_source": "course_chunks"},
    )


def upsert_course_chunks(chunks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [upsert_course_chunk(**chunk) for chunk in chunks]


def search_course_chunks(
    embedding: Sequence[float],
    *,
    match_count: int = 5,
    course_id: str | None = None,
    module_id: str | None = None,
    filiere: str | None = None,
) -> list[dict[str, Any]]:
    return search_document_chunks(
        embedding,
        match_count=match_count,
        source_type="course",
        source_id=course_id,
        module_id=module_id,
        filiere=filiere,
    )


def delete_course_chunks(course_id: str) -> int:
    return delete_document_chunks(source_type="course", source_id=course_id)
