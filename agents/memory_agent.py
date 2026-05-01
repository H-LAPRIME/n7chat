"""
agents/memory_agent.py
────────────────────────
Memory Agent — Mistral LLM
Handles short-term (session) and long-term (DB) memory.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_mistral_client


def memory_node(state: AgentState) -> AgentState:
    """
    Save the current turn to Conversations DB and
    optionally compress long-term history.
    """
    client = get_mistral_client()

    # Build a short summary of the conversation so far
    history_text = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in state.get("short_term_history", [])[-10:]
    )
    prompt = (
        f"Summarise the following conversation for long-term memory:\n{history_text}\n"
        f"New user message: {state['user_message']}"
    )

    resp = client.chat(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    summary = resp.choices[0].message.content.strip()

    # TODO: persist turn + summary to Conversations DB (MongoDB/PostgreSQL)
    return {
        **state,
        "agent_used": "memory",
        "response": "✅ I have saved this to your memory.",
        "long_term_summary": summary,
    }
