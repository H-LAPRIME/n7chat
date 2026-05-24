from backend.agents.graph import route_from_intent
from backend.agents import orchestrator
from backend.agents.orchestrator import _fallback_intent, _fallback_plan, _parse_decision


def test_fallback_intent_detects_core_domains():
    assert _fallback_intent("donne moi mes notes") == "notes"
    assert _fallback_intent("combien d'absences j'ai ?") == "absence"
    assert _fallback_intent("mon emploi du temps demain") == "emploi_du_temps"
    assert _fallback_intent("cherche dans les cours de base de donnees") == "courses"
    assert _fallback_intent("document administratif sur les absences") == "courses"
    assert _fallback_intent("cherche dans le fichier emploi du temps") == "courses"
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


def test_parse_decision_accepts_hybrid_agent_plan():
    decision = _parse_decision(
        '{"intent":"emploi_du_temps","confidence":0.82,"reason":"mixed","plan":[{"agent":"hybrid","purpose":"sql plus docs"}]}',
        "mon emploi du temps",
    )

    assert decision["intent"] == "emploi_du_temps"
    assert decision["plan"] == [{"agent": "hybrid", "purpose": "sql plus docs"}]


def test_parse_decision_keeps_rag_pdf_plan_for_document_report():
    decision = _parse_decision(
        '{"intent":"pdf_report","confidence":0.88,"reason":"document report","plan":[{"agent":"rag","purpose":"docs"},{"agent":"pdf","purpose":"render"}]}',
        "genere un rapport pdf sur le reglement",
    )

    assert [step["agent"] for step in decision["plan"]] == ["rag", "pdf"]


def test_pdf_request_uses_previous_timetable_context_for_plan():
    decision = _parse_decision(
        '{"intent":"pdf_report","confidence":0.9,"reason":"pdf","plan":[{"agent":"pdf","purpose":"render"}]}',
        "genere sous format pdf",
        history=[
            {
                "role": "assistant",
                "content": "Voici l'emploi du temps pour la filiere GEER avec les seances du lundi au samedi.",
            }
        ],
    )

    assert [step["agent"] for step in decision["plan"]] == ["hybrid", "pdf"]


def test_timetable_decision_forces_pdf_suggestion_when_llm_says_false():
    decision = _parse_decision(
        '{"intent":"emploi_du_temps","confidence":0.9,"reason":"schedule","suggest_pdf":false,"plan":[{"agent":"hybrid","purpose":"schedule"}]}',
        "qulle lemploi du temps de geer",
    )

    assert decision["suggest_pdf"] is True


def test_fallback_plan_uses_hybrid_for_mixed_timetable_documents():
    plan = _fallback_plan("emploi_du_temps", "mon emploi du temps")

    assert plan[0]["agent"] == "hybrid"


def test_fallback_pdf_plan_uses_matching_collector():
    assert [step["agent"] for step in _fallback_plan("pdf_report", "genere un rapport pdf sur ce cours")] == ["rag", "pdf"]
    assert [step["agent"] for step in _fallback_plan("pdf_report", "genere un rapport pdf emploi du temps")] == ["hybrid", "pdf"]
    assert [step["agent"] for step in _fallback_plan("pdf_report", "genere mon bulletin pdf")] == ["pdf"]


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
    assert route_from_intent({"intent": "emploi_du_temps"}) == "hybrid"
    assert (
        route_from_intent(
            {
                "intent": "emploi_du_temps",
                "plan": [{"agent": "hybrid"}],
            }
        )
        == "hybrid"
    )
    assert (
        route_from_intent(
            {
                "intent": "emploi_du_temps",
                "plan": [{"agent": "hybrid"}, {"agent": "pdf"}],
                "executed_agents": ["hybrid"],
            }
        )
        == "pdf"
    )
    assert route_from_intent({"intent": "courses"}) == "rag"
    assert route_from_intent({"intent": "pdf_report"}) == "pdf"
    assert (
        route_from_intent(
            {"intent": "pdf_report", "plan": [{"agent": "sql"}, {"agent": "pdf"}], "executed_agents": ["sql"]}
        )
        == "pdf"
    )
    assert (
        route_from_intent(
            {"intent": "pdf_report", "plan": [{"agent": "rag"}, {"agent": "pdf"}], "executed_agents": ["rag"]}
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
