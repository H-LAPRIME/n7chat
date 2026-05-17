"""General LLM Task.

Handles chitchat, greetings, and general questions outside of specific
SQL/RAG data domains. Uses Mistral to provide a natural, helpful response
in the persona of the university platform assistant.
"""

from __future__ import annotations

import json
from os import environ
from typing import Any

from backend.tasks.orchestrator_llm_task import _extract_content, _mistral_client, DEFAULT_MODEL

SYSTEM_PROMPT = """
Tu es l'assistant IA de la plateforme universitaire n7chat de l'ecole ENSET MOHAMMEDIA.
Tu aides les étudiants et les enseignants.

Ton but dans cette interaction est de répondre à des questions générales, des salutations,
ou des questions de clarification ("qui es-tu ?", "que fais-tu ?").

Règles:
1. Sois poli, concis et utile.
2. Si l'utilisateur pose une question sur ses notes, son emploi du temps, ses absences ou ses cours,
   rappelle-lui de formuler sa demande clairement (par exemple : "peux-tu me donner mes notes ?")
   pour que tu puisses interroger la base de données.
3. NE DOIS JAMAIS inventer de notes, d'horaires ou de données scolaires.
4. Réponds toujours en français.
"""

def answer_general_task(
    message: str,
    history: list[dict[str, Any]] | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Mistral to answer a general/chitchat query."""
    user_context = json.dumps(user or {}, ensure_ascii=False, default=str)
    system_prompt_with_context = SYSTEM_PROMPT + f"\n\nContexte de l'utilisateur actuel:\n{user_context}"
    messages = [{"role": "system", "content": system_prompt_with_context}]
    
    # Add history
    for msg in (history or [])[-6:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
        
    messages.append({"role": "user", "content": message})

    try:
        response = _mistral_client().chat.complete(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.3,
        )
        answer = _extract_content(response)
        return {"answer": answer, "error": None}
    except Exception as exc:
        print(f"[general_llm_task error] {exc}")
        return {
            "answer": "Désolé, je rencontre un problème de connexion en ce moment.",
            "error": str(exc),
        }
