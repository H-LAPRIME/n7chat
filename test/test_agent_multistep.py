from __future__ import annotations

import asyncio

from backend.agents import graph as agent_graph


USER = {
    "id": "user-1",
    "sub": "user-1",
    "role": "student",
    "student_id": "student-1",
    "filiere_id": "filiere-1",
    "semester": 3,
}


async def _run_once(message: str) -> str:
    chunks = []
    async for chunk in agent_graph.run_agent(message, history=[], user=USER):
        chunks.append(chunk)
    return "".join(chunks)


def test_pdf_request_executes_sql_then_pdf_with_shared_context(monkeypatch):
    calls = []

    async def fake_orchestrator(message, history, user):
        calls.append(("orchestrator", message))
        return {
            "intent": "pdf_report",
            "confidence": 0.99,
            "reason": "Needs structured grades before PDF generation.",
            "plan": [
                {"agent": "sql", "purpose": "Collect notes and absences."},
                {"agent": "pdf", "purpose": "Generate bulletin PDF."},
            ],
        }

    async def fake_sql(message, intent, user):
        calls.append(("sql", intent))
        return {
            "ok": True,
            "answer": "Collected notes.",
            "data": {
                "notes": {"data": [{"module_name": "BD", "score": 16}]},
                "absences": {"data": [{"module_name": "Algo", "justified": False}]},
            },
            "error": None,
        }

    async def fake_pdf(message, user, report_type=None, data_context=None):
        calls.append(("pdf", bool(data_context and data_context.get("sql"))))
        assert data_context["sql"]["notes"]["data"][0]["score"] == 16
        return {
            "ok": True,
            "answer": "Le PDF bulletin est pret: C:/tmp/bulletin.pdf",
            "artifact": {"type": "bulletin", "file_path": "C:/tmp/bulletin.pdf"},
            "data": {},
            "error": None,
        }

    async def fail_rag(*args, **kwargs):
        raise AssertionError("RAG should not be called for this plan")

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", fake_orchestrator)
    monkeypatch.setattr(agent_graph, "run_sql_agent", fake_sql)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", fake_pdf)
    monkeypatch.setattr(agent_graph, "run_rag_agent", fail_rag)

    response = asyncio.run(_run_once("Genere un bulletin PDF avec mes notes"))

    assert response == "Le PDF bulletin est pret: C:/tmp/bulletin.pdf"
    assert calls == [
        ("orchestrator", "Genere un bulletin PDF avec mes notes"),
        ("sql", "pdf_report"),
        ("pdf", True),
    ]
