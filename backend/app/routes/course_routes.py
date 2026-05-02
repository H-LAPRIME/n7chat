"""
backend/app/routes/course_routes.py
──────────────────────────────────────
/courses  — CRUD for courses and modules
"""

from flask import Blueprint, request, jsonify
from app.auth.jwt_utils import require_auth, require_role

from app.utils.recommender import get_recommendations

courses_bp = Blueprint("courses", __name__)


@courses_bp.get("/")
@require_auth
def list_courses():
    """GET /courses — list all courses."""
    from app.utils.recommender import MOCK_COURSES
    return jsonify({"courses": MOCK_COURSES}), 200


@courses_bp.get("/recommended")
@require_auth
def recommended_courses():
    """GET /courses/recommended — personalized course list."""
    # sub from JWT is used as user_id
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ")[1]
    from app.auth.jwt_utils import decode_token
    payload = decode_token(token)
    
    recs = get_recommendations(payload.get("sub", "anon"))
    return jsonify({"recommendations": recs}), 200


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
