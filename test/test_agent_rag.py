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


def test_answer_from_documents_retries_public_docs_when_filiere_empty(monkeypatch):
    calls = []

    def fake_search_document_content(**kwargs):
        calls.append(kwargs)
        if kwargs.get("accessible_filiere_id") and kwargs.get("visibility_scope") != "public":
            return {"context": "", "data": []}
        if kwargs.get("source_type") != "timetable":
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
        {"id": "student-1", "filiere_id": "filiere-1", "filiere_name": "GI"},
    )

    assert calls[0]["accessible_filiere_id"] == "filiere-1"
    assert all(call.get("source_type") != "course" for call in calls[1:])
    assert result["ok"] is True
    assert result["sources"][0]["source_type"] == "timetable"


def test_answer_from_documents_does_not_global_fallback_for_course_filter(monkeypatch):
    calls = []

    def fake_search_document_content(**kwargs):
        calls.append(kwargs)
        return {"context": "", "data": []}

    monkeypatch.setattr(rag_agent, "search_document_content", fake_search_document_content)

    class FakeChat:
        def complete(self, **kwargs):
            class Message:
                content = "Aucun cours trouve."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(rag_agent, "_mistral_client", lambda: FakeClient())

    result = rag_agent.answer_from_documents_sync(
        "explique ce cours",
        {"id": "student-1", "filiere_id": "filiere-1"},
        {"source_type": "course"},
    )

    assert len(calls) == 1
    assert calls[0]["source_type"] == "course"
    assert calls[0]["accessible_filiere_id"] == "filiere-1"
    assert result["ok"] is True


def test_uploaded_course_lookup_uses_courses_table_not_timetable(monkeypatch):
    searched = []

    monkeypatch.setattr(
        rag_agent,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {
                "id": "course-1",
                "title": "Cours de Francais",
                "file_url": "https://example.test/fr.pdf",
                "file_type": "pdf",
                "visibility_scope": "public",
                "module_name": "Francais",
                "uploader_name": "Mme Naim",
                "teacher_code": "ENS-9",
            }
        ],
    )

    def fake_search_document_content(**kwargs):
        searched.append(kwargs)
        return {"context": "[timetable: wrong]", "data": [{"source_type": "timetable"}]}

    monkeypatch.setattr(rag_agent, "search_document_content", fake_search_document_content)

    result = rag_agent.answer_from_documents_sync(
        "est-ce qu'il ya un cour de francai deja uploaded ?",
        {"id": "student-1", "filiere_id": "filiere-1"},
    )

    assert searched == []
    assert result["ok"] is True
    assert "Cours de Francais" in result["answer"]
    assert "Mme Naim" in result["answer"]
    assert "[Ouvrir le PDF](https://example.test/fr.pdf)" in result["answer"]
    assert result["sources"][0]["title"] == "Cours de Francais"


def test_uploaded_course_lookup_does_not_answer_from_timetable_when_empty(monkeypatch):
    monkeypatch.setattr(rag_agent, "fetch_all", lambda *_args, **_kwargs: [])

    def fail_search_document_content(**kwargs):
        raise AssertionError("course lookup should not fallback to timetable RAG")

    monkeypatch.setattr(rag_agent, "search_document_content", fail_search_document_content)

    result = rag_agent.answer_from_documents_sync(
        "qulle sont les coures existe dans db",
        {"id": "student-1", "filiere_id": "filiere-1"},
    )

    assert result["ok"] is True
    assert "aucun support de cours" in result["answer"].lower()


def test_course_content_followup_uses_previous_course_source(monkeypatch):
    calls = []

    monkeypatch.setattr(
        rag_agent,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {
                "id": "course-1",
                "title": "francais",
                "file_url": "https://example.test/cours_francais.pdf",
                "file_type": "pdf",
                "visibility_scope": "filiere",
                "module_name": "Francais",
                "uploader_name": "francais prof",
                "teacher_code": "1212",
            }
        ],
    )

    def fake_search_document_content(**kwargs):
        calls.append(kwargs)
        assert kwargs["source_type"] == "course"
        assert kwargs["source_id"] == "course-1"
        return {
            "context": "[course: francais]\nAlphabet et grammaire francaise.",
            "data": [{"source_type": "course", "title": "francais", "content": "Alphabet et grammaire francaise."}],
        }

    monkeypatch.setattr(rag_agent, "search_document_content", fake_search_document_content)

    class FakeChat:
        def complete(self, **kwargs):
            assert "Alphabet et grammaire" in kwargs["messages"][1]["content"]
            assert "timetable" not in kwargs["messages"][1]["content"].lower()

            class Message:
                content = "Il contient des notions d'alphabet et de grammaire francaise."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(rag_agent, "_mistral_client", lambda: FakeClient())

    result = rag_agent.answer_from_documents_sync(
        "il contient qoui",
        {"id": "student-1", "filiere_id": "filiere-1"},
        history=[
            {"role": "user", "content": "est-ce qu'il ya un cour de francai deja ulpoade ?"},
            {
                "role": "assistant",
                "content": (
                    "Voici les supports de cours uploades auxquels tu as acces :\n"
                    "1. **francais** - Francais - francais prof (1212) - Classe: Genie Informatique - pdf\n"
                    "   Lien: https://example.test/cours_francais.pdf"
                ),
            },
        ],
    )

    assert len(calls) == 1
    assert result["ok"] is True
    assert "grammaire" in result["answer"]


def test_previous_answer_summary_followup_does_not_search_timetable(monkeypatch):
    def fail_search_document_content(**kwargs):
        raise AssertionError("previous-answer followup should not run vector search")

    monkeypatch.setattr(rag_agent, "search_document_content", fail_search_document_content)

    class FakeChat:
        def complete(self, **kwargs):
            prompt = kwargs["messages"][1]["content"]
            assert "Vecteurs et Espaces Vectoriels" in prompt
            assert "emploi du temps" not in prompt.lower()

            class Message:
                content = "Résumé court : le dernier contenu explique les vecteurs, matrices et déterminants."

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            return Response()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(rag_agent, "_mistral_client", lambda: FakeClient())

    result = rag_agent.answer_from_documents_sync(
        "resmer moi ce dernier",
        {"id": "student-1", "filiere_id": "filiere-1"},
        history=[
            {
                "role": "assistant",
                "content": (
                    "D'après le document Algèbre Linéaire, voici les thèmes :\n"
                    "1. Vecteurs et Espaces Vectoriels\n"
                    "2. Matrices\n"
                    "3. Déterminants"
                ),
            }
        ],
    )

    assert result["ok"] is True
    assert "vecteurs" in result["answer"].lower()
