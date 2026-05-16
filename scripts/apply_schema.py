from pathlib import Path

import psycopg
from dotenv import load_dotenv
from os import environ


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCHEMA_PATH = BACKEND / "db" / "schema.sql"


def main() -> None:
    load_dotenv(BACKEND / ".env")
    database_url = environ.get("STRUCTURE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("STRUCTURE_DATABASE_URL is missing from backend/.env")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()

    print("Supabase schema applied.")


if __name__ == "__main__":
    main()
