from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FileType = Literal["pdf", "docx", "ppt", "video", "link", "text"]


class CourseCreate(BaseModel):
    module_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    file_url: str | None = None
    file_type: FileType | None = None


class CourseUpdate(BaseModel):
    module_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    file_url: str | None = None
    file_type: FileType | None = None
