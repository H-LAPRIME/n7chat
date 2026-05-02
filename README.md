# 🧠 N7chat — Plateforme Éducative Intelligente

**N7chat** est une plateforme d'apprentissage moderne propulsée par l'IA. Elle utilise une architecture multi-agents (LangGraph), une recherche sémantique (RAG) et un système d'authentification complet.

---

## 🚀 Guide d'Installation (Windows)

### 1. Prérequis
Assurez-vous d'avoir installé :
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (3.10+)
- [Git](https://git-scm.com/)

### 2. Clonage du Projet
Ouvrez votre terminal (PowerShell ou CMD) :
```powershell
git clone https://github.com/H-LAPRIME/n7chat.git
cd n7chat
```

### 3. Configuration du Backend (Flask)
```powershell
cd backend

# Création de l'environnement virtuel
python -m venv venv

# Activation de l'environnement
.\venv\Scripts\activate

# Installation des dépendances
pip install -r requirements.txt
pip install flask-sqlalchemy gevent-websocket

# Configuration des variables d'environnement
# Modifiez le fichier .env avec vos clés API et identifiants SMTP
notepad .env 

# Lancement du serveur
python run.py
```

### 4. Configuration du Frontend (Next.js)
Ouvrez un **deuxième terminal** dans le dossier racine :
```powershell
cd frontend

# Installation des dépendances
npm install

# Configuration des variables d'environnement
notepad .env.local
# Assurez-vous que NEXT_PUBLIC_API_URL=http://localhost:5000

# Lancement de l'interface
npm run dev
```

---

## 🔐 Fonctionnalités Clés

### 📧 Récupération de Mot de Passe (OTP)
Le système intègre désormais un flux sécurisé par code à 6 chiffres :
1. L'utilisateur demande une récupération via son email.
2. Un code **OTP** est envoyé via SMTP (Gmail).
3. L'utilisateur saisit le code et son nouveau mot de passe directement sur l'interface.

### 🤖 Système Multi-Agents
- **Orchestrateur** : Analyse l'intention et route vers le bon agent.
- **RAG Agent** : Recherche intelligente dans les documents PDF via FAISS.
- **Action Agent** : Gestion des inscriptions et du profil.
- **Memory Agent** : Conservation du contexte de la conversation.

---

## 🛠 Commandes Utiles (Outils CLI)

| Action | Commande (avec venv activé) |
|---|---|
| **Ingérer des PDFs** | `python scripts/ingest_documents.py --path ./storage/documents/pdfs/` |
| **Ajouter un Admin** | `python scripts/add_enseignant.py --email nom@n7.fr --password Pass123` |
| **Lancer les tests** | `pytest tests/ -v` |

---

## 📂 Structure du Monorepo
- `frontend/` : Next.js 14, TypeScript, TailwindCSS.
- `backend/` : Flask API, Auth JWT, SQLite (SQLAlchemy).
- `agents/` : Orchestration LangGraph & LLMs.
- `storage/` : Index FAISS et documents bruts.

---
*Développé avec ❤️ par H-LAPRIME — n7chat v1.2*
