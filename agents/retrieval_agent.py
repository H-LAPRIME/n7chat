"""
agents/retrieval_agent.py
───────────────────────────
Retrieval Agent (RAG) — FAISS + BM25 + GROQ
Hybrid semantic + keyword search over ingested documents.
"""

from rank_bm25 import BM25Okapi

from agents.state import AgentState
from agents.utils.embeddings import search_index
from agents.utils.llm_clients import get_langchain_openrouter_rag

RETRIEVAL_SYSTEM = """You are an educational assistant for n7chat.
Answer the user's question based ONLY on the provided context chunks below.
If the context doesn't contain enough information, say so clearly.
Always cite the source document and page number when possible.
Respond in the same language as the user's question."""


def _bm25_rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """Re-rank FAISS candidates with BM25 for hybrid search."""
    if not candidates:
        return []
    corpus = [c["text"].split() for c in candidates]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query.split())
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [item for item, _ in ranked[:top_k]]


def retrieval_node(state: AgentState) -> AgentState:
    query = state["user_message"]

    # 1. FAISS vector search
    raw_candidates = search_index(query, top_k=10)

    # 2. BM25 re-ranking
    top_chunks = _bm25_rerank(query, raw_candidates, top_k=5)

    if not top_chunks:
        return {
            **state,
            "agent_used": "retrieval",
            "response": "Je n'ai pas trouvé de documents pertinents pour votre question.",
            "sources": [],
        }

    # 3. Build context for GROQ
    context = "\n\n".join(
        f"[Source: {c.get('filename','?')}, page {c.get('page','?')}]\n{c['text']}"
        for c in top_chunks
    )
    sources = [
        {"doc": c.get("filename", "?"), "page": c.get("page", "?")}
        for c in top_chunks
    ]

    llm = get_langchain_openrouter_rag()
    response = llm.invoke(
        [
            {"role": "system", "content": RETRIEVAL_SYSTEM},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ]
    )

    return {
        **state,
        "agent_used": "retrieval",
        "response": response.content.strip(),
        "sources": sources,
    }
