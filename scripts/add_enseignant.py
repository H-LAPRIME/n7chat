"""
Add an enseignant account with the backend application database.

Usage:
    python scripts/add_enseignant.py --email prof@n7.fr --password MonMotDePasse123
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from app import create_app, db
from app.models.user import User


def add_enseignant(email: str, password: str) -> None:
    app = create_app()

    with app.app_context():
        db.create_all()

        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"Erreur : l'utilisateur {email} existe deja.")
            return

        new_prof = User(email=email, role="admin")
        new_prof.set_password(password)

        db.session.add(new_prof)
        db.session.commit()

        print(f"Succes : l'enseignant {email} a ete ajoute.")
        print("Role : Enseignant (admin)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajouter un nouvel enseignant")
    parser.add_argument("--email", required=True, help="Email de l'enseignant")
    parser.add_argument("--password", required=True, help="Mot de passe de l'enseignant")

    args = parser.parse_args()
    add_enseignant(args.email, args.password)
