"""
agents/utils/embeddings.py
────────────────────────────
Embedding utilities — generate and manage vector embeddings using pgvector.
"""

from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector

env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
load_dotenv(dotenv_path=env_path)

POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL must be set in .env")

engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Ensure pgvector extension exists
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.commit()

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True)
    filename = Column(String)
    page = Column(Integer)
    chunk_index = Column(Integer)
    text = Column(Text)
    file_url = Column(String)
    embedding = Column(Vector(384))

Base.metadata.create_all(bind=engine)

# ── Sentence-Transformers model ───────────────────────────────

@lru_cache(maxsize=1)
def get_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list[str]) -> np.ndarray:
    """Return L2-normalised embeddings for a list of texts."""
    encoder = get_encoder()
    embeddings = encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.astype("float32")

# ── Vector DB management ──────────────────────────────────────

def add_chunks_to_index(chunks: list[dict]) -> None:
    """
    Add text chunks to PostgreSQL vector table.
    Each chunk: {"doc_id": str, "filename": str, "page": int, "chunk_index": int, "text": str}
    """
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    
    with SessionLocal() as session:
        for chunk, vector in zip(chunks, vectors):
            doc = DocumentChunk(
                doc_id=chunk.get("doc_id"),
                filename=chunk.get("filename"),
                page=chunk.get("page"),
                chunk_index=chunk.get("chunk_index"),
                text=chunk.get("text"),
                file_url=chunk.get("file_url"),
                embedding=vector
            )
            session.add(doc)
        session.commit()

def search_index(query: str, top_k: int = 5) -> list[dict]:
    """Return top-K closest chunks using Inner Product."""
    vector = embed_texts([query])[0]
    
    with SessionLocal() as session:
        # max_inner_product sorts by inner product (descending internally via <#>)
        results = session.query(DocumentChunk).order_by(
            DocumentChunk.embedding.max_inner_product(vector)
        ).limit(top_k).all()
        
        return [
            {
                "doc_id": r.doc_id,
                "filename": r.filename,
                "page": r.page,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "file_url": r.file_url,
            }
            for r in results
        ]
