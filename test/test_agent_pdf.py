from pathlib import Path

from backend.agents.pdf_agent import _infer_report_type, build_pdf_report_sync
from backend.tools.pdf_tool import build_bulletin_pdf, build_notes_pdf


def test_infer_report_type():
    assert _infer_report_type("genere mes notes pdf") == "notes"
    assert _infer_report_type("genere mon bulletin") == "bulletin"
    assert _infer_report_type("anything", "bulletin") == "bulletin"


def test_build_notes_pdf_creates_file():
    path = build_notes_pdf(
        {"first_name": "Sara", "last_name": "Test", "filiere_name": "GI", "level_name": "L2"},
        [
            {
                "module_name": "Bases de donnees",
                "exam_type": "cc",
                "score": 16,
                "coefficient": 0.4,
                "published_at": "2026-05-17",
            }
        ],
    )

    assert Path(path).exists()
    assert Path(path).suffix == ".pdf"


def test_build_bulletin_pdf_creates_file():
    path = build_bulletin_pdf(
        {"first_name": "Omar", "last_name": "Test", "filiere_name": "GI", "level_name": "L2"},
        [{"module_name": "Algo", "exam_type": "exam", "score": 13, "semester": 3}],
        [{"module_name": "Algo", "date": "2026-05-05", "justified": False}],
    )

    assert Path(path).exists()
    assert Path(path).suffix == ".pdf"


def test_build_pdf_report_sync_uses_tools(monkeypatch):
    monkeypatch.setattr(
        "backend.agents.pdf_agent.get_student_profile",
        lambda **_: {"ok": True, "data": {"first_name": "Sara", "last_name": "Test"}},
    )
    monkeypatch.setattr(
        "backend.agents.pdf_agent.get_student_notes",
        lambda **_: {"ok": True, "data": []},
    )
    monkeypatch.setattr(
        "backend.agents.pdf_agent.get_student_absences",
        lambda **_: {"ok": True, "data": []},
    )

    result = build_pdf_report_sync(
        "bulletin pdf",
        {"id": "user-1", "student_id": "student-1"},
    )

    assert result["ok"] is True
    assert result["artifact"]["type"] == "bulletin"
    assert Path(result["artifact"]["file_path"]).exists()
