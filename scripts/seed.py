from __future__ import annotations

from datetime import date, datetime, timedelta
from os import environ
from pathlib import Path
from uuid import UUID, uuid5

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
NAMESPACE = UUID("d90bbfcc-7d52-4b59-a5d8-0f8f9161789d")
PASSWORD_HASH = "dev-password-hash-change-me"


def stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE, name))


def upsert(cur: psycopg.Cursor, table: str, row: dict[str, object]) -> None:
    columns = list(row.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    update_sql = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in columns if column != "id"
    )

    cur.execute(
        f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {update_sql}
        """,
        [row[column] for column in columns],
    )


def main() -> None:
    load_dotenv(BACKEND / ".env")
    database_url = environ.get("STRUCTURE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("STRUCTURE_DATABASE_URL is missing from backend/.env")

    now = datetime.utcnow()
    users = {
        "admin": stable_id("user:admin@n7chat.local"),
        "teacher_amal": stable_id("user:amal.benali@n7chat.local"),
        "teacher_youssef": stable_id("user:youssef.elidrissi@n7chat.local"),
        "student_sara": stable_id("user:sara.elamrani@n7chat.local"),
        "student_omar": stable_id("user:omar.elfassi@n7chat.local"),
    }
    departments = {
        "informatique": stable_id("department:informatique"),
        "mathematiques": stable_id("department:mathematiques"),
    }
    levels = {
        "l1": stable_id("level:l1"),
        "l2": stable_id("level:l2"),
        "l3": stable_id("level:l3"),
    }
    filieres = {
        "gi": stable_id("filiere:gi"),
        "mi": stable_id("filiere:mi"),
    }
    teachers = {
        "amal": stable_id("teacher:amal"),
        "youssef": stable_id("teacher:youssef"),
    }
    students = {
        "sara": stable_id("student:sara"),
        "omar": stable_id("student:omar"),
    }
    modules = {
        "bd": stable_id("module:bd"),
        "algo": stable_id("module:algo"),
        "analyse": stable_id("module:analyse"),
    }
    courses = {
        "bd_intro": stable_id("course:bd_intro"),
        "algo_graphs": stable_id("course:algo_graphs"),
        "analyse_limits": stable_id("course:analyse_limits"),
    }
    conversations = {
        "sara": stable_id("conversation:sara:first"),
    }

    seed_rows: list[tuple[str, dict[str, object]]] = [
        (
            "users",
            {
                "id": users["admin"],
                "email": "admin@n7chat.local",
                "password_hash": PASSWORD_HASH,
                "role": "admin",
                "is_active": True,
            },
        ),
        (
            "users",
            {
                "id": users["teacher_amal"],
                "email": "amal.benali@n7chat.local",
                "password_hash": PASSWORD_HASH,
                "role": "teacher",
                "is_active": True,
            },
        ),
        (
            "users",
            {
                "id": users["teacher_youssef"],
                "email": "youssef.elidrissi@n7chat.local",
                "password_hash": PASSWORD_HASH,
                "role": "teacher",
                "is_active": True,
            },
        ),
        (
            "users",
            {
                "id": users["student_sara"],
                "email": "sara.elamrani@n7chat.local",
                "password_hash": PASSWORD_HASH,
                "role": "student",
                "is_active": True,
            },
        ),
        (
            "users",
            {
                "id": users["student_omar"],
                "email": "omar.elfassi@n7chat.local",
                "password_hash": PASSWORD_HASH,
                "role": "student",
                "is_active": True,
            },
        ),
        (
            "departments",
            {
                "id": departments["informatique"],
                "name": "Informatique",
                "description": "Departement informatique et systemes d'information",
            },
        ),
        (
            "departments",
            {
                "id": departments["mathematiques"],
                "name": "Mathematiques",
                "description": "Departement mathematiques appliquees",
            },
        ),
        ("levels", {"id": levels["l1"], "name": "Licence 1", "order_number": 1}),
        ("levels", {"id": levels["l2"], "name": "Licence 2", "order_number": 2}),
        ("levels", {"id": levels["l3"], "name": "Licence 3", "order_number": 3}),
        (
            "filieres",
            {
                "id": filieres["gi"],
                "department_id": departments["informatique"],
                "name": "Genie Informatique",
                "code": "GI",
                "description": "Developpement logiciel, donnees et reseaux",
                "duration_years": 3,
            },
        ),
        (
            "filieres",
            {
                "id": filieres["mi"],
                "department_id": departments["mathematiques"],
                "name": "Mathematiques et Informatique",
                "code": "MI",
                "description": "Mathematiques appliquees et informatique",
                "duration_years": 3,
            },
        ),
        (
            "enseignants",
            {
                "id": teachers["amal"],
                "user_id": users["teacher_amal"],
                "teacher_code": "ENS-001",
                "first_name": "Amal",
                "last_name": "Benali",
                "specialization": "Bases de donnees",
                "department_id": departments["informatique"],
                "office": "B-204",
                "phone": "+212600000001",
            },
        ),
        (
            "enseignants",
            {
                "id": teachers["youssef"],
                "user_id": users["teacher_youssef"],
                "teacher_code": "ENS-002",
                "first_name": "Youssef",
                "last_name": "El Idrissi",
                "specialization": "Algorithmique",
                "department_id": departments["informatique"],
                "office": "B-208",
                "phone": "+212600000002",
            },
        ),
        (
            "students",
            {
                "id": students["sara"],
                "user_id": users["student_sara"],
                "student_code": "STU-001",
                "first_name": "Sara",
                "last_name": "El Amrani",
                "birth_date": date(2004, 3, 12),
                "gender": "female",
                "phone": "+212600000101",
                "address": "Casablanca",
                "filiere_id": filieres["gi"],
                "level_id": levels["l2"],
                "enrollment_year": 2024,
                "status": "active",
            },
        ),
        (
            "students",
            {
                "id": students["omar"],
                "user_id": users["student_omar"],
                "student_code": "STU-002",
                "first_name": "Omar",
                "last_name": "El Fassi",
                "birth_date": date(2003, 11, 4),
                "gender": "male",
                "phone": "+212600000102",
                "address": "Rabat",
                "filiere_id": filieres["gi"],
                "level_id": levels["l2"],
                "enrollment_year": 2024,
                "status": "active",
            },
        ),
        (
            "modules",
            {
                "id": modules["bd"],
                "filiere_id": filieres["gi"],
                "teacher_id": teachers["amal"],
                "name": "Bases de donnees",
                "code": "GI-S3-BD",
                "semester": 3,
                "coefficient": 2.0,
                "credits": 5.0,
                "description": "Modelisation relationnelle, SQL et transactions",
            },
        ),
        (
            "modules",
            {
                "id": modules["algo"],
                "filiere_id": filieres["gi"],
                "teacher_id": teachers["youssef"],
                "name": "Algorithmique avancee",
                "code": "GI-S3-ALG",
                "semester": 3,
                "coefficient": 2.0,
                "credits": 5.0,
                "description": "Graphes, complexite et structures avancees",
            },
        ),
        (
            "modules",
            {
                "id": modules["analyse"],
                "filiere_id": filieres["mi"],
                "teacher_id": teachers["youssef"],
                "name": "Analyse",
                "code": "MI-S1-ANA",
                "semester": 1,
                "coefficient": 1.5,
                "credits": 4.0,
                "description": "Suites, limites et continuite",
            },
        ),
        (
            "courses",
            {
                "id": courses["bd_intro"],
                "module_id": modules["bd"],
                "title": "Introduction au modele relationnel",
                "description": "Cours d'introduction aux tables, cles et relations.",
                "file_url": "storage://courses/gi-s3-bd/introduction.pdf",
                "file_type": "pdf",
                "uploaded_by": teachers["amal"],
            },
        ),
        (
            "courses",
            {
                "id": courses["algo_graphs"],
                "module_id": modules["algo"],
                "title": "Graphes et parcours",
                "description": "DFS, BFS et representations de graphes.",
                "file_url": "storage://courses/gi-s3-alg/graphes.pdf",
                "file_type": "pdf",
                "uploaded_by": teachers["youssef"],
            },
        ),
        (
            "courses",
            {
                "id": courses["analyse_limits"],
                "module_id": modules["analyse"],
                "title": "Limites de suites",
                "description": "Rappels et exercices corriges sur les limites.",
                "file_url": "storage://courses/mi-s1-ana/limites.pdf",
                "file_type": "pdf",
                "uploaded_by": teachers["youssef"],
            },
        ),
        (
            "notes",
            {
                "id": stable_id("note:sara:bd:cc"),
                "student_id": students["sara"],
                "module_id": modules["bd"],
                "teacher_id": teachers["amal"],
                "exam_type": "cc",
                "score": 16.0,
                "coefficient": 0.4,
            },
        ),
        (
            "notes",
            {
                "id": stable_id("note:sara:bd:exam"),
                "student_id": students["sara"],
                "module_id": modules["bd"],
                "teacher_id": teachers["amal"],
                "exam_type": "exam",
                "score": 14.5,
                "coefficient": 0.6,
            },
        ),
        (
            "notes",
            {
                "id": stable_id("note:omar:algo:cc"),
                "student_id": students["omar"],
                "module_id": modules["algo"],
                "teacher_id": teachers["youssef"],
                "exam_type": "cc",
                "score": 13.0,
                "coefficient": 0.4,
            },
        ),
        (
            "absences",
            {
                "id": stable_id("absence:sara:algo:2026-05-05"),
                "student_id": students["sara"],
                "module_id": modules["algo"],
                "date": date(2026, 5, 5),
                "justified": False,
                "justification_file": None,
                "recorded_by": teachers["youssef"],
            },
        ),
        (
            "events",
            {
                "id": stable_id("event:exam:bd:2026-06-10"),
                "title": "Examen Bases de donnees",
                "description": "Examen final du module Bases de donnees.",
                "event_type": "exam",
                "start_date": datetime(2026, 6, 10, 9, 0),
                "end_date": datetime(2026, 6, 10, 11, 0),
                "location": "Amphi A",
                "created_by": users["admin"],
            },
        ),
        (
            "events",
            {
                "id": stable_id("event:conference:ai:2026-05-28"),
                "title": "Conference IA et education",
                "description": "Rencontre autour des usages de l'IA dans l'enseignement.",
                "event_type": "conference",
                "start_date": datetime(2026, 5, 28, 14, 0),
                "end_date": datetime(2026, 5, 28, 16, 0),
                "location": "Salle polyvalente",
                "created_by": users["admin"],
            },
        ),
        (
            "notifications",
            {
                "id": stable_id("notification:sara:exam_bd"),
                "user_id": users["student_sara"],
                "title": "Examen programme",
                "message": "Votre examen Bases de donnees est prevu le 10/06/2026.",
                "type": "exam",
                "is_read": False,
            },
        ),
        (
            "conversations",
            {
                "id": conversations["sara"],
                "user_id": users["student_sara"],
                "title": "Question sur les notes",
                "context_summary": "L'etudiante demande un resume de ses notes.",
                "started_at": now,
                "updated_at": now,
            },
        ),
        (
            "messages",
            {
                "id": stable_id("message:sara:first:user"),
                "conversation_id": conversations["sara"],
                "sender_type": "user",
                "content": "Peux-tu me donner mes notes en bases de donnees ?",
                "message_type": "text",
            },
        ),
        (
            "messages",
            {
                "id": stable_id("message:sara:first:assistant"),
                "conversation_id": conversations["sara"],
                "sender_type": "assistant",
                "content": "Tu as 16.0 au controle continu et 14.5 a l'examen.",
                "message_type": "text",
            },
        ),
        (
            "refresh_tokens",
            {
                "id": stable_id("refresh-token:sara:dev"),
                "user_id": users["student_sara"],
                "token": "dev-refresh-token-sara",
                "expires_at": now + timedelta(days=30),
                "revoked": False,
            },
        ),
        (
            "generated_reports",
            {
                "id": stable_id("report:sara:notes"),
                "user_id": users["student_sara"],
                "type": "notes",
                "file_url": "storage://reports/sara-notes.pdf",
            },
        ),
    ]

    course_chunks = [
        {
            "id": stable_id("chunk:bd_intro:0"),
            "course_id": courses["bd_intro"],
            "module_id": modules["bd"],
            "chunk_index": 0,
            "content": "Le modele relationnel organise les donnees en tables composees de lignes et de colonnes.",
            "embedding": "[" + ",".join(["0"] * 1024) + "]",
            "title": "Introduction au modele relationnel",
            "module_name": "Bases de donnees",
            "filiere": "Genie Informatique",
            "file_type": "pdf",
        },
        {
            "id": stable_id("chunk:algo_graphs:0"),
            "course_id": courses["algo_graphs"],
            "module_id": modules["algo"],
            "chunk_index": 0,
            "content": "Un parcours BFS explore un graphe niveau par niveau a partir d'un sommet source.",
            "embedding": "[" + ",".join(["0"] * 1024) + "]",
            "title": "Graphes et parcours",
            "module_name": "Algorithmique avancee",
            "filiere": "Genie Informatique",
            "file_type": "pdf",
        },
    ]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for table, row in seed_rows:
                upsert(cur, table, row)

            for row in course_chunks:
                cur.execute(
                    """
                    INSERT INTO course_chunks (
                      id, course_id, module_id, chunk_index, content, embedding,
                      title, module_name, filiere, file_type
                    )
                    VALUES (
                      %(id)s, %(course_id)s, %(module_id)s, %(chunk_index)s,
                      %(content)s, %(embedding)s::vector, %(title)s,
                      %(module_name)s, %(filiere)s, %(file_type)s
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
                    """,
                    row,
                )

        conn.commit()

    print("Seed data inserted.")
    print("Demo accounts use password hash placeholder:", PASSWORD_HASH)


if __name__ == "__main__":
    main()
