from __future__ import annotations

from pydantic import BaseModel, Field


class StudentProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None


class TeacherProfileUpdate(BaseModel):
    office: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
