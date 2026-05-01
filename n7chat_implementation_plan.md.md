# 🧠 N7chat — Full Implementation Plan

> AI-powered educational platform with multi-agent orchestration, semantic search, and role-based access.

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Technology Stack](#3-technology-stack)
4. [Design Stack](#4-design-stack)
5. [Workflow Stack](#5-workflow-stack)
6. [Implementation Phases](#6-implementation-phases)
7. [Module Breakdown](#7-module-breakdown)
   - [7.1 Security Layer](#71-security-layer)
   - [7.2 API Gateway](#72-api-gateway)
   - [7.3 Frontend (System Dev)](#73-frontend-system-dev)
   - [7.4 Mind Player — Orchestration Engine](#74-mind-player--orchestration-engine)
   - [7.5 Sub-Agents System](#75-sub-agents-system)
   - [7.6 Storage Types](#76-storage-types)
8. [Agent Definitions](#8-agent-definitions)
9. [Data Flow](#9-data-flow)
10. [API Contracts](#10-api-contracts)
11. [Environment Setup](#11-environment-setup)
12. [Folder Structure](#12-folder-structure)
13. [Agent Prompts & Config](#13-agent-prompts--config)
14. [Testing Strategy](#14-testing-strategy)


---

## 1. Project Overview

**n7chat** is an intelligent educational assistant platform with:

- **Role-based users**: `student` (read-only) and `admin` (full CRUD)
- **AI chatbot core** with short-term and long-term memory
- **Multi-agent orchestration** via LangGraph/LangChain
- **Hybrid semantic search** (vector + BM25 re-ranking)
- **Multi-LLM support**: Groq (Llama3), Gemini Flash 2.0, Mistral, DeepSeek (via OpenRouter)
- **Document intelligence**: PDF ingestion, explanation, RAG pipeline
- **Multi-language UI**: FR, AR, MA (Darija), EN, US

---

## 2. Architecture Summary

```
[Student / Admin]
      │
      ▼
[Chatbot Core]  ──────────────────────────────────────────►  [Auth Service JWT+RBAC]
      │
      ▼
[API Gateway — Flask]  (Async | Rate-limiting | Logging)
      │
      ▼
[Orchestrator Agent]  (Understand intent → Route → Combine results)
      │
      ├──► GROQ LLM (Quick answer)
      ├──► Planner Agent (complex tasks → plan)
      ├──► Memory Agent (Mistral | short/long term)
      ├──► Action Agent (CRUD / Inscription / Demande)
      ├──► FAQ Agent (cache-hit fast answers)
      ├──► Retrieval Agent RAG (PDF | règlements | hybrid search)
      └──► Fallback Agent (uncertain intent → escalate → Gemini Flash 2.0)
                │
      [Storage Layer]
      ├── Conversations DB (History / Memory)
      ├── STRUCTUR DB (Roles)
      ├── Cache Layer (in-memory: session, context, cached responses)
      ├── Vector DB FAISS (embeddings, semantic search)
      └── Documents Store (PDFs / Règlements)
```

---

## 3. Technology Stack

### 3.1 Backend

| Layer | Technology | Purpose |
|---|---|---|
| API Gateway | `Flask` + `asyncio` | Async REST endpoints, rate limiting, logging |
| Auth | `JWT` + `RBAC` | Token auth, refresh, role enforcement |
| Orchestration | `LangGraph` | Multi-agent workflow graph |
| LLM — Primary | `Groq API` (Llama 3.x / 70B) | Fast inference, primary Q&A |
| LLM — Planning | `Gemini Flash 2.0` | Complex task decomposition |
| LLM — Memory | `Mistral` (via API) | Short/long-term memory summarization |
| LLM — Fallback | `Gemini Flash 2.0` | Uncertain/escalated intents |
| LLM — OpenRouter | `DeepSeek Free` | Routing to free-tier models |
| Embeddings | `sentence-transformers` or `Gemini embeddings` | Vector creation |
| Vector DB | `FAISS` | Semantic similarity search |
| Re-ranking | `BM25` + cross-encoder | Hybrid search re-rank |
| Cache | `Redis` or in-memory dict | Session, context, response cache |
| Doc Storage | `Local FS` or `S3-compatible` | PDFs, règlements |
| Structured DB | `PostgreSQL` or `SQLite` | Users, roles, courses, modules |
| Conversation DB | `MongoDB` or `PostgreSQL` | Chat history, memory |

### 3.2 Frontend

| Layer | Technology | Purpose |
|---|---|---|
| Framework | `Next.js 14+` (App Router) | SSR, routing, API routes |
| Language | `TypeScript` | Type safety |
| Styling | `TailwindCSS` | Utility-first CSS |
| UI Components | `shadcn/ui` | Accessible component library |
| State | `Zustand` or `Redux Toolkit` | Global state management |
| Realtime | `WebSocket` (Flask-SocketIO) | Live chat streaming |
| i18n | `next-intl` | FR, AR, MA, EN, US |
| Auth Client | `NextAuth.js` or custom JWT | Token management |


---

## 4. Design Stack

### 4.1 UI Design System

- **Design Tool**: Figma
- **Component Library**: shadcn/ui + Radix UI primitives
- **Typography**: Inter (Latin) + Noto Sans Arabic (Arabic/Darija)
- **Color Palette**:
  - Primary: `#6C5CE7` (violet — AI/intelligence)
  - Secondary: `#00B894` (green — success, memory)
  - Accent: `#FDCB6E` (amber — actions, admin)
  - Danger: `#D63031` (red — security, errors)
  - Neutral: `#2D3436` / `#DFE6E9`
- **Dark Mode**: Supported via Tailwind `dark:` classes

### 4.2 UX Principles

- **Role-based UI**: Admin sees full CRUD controls; Student sees read-only
- **Quick-access buttons**: Pre-defined prompt shortcuts per role
- **Responsive**: Mobile-first with collapsible sidebar
- **RTL Support**: Full right-to-left for AR/MA layouts
- **Streaming chat**: Token-by-token response rendering

---

## 5. Workflow Stack

### 5.1 User Message → Response Flow

```
User sends message
      │
      ▼
[Chatbot Core]
  - Attach session context (history + prefs)
  - Attach user profile (long-term memory)
      │
      ▼
[API Gateway — Flask]
  - Validate JWT token
  - Rate limit check
  - Log request
      │
      ▼
[Orchestrator Agent — LangGraph Node]
  - Classify intent:
    │
    ├── "quick_answer"     → GROQ LLM direct
    ├── "perform_task"     → Planner Agent
    ├── "save"             → Memory Agent (Mistral)
    ├── "doc_search"       → Retrieval Agent (RAG)
    └── "unknown_intent"   → Fallback Agent (Gemini)
      │
      ▼
[Sub-Agent executes]
      │
      ▼
[Storage R/W as needed]
  - Read/write Conversations DB
  - CRUD on STRUCTUR DB
  - Vector search on FAISS
  - Cache hit/store on Redis
      │
      ▼
[Response assembled by Orchestrator]
      │
      ▼
[Streamed back to user via WebSocket/HTTP]
```

### 5.2 Document Ingestion Flow (Admin)

```
Admin uploads PDF
      │
      ▼
[Doc Upload Service]
  - Validate file
  - Parse PDF → chunks (LangChain TextSplitter)
      │
      ▼
[LLM Embedding] (sentence-transformers / Gemini)
  - Generate vector embeddings per chunk
      │
      ▼
[FAISS Vector DB]
  - Store vectors + metadata
      │
      ▼
[Documents Store]
  - Save original PDF
      │
      ▼
[STRUCTUR DB]
  - Register document metadata (name, type, date, uploader)
```

### 5.3 Auth Flow

```
User submits credentials
      │
      ▼
[Auth Service]
  - Validate credentials against DB
  - Assign role: student (read-only) | admin (CRUD)
  - Issue JWT (access token + refresh token)
      │
      ▼
[API Gateway]
  - All subsequent requests: validate JWT
  - RBAC middleware: check role permissions per endpoint
      │
      ▼
[Token Expiry]
  - Auto-refresh via refresh token
  - Logout clears tokens
```

---

## 6. Implementation Phases

### Phase 1 — Foundation (Week 1–2)

- [ ] Setup monorepo: `/frontend`, `/backend`, `/agents`, `/storage`
- [ ] Initialize Next.js 14 frontend with Tailwind + shadcn
- [ ] Initialize Flask backend with async support
- [ ] Setup PostgreSQL + MongoDB (or single Postgres with JSONB)
- [ ] Implement JWT Auth Service (login, register, refresh, RBAC middleware)
- [ ] Basic chatbot UI (message input, history display)
- [ ] Connect frontend ↔ backend via HTTP

### Phase 2 — Core Agent Engine (Week 3–4)

- [ ] Integrate Groq API (primary LLM)
- [ ] Build Orchestrator Agent with LangGraph
- [ ] Implement intent classification (quick_answer, task, save, doc_search, unknown)
- [ ] Build Memory Agent (Mistral) with short-term (session) + long-term (DB) memory
- [ ] Build Action Agent (CRUD operations: inscription, demande)
- [ ] Connect WebSocket for streaming responses

### Phase 3 — RAG & Document Intelligence (Week 5–6)

- [ ] PDF upload endpoint (admin only)
- [ ] PDF parsing + chunking (LangChain)
- [ ] Embedding generation + FAISS indexing
- [ ] Retrieval Agent with hybrid search (BM25 + vector + re-rank)
- [ ] FAQ Agent with Redis cache layer
- [ ] Document Store (local or S3)

### Phase 4 — Sub-Agents & Fallback (Week 7–8)

- [ ] Planner Agent (Gemini Flash 2.0) for complex task decomposition
- [ ] Fallback Agent (Gemini Flash 2.0) for uncertain intents
- [ ] OpenRouter integration (DeepSeek free tier)
- [ ] LangGraph orchestration: all agents connected
- [ ] Admin CRUD dashboard (courses, modules, users, documents)

### Phase 5 — Frontend Completion (Week 9–10)

- [ ] Multi-language support (next-intl: FR, AR, MA, EN)
- [ ] RTL layout for Arabic
- [ ] Role-based UI (student vs admin views)
- [ ] Notification system (in-app + email)
- [ ] Analytics dashboard (top questions, user activity, errors)
- [ ] Recommender system UI (courses/modules personalized)
- [ ] Quick-buttons per role

### Phase 6 — Polish (Week 11–12)


- [ ] Rate limiting (Flask-Limiter)
- [ ] Logging (structlog or Python logging → file)
- [ ] Error handling & monitoring (Sentry or simple try/catch logging)
- [ ] End-to-end testing
- [ ] Code review & cleanup
- [ ] README + developer docs
---

## 7. Module Breakdown

### 7.1 Security Layer

**Component**: `Auth Service`

```python
# Stack: Flask + PyJWT + bcrypt

# Endpoints:
POST /auth/register    # Create user (admin only can create admin)
POST /auth/login       # Returns access_token + refresh_token
POST /auth/refresh     # Returns new access_token
POST /auth/logout      # Invalidate refresh token

# RBAC Roles:
# - student: GET only (courses, modules, chat)
# - admin: GET + POST + PUT + DELETE (all resources)

# JWT Payload:
{
  "sub": "user_id",
  "role": "student" | "admin",
  "exp": <timestamp>,
  "iat": <timestamp>
}
```

**Middleware** (applies to all protected routes):

```python
@require_auth
@require_role("admin")
def admin_only_endpoint():
    ...
```

---

### 7.2 API Gateway

**Component**: `Flask API Gateway`

```python
# Features:
# - Async with Flask + asyncio or FastAPI alternative
# - Rate limiting: Flask-Limiter (e.g. 60 req/min per user)
# - Request logging: structlog
# - CORS: flask-cors
# - WebSocket: Flask-SocketIO

# Key Routes:
POST   /chat              # Send message → Orchestrator
GET    /chat/history      # Fetch conversation history
POST   /documents/upload  # Upload PDF (admin)
GET    /courses           # List courses
POST   /courses           # Create course (admin)
PUT    /courses/:id       # Update course (admin)
DELETE /courses/:id       # Delete course (admin)
GET    /analytics         # Dashboard stats (admin)
```

---

### 7.3 Frontend (System Dev)

**Stack**: Next.js 14 + TypeScript + TailwindCSS + shadcn/ui

```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── register/page.tsx
├── (dashboard)/
│   ├── chat/page.tsx          # Main chatbot interface
│   ├── courses/page.tsx       # Course listing
│   ├── documents/page.tsx     # Document upload/browse (admin)
│   ├── analytics/page.tsx     # Analytics dashboard (admin)
│   └── settings/page.tsx
├── components/
│   ├── ChatWindow.tsx         # WebSocket streaming chat
│   ├── QuickButtons.tsx       # Role-based quick prompts
│   ├── Sidebar.tsx            # Role-based navigation
│   └── LanguageSwitcher.tsx   # FR/AR/MA/EN toggle
├── lib/
│   ├── auth.ts                # JWT handling
│   ├── api.ts                 # API client
│   └── socket.ts              # WebSocket client
└── messages/                  # i18n translations
    ├── fr.json
    ├── ar.json
    ├── ma.json
    └── en.json
```

**Key Features**:
- `Quick-Buttons`: Pre-built prompts per role (e.g. student: "Expliquer ce cours", admin: "Ajouter un module")
- `Role-based UI`: Admin panels hidden for students via middleware check
- `Streaming`: Token-by-token chat rendering via WebSocket

---

### 7.4 Mind Player — Orchestration Engine

**Stack**: LangGraph + Python

```python
# agents/orchestrator.py

from langgraph.graph import StateGraph

# Intent types:
INTENTS = [
    "quick_answer",    # → GROQ LLM direct
    "perform_task",    # → Planner Agent
    "save",            # → Memory Agent
    "doc_search",      # → Retrieval Agent (RAG)
    "unknown_intent",  # → Fallback Agent
]

# Graph nodes:
graph = StateGraph(AgentState)
graph.add_node("classify_intent", classify_intent_node)
graph.add_node("groq_direct", groq_direct_node)
graph.add_node("planner", planner_agent_node)
graph.add_node("memory", memory_agent_node)
graph.add_node("retrieval", retrieval_agent_node)
graph.add_node("fallback", fallback_agent_node)
graph.add_node("action", action_agent_node)
graph.add_node("faq", faq_agent_node)

# Conditional edges based on intent classification
graph.add_conditional_edges("classify_intent", route_intent)
```

**Orchestrator Responsibilities**:
1. Receive user message + context
2. Classify intent using a fast LLM prompt
3. Route to the correct sub-agent
4. Combine results if multiple agents are used
5. Stream final response back

---

### 7.5 Sub-Agents System

**Stack**: LangGraph nodes + individual LLM API calls

#### Memory Agent (Mistral)

```python
# Purpose: Short-term (session) + Long-term (DB) memory management
# LLM: Mistral API
# Actions:
#   - save_history: Store conversation turn in Conversations DB
#   - retrieve_context: Fetch last N turns for context window
#   - summarize_long_term: Compress old history into user profile summary
```

#### Planner Agent (Gemini Flash 2.0)

```python
# Purpose: Decompose complex tasks into sub-tasks
# LLM: Gemini Flash 2.0
# Input: Complex user request
# Output: Ordered list of sub-tasks → dispatched to other agents
# Example: "Inscris-moi au cours de Python et explique le module 1"
#   → [action: inscribe_to_course, retrieval: explain_module_1]
```

#### Action Agent (GROQ LLM)

```python
# Purpose: Execute CRUD operations
# LLM: GROQ
# Actions:
#   - inscription: Enroll student in course
#   - demande: Submit a request/ticket
#   - update_profile: Modify user preferences
```

#### FAQ Agent (GROQ LLM + Redis Cache)

```python
# Purpose: Answer frequently asked questions instantly
# Cache: Redis (key = normalized question, value = cached answer)
# Flow: Check cache first → if hit, return cached → else query LLM → store in cache
```

#### Retrieval Agent / RAG (FAISS + BM25 + GROQ)

```python
# Purpose: Search PDFs, règlements, course content
# Steps:
#   1. Embed user query
#   2. FAISS vector search (top-K candidates)
#   3. BM25 keyword search on same corpus
#   4. OpenRouter/DeepSeek or cross-encoder re-ranking
#   5. Feed top chunks to GROQ LLM for answer generation
```

#### Fallback Agent (Gemini Flash 2.0)

```python
# Purpose: Handle uncertain/out-of-scope intents
# LLM: Gemini Flash 2.0
# Actions:
#   - Try to answer generically
#   - If still uncertain, escalate (notify admin or return "Je ne sais pas")
```

---

### 7.6 Storage Types

#### Conversations DB

```python
# Engine: MongoDB (preferred) or PostgreSQL JSONB
# Schema:
{
  "session_id": "uuid",
  "user_id": "uuid",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "summary": "...",  # long-term compression
  "created_at": "..."
}
```

#### STRUCTUR DB (Roles & Courses)

```sql
-- PostgreSQL

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE,
  password_hash TEXT,
  role TEXT CHECK(role IN ('student', 'admin')),
  created_at TIMESTAMP
);

CREATE TABLE courses (
  id UUID PRIMARY KEY,
  title TEXT,
  description TEXT,
  created_by UUID REFERENCES users(id)
);

CREATE TABLE modules (
  id UUID PRIMARY KEY,
  course_id UUID REFERENCES courses(id),
  title TEXT,
  content TEXT
);

CREATE TABLE enrollments (
  user_id UUID REFERENCES users(id),
  course_id UUID REFERENCES courses(id),
  enrolled_at TIMESTAMP,
  PRIMARY KEY (user_id, course_id)
);
```

#### Vector DB (FAISS)

```python
# Library: faiss-cpu or faiss-gpu
# Index type: IndexFlatL2 or IndexIVFFlat (for large scale)
# Metadata store: Alongside FAISS with a JSON/DB mapping index → chunk metadata

# Chunk metadata:
{
  "doc_id": "uuid",
  "filename": "reglements_2024.pdf",
  "page": 3,
  "chunk_index": 12,
  "text": "Les élèves doivent..."
}
```

#### Cache Layer (Redis)

```python
# Keys:
# - "session:{session_id}" → last N messages (TTL: 1 hour)
# - "faq:{normalized_question_hash}" → cached LLM answer (TTL: 24 hours)
# - "context:{user_id}" → user preferences + profile (TTL: session)
```

#### Documents Store

```
/storage/documents/
├── pdfs/
│   ├── reglements_2024.pdf
│   └── programme_python.pdf
└── processed/
    └── reglements_2024/
        ├── chunks.json
        └── metadata.json
```

---

## 8. Agent Definitions

| Agent | LLM | Trigger | Input | Output |
|---|---|---|---|---|
| Orchestrator | GROQ | Every message | user message + context | routed intent |
| Planner | Gemini Flash 2.0 | `perform_task` | complex request | sub-task plan |
| Memory | Mistral | `save` / always | conversation turns | stored/retrieved context |
| Action | GROQ | `perform_task` (CRUD) | task description | CRUD confirmation |
| FAQ | GROQ + Redis | `quick_answer` | question | cached/LLM answer |
| Retrieval/RAG | GROQ + FAISS | `doc_search` | query | sourced answer + citations |
| Fallback | Gemini Flash 2.0 | `unknown_intent` | unclear query | best-effort answer or escalation |

---

## 9. Data Flow

### 9.1 Standard Chat Flow

```
User: "Explique-moi le module 2 du cours Python"

1. Chatbot Core: attach session context + user profile
2. API Gateway: validate JWT (student role) → allow GET operations
3. Orchestrator: classify intent → "doc_search"
4. Retrieval Agent:
   a. Embed query → vector search in FAISS
   b. BM25 keyword search
   c. Re-rank top 5 chunks
   d. Send to GROQ LLM with context prompt
5. GROQ LLM: generate answer from retrieved chunks
6. Memory Agent: save turn to Conversations DB
7. Response: streamed back to user via WebSocket
```

### 9.2 Admin Upload Flow

```
Admin uploads "programme_2025.pdf"

1. API Gateway: validate JWT (admin role) → allow POST
2. Doc Upload Service:
   a. Save to /storage/documents/pdfs/
   b. Parse PDF with PyPDF2 / pdfplumber
   c. Split into chunks (RecursiveCharacterTextSplitter, 512 tokens, 50 overlap)
3. LLM Embedding: generate vectors for each chunk
4. FAISS: add vectors to index
5. STRUCTUR DB: register document metadata
6. Response: "Document indexed successfully"
```

---

## 10. API Contracts

### POST /chat

```json
// Request
{
  "message": "Explique le module 1",
  "session_id": "uuid"
}

// Response (or streamed via WebSocket)
{
  "response": "Le module 1 couvre...",
  "agent_used": "retrieval",
  "sources": [
    { "doc": "programme_python.pdf", "page": 4 }
  ],
  "session_id": "uuid"
}
```

### POST /documents/upload

```
Content-Type: multipart/form-data
Authorization: Bearer <admin_jwt>

file: <binary PDF>
doc_type: "reglements" | "cours" | "autre"
```

### GET /analytics

```json
// Response (admin only)
{
  "top_questions": ["Qu'est-ce que Python?", ...],
  "user_activity": { "today": 42, "week": 300 },
  "errors": { "count": 3, "last": "2025-01-01T12:00:00Z" }
}
```

---

## 11. Environment Setup

### `.env` (Backend)

```env
# LLM APIs
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
MISTRAL_API_KEY=...
OPENROUTER_API_KEY=...

# Auth
JWT_SECRET_KEY=super_secret_key
JWT_ACCESS_EXPIRES=3600       # 1 hour
JWT_REFRESH_EXPIRES=604800    # 7 days

# Databases
POSTGRES_URL=postgresql://user:pass@localhost:5432/n7chat
MONGODB_URL=mongodb://localhost:27017/n7chat
REDIS_URL=redis://localhost:6379

# Storage
DOCS_PATH=/storage/documents
FAISS_INDEX_PATH=/storage/faiss_index

# App
FLASK_ENV=development
FRONTEND_URL=http://localhost:3000
```

### `.env.local` (Frontend)

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_WS_URL=ws://localhost:5000
NEXT_PUBLIC_DEFAULT_LOCALE=fr
```

---

## 12. Folder Structure

```
n7chat/
│
├── frontend/                        # Next.js 14
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── messages/                    # i18n
│   └── public/
│
├── backend/                         # Flask API Gateway
│   ├── app/
│   │   ├── __init__.py
│   │   ├── auth/                    # JWT + RBAC
│   │   ├── routes/                  # chat, docs, courses, analytics
│   │   ├── middleware/              # rate_limit, logging, cors
│   │   └── models/                 # DB models
│   ├── config.py
│   └── run.py
│
├── agents/                          # LangGraph Agent System
│   ├── orchestrator.py
│   ├── planner_agent.py
│   ├── memory_agent.py
│   ├── action_agent.py
│   ├── faq_agent.py
│   ├── retrieval_agent.py
│   ├── fallback_agent.py
│   ├── state.py                     # AgentState TypedDict
│   └── utils/
│       ├── llm_clients.py           # Groq, Gemini, Mistral, OpenRouter
│       └── embeddings.py
│
├── storage/
│   ├── documents/                   # Raw PDFs
│   ├── faiss_index/                 # FAISS index files
│   └── processed/                   # Chunked + metadata
│
│
├── scripts/
│   ├── ingest_documents.py          # Bulk PDF ingestion
│   └── seed_db.py                   # Dev data seeding
│
└── tests/
    ├── test_agents.py
    ├── test_auth.py
    └── test_rag.py
```

---

## 13. Agent Prompts & Config

### Orchestrator System Prompt

```
You are an intent classifier for an educational AI assistant.
Given a user message and context, classify the intent as ONE of:
- quick_answer: Simple factual or general question
- perform_task: Request to do something (enroll, submit, create)
- save: Explicitly ask to remember/save something
- doc_search: Question requiring document search (PDFs, regulations, courses)
- unknown_intent: Unclear or out-of-scope

Respond ONLY with the intent label, nothing else.
```

### Retrieval Agent System Prompt

```
You are an educational assistant for n7chat.
Answer the user's question based ONLY on the provided context chunks.
If the context doesn't contain enough information, say so clearly.
Always cite the source document and page number.
Respond in the same language as the user's question.
```

### Fallback Agent System Prompt

```
You are a helpful fallback assistant for n7chat.
The user's question could not be handled by specialized agents.
Try your best to help, but if the question is truly out of scope,
politely explain that you cannot help with this and suggest they
contact an admin or rephrase their question.
```

---

## 14. Testing Strategy

### Unit Tests

```python
# tests/test_agents.py
def test_intent_classification():
    result = classify_intent("Explique le cours Python")
    assert result == "doc_search"

def test_faq_cache_hit():
    # Pre-populate cache
    # Call FAQ agent twice
    # Assert second call returns cached response
    pass

def test_rag_retrieval():
    # Ingest test PDF
    # Query for known content
    # Assert correct chunk retrieved
    pass
```

### Integration Tests

- Full chat flow: message → agent → DB → response
- Auth flow: login → JWT → protected route
- Doc upload: file → parse → embed → FAISS index

### Load Testing

- `locust` for API Gateway rate limiting validation
- Target: 100 concurrent users, <500ms p95 response time

---




---

## 📌 Quick Start for Agent

```bash
# 1.  repo
https://github.com/H-LAPRIME/n7chat.git


# 2. Setup backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
python run.py

# 3. Setup frontend
cd ../frontend
npm install
cp .env.example .env.local  # fill in URLs
npm run dev

# 4. Ingest documents (optional)
cd ..
python scripts/ingest_documents.py --path ./storage/documents/pdfs/


```

---

*Generated from architecture diagram — n7chat v1.0*
*Ready for agent-driven implementation.*
