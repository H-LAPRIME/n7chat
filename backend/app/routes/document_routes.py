"""
backend/app/routes/document_routes.py
───────────────────────────────────────
/documents  — upload PDF (admin only), list documents
"""

import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.auth.jwt_utils import require_auth, require_role

documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@documents_bp.post("/upload")
@require_role("admin")
def upload_document():
    """
    POST /documents/upload  (admin only)
    Form fields: file (PDF), doc_type (reglements|cours|autre)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    doc_type = request.form.get("doc_type", "autre")

    if file.filename == "" or not _allowed(file.filename):
        return jsonify({"error": "Invalid or missing PDF file"}), 400

    filename = secure_filename(file.filename)
    save_dir = os.path.join(current_app.config["DOCS_PATH"], "pdfs")
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))

    # TODO: trigger async ingestion pipeline (parse → embed → FAISS → DB)
    return jsonify({"message": "Document uploaded", "filename": filename, "doc_type": doc_type}), 201


@documents_bp.get("/")
@require_auth
def list_documents():
    """GET /documents — list indexed documents."""
    # TODO: fetch from STRUCTUR DB
    return jsonify({"documents": []}), 200
