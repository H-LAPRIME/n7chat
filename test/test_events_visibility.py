from backend.routers import events


def test_teacher_event_list_is_scoped_to_author_or_assigned_audience(monkeypatch):
    captured = {}

    def fake_fetch_all(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(events, "fetch_all", fake_fetch_all)

    rows = events.list_events(
        user={
            "role": "teacher",
            "sub": "11111111-1111-1111-1111-111111111111",
            "teacher_id": "22222222-2222-2222-2222-222222222222",
        }
    )

    assert rows == []
    assert captured["params"]["role"] == "teacher"
    assert captured["params"]["teacher_id"] == "22222222-2222-2222-2222-222222222222"
    assert "%(is_staff)s = TRUE" not in captured["query"]
    assert "created_by = %(user_id)s::uuid" in captured["query"]
    assert "WHERE teacher_id = %(teacher_id)s::uuid" in captured["query"]


def test_student_event_list_is_scoped_to_public_or_own_filiere(monkeypatch):
    captured = {}

    def fake_fetch_all(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(events, "fetch_all", fake_fetch_all)

    rows = events.list_events(
        user={
            "role": "student",
            "sub": "33333333-3333-3333-3333-333333333333",
            "filiere_id": "44444444-4444-4444-4444-444444444444",
        }
    )

    assert rows == []
    assert captured["params"]["role"] == "student"
    assert captured["params"]["filiere_id"] == "44444444-4444-4444-4444-444444444444"
    assert "%(is_staff)s = TRUE" not in captured["query"]
    assert "visibility_scope = 'public'" in captured["query"]
    assert "module_id IN (SELECT id FROM modules WHERE filiere_id = %(filiere_id)s::uuid)" in captured["query"]
