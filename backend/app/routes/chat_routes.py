"""
Chat routes: send messages through the orchestrator and read session history.
"""

from flask import Blueprint, jsonify, request

from app import db
from app.auth.jwt_utils import require_auth
from app.models.conversation import ConversationMemory, ConversationMessage

chat_bp = Blueprint("chat", __name__)


def _recent_history(session_id: str, limit: int = 10) -> list[dict]:
    rows = (
        ConversationMessage.query.filter_by(session_id=session_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"role": row.role, "content": row.content}
        for row in reversed(rows)
    ]


@chat_bp.post("/")
@require_auth
def send_message():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    user_id = request.current_user.get("sub")
    memory = db.session.get(ConversationMemory, user_id)
    history = _recent_history(session_id)

    user_row = ConversationMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=message,
    )
    db.session.add(user_row)
    db.session.commit()

    try:
        from agents.orchestrator import run

        result = run(
            message,
            session_id,
            user={
                **request.current_user,
                "short_term_history": history,
                "long_term_summary": memory.summary if memory else "",
            },
        )
    except Exception as e:
        print(f"Orchestrator Error: {e}")
        result = {
            "response": "Je n'ai pas pu joindre l'orchestrateur IA pour le moment. Reessayez dans quelques instants.",
            "agent_used": "fallback",
            "sources": [],
            "session_id": session_id,
        }

    assistant_row = ConversationMessage(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=result.get("response", ""),
        agent=result.get("agent_used"),
        sources=result.get("sources", []),
    )
    db.session.add(assistant_row)
    db.session.commit()

    return jsonify(result), 200


@chat_bp.get("/history")
@require_auth
def get_history():
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    messages = (
        ConversationMessage.query.filter_by(
            session_id=session_id,
            user_id=request.current_user.get("sub"),
        )
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return jsonify({"session_id": session_id, "messages": [m.to_dict() for m in messages]}), 200
