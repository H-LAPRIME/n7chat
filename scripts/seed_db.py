"""
Seed the configured backend database with initial dev users.

Usage:
    python scripts/seed_db.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from app import create_app, db
from app.models.user import User


def upsert_user(email: str, password: str, role: str) -> None:
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, role=role)
        db.session.add(user)

    user.role = role
    user.set_password(password)


def seed() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        upsert_user("admin@n7chat.dev", "Admin1234!", "admin")
        upsert_user("student@n7chat.dev", "Student1234!", "student")
        db.session.commit()
        print("Seeded: admin@n7chat.dev (admin) and student@n7chat.dev (student)")


if __name__ == "__main__":
    seed()
