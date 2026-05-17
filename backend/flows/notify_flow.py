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
        SELECT title, event_type, start_date, location
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
        WHERE u.role = 'student' AND u.is_active = TRUE
        """,
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
