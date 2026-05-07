"""
Planner Agent: decomposes complex tasks and dispatches simple actions.
"""

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_gemini

PLANNER_SYSTEM = """You are a task planner for an educational AI assistant.
Break down the user's complex request into a numbered list of atomic sub-tasks.
Each sub-task must map to one of: quick_answer, doc_search, action, save.
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

    if "action" in plan.lower():
        from agents.action_agent import action_node

        action_state = action_node(state)
        return {
            **action_state,
            "agent_used": "planner -> action",
            "response": f"Plan:\n{plan}\n\nExecution:\n{action_state.get('response', '')}",
        }

    return {
        **state,
        "agent_used": "planner",
        "response": f"Plan:\n{plan}",
    }
