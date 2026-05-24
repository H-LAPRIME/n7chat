from __future__ import annotations

from typing import Iterable

from backend.db.supabase import execute, fetch_all, fetch_one


def create_notification(
    *,
    user_id: str,
    title: str,
    message: str,
    type: str | None = None,
) -> None:
    execute(
        """
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (%(user_id)s, %(title)s, %(message)s, %(type)s)
        """,
        {"user_id": user_id, "title": title, "message": message, "type": type},
    )


def notify_users(
    user_ids: Iterable[str],
    *,
    title: str,
    message: str,
    type: str | None = None,
) -> int:
    count = 0
    for user_id in user_ids:
        create_notification(user_id=user_id, title=title, message=message, type=type)
        count += 1
    return count


def notify_event_created(event_id: str) -> int:
    event = fetch_one(
        """
        SELECT title, event_type, start_date, location, visibility_scope, filiere_id, module_id
        FROM events
        WHERE id = %(id)s
        """,
        {"id": event_id},
    )
    if not event:
        return 0

    users = fetch_all(
        """
        SELECT u.id
        FROM users u
        LEFT JOIN students s ON s.user_id = u.id
        WHERE u.role = 'student' AND u.is_active = TRUE
          AND (
            %(visibility_scope)s = 'public'
            OR s.filiere_id = %(filiere_id)s::uuid
            OR s.filiere_id = (
              SELECT filiere_id FROM modules WHERE id = %(module_id)s::uuid
            )
          )
        """,
        {
            "visibility_scope": event.get("visibility_scope") or "public",
            "filiere_id": event.get("filiere_id"),
            "module_id": event.get("module_id"),
        },
    )
    message = f"{event['title']} - {event['start_date']}"
    if event.get("location"):
        message = f"{message} ({event['location']})"
    return notify_users(
        [str(user["id"]) for user in users],
        title="Nouvel evenement",
        message=message,
        type=str(event["event_type"]),
    )
