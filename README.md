# N7Chat

N7Chat est une plateforme universitaire avec un assistant IA pour les etudiants,
enseignants et administrateurs. Le projet contient un backend FastAPI et un
frontend Next.js.

## Fonctionnalites principales

- Authentification JWT avec roles `student`, `teacher` et `admin`.
- Chat IA avec routage LangGraph vers SQL, RAG, PDF ou conversation generale.
- Recherche RAG dans les cours, documents administratifs, evenements et emplois du temps.
- Controle d'acces par filiere, module, enseignant, visibilite publique/privee et classe cible.
- Upload et gestion des cours par enseignant ou administrateur.
- Upload et gestion des documents administratifs.
- Gestion des evenements avec visibilite publique ou ciblee.
- Profil utilisateur avec photo stockee dans le bucket Supabase `profiles`.
- Generation de rapports PDF a partir du contexte de conversation.
- Rendu Markdown et formules mathematiques dans le chat.

## Structure

```text
n7chat/
  backend/    API FastAPI, agents IA, outils RAG/SQL/PDF, acces DB
  frontend/   Application Next.js
  test/       Tests backend
  docs/       Documents et assets de rapport locaux
```

## Prerequis

- Python 3.12
- Node.js 20 a 22
- Supabase avec une base PostgreSQL et les buckets requis
- Cles API Mistral

## Configuration backend

Creer `backend/.env` avec au minimum :

```env
STRUCTURE_DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
JWT_SECRET=change-me-with-at-least-32-bytes
MISTRAL_KEY_ORCHESTRATOR=...
MISTRAL_KEY_SQL=...
MISTRAL_KEY_RAG=...
MISTRAL_KEY_PDF=...
MISTRAL_MODEL=mistral-large-latest
```

Initialiser l'environnement Python :

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Lancer l'API :

```bash
python -m backend.main
```

API locale par defaut : `http://127.0.0.1:8000`

## Configuration frontend

```bash
cd frontend
npm install
npm run dev
```

Application locale par defaut : `http://localhost:3000`

Le frontend utilise actuellement `http://localhost:8000` comme API dans
`frontend/src/lib/api.ts`.

## Base de donnees

Le schema principal se trouve dans :

```text
backend/db/schema.sql
```

Appliquer ce schema dans Supabase/PostgreSQL avant de lancer l'application.
Les embeddings et recherches vectorielles dependent de la configuration SQL et
des fonctions RPC definies cote base.

## Buckets Supabase

Prevoir les buckets suivants selon les fonctionnalites utilisees :

- `courses` pour les fichiers de cours.
- `documents` pour les documents administratifs.
- `profiles` pour les photos de profil.
- `logos` pour les logos de la plateforme, par exemple `logo_enset.png`.

## Tests et validation

Depuis la racine du projet :

```bash
.\backend\.venv\Scripts\python.exe -m pytest
```

Frontend :

```bash
cd frontend
npm run lint
npm run build
```

## Workflow de developpement

1. Lancer le backend sur le port `8000`.
2. Lancer le frontend sur le port `3000`.
3. Se connecter avec un utilisateur cree dans la base.
4. Tester les pages principales : chat, cours, documents, evenements, profil et admin.
5. Executer les tests avant de pousser.

## Notes securite

- Ne jamais commiter `backend/.env` ni les cles Supabase/Mistral.
- Utiliser un `JWT_SECRET` long, au moins 32 bytes.
- Les acces aux cours, documents et evenements doivent toujours passer par le
  contexte utilisateur issu du JWT.
- Les fichiers indexes dans le vector store doivent conserver leurs metadonnees
  de visibilite pour que le RAG respecte les droits d'acces.

