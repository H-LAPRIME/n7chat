"""
scripts/seed_db.py
────────────────────
Seeds the PostgreSQL database with initial dev data.
Run once after running database migrations.

Usage:
    python scripts/seed_db.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv("backend/.env")

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models.user import Base, User


def seed():
    engine = create_engine(os.environ["POSTGRES_URL"])
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Seed admin user
        admin = User(email="admin@n7chat.dev", role="admin")
        admin.set_password("Admin1234!")

        # Seed student user
        student = User(email="student@n7chat.dev", role="student")
        student.set_password("Student1234!")

        session.add_all([admin, student])
        session.commit()
        print("✅ Seeded: admin@n7chat.dev (admin) and student@n7chat.dev (student)")


if __name__ == "__main__":
    seed()
