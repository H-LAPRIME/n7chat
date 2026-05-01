"""
agents/fallback_agent.py
──────────────────────────
Fallback Agent — Gemini Flash 2.0
Handles uncertain / out-of-scope intents gracefully.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_gemini

FALLBACK_SYSTEM = """You are a helpful fallback assistant for n7chat.
The user's question could not be handled by specialized agents.
Try your best to help. If the question is truly out of scope,
politely explain that you cannot help and suggest they contact an admin
or rephrase their question. Respond in the same language as the user."""


def fallback_node(state: AgentState) -> AgentState:
    llm = get_langchain_gemini()
    response = llm.invoke(
        [
            {"role": "system", "content": FALLBACK_SYSTEM},
            {"role": "user", "content": state["user_message"]},
        ]
    )
    return {
        **state,
        "agent_used": "fallback",
        "response": response.content.strip(),
    }
