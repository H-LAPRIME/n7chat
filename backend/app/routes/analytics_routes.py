"""
Analytics routes for admin dashboard.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from sqlalchemy import func

from app.auth.jwt_utils import require_role
from app.models.conversation import ConversationMessage

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/")
@require_role("admin")
def get_analytics():
    now = datetime.utcnow()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = now - timedelta(days=7)

    today_count = ConversationMessage.query.filter(
        ConversationMessage.role == "user",
        ConversationMessage.created_at >= start_today,
    ).count()
    week_count = ConversationMessage.query.filter(
        ConversationMessage.role == "user",
        ConversationMessage.created_at >= start_week,
    ).count()

    top_rows = (
        ConversationMessage.query.with_entities(
            ConversationMessage.content,
            func.count(ConversationMessage.id).label("count"),
        )
        .filter(ConversationMessage.role == "user")
        .group_by(ConversationMessage.content)
        .order_by(func.count(ConversationMessage.id).desc())
        .limit(5)
        .all()
    )

    return jsonify(
        {
            "top_questions": [row.content for row in top_rows],
            "user_activity": {"today": today_count, "week": week_count},
            "errors": {"count": 0, "last": None},
        }
    ), 200
