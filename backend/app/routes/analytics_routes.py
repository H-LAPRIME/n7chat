"""
backend/app/routes/analytics_routes.py
─────────────────────────────────────────
/analytics  — dashboard stats (admin only)
"""

from flask import Blueprint, jsonify
from app.auth.jwt_utils import require_role

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/")
@require_role("admin")
def get_analytics():
    """
    GET /analytics  (admin only)
    Returns top questions, user activity, and error counts.
    """
    # TODO: aggregate from Conversations DB + error logs
    return jsonify(
        {
            "top_questions": [],
            "user_activity": {"today": 0, "week": 0},
            "errors": {"count": 0, "last": None},
        }
    ), 200
