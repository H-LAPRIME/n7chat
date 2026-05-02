"""
scripts/add_enseignant.py
─────────────────────────
Script pour ajouter un nouvel enseignant (rôle admin) dans la base de données.

Usage:
    python scripts/add_enseignant.py --email prof@n7.fr --password MonMotDePasse123
"""

import sys
import argparse
import os
from pathlib import Path

# Ajouter le dossier parent au path pour importer les modules du backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv("backend/.env")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.models.user import User

def add_enseignant(email, password):
    # Vérification de l'URL de la base de données
    db_url = os.environ.get("POSTGRES_URL")
    if not db_url:
        print("❌ Erreur : POSTGRES_URL non trouvée dans le fichier .env")
        return

    engine = create_engine(db_url)
    
    try:
        with Session(engine) as session:
            # Vérifier si l'utilisateur existe déjà
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                print(f"❌ Erreur : L'utilisateur {email} existe déjà.")
                return

            # Création de l'enseignant
            new_prof = User(email=email, role="admin") # Le rôle technique reste 'admin'
            new_prof.set_password(password)
            
            session.add(new_prof)
            session.commit()
            print(f"✅ Succès : L'enseignant {email} a été ajouté avec succès.")
            print(f"   Rôle : Enseignant (admin)")

    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ajouter un nouvel Enseignant")
    parser.add_argument("--email", required=True, help="Email de l'enseignant")
    parser.add_argument("--password", required=True, help="Mot de passe de l'enseignant")
    
    args = parser.parse_args()
    add_enseignant(args.email, args.password)
