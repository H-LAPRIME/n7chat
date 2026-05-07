"""
Simple course recommendation helpers backed by the application database.
"""

DEFAULT_COURSES = [
    {"id": "c1", "title": "Algorithmique Avancee", "category": "CS", "level": "L3"},
    {"id": "c2", "title": "Intelligence Artificielle", "category": "CS", "level": "M1"},
    {"id": "c3", "title": "Reseaux & Protocoles", "category": "Telecom", "level": "L3"},
    {"id": "c4", "title": "Analyse de Donnees", "category": "Math", "level": "M1"},
    {"id": "c5", "title": "Cybersecurite", "category": "Telecom", "level": "M2"},
]


def get_recommendations(user_id: str, limit: int = 3) -> list[dict]:
    from app.models.course import Course, Enrollment

    enrolled_ids = [
        str(row.course_id)
        for row in Enrollment.query.filter_by(user_id=user_id).all()
    ]
    query = Course.query
    if enrolled_ids:
        valid_course_ids = [course_id for course_id in enrolled_ids if len(course_id) == 36]
        if valid_course_ids:
            query = query.filter(~Course.id.in_(valid_course_ids))

    return [course.to_dict() for course in query.order_by(Course.created_at.desc()).limit(limit).all()]
