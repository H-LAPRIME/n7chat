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
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

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
    row = fetch_one(
        """
        INSERT INTO messages (conversation_id, sender_type, content, message_type)
        VALUES (%(conversation_id)s, %(sender_type)s, %(content)s, %(message_type)s)
        RETURNING *
        """,
        {
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "content": content,
            "message_type": message_type,
        }
    )
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
        FROM messages
        WHERE conversation_id = %(conv_id)s
        ORDER BY created_at ASC
        LIMIT %(limit)s
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

    # 1. Verify conversation ownership (raises 404 if wrong user or missing)
    _assert_conversation_owner(body.conversation_id, user_id)

    # 2. Persist the user's message immediately
    _save_message(body.conversation_id, "user", body.message)

    # 3. Load conversation history (before the just-saved message was added,
    #    so the agent sees the prior exchange; the new message is passed as
    #    the explicit `message` arg).
    history = _load_history(body.conversation_id, limit=12)

    async def event_generator():
        full_response = ""
        had_error = False

        try:
            async for chunk in run_agent(body.message, history, user):
                if not chunk:
                    continue
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                # Let the event loop breathe between chunks
                await asyncio.sleep(0)

        except Exception as exc:
            had_error = True
            error_msg = f"Erreur interne du serveur: {exc}"
            logger.exception("run_agent raised an exception: %s", exc)
            # Surface error as an SSE event so the client can display it
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
            full_response = full_response or error_msg

        finally:
            # 4. Persist the assistant's complete response
            if full_response:
                _save_message(
                    body.conversation_id,
                    "assistant",
                    full_response,
                    message_type="text",
                )

            # 5. Touch conversation timestamp
            _touch_conversation(body.conversation_id)

            # 6. Signal end of stream
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
