"""
backend/app/routes/notification_routes.py
─────────────────────────────────────────
/notifications  — list, read, broadcast
"""

from flask import Blueprint, request, jsonify
from app.auth.jwt_utils import require_auth, decode_token
from app import socketio

notifications_bp = Blueprint("notifications", __name__)

# Mock storage for notifications
# In production, this should be in a database (e.g. Postgres)
MOCK_NOTIFICATIONS = [
    {
        "id": "1",
        "user_id": "all",
        "title": "Bienvenue sur n7chat !",
        "message": "Explorez vos nouveaux modules de cours et discutez avec l'IA.",
        "type": "info",
        "is_read": False,
        "timestamp": "2026-05-02T10:00:00Z"
    },
    {
        "id": "2",
        "user_id": "all",
        "title": "Nouveau PDF disponible",
        "message": "Le règlement des études 2024 a été ajouté à vos documents.",
        "type": "update",
        "is_read": False,
        "timestamp": "2026-05-02T11:00:00Z"
    }
]

@notifications_bp.get("/")
@require_auth
def list_notifications():
    """
    GET /notifications
    Returns list of notifications for the user.
    """
    # For now, return all "all" notifications
    return jsonify({"notifications": MOCK_NOTIFICATIONS}), 200

@notifications_bp.post("/read/<id>")
@require_auth
def mark_as_read(id):
    """
    POST /notifications/read/<id>
    Marks a notification as read.
    """
    for n in MOCK_NOTIFICATIONS:
        if n["id"] == id:
            n["is_read"] = True
            return jsonify({"message": "Marked as read"}), 200
    return jsonify({"error": "Notification not found"}), 404

@notifications_bp.post("/broadcast")
@require_auth
def broadcast_notification():
    """
    POST /notifications/broadcast
    (Admin only) Send notification to all users via Socket.io.
    """
    # Check if admin (this check should be more robust in production)
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ")[1]
    payload = decode_token(token)
    
    if payload.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403

    data = request.get_json() or {}
    new_notif = {
        "id": str(len(MOCK_NOTIFICATIONS) + 1),
        "user_id": "all",
        "title": data.get("title", "Annonce"),
        "message": data.get("message", ""),
        "type": data.get("type", "info"),
        "is_read": False,
        "timestamp": "2026-05-02T12:00:00Z"
    }
    MOCK_NOTIFICATIONS.insert(0, new_notif)
    
    # Real-time broadcast
    socketio.emit("new_notification", new_notif)
    
    return jsonify({"message": "Broadcast sent", "notification": new_notif}), 201
