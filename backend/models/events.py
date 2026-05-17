from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal["exam", "conference", "holiday", "meeting"]


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    event_type: EventType
    start_date: datetime
    end_date: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    notify_students: bool = True


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    event_type: EventType | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    notify_students: bool = False
