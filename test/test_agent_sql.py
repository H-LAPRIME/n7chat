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
    assert data["events"]["payload"] == {"limit": 20}


def test_collect_sql_context_reports_missing_student_id():
    data = sql_agent.collect_sql_context("notes", {})

    assert data["notes"]["ok"] is False
    assert "student_id" in data["notes"]["error"]
