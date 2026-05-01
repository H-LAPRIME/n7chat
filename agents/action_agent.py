"""
agents/action_agent.py
────────────────────────
Action Agent — GROQ LLM
Executes CRUD operations: inscription, demande, profile updates.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_groq_action

ACTION_SYSTEM = """You are an action executor for an educational platform.
Given the user's request, confirm what CRUD action to take and return a structured summary.
Supported actions: enroll_course, submit_request, update_profile.
Always confirm the action in the user's language."""


def action_node(state: AgentState) -> AgentState:
    llm = get_langchain_groq_action()
    response = llm.invoke(
        [
            {"role": "system", "content": ACTION_SYSTEM},
            {"role": "user", "content": state["user_message"]},
        ]
    )
    action_result = response.content.strip()

    # TODO: execute actual DB mutation based on parsed action
    return {
        **state,
        "agent_used": "action",
        "response": action_result,
    }
