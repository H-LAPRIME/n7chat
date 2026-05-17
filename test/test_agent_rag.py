from backend.agents import rag_agent
from backend.tools.rag_tool import format_rag_context


def test_format_rag_context_includes_source_type_title_and_content():
    context = format_rag_context(
        [
            {
                "source_type": "admin_document",
                "title": "Reglement",
                "module_name": None,
                "filiere": "GI",
                "similarity": 0.87,
                "content": "Depot des justificatifs avant 48h.",
            }
        ]
    )

    assert "admin_document: Reglement" in context
    assert "GI" in context
    assert "Depot des justificatifs" in context
    assert "score=0.870" in context


def test_answer_from_documents_uses_search_context_and_mistral(monkeypatch):
    monkeypatch.setattr(
        rag_agent,
        "search_document_content",
        lambda **_: {
            "context": "[course: BD]\nSQL basics",
            "data": [{"title": "BD", "content": "SQL basics"}],
        },
    )

    class FakeChat:
        def complete(self, **kwargs):
            assert "SQL basics" in kwargs["messages"][1]["content"]

            class Message:
                content = "Reponse depuis le contexte."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(rag_agent, "_mistral_client", lambda: FakeClient())

    result = rag_agent.answer_from_documents_sync("explique SQL", {"id": "user-1"})

    assert result["ok"] is True
    assert result["answer"] == "Reponse depuis le contexte."
    assert result["sources"][0]["title"] == "BD"


def test_answer_from_documents_retries_global_admin_docs_when_filiere_empty(monkeypatch):
    calls = []

    def fake_search_document_content(**kwargs):
        calls.append(kwargs)
        if kwargs.get("filiere"):
            return {"context": "", "data": []}
        return {
            "context": "[timetable: Emploi du temps]\nLundi POO salle A1",
            "data": [{"source_type": "timetable", "title": "Emploi du temps"}],
        }

    monkeypatch.setattr(rag_agent, "search_document_content", fake_search_document_content)

    class FakeChat:
        def complete(self, **kwargs):
            assert "Lundi POO salle A1" in kwargs["messages"][1]["content"]

            class Message:
                content = "Votre emploi du temps indique POO lundi en salle A1."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(rag_agent, "_mistral_client", lambda: FakeClient())

    result = rag_agent.answer_from_documents_sync(
        "mon emploi du temps",
        {"id": "student-1", "filiere_name": "GI"},
    )

    assert calls[0]["filiere"] == "GI"
    assert calls[1]["filiere"] is None
    assert result["ok"] is True
    assert result["sources"][0]["source_type"] == "timetable"
