"""
Memory Agent: summarises and persists long-term user memory.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_mistral_client


def _save_summary(user_id: str, summary: str) -> None:
    try:
        from app import db
        from app.models.conversation import ConversationMemory

        memory = db.session.get(ConversationMemory, user_id)
        if not memory:
            memory = ConversationMemory(user_id=user_id)
            db.session.add(memory)

        memory.summary = summary
        db.session.commit()
    except Exception as e:
        print(f"Memory persistence error: {e}")


def memory_node(state: AgentState) -> AgentState:
    history_text = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in state.get("short_term_history", [])[-10:]
    )
    current_summary = state.get("long_term_summary", "")
    prompt = (
        "Update this long-term memory summary for the user.\n"
        f"Existing summary:\n{current_summary or 'None'}\n\n"
        f"Recent conversation:\n{history_text or 'None'}\n\n"
        f"New user message: {state['user_message']}\n\n"
        "Return a concise useful memory summary."
    )

    try:
        client = get_mistral_client()
        resp = client.chat(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        summary = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Mistral memory error: {e}")
        summary = current_summary or state["user_message"]

    _save_summary(state.get("user_id", ""), summary)

    return {
        **state,
        "agent_used": "memory",
        "response": "C'est note, je l'ai ajoute a votre memoire.",
        "long_term_summary": summary,
    }
