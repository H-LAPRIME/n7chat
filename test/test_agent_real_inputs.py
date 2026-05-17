from __future__ import annotations

import asyncio
from pathlib import Path

from backend.agents import graph as agent_graph


DEMO_USER = {
    "id": "user-1",
    "sub": "user-1",
    "role": "student",
    "student_id": "student-1",
    "filiere_id": "filiere-1",
    "filiere_name": "Genie Informatique",
    "semester": 3,
}


async def _run_once(message: str, user: dict | None = None) -> str:
    chunks = []
    async for chunk in agent_graph.run_agent(message, history=[], user=user or DEMO_USER):
        chunks.append(chunk)
    return "".join(chunks)


def test_real_user_input_notes_routes_to_sql_agent(monkeypatch):
    calls = []

    async def fake_orchestrator(message, history, user):
        calls.append(("orchestrator", message))
        return {"intent": "notes", "confidence": 0.99, "reason": "asks for grades"}

    async def fake_sql(message, intent, user):
        calls.append(("sql", intent, user["student_id"]))
        return {
            "ok": True,
            "answer": "Tu as 16 en controle continu et 14.5 a l'examen de BD.",
            "data": {"notes": [{"score": 16}, {"score": 14.5}]},
            "error": None,
        }

    async def fail_rag(*args, **kwargs):
        raise AssertionError("RAG agent should not be called for notes")

    async def fail_pdf(*args, **kwargs):
        raise AssertionError("PDF agent should not be called for notes")

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", fake_orchestrator)
    monkeypatch.setattr(agent_graph, "run_sql_agent", fake_sql)
    monkeypatch.setattr(agent_graph, "run_rag_agent", fail_rag)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", fail_pdf)

    response = asyncio.run(_run_once("Donne-moi mes notes en base de donnees."))

    assert "16" in response
    assert "14.5" in response
    assert calls == [
        ("orchestrator", "Donne-moi mes notes en base de donnees."),
        ("sql", "notes", "student-1"),
    ]


def test_real_user_input_document_question_routes_to_rag_agent(monkeypatch):
    calls = []

    async def fake_orchestrator(message, history, user):
        calls.append(("orchestrator", message))
        return {"intent": "courses", "confidence": 0.95, "reason": "asks document content"}

    async def fake_rag(message, user):
        calls.append(("rag", message, user["filiere_name"]))
        return {
            "ok": True,
            "answer": "Le reglement indique que le justificatif doit etre depose sous 48h.",
            "context": "[admin_document: Reglement]\nDepot sous 48h.",
            "sources": [{"source_type": "admin_document", "title": "Reglement"}],
            "error": None,
        }

    async def fail_sql(*args, **kwargs):
        raise AssertionError("SQL agent should not be called for document search")

    async def fail_pdf(*args, **kwargs):
        raise AssertionError("PDF agent should not be called for document search")

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", fake_orchestrator)
    monkeypatch.setattr(agent_graph, "run_rag_agent", fake_rag)
    monkeypatch.setattr(agent_graph, "run_sql_agent", fail_sql)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", fail_pdf)

    response = asyncio.run(
        _run_once("Que dit le document administratif sur les justificatifs d'absence ?")
    )

    assert "48h" in response
    assert calls == [
        (
            "orchestrator",
            "Que dit le document administratif sur les justificatifs d'absence ?",
        ),
        (
            "rag",
            "Que dit le document administratif sur les justificatifs d'absence ?",
            "Genie Informatique",
        ),
    ]


def test_real_user_input_pdf_routes_to_pdf_agent(monkeypatch, tmp_path):
    pdf_path = tmp_path / "bulletin.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls = []

    async def fake_orchestrator(message, history, user):
        calls.append(("orchestrator", message))
        return {"intent": "pdf_report", "confidence": 0.98, "reason": "asks PDF report"}

    async def fake_pdf(message, user):
        calls.append(("pdf", message, user["student_id"]))
        return {
            "ok": True,
            "answer": f"Le PDF bulletin est pret: {pdf_path}",
            "artifact": {"type": "bulletin", "file_path": str(pdf_path)},
            "data": {},
            "error": None,
        }

    async def fail_sql(*args, **kwargs):
        raise AssertionError("SQL agent should not be called directly for PDF")

    async def fail_rag(*args, **kwargs):
        raise AssertionError("RAG agent should not be called for PDF")

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", fake_orchestrator)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", fake_pdf)
    monkeypatch.setattr(agent_graph, "run_sql_agent", fail_sql)
    monkeypatch.setattr(agent_graph, "run_rag_agent", fail_rag)

    response = asyncio.run(_run_once("Genere mon bulletin PDF avec mes notes et absences."))

    assert "bulletin" in response
    assert str(pdf_path) in response
    assert Path(pdf_path).exists()
    assert calls == [
        ("orchestrator", "Genere mon bulletin PDF avec mes notes et absences."),
        ("pdf", "Genere mon bulletin PDF avec mes notes et absences.", "student-1"),
    ]


def test_real_user_input_general_returns_clarification(monkeypatch):
    async def fake_orchestrator(message, history, user):
        return {"intent": "general", "confidence": 0.6, "reason": "greeting"}

    async def fail_sql(*args, **kwargs):
        raise AssertionError("SQL agent should not be called for general")

    async def fail_rag(*args, **kwargs):
        raise AssertionError("RAG agent should not be called for general")

    async def fail_pdf(*args, **kwargs):
        raise AssertionError("PDF agent should not be called for general")

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", fake_orchestrator)
    monkeypatch.setattr(agent_graph, "run_sql_agent", fail_sql)
    monkeypatch.setattr(agent_graph, "run_rag_agent", fail_rag)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", fail_pdf)

    response = asyncio.run(_run_once("Salut"))

    assert "notes" in response
    assert "emploi du temps" in response
