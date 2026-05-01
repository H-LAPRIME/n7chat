"""
agents/planner_agent.py
─────────────────────────
Planner Agent — Gemini Flash 2.0
Decomposes complex tasks into ordered sub-tasks.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_gemini

PLANNER_SYSTEM = """You are a task planner for an educational AI assistant.
Break down the user's complex request into a numbered list of atomic sub-tasks.
Each sub-task must map to one of: quick_answer, doc_search, action (CRUD), save.
Return ONLY the numbered list, no extra explanation."""


def planner_node(state: AgentState) -> AgentState:
    llm = get_langchain_gemini()
    response = llm.invoke(
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": state["user_message"]},
        ]
    )
    plan = response.content.strip()

    # TODO: parse plan and dispatch sub-tasks to other agents
    return {
        **state,
        "agent_used": "planner",
        "response": f"📋 Here is my plan:\n{plan}",
    }
