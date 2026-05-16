from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from functools import lru_cache
from os import environ
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from supabase import Client, create_client


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / "backend" / ".env"


load_dotenv(ENV_PATH)


def _required_env(name: str) -> str:
    value = environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is missing from backend/.env")
    return value


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    return create_client(
        _required_env("SUPABASE_URL"),
        _required_env("SUPABASE_SERVICE_KEY"),
    )


def get_database_url() -> str:
    return _required_env("STRUCTURE_DATABASE_URL")


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(
    query: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())


def fetch_one(
    query: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute(
    query: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount


def insert_row(table: str, data: dict[str, Any]) -> dict[str, Any]:
    response = get_supabase_client().table(table).insert(data).execute()
    return response.data[0]


def upsert_row(
    table: str,
    data: dict[str, Any],
    on_conflict: str = "id",
) -> dict[str, Any]:
    response = (
        get_supabase_client()
        .table(table)
        .upsert(data, on_conflict=on_conflict)
        .execute()
    )
    return response.data[0]


def select_rows(
    table: str,
    columns: str = "*",
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    query = get_supabase_client().table(table).select(columns)
    for column, value in (filters or {}).items():
        query = query.eq(column, value)
    return query.execute().data
