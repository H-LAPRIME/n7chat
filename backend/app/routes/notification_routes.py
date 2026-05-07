"""
Notification routes: list, read and admin broadcast.
"""

from flask import Blueprint, jsonify, request

from app import db, socketio
from app.auth.jwt_utils import require_auth, require_role
from app.models.notification import Notification

notifications_bp = Blueprint("notifications", __name__)


def _seed_default_notifications() -> None:
    if Notification.query.count() > 0:
        return

    db.session.add_all(
        [
            Notification(
                title="Bienvenue sur n7chat !",
                message="Explorez vos modules de cours et discutez avec l'IA.",
                type="info",
            ),
            Notification(
                title="Nouveau PDF disponible",
                message="Les documents ajoutes par les enseignants seront visibles ici.",
                type="update",
            ),
        ]
    )
    db.session.commit()


@notifications_bp.get("/")
@require_auth
def list_notifications():
    _seed_default_notifications()
    user_id = request.current_user.get("sub")
    notifications = (
        Notification.query.filter((Notification.user_id.is_(None)) | (Notification.user_id == user_id))
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"notifications": [notification.to_dict() for notification in notifications]}), 200


@notifications_bp.post("/read/<notification_id>")
@require_auth
def mark_as_read(notification_id):
    notification = db.session.get(Notification, notification_id)
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    notification.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


@notifications_bp.post("/broadcast")
@require_role("admin")
def broadcast_notification():
    data = request.get_json(silent=True) or {}
    notification = Notification(
        title=data.get("title", "Annonce"),
        message=data.get("message", ""),
        type=data.get("type", "info"),
    )
    db.session.add(notification)
    db.session.commit()

    payload = notification.to_dict()
    socketio.emit("new_notification", payload)

    return jsonify({"message": "Broadcast sent", "notification": payload}), 201
