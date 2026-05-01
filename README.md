# 🧠 N7chat

> AI-powered educational platform with multi-agent orchestration, semantic search, and role-based access.

---

## 📁 Project Structure

```
n7chat/
├── frontend/          # Next.js 14 — TypeScript + TailwindCSS + shadcn/ui
├── backend/           # Flask API Gateway — Auth, Routes, Middleware
│   └── venv/          # Python virtual environment (isolated)
├── agents/            # LangGraph multi-agent system
│   └── utils/         # LLM clients, embeddings
├── storage/
│   ├── documents/pdfs/   # Raw uploaded PDFs
│   ├── faiss_index/      # FAISS vector index files
│   └── processed/        # Chunked document metadata
├── scripts/           # CLI utilities (ingest, seed)
└── tests/             # pytest unit tests
```

---

## ⚡ Quick Start

### 1 — Clone

```bash
git clone https://github.com/H-LAPRIME/n7chat.git
cd n7chat
```

### 2 — Backend (Flask)

```bash
cd backend

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies (already done if venv exists)
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# → Fill in your API keys in .env

# Run
python run.py
```

### 3 — Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local
# → Fill in backend URLs in .env.local
npm run dev
```

### 4 — Ingest Documents (optional)

```bash
# From project root, with backend venv active:
python scripts/ingest_documents.py --path ./storage/documents/pdfs/
```

### 5 — Seed Database (optional)

```bash
python scripts/seed_db.py
```

---

## 🤖 Agent System

| Agent | LLM | Trigger | Role |
|---|---|---|---|
| **Orchestrator** | GROQ (Llama 3) | Every message | Intent classification + routing |
| **FAQ** | GROQ + Redis | `quick_answer` | Cache-first fast answers |
| **Planner** | Gemini Flash 2.0 | `perform_task` | Complex task decomposition |
| **Memory** | Mistral | `save` | Short/long-term memory |
| **Action** | GROQ | CRUD tasks | Inscription, demande, profile |
| **Retrieval/RAG** | GROQ + FAISS | `doc_search` | Hybrid semantic + BM25 search |
| **Fallback** | Gemini Flash 2.0 | `unknown_intent` | Graceful escalation |

---

## 🔐 Auth

- **JWT** access tokens (1 hour) + refresh tokens (7 days)
- **RBAC**: `student` (GET only) · `admin` (full CRUD)
- Endpoints: `POST /auth/register` · `/auth/login` · `/auth/refresh` · `/auth/logout`

---

## 🧪 Tests

```bash
# From project root with venv active:
cd backend && ..\venv\Scripts\activate   # Windows
pytest ../tests/ -v
```

---

## 🌍 Languages

UI supports: **FR** · **AR** · **MA (Darija)** · **EN** — with full RTL support for Arabic.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, TailwindCSS, shadcn/ui |
| Backend | Flask, Flask-SocketIO, Flask-Limiter |
| Orchestration | LangGraph, LangChain |
| LLMs | Groq (Llama 3), Gemini Flash 2.0, Mistral, DeepSeek (OpenRouter) |
| Vector DB | FAISS + sentence-transformers |
| Reranking | BM25 (rank-bm25) |
| Cache | Redis |
| Structured DB | PostgreSQL (SQLAlchemy) |
| Conversation DB | MongoDB |

---

*n7chat v1.0 — Built by pikouch laprime*
