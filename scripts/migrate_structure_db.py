"""
Migrate n7chat storage layers.

This script can migrate:
- STRUCTURE DB tables: users, roles/courses, documents metadata, conversations, notifications.
- VECTOR DB table: document_chunks with pgvector embeddings.
- DOCUMENTS: optional PDF upload/re-ingest through scripts.ingest_documents.

Common usage:
    python scripts/migrate_structure_db.py
    python scripts/migrate_structure_db.py --all
    python scripts/migrate_structure_db.py --structure
    python scripts/migrate_structure_db.py --vectors
    python scripts/migrate_structure_db.py --ingest-documents --documents-path ./storage/documents/pdfs
    python scripts/migrate_structure_db.py --all --dry-run

Environment:
    Structure source: SOURCE_STRUCTURE_DATABASE_URL, OLD_STRUCTURE_DATABASE_URL, DATABASE_URL, POSTGRES_URL
    Structure target: STRUCTURE_DATABASE_URL, SUPABASE_DATABASE_URL
    Vector source:    SOURCE_VECTOR_DATABASE_URL, OLD_VECTOR_DATABASE_URL, POSTGRES_URL
    Vector target:    TARGET_VECTOR_DATABASE_URL, NEW_VECTOR_DATABASE_URL, VECTOR_DATABASE_URL
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import URL, make_url

load_dotenv(BACKEND_DIR / ".env", override=True)

VECTOR_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR,
    filename VARCHAR,
    page INTEGER,
    chunk_index INTEGER,
    text TEXT,
    file_url VARCHAR,
    embedding vector(384)
);
"""


def env(name: str) -> str:
    return os.getenv(name, "").strip()


def mask_url(url: str) -> str:
    if not url:
        return "<missing>"
    if "@" not in url or "://" not in url:
        return "<set>"
    scheme, rest = url.split("://", 1)
    host = rest.split("@", 1)[1]
    return f"{scheme}://***@{host}"


def validate_database_url(url: str, label: str) -> None:
    try:
        make_url(url)
    except Exception as exc:
        raise SystemExit(
            f"Invalid {label} database URL. If the password contains special characters "
            f"like @, :, /, ?, #, %, encode them first. Original error: {exc}"
        ) from exc


def parsed_database_url(url: str, label: str) -> URL:
    validate_database_url(url, label)
    parsed = make_url(url)
    if parsed.drivername == "postgres":
        parsed = parsed.set(drivername="postgresql")
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg2")
    return parsed


def create_db_engine(url: str, label: str):
    parsed = parsed_database_url(url, label)
    return create_engine(parsed, pool_pre_ping=True, connect_args={"client_encoding": "utf8"})


def short_error(exc: Exception) -> str:
    return str(exc).replace("\n", " ").strip()[:260]


def database_url_error(label: str, exc: Exception) -> SystemExit:
    return SystemExit(
        f"Could not connect to {label} database. This is usually caused by an unencoded "
        f"password character or the wrong Supabase connection string. Encode password characters "
        f"(@ -> %40, # -> %23, % -> %25, / -> %2F, : -> %3A), and prefer the Supabase "
        f"Transaction Pooler URI on port 6543. Original error: {exc}"
    )


def first_env(*names: str) -> str:
    for name in names:
        value = env(name)
        if value:
            return value
    return ""


def row_data(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def structure_models():
    from app.models.conversation import ConversationMemory, ConversationMessage
    from app.models.course import Course, Enrollment, Module
    from app.models.document import Document
    from app.models.notification import Notification
    from app.models.user import User

    return [
        User,
        Course,
        Module,
        Enrollment,
        Document,
        ConversationMemory,
        ConversationMessage,
        Notification,
    ]


def migrate_structure(dry_run: bool = False) -> None:
    source_url = first_env(
        "SOURCE_STRUCTURE_DATABASE_URL",
        "OLD_STRUCTURE_DATABASE_URL",
        "DATABASE_URL",
        "POSTGRES_URL",
    )
    target_url = first_env("STRUCTURE_DATABASE_URL", "SUPABASE_DATABASE_URL")

    print("Structure DB")
    print(f"  source: {mask_url(source_url)}")
    print(f"  target: {mask_url(target_url)}")

    if not source_url:
        print("  skipped: missing source DB URL")
        return
    if not target_url:
        print("  skipped: missing STRUCTURE_DATABASE_URL / SUPABASE_DATABASE_URL")
        return
    if source_url == target_url:
        print("  skipped: source and target are identical")
        return
    if dry_run:
        print("  dry-run: would copy structured tables")
        return

    from app import db

    source_engine = create_db_engine(source_url, "source structure")
    SourceSession = sessionmaker(bind=source_engine)

    target_engine = create_db_engine(target_url, "target structure")
    models = structure_models()
    try:
        db.Model.metadata.create_all(bind=target_engine)
    except UnicodeDecodeError as exc:
        raise database_url_error("target structure", exc) from exc
    TargetSession = sessionmaker(bind=target_engine)

    with SourceSession() as source_session, TargetSession() as target_session:
        inspector = inspect(source_engine)
        for model in models:
            table_name = model.__tablename__
            try:
                source_columns = {column["name"] for column in inspector.get_columns(table_name)}
                model_columns = [column for column in model.__table__.columns if column.name in source_columns]
                if not model_columns:
                    print(f"  skipped {table_name}: no matching source columns")
                    continue
                rows = source_session.execute(select(*model_columns)).mappings().all()
            except UnicodeDecodeError as exc:
                raise database_url_error("source structure", exc) from exc
            except SQLAlchemyError as exc:
                source_session.rollback()
                print(f"  skipped {table_name}: {exc.__class__.__name__}: {short_error(exc)}")
                continue

            for row in rows:
                target_session.merge(model(**dict(row)))
            try:
                target_session.commit()
            except UnicodeDecodeError as exc:
                raise database_url_error("target structure", exc) from exc
            except SQLAlchemyError as exc:
                target_session.rollback()
                print(f"  skipped {table_name}: {exc.__class__.__name__}: {short_error(exc)}")
                continue
            print(f"  migrated {len(rows)} rows from {table_name}")


def migrate_vectors(dry_run: bool = False, truncate_target: bool = False) -> None:
    source_url = first_env("SOURCE_VECTOR_DATABASE_URL", "OLD_VECTOR_DATABASE_URL", "POSTGRES_URL")
    target_url = first_env("TARGET_VECTOR_DATABASE_URL", "NEW_VECTOR_DATABASE_URL", "VECTOR_DATABASE_URL")

    print("Vector DB")
    print(f"  source: {mask_url(source_url)}")
    print(f"  target: {mask_url(target_url)}")

    if not source_url:
        print("  skipped: missing vector source URL")
        return
    if not target_url:
        print("  skipped: missing vector target URL")
        return
    if source_url == target_url:
        print("  skipped: source and target are identical")
        return
    if dry_run:
        print("  dry-run: would copy document_chunks")
        return

    source_engine = create_db_engine(source_url, "source vector")
    target_engine = create_db_engine(target_url, "target vector")

    try:
        with target_engine.begin() as target:
            target.execute(text(VECTOR_TABLE_SQL))
            if truncate_target:
                target.execute(text("TRUNCATE TABLE document_chunks RESTART IDENTITY;"))
    except UnicodeDecodeError as exc:
        raise database_url_error("target vector", exc) from exc

    try:
        with source_engine.connect() as source:
            rows = source.execute(
                text(
                    """
                    SELECT doc_id, filename, page, chunk_index, text, file_url, embedding::text AS embedding
                    FROM document_chunks
                    ORDER BY id ASC
                    """
                )
            ).mappings().all()
    except UnicodeDecodeError as exc:
        raise database_url_error("source vector", exc) from exc

    insert_sql = text(
        """
        INSERT INTO document_chunks (doc_id, filename, page, chunk_index, text, file_url, embedding)
        VALUES (:doc_id, :filename, :page, :chunk_index, :text, :file_url, CAST(:embedding AS vector))
        """
    )
    try:
        with target_engine.begin() as target:
            if rows:
                target.execute(insert_sql, [dict(row) for row in rows])
    except UnicodeDecodeError as exc:
        raise database_url_error("target vector", exc) from exc

    print(f"  migrated {len(rows)} rows from document_chunks")


def ingest_documents(documents_path: str, dry_run: bool = False) -> None:
    path = Path(documents_path)
    pdfs = list(path.glob("*.pdf"))

    print("Documents")
    print(f"  path: {path}")
    print(f"  pdfs: {len(pdfs)}")

    if dry_run:
        print("  dry-run: would upload PDFs to Supabase Storage and index chunks")
        return
    if not pdfs:
        print("  skipped: no PDFs found")
        return

    from scripts.ingest_documents import ingest_folder

    ingest_folder(str(path))


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input(f"{prompt} [{suffix}]: ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    if answer in {"y", "yes", "o", "oui", "1", "true"}:
        return True
    if answer in {"n", "no", "non", "0", "false"}:
        return False
    print(f"  Invalid answer '{answer}', using default: {'yes' if default else 'no'}")
    return default


def ask_text(prompt: str, default: str) -> str:
    try:
        answer = input(f"{prompt} [{default}]: ").strip()
    except EOFError:
        return default
    if answer.lower() in {"y", "yes", "o", "oui"}:
        return default
    return answer or default


def print_menu() -> None:
    print()
    print("n7chat migration menu")
    print("=====================")
    print("1. Migrate STRUCTURE DB only (Aiven/source -> Supabase)")
    print("2. Migrate VECTOR DB only (document_chunks)")
    print("3. Upload/re-ingest PDFs only (Supabase Storage + vector index)")
    print("4. Migrate STRUCTURE + VECTOR DB")
    print("5. Run everything (STRUCTURE + VECTOR + PDFs)")
    print("6. Dry-run everything")
    print("0. Exit")
    print()


def interactive_main() -> None:
    try:
        while True:
            print_menu()
            choice = input("Choose an option: ").strip()

            if choice == "0":
                print("Bye.")
                return

            if choice not in {"1", "2", "3", "4", "5", "6"}:
                print("Invalid choice. Try again.")
                continue

            dry_run = choice == "6" or ask_yes_no("Dry-run only?", default=True)
            documents_path = "./storage/documents/pdfs"
            truncate_vector_target = False

            run_structure = choice in {"1", "4", "5", "6"}
            run_vectors = choice in {"2", "4", "5", "6"}
            run_documents = choice in {"3", "5", "6"}

            if run_vectors and not dry_run:
                truncate_vector_target = ask_yes_no("Truncate target vector table before copying?", default=False)
            if run_documents:
                documents_path = ask_text("PDF folder path", documents_path)

            print()
            print("Planned migration")
            print("-----------------")
            print(f"Structure DB: {'yes' if run_structure else 'no'}")
            print(f"Vector DB:    {'yes' if run_vectors else 'no'}")
            print(f"Documents:    {'yes' if run_documents else 'no'}")
            print(f"Dry-run:      {'yes' if dry_run else 'no'}")
            print(f"PDF path:     {documents_path if run_documents else '-'}")
            print()

            if not dry_run and not ask_yes_no("This can write to remote databases. Continue?", default=False):
                print("Cancelled.")
                continue

            if run_structure:
                migrate_structure(dry_run=dry_run)
            if run_vectors:
                migrate_vectors(dry_run=dry_run, truncate_target=truncate_vector_target)
            if run_documents:
                ingest_documents(documents_path, dry_run=dry_run)

            print("Migration command complete.")
            if not ask_yes_no("Return to menu?", default=False):
                return
    except KeyboardInterrupt:
        print("\nCancelled.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate n7chat databases and documents")
    parser.add_argument("--all", action="store_true", help="Run structure + vector migrations")
    parser.add_argument("--structure", action="store_true", help="Migrate structured app DB")
    parser.add_argument("--vectors", action="store_true", help="Migrate document_chunks vector DB")
    parser.add_argument("--ingest-documents", action="store_true", help="Upload/re-ingest local PDFs")
    parser.add_argument("--documents-path", default="./storage/documents/pdfs", help="Folder containing PDFs")
    parser.add_argument("--truncate-vector-target", action="store_true", help="Clear target document_chunks before copying")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    args = parser.parse_args()

    if not any([args.all, args.structure, args.vectors, args.ingest_documents]):
        interactive_main()
        return

    if args.all or args.structure:
        migrate_structure(dry_run=args.dry_run)
    if args.all or args.vectors:
        migrate_vectors(dry_run=args.dry_run, truncate_target=args.truncate_vector_target)
    if args.ingest_documents:
        ingest_documents(args.documents_path, dry_run=args.dry_run)

    print("Migration command complete.")


if __name__ == "__main__":
    main()
