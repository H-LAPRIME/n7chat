"""
Course routes: list, recommendations and admin CRUD.
"""

from flask import Blueprint, jsonify, request

from app import db
from app.auth.jwt_utils import require_auth, require_role
from app.models.course import Course
from app.utils.recommender import DEFAULT_COURSES, get_recommendations

courses_bp = Blueprint("courses", __name__)


def _seed_courses_if_empty() -> None:
    if Course.query.count() > 0:
        return
    for course in DEFAULT_COURSES:
        db.session.add(
            Course(
                title=course["title"],
                description=course.get("description", f"Module {course.get('category', 'general')} - niveau {course.get('level', 'N/A')}."),
            )
        )
    db.session.commit()


@courses_bp.get("/")
@require_auth
def list_courses():
    _seed_courses_if_empty()
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return jsonify({"courses": [course.to_dict() for course in courses]}), 200


@courses_bp.get("/recommended")
@require_auth
def recommended_courses():
    _seed_courses_if_empty()
    recs = get_recommendations(request.current_user.get("sub", "anon"))
    return jsonify({"recommendations": recs}), 200


@courses_bp.post("/")
@require_role("admin")
def create_course():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()

    if not title:
        return jsonify({"error": "title is required"}), 400

    course = Course(
        title=title,
        description=description,
        created_by=request.current_user.get("sub"),
    )
    db.session.add(course)
    db.session.commit()

    return jsonify({"message": "Course created", "course": course.to_dict()}), 201


@courses_bp.put("/<course_id>")
@require_role("admin")
def update_course(course_id: str):
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    description = data.get("description")

    if title is not None:
        title = title.strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        course.title = title
    if description is not None:
        course.description = description.strip()

    db.session.commit()
    return jsonify({"message": "Course updated", "course": course.to_dict()}), 200


@courses_bp.delete("/<course_id>")
@require_role("admin")
def delete_course(course_id: str):
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted", "id": course_id}), 200
