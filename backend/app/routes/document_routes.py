"""
Document routes: upload, list, open and delete PDF resources.
"""

import os

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app import db
from app.auth.jwt_utils import require_auth, require_role
from app.models.document import Document

documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _pdf_dir() -> str:
    save_dir = os.path.join(current_app.config["DOCS_PATH"], "pdfs")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


@documents_bp.post("/upload")
@require_role("admin")
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    doc_type = request.form.get("doc_type", "autre")

    if file.filename == "" or not _allowed(file.filename):
        return jsonify({"error": "Invalid or missing PDF file"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(_pdf_dir(), filename))

    document = Document(
        filename=filename,
        doc_type=doc_type,
        uploaded_by=request.current_user.get("sub"),
    )
    db.session.add(document)
    db.session.commit()

    return jsonify({"message": "Document uploaded", "document": document.to_dict()}), 201


@documents_bp.get("/")
@require_auth
def list_documents():
    documents = Document.query.order_by(Document.uploaded_at.desc()).all()
    return jsonify({"documents": [document.to_dict() for document in documents]}), 200


@documents_bp.get("/<document_id>/file")
@require_auth
def open_document(document_id: str):
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    return send_from_directory(_pdf_dir(), document.filename, as_attachment=False)


@documents_bp.delete("/<document_id>")
@require_role("admin")
def delete_document(document_id: str):
    document = db.session.get(Document, document_id)
    if not document:
        return jsonify({"error": "Document not found"}), 404

    path = os.path.join(_pdf_dir(), document.filename)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(document)
    db.session.commit()
    return jsonify({"message": "Document deleted", "id": document_id}), 200
