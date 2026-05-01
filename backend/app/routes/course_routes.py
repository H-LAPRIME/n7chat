"""
backend/app/routes/course_routes.py
──────────────────────────────────────
/courses  — CRUD for courses and modules
"""

from flask import Blueprint, request, jsonify
from app.auth.jwt_utils import require_auth, require_role

courses_bp = Blueprint("courses", __name__)


@courses_bp.get("/")
@require_auth
def list_courses():
    """GET /courses — list all courses."""
    # TODO: query STRUCTUR DB
    return jsonify({"courses": []}), 200


@courses_bp.post("/")
@require_role("admin")
def create_course():
    """POST /courses — create a new course (admin only)."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    # TODO: insert into STRUCTUR DB
    return jsonify({"message": "Course created", "title": title}), 201


@courses_bp.put("/<course_id>")
@require_role("admin")
def update_course(course_id: str):
    """PUT /courses/<id> — update course (admin only)."""
    data = request.get_json(silent=True) or {}
    # TODO: update in STRUCTUR DB
    return jsonify({"message": "Course updated", "id": course_id}), 200


@courses_bp.delete("/<course_id>")
@require_role("admin")
def delete_course(course_id: str):
    """DELETE /courses/<id> — delete course (admin only)."""
    # TODO: delete from STRUCTUR DB
    return jsonify({"message": "Course deleted", "id": course_id}), 200
