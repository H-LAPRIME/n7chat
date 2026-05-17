from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["student", "teacher", "admin"]
StudentStatus = Literal["active", "suspended", "graduated"]


class AdminUserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)
    role: UserRole
    is_active: bool = True


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class LevelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    order_number: int = Field(..., ge=1)


class FiliereCreate(BaseModel):
    department_id: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    duration_years: int | None = Field(default=None, ge=1)


class TeacherCreate(BaseModel):
    user_id: str
    teacher_code: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    specialization: str | None = Field(default=None, max_length=255)
    department_id: str | None = None
    office: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class StudentCreate(BaseModel):
    user_id: str
    student_code: str = Field(..., min_length=1, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    filiere_id: str | None = None
    level_id: str | None = None
    enrollment_year: int | None = None
    status: StudentStatus = "active"


class ModuleCreate(BaseModel):
    filiere_id: str
    teacher_id: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    semester: int | None = Field(default=None, ge=1)
    coefficient: float | None = None
    credits: float | None = None
    description: str | None = None


class StudentAssignment(BaseModel):
    filiere_id: str | None = None
    level_id: str | None = None
    status: StudentStatus | None = None


class TeacherModuleAssignment(BaseModel):
    teacher_id: str | None = None
