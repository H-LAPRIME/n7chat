"""Chat router — SSE streaming + conversation management.

Endpoints
---------
POST   /chat/stream
    Stream an AI response chunk-by-chunk via Server-Sent Events.
    Persists user message before streaming and assistant message after.

GET    /chat/conversations
    List the authenticated user's conversations (newest first).

POST   /chat/conversations
    Create a new conversation and return it.

PATCH  /chat/conversations/{conv_id}
    Rename a conversation.

DELETE /chat/conversations/{conv_id}
    Delete a conversation (and its messages via cascade).

GET    /chat/conversations/{conv_id}/messages
    Fetch paginated message history for one conversation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from backend.agents.graph import run_agent
from backend.db.supabase import execute, fetch_all, fetch_one, get_supabase_client
from backend.middleware.jwt_auth import get_current_user
from backend.models.chat import ChatRequest, CreateConversationRequest, RenameConversationRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_sb = None  # lazy singleton


def _supabase():
    global _sb
    if _sb is None:
        _sb = get_supabase_client()
    return _sb


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_conversation_owner(conv_id: str, user_id: str) -> dict[str, Any]:
    """Raise HTTP 404 if the conversation doesn't exist or belongs to another user."""
    row = fetch_one(
        "SELECT id, user_id, title FROM conversations WHERE id = %(id)s",
        {"id": conv_id},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if str(row["user_id"]) != str(user_id):
        # Return 404 (not 403) to avoid leaking existence of other users' conversations
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return dict(row)


def _save_message(
    conversation_id: str,
    sender_type: str,  # "user" | "assistant" | "system"
    content: str,
    message_type: str = "text",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert a message row and return it."""
    params = {
        "conversation_id": conversation_id,
        "sender_type": sender_type,
        "content": content,
        "message_type": message_type,
    }
    query = """
    INSERT INTO messages (conversation_id, sender_type, content, message_type)
    VALUES (%(conversation_id)s, %(sender_type)s, %(content)s, %(message_type)s)
    RETURNING *
    """
    try:
        row = fetch_one(query, params)
    except Exception as exc:
        # Older databases only know text/json. Keep the SSE alive until schema.sql
        # is applied, then persisted history will retain the markdown type too.
        if message_type != "text" and "message_type_enum" in str(exc):
            params["message_type"] = "text"
            row = fetch_one(query, params)
        else:
            raise
    return dict(row) if row else {}


def _touch_conversation(conv_id: str) -> None:
    """Update the updated_at timestamp on a conversation."""
    try:
        execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = %(id)s",
            {"id": conv_id},
        )
    except Exception as exc:
        logger.warning("Could not touch conversation %s: %s", conv_id, exc)


def _load_history(conversation_id: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return the last *limit* messages formatted for the agent."""
    rows = fetch_all(
        """
        SELECT sender_type, content
        FROM (
            SELECT sender_type, content, created_at
            FROM messages
            WHERE conversation_id = %(conv_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s
        ) recent_messages
        ORDER BY created_at ASC
        """,
        {"conv_id": conversation_id, "limit": limit},
    )
    # Normalise sender_type → role expected by the LLM history format
    role_map = {"user": "user", "assistant": "assistant", "system": "system"}
    return [
        {
            "role": role_map.get(row["sender_type"], "user"),
            "content": row["content"] or "",
        }
        for row in rows
    ]


def _message_format(content: str) -> str:
    lines = [line.strip() for line in content.splitlines()]
    has_table = any(line.startswith("|") and line.endswith("|") for line in lines)
    has_heading = any(line.startswith("#") for line in lines)
    return "markdown" if has_table or has_heading else "text"


def _pdf_cache_path(user_id: str, filename: str) -> Path:
    if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF filename.")
    return Path(tempfile.gettempdir()) / "n7chat-pdf-cache" / user_id / filename


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the AI response via Server-Sent Events.

    Protocol
    --------
    Each SSE event is ``data: <json>\\n\\n``.
    Possible JSON shapes:
      - ``{"chunk": "..."}``        – text token chunk
      - ``{"artifact": {...}}``     – PDF or other generated file metadata
      - ``{"error": "..."}``        – non-fatal error surfaced to the client
      - ``[DONE]``                  – literal string signalling end of stream
    """
    user_id: str = user["sub"]

    print(f"\n{'='*60}")
    print(f"[CHAT] 📨 Nouveau message reçu de user={user_id[:8]}...")
    print(f"[CHAT] 💬 Message : {body.message[:80]}{'...' if len(body.message) > 80 else ''}")
    print(f"[CHAT] 🗂️  Conversation : {body.conversation_id}")

    # 1. Verify conversation ownership (raises 404 if wrong user or missing)
    print("[CHAT] 🔐 Vérification propriétaire de la conversation...")
    _assert_conversation_owner(body.conversation_id, user_id)
    print("[CHAT] ✅ Propriétaire vérifié.")

    # 2. Load prior history before saving the new message. The current message
    #    is passed separately to the agent, so it must not be duplicated here.
    print("[CHAT] 📜 Chargement de l'historique...")
    history = _load_history(body.conversation_id, limit=12)
    print(f"[CHAT] ✅ Historique chargé ({len(history)} messages).")

    # 3. Persist the user's message immediately.
    print("[CHAT] 💾 Sauvegarde du message utilisateur en DB...")
    _save_message(body.conversation_id, "user", body.message)
    print("[CHAT] ✅ Message utilisateur sauvegardé.")

    print("[CHAT] 🤖 Lancement de l'agent IA...")
    print(f"{'='*60}")

    async def event_generator():
        full_response = ""
        had_error = False
        chunk_count = 0

        try:
            async for chunk in run_agent(body.message, history, user):
                if not chunk:
                    continue
                if isinstance(chunk, dict):
                    artifact = chunk.get("artifact")
                    if artifact:
                        print(f"[CHAT] 📎 Artifact généré : {artifact.get('filename', '?')}")
                        yield f"data: {json.dumps({'artifact': artifact}, ensure_ascii=False)}\n\n"
                    continue
                full_response += chunk
                chunk_count += 1
                if chunk_count == 1:
                    print("[CHAT] ✍️  Streaming de la réponse en cours...")
                yield f"data: {json.dumps({'chunk': chunk, 'format': _message_format(full_response)}, ensure_ascii=False)}\n\n"
                # Let the event loop breathe between chunks
                await asyncio.sleep(0)

        except Exception as exc:
            had_error = True
            error_msg = f"Erreur interne du serveur: {exc}"
            logger.exception("run_agent raised an exception: %s", exc)
            print(f"[CHAT] ❌ Erreur agent : {exc}")
            # Surface error as an SSE event so the client can display it
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
            full_response = full_response or error_msg

        finally:
            print(f"[CHAT] ✅ Réponse complète ({len(full_response)} chars, {chunk_count} chunks).")
            # 4. Persist the assistant's complete response
            if full_response:
                message_type = _message_format(full_response)
                print(f"[CHAT] 💾 Sauvegarde réponse assistant (type={message_type})...")
                _save_message(
                    body.conversation_id,
                    "assistant",
                    full_response,
                    message_type=message_type,
                )
                print("[CHAT] ✅ Réponse assistant sauvegardée.")

            # 5. Touch conversation timestamp
            _touch_conversation(body.conversation_id)

            # 6. Signal end of stream
            print(f"[CHAT] 🏁 Stream terminé.\n{'='*60}\n")
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent proxy / browser buffering
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/artifacts/pdf/{filename}")
def download_pdf_artifact(
    filename: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> FileResponse:
    """Download a temporary PDF artifact owned by the current user."""
    path = _pdf_cache_path(str(user["sub"]), filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found or expired.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------


@router.get("/conversations")
def list_conversations(
    user: dict[str, Any] = Depends(get_current_user),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """List conversations for the current user, newest first."""
    rows = fetch_all(
        """
        SELECT
          c.id,
          c.title,
          c.context_summary,
          c.started_at,
          c.updated_at,
          (
            SELECT content
            FROM messages m
            WHERE m.conversation_id = c.id
            ORDER BY m.created_at DESC
            LIMIT 1
          ) AS last_message
        FROM conversations c
        WHERE c.user_id = %(user_id)s
        ORDER BY c.updated_at DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"user_id": user["sub"], "limit": limit, "offset": offset},
    )
    return [dict(r) for r in rows]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationRequest = CreateConversationRequest(),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new conversation and return it."""
    row = fetch_one(
        """
        INSERT INTO conversations (user_id, title)
        VALUES (%(user_id)s, %(title)s)
        RETURNING *
        """,
        {"user_id": user["sub"], "title": body.title}
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation.",
        )
    return dict(row)


@router.patch("/conversations/{conv_id}")
def rename_conversation(
    conv_id: str,
    body: RenameConversationRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Rename a conversation title."""
    _assert_conversation_owner(conv_id, user["sub"])
    row = fetch_one(
        """
        UPDATE conversations SET title = %(title)s
        WHERE id = %(id)s
        RETURNING *
        """,
        {"title": body.title, "id": conv_id}
    )
    return dict(row) if row else {"id": conv_id, "title": body.title}


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a conversation and all its messages (cascade)."""
    _assert_conversation_owner(conv_id, user["sub"])
    execute(
        "DELETE FROM conversations WHERE id = %(id)s",
        {"id": conv_id}
    )


@router.get("/conversations/{conv_id}/messages")
def get_messages(
    conv_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    before_id: str | None = Query(default=None, description="Cursor for pagination."),
) -> list[dict[str, Any]]:
    """Return messages for a conversation (newest first for cursor pagination).

    Parameters
    ----------
    limit:
        Maximum messages to return.
    before_id:
        If given, return only messages created before the message with this id
        (used for infinite-scroll / load-more).
    """
    _assert_conversation_owner(conv_id, user["sub"])

    if before_id:
        # Get the created_at of the cursor message
        cursor_row = fetch_one(
            "SELECT created_at FROM messages WHERE id = %(id)s",
            {"id": before_id},
        )
        if not cursor_row:
            raise HTTPException(status_code=404, detail="Cursor message not found.")
        rows = fetch_all(
            """
            SELECT id, sender_type, content, message_type, created_at
            FROM messages
            WHERE conversation_id = %(conv_id)s
              AND created_at < %(cursor)s
            ORDER BY created_at DESC
            LIMIT %(limit)s
            """,
            {"conv_id": conv_id, "cursor": cursor_row["created_at"], "limit": limit},
        )
    else:
        rows = fetch_all(
            """
            SELECT id, sender_type, content, message_type, created_at
            FROM messages
            WHERE conversation_id = %(conv_id)s
            ORDER BY created_at DESC
            LIMIT %(limit)s
            """,
            {"conv_id": conv_id, "limit": limit},
        )

    return [dict(r) for r in rows]
