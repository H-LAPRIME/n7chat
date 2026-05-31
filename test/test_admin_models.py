from backend.models.admin import (
    AdminUserCreate,
    FiliereCreate,
    ModuleCreate,
    StudentAssignment,
    StudentCreate,
    TeacherCreate,
    TeacherModuleAssignment,
)
from backend.routers import admin
from backend.security.passwords import verify_password
from fastapi import HTTPException


def test_admin_user_create_accepts_roles():
    user = AdminUserCreate(
        email="new.teacher@n7chat.local",
        password="dev-password-hash-change-me",
        role="teacher",
    )

    assert user.role == "teacher"
    assert user.is_active is True


def test_admin_academic_models_cover_creation_and_assignment():
    filiere = FiliereCreate(name="Genie Logiciel", code="GL", duration_years=3)
    module = ModuleCreate(
        filiere_id="filiere-1",
        teacher_id="teacher-1",
        name="Architecture logicielle",
        code="GL-ARCH",
        semester=5,
    )
    teacher_assignment = TeacherModuleAssignment(teacher_id="teacher-2")

    assert filiere.code == "GL"
    assert module.teacher_id == "teacher-1"
    assert teacher_assignment.teacher_id == "teacher-2"


def test_admin_people_models_cover_student_and_teacher_profiles():
    student = StudentCreate(
        user_id="user-student-1",
        student_code="STU-100",
        first_name="Nora",
        last_name="Test",
        filiere_id="filiere-1",
        level_id="level-1",
    )
    teacher = TeacherCreate(
        user_id="user-teacher-1",
        teacher_code="ENS-100",
        first_name="Karim",
        last_name="Test",
    )
    assignment = StudentAssignment(filiere_id="filiere-2", level_id="level-2")

    assert student.status == "active"
    assert teacher.teacher_code == "ENS-100"
    assert assignment.model_dump(exclude_unset=True) == {
        "filiere_id": "filiere-2",
        "level_id": "level-2",
    }


def test_admin_password_hash_keeps_dev_placeholder():
    assert admin._hash_password("dev-password-hash-change-me") == "dev-password-hash-change-me"


def test_admin_password_hash_uses_bcrypt_without_passlib():
    password_hash = admin._hash_password("plain-password")

    assert password_hash.startswith("$2")
    assert verify_password("plain-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_admin_password_hash_rejects_password_over_bcrypt_limit():
    try:
        admin._hash_password("a" * 73)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "72 bytes" in str(exc.detail)
    else:
        raise AssertionError("Expected HTTPException for password over bcrypt limit")
