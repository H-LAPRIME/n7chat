from backend.agents.graph import route_from_intent
from backend.agents import orchestrator
from backend.agents.orchestrator import _fallback_intent, _parse_decision


def test_fallback_intent_detects_core_domains():
    assert _fallback_intent("donne moi mes notes") == "notes"
    assert _fallback_intent("combien d'absences j'ai ?") == "absence"
    assert _fallback_intent("mon emploi du temps demain") == "emploi_du_temps"
    assert _fallback_intent("cherche dans les cours de base de donnees") == "courses"
    assert _fallback_intent("document administratif sur les absences") == "courses"
    assert _fallback_intent("genere un bulletin pdf") == "pdf_report"
    assert _fallback_intent("salut") == "general"


def test_parse_decision_keeps_valid_json_intent():
    decision = _parse_decision(
        '{"intent":"courses","confidence":0.91,"reason":"document search"}',
        "cherche un cours",
    )

    assert decision["intent"] == "courses"
    assert decision["confidence"] == 0.91
    assert decision["reason"] == "document search"


def test_parse_decision_falls_back_for_invalid_intent():
    decision = _parse_decision(
        '{"intent":"unknown","confidence":5,"reason":"bad"}',
        "mes notes",
    )

    assert decision["intent"] == "notes"
    assert decision["confidence"] == 1.0


def test_graph_routes_intents_to_expected_agent_nodes():
    assert route_from_intent({"intent": "notes"}) == "sql"
    assert route_from_intent({"intent": "absence"}) == "sql"
    assert route_from_intent({"intent": "emploi_du_temps"}) == "sql"
    assert route_from_intent({"intent": "courses"}) == "rag"
    assert route_from_intent({"intent": "pdf_report"}) == "sql"
    assert (
        route_from_intent(
            {"intent": "pdf_report", "plan": [{"agent": "sql"}, {"agent": "pdf"}], "executed_agents": ["sql"]}
        )
        == "pdf"
    )
    assert route_from_intent({"intent": "general"}) == "general"


def test_orchestrator_context_includes_database_schema(monkeypatch):
    orchestrator.get_orchestrator_context.cache_clear()

    def fake_tool_invoke(tool_obj, payload=None):
        return {
            "ok": True,
            "tables": {
                "notes": [
                    {"name": "student_id", "type": "uuid"},
                    {"name": "score", "type": "float8"},
                ],
                "document_chunks": [
                    {"name": "source_type", "type": "document_source_enum"},
                    {"name": "content", "type": "text"},
                ],
            },
            "error": None,
        }

    monkeypatch.setattr(orchestrator, "_tool_invoke", fake_tool_invoke)

    context = orchestrator.get_orchestrator_context()

    assert context["capabilities"]["intents"]["notes"]["route"] == "sql"
    assert context["capabilities"]["intents"]["courses"]["route"] == "rag"
    assert "student_id:uuid" in context["database_schema"]["tables"]["notes"]
    assert (
        "source_type:document_source_enum"
        in context["database_schema"]["tables"]["document_chunks"]
    )

    orchestrator.get_orchestrator_context.cache_clear()
