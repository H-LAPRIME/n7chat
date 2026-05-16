from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from psycopg.rows import dict_row

from backend.db.supabase import get_database_url
import psycopg


EMBEDDING_DIMENSIONS = 1024


def _format_vector(embedding: Sequence[float]) -> str:
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"embedding must contain {EMBEDDING_DIMENSIONS} values, "
            f"got {len(embedding)}"
        )
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def upsert_course_chunk(
    *,
    course_id: str,
    module_id: str,
    chunk_index: int,
    content: str,
    embedding: Sequence[float],
    title: str | None = None,
    module_name: str | None = None,
    filiere: str | None = None,
    file_type: str | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO course_chunks (
                  id, course_id, module_id, chunk_index, content, embedding,
                  title, module_name, filiere, file_type
                )
                VALUES (
                  COALESCE(%(id)s, uuid_generate_v4()), %(course_id)s,
                  %(module_id)s, %(chunk_index)s, %(content)s,
                  %(embedding)s::vector, %(title)s, %(module_name)s,
                  %(filiere)s, %(file_type)s
                )
                ON CONFLICT (id) DO UPDATE SET
                  course_id = EXCLUDED.course_id,
                  module_id = EXCLUDED.module_id,
                  chunk_index = EXCLUDED.chunk_index,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  title = EXCLUDED.title,
                  module_name = EXCLUDED.module_name,
                  filiere = EXCLUDED.filiere,
                  file_type = EXCLUDED.file_type
                RETURNING *
                """,
                {
                    "id": chunk_id,
                    "course_id": course_id,
                    "module_id": module_id,
                    "chunk_index": chunk_index,
                    "content": content,
                    "embedding": _format_vector(embedding),
                    "title": title,
                    "module_name": module_name,
                    "filiere": filiere,
                    "file_type": file_type,
                },
            )
            row = cur.fetchone()
        conn.commit()
    return dict(row)


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
    filters = []
    params: dict[str, Any] = {
        "embedding": _format_vector(embedding),
        "match_count": match_count,
    }

    if course_id:
        filters.append("course_id = %(course_id)s")
        params["course_id"] = course_id
    if module_id:
        filters.append("module_id = %(module_id)s")
        params["module_id"] = module_id
    if filiere:
        filters.append("filiere = %(filiere)s")
        params["filiere"] = filiere

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                  id,
                  course_id,
                  module_id,
                  chunk_index,
                  content,
                  title,
                  module_name,
                  filiere,
                  file_type,
                  1 - (embedding <=> %(embedding)s::vector) AS similarity
                FROM course_chunks
                {where_sql}
                ORDER BY embedding <=> %(embedding)s::vector
                LIMIT %(match_count)s
                """,
                params,
            )
            return [dict(row) for row in cur.fetchall()]


def delete_course_chunks(course_id: str) -> int:
    with psycopg.connect(get_database_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM course_chunks WHERE course_id = %s", (course_id,))
            deleted = cur.rowcount
        conn.commit()
    return deleted
