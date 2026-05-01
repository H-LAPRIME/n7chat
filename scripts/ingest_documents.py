"""
scripts/ingest_documents.py
─────────────────────────────
Bulk-ingests PDFs from a given folder into the FAISS vector index.

Usage:
    python scripts/ingest_documents.py --path ./storage/documents/pdfs/
"""

import argparse
import os
import uuid
from pathlib import Path

import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Adjust sys.path so agents/ is importable when run from project root
import sys
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

from agents.utils.embeddings import add_chunks_to_index
from backend.app.utils.storage import upload_document_to_supabase

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def parse_pdf(pdf_path: str, file_url: str = None) -> list[dict]:
    """Extract text chunks from a PDF file."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    doc_id = str(uuid.uuid4())
    filename = os.path.basename(pdf_path)
    chunks: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            splits = splitter.split_text(text)
            for idx, chunk_text in enumerate(splits):
                chunks.append(
                    {
                        "doc_id": doc_id,
                        "filename": filename,
                        "page": page_num,
                        "chunk_index": idx,
                        "text": chunk_text,
                        "file_url": file_url,
                    }
                )
    return chunks


def ingest_folder(folder_path: str) -> None:
    pdf_files = list(Path(folder_path).glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {folder_path}")
        return

    for pdf_path in pdf_files:
        print(f"  Ingesting: {pdf_path.name} ...", end=" ", flush=True)
        
        # 1. Upload to Supabase first
        file_url = None
        try:
            file_url = upload_document_to_supabase(str(pdf_path), pdf_path.name)
            print("[Cloud Uploaded]", end=" ", flush=True)
        except Exception as e:
            print(f"[Upload Failed: {str(e)}]", end=" ", flush=True)

        # 2. Extract and chunk PDF
        chunks = parse_pdf(str(pdf_path), file_url=file_url)
        if chunks:
            add_chunks_to_index(chunks)
            print(f"{len(chunks)} chunks indexed ✓")
        else:
            print("no text extracted ✗")

    print(f"\n✅ Done — ingested {len(pdf_files)} file(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDFs into FAISS index")
    parser.add_argument(
        "--path",
        default="./storage/documents/pdfs/",
        help="Path to folder containing PDF files",
    )
    args = parser.parse_args()
    ingest_folder(args.path)
