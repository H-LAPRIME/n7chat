from __future__ import annotations

import asyncio
from typing import Any

from dotenv import load_dotenv

from backend.db.supabase import get_supabase_client
from backend.flows.index_flow import index_document, trigger_index_course


load_dotenv("backend/.env")


async def index_courses() -> int:
    supabase = get_supabase_client()
    response = (
        supabase.table("courses")
        .select("id")
        .execute()
    )

    count = 0
    for course in response.data:
        count += await trigger_index_course(course["id"])
    return count


async def index_events() -> int:
    supabase = get_supabase_client()
    response = (
        supabase.table("events")
        .select("id, title, description, event_type, start_date, end_date, location")
        .execute()
    )

    count = 0
    for event in response.data:
        content = " ".join(
            str(event.get(key) or "")
            for key in ["title", "description", "event_type", "start_date", "end_date", "location"]
        )
        count += await index_document(
            source_type="event",
            source_id=event["id"],
            source_table="events",
            content=content,
            title=event.get("title"),
            file_type="text",
            metadata={
                "event_type": event.get("event_type"),
                "location": event.get("location"),
            },
        )
    return count


async def index_text_document(document: dict[str, Any]) -> int:
    """Index a generic already-extracted text document.

    Expected keys: id, source_type, content. Optional keys: title, file_type,
    source_url, module_id, user_id, module_name, filiere, metadata.
    """
    return await index_document(
        source_type=document.get("source_type", "other"),
        source_id=document["id"],
        source_table=document.get("source_table"),
        source_url=document.get("source_url"),
        module_id=document.get("module_id"),
        user_id=document.get("user_id"),
        content=document["content"],
        title=document.get("title"),
        module_name=document.get("module_name"),
        filiere=document.get("filiere"),
        file_type=document.get("file_type"),
        metadata=document.get("metadata") or {},
    )


async def main() -> None:
    course_chunks = await index_courses()
    event_chunks = await index_events()
    print(f"Indexed {course_chunks} course chunks.")
    print(f"Indexed {event_chunks} event chunks.")


if __name__ == "__main__":
    asyncio.run(main())
