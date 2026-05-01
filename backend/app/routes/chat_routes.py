"""
backend/app/routes/chat_routes.py
───────────────────────────────────
/chat  — send message, fetch history
"""

from flask import Blueprint, request, jsonify
from app.auth.jwt_utils import require_auth

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/")
@require_auth
def send_message():
    """
    POST /chat
    Body: { "message": str, "session_id": str }
    Forwards to the Orchestrator agent and returns response.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "")

    if not message:
        return jsonify({"error": "message is required"}), 400

    # TODO: call agents.orchestrator.run(message, session_id, user=request.current_user)
    return jsonify(
        {
            "response": "[Orchestrator placeholder]",
            "agent_used": "orchestrator",
            "sources": [],
            "session_id": session_id,
        }
    ), 200


@chat_bp.get("/history")
@require_auth
def get_history():
    """
    GET /chat/history?session_id=<uuid>
    Returns conversation history for the given session.
    """
    session_id = request.args.get("session_id", "")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # TODO: fetch from Conversations DB
    return jsonify({"session_id": session_id, "messages": []}), 200
