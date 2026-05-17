from __future__ import annotations

import asyncio

from backend.agents import graph as agent_graph


TRACE_USER = {
    "id": "user-1",
    "sub": "user-1",
    "role": "student",
    "student_id": "student-1",
    "filiere_id": "filiere-1",
    "filiere_name": "Genie Informatique",
    "semester": 3,
}


async def _run_agent_text(message: str) -> str:
    chunks = []
    async for chunk in agent_graph.run_agent(message, history=[], user=TRACE_USER):
        chunks.append(chunk)
    return "".join(chunks)


def _intent_for_message(message: str) -> str:
    text = message.lower()
    if "bulletin" in text or "pdf" in text:
        return "pdf_report"
    if "document" in text or "cours" in text:
        return "courses"
    if "note" in text:
        return "notes"
    if "absence" in text:
        return "absence"
    if "emploi" in text or "planning" in text:
        return "emploi_du_temps"
    return "general"


def test_print_real_like_agent_flow(monkeypatch, capsys):
    """Run this with -s to see each graph step printed in the terminal.

    From backend/:
      python -m pytest ..\\test\\test_agent_flow_trace.py -s
    """

    async def traced_orchestrator(message, history, user):
        intent = _intent_for_message(message)
        print("\n[1] USER INPUT")
        print(f"    message: {message}")
        print("[2] ORCHESTRATOR")
        print(f"    role: {user['role']}")
        print(f"    classified_intent: {intent}")
        return {
            "intent": intent,
            "confidence": 0.99,
            "reason": f"demo keyword routing for {intent}",
        }

    async def traced_sql(message, intent, user):
        print("[3] SQL AGENT")
        print(f"    intent: {intent}")
        print(f"    student_id: {user.get('student_id')}")
        if intent == "notes":
            answer = "Tu as 16 en controle continu et 14.5 a l'examen de BD."
        elif intent == "absence":
            answer = "Tu as 1 absence non justifiee en Algorithmique."
        else:
            answer = "Ton emploi du temps contient BD lundi 09:00 et Algo mardi 10:00."
        print("[4] SQL RESULT")
        print(f"    answer: {answer}")
        return {"ok": True, "answer": answer, "data": {}, "error": None}

    async def traced_rag(message, user):
        print("[3] RAG AGENT")
        print(f"    filiere: {user.get('filiere_name')}")
        print("    search: document_chunks")
        answer = "Le document administratif dit de deposer le justificatif sous 48h."
        print("[4] RAG RESULT")
        print("    source: admin_document / Reglement")
        print(f"    answer: {answer}")
        return {
            "ok": True,
            "answer": answer,
            "context": "[admin_document: Reglement]\nDepot sous 48h.",
            "sources": [{"source_type": "admin_document", "title": "Reglement"}],
            "error": None,
        }

    async def traced_pdf(message, user):
        print("[3] PDF AGENT")
        print(f"    student_id: {user.get('student_id')}")
        print("    report_type: bulletin")
        answer = "Le PDF bulletin est pret: C:/tmp/bulletin-demo.pdf"
        print("[4] PDF RESULT")
        print(f"    answer: {answer}")
        return {
            "ok": True,
            "answer": answer,
            "artifact": {"type": "bulletin", "file_path": "C:/tmp/bulletin-demo.pdf"},
            "data": {},
            "error": None,
        }

    monkeypatch.setattr(agent_graph, "run_orchestrator_agent", traced_orchestrator)
    monkeypatch.setattr(agent_graph, "run_sql_agent", traced_sql)
    monkeypatch.setattr(agent_graph, "run_rag_agent", traced_rag)
    monkeypatch.setattr(agent_graph, "run_pdf_agent", traced_pdf)

    messages = [
        "Donne-moi mes notes en base de donnees.",
        "Que dit le document administratif sur les justificatifs d'absence ?",
        "Genere mon bulletin PDF avec mes notes et absences.",
    ]

    responses = []
    for message in messages:
        response = asyncio.run(_run_agent_text(message))
        print("[5] FINAL RESPONSE")
        print(f"    {response}")
        responses.append(response)

    output = capsys.readouterr().out
    print(output)

    assert "[2] ORCHESTRATOR" in output
    assert "[3] SQL AGENT" in output
    assert "[3] RAG AGENT" in output
    assert "[3] PDF AGENT" in output
    assert responses == [
        "Tu as 16 en controle continu et 14.5 a l'examen de BD.",
        "Le document administratif dit de deposer le justificatif sous 48h.",
        "Le PDF bulletin est pret: C:/tmp/bulletin-demo.pdf",
    ]
