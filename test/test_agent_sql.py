from backend.agents import sql_agent


def _fake_tool(name):
    def inner(**payload):
        return {"ok": True, "name": name, "payload": payload, "data": [payload]}

    return inner


def test_collect_sql_context_for_notes(monkeypatch):
    monkeypatch.setattr(sql_agent, "get_student_notes", _fake_tool("notes"))

    data = sql_agent.collect_sql_context(
        "notes",
        {"student_id": "student-1"},
    )

    assert data["notes"]["ok"] is True
    assert data["notes"]["payload"] == {"student_id": "student-1"}


def test_collect_sql_context_for_absence_uses_nested_student(monkeypatch):
    monkeypatch.setattr(sql_agent, "get_student_absences", _fake_tool("absences"))

    data = sql_agent.collect_sql_context(
        "absence",
        {"student": {"id": "student-2"}},
    )

    assert data["absences"]["payload"] == {"student_id": "student-2"}


def test_collect_sql_context_for_timetable(monkeypatch):
    monkeypatch.setattr(sql_agent, "get_filiere_modules", _fake_tool("modules"))
    monkeypatch.setattr(sql_agent, "get_upcoming_events", _fake_tool("events"))

    data = sql_agent.collect_sql_context(
        "emploi_du_temps",
        {"filiere_id": "filiere-1", "semester": 3},
    )

    assert data["modules"]["payload"] == {"filiere_id": "filiere-1", "semester": 3}
    assert data["events"]["payload"] == {
        "limit": 20,
        "filiere_id": "filiere-1",
        "is_staff": False,
    }


def test_collect_sql_context_reports_missing_student_id():
    data = sql_agent.collect_sql_context("notes", {})

    assert data["notes"]["ok"] is False
    assert "student_id" in data["notes"]["error"]


def test_collect_sql_context_for_pdf_report(monkeypatch):
    monkeypatch.setattr(sql_agent, "get_student_profile", _fake_tool("profile"))
    monkeypatch.setattr(sql_agent, "get_student_notes", _fake_tool("notes"))
    monkeypatch.setattr(sql_agent, "get_student_absences", _fake_tool("absences"))

    data = sql_agent.collect_sql_context(
        "pdf_report",
        {"id": "user-1", "student_id": "student-1"},
    )

    assert data["profile"]["payload"] == {"user_id": "user-1"}
    assert data["notes"]["payload"] == {"student_id": "student-1"}
    assert data["absences"]["payload"] == {"student_id": "student-1"}


def test_format_sql_context_for_notes_uses_markdown_table():
    formatted = sql_agent.format_sql_context(
        "notes",
        {
            "notes": {
                "ok": True,
                "data": [
                    {
                        "module_name": "Algorithmique",
                        "exam_type": "cc",
                        "score": 13,
                        "coefficient": 0.4,
                        "published_at": "2026-05-17",
                    }
                ],
            }
        },
    )

    assert "| module_name | exam_type | score | coefficient | published_at |" in formatted
    assert "| Algorithmique | cc | 13 | 0.4 | 2026-05-17 |" in formatted


def test_format_sql_context_for_profile_uses_user_friendly_tables():
    formatted = sql_agent.format_sql_context(
        "profile",
        {
            "profile": {
                "data": {
                    "first_name": "Omar",
                    "last_name": "El Fassi",
                    "student_code": "STU-002",
                    "filiere_name": "Genie Informatique",
                    "filiere_code": "GI",
                    "level_name": "Licence 2",
                    "enrollment_year": 2024,
                    "status": "active",
                }
            },
            "modules": {
                "data": [
                    {
                        "module_name": "Algorithmique avancee",
                        "module_code": "GI-S3-ALG",
                        "semester": 3,
                        "teacher_first_name": "Youssef",
                        "teacher_last_name": "El Idrissi",
                    }
                ]
            },
        },
    )

    assert "### Profil etudiant" in formatted
    assert "| Information | Valeur |" in formatted
    assert "| Nom complet | Omar El Fassi |" in formatted
    assert "| Module | Code | Semestre | Enseignant |" in formatted
    assert "| Algorithmique avancee | GI-S3-ALG | 3 | Youssef El Idrissi |" in formatted


def test_answer_from_sql_sync_attaches_formatted_context(monkeypatch):
    monkeypatch.setattr(sql_agent, "collect_sql_context", lambda *_: {"notes": {"data": []}})
    monkeypatch.setattr(sql_agent, "enforce_student_scope", lambda _user, data: data)

    captured = {}

    def fake_answer(message, intent, user, data):
        captured["data"] = data
        return {"ok": True, "answer": data["formatted_context"], "data": data, "error": None}

    monkeypatch.setattr(sql_agent, "answer_from_sql_task", fake_answer)

    result = sql_agent.answer_from_sql_sync("mes notes", "notes", {"student_id": "student-1"})

    assert result["ok"] is True
    assert captured["data"]["formatted_context"] == "_Aucune note trouvee._"
