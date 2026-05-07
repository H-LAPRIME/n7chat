"""
Action Agent: executes small CRUD operations when intent is actionable.
"""

import re

from agents.state import AgentState
from agents.utils.llm_clients import get_langchain_groq_action

ACTION_SYSTEM = """You are an action executor for an educational platform.
Given the user's request, confirm what CRUD action to take and return a concise structured summary.
Supported actions: enroll_course, create_course, submit_request.
Respond in the user's language."""


def _normalise(text: str) -> str:
    return text.lower().strip()


def _extract_course_title(message: str) -> str:
    patterns = [
        r"(?:module|cours|course)\s+(.+)$",
        r"(?:ajouter|creer|créer|create)\s+(.+)$",
        r"(?:inscrire|inscription|enroll).*?(?:a|à|au|cours|module)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .:;")
    return message.strip(" .:;")


def _execute_action(state: AgentState) -> str | None:
    try:
        from app import db
        from app.models.course import Course, Enrollment
    except Exception as e:
        print(f"Action DB import error: {e}")
        return None

    message = state["user_message"]
    text = _normalise(message)
    user_id = state.get("user_id")
    role = state.get("role", "student")

    if any(word in text for word in ("ajouter", "creer", "créer", "create")) and any(
        word in text for word in ("module", "cours", "course")
    ):
        if role != "admin":
            return "Seul un enseignant/admin peut creer un module."

        title = _extract_course_title(message)
        course = Course(title=title, description="", created_by=user_id)
        db.session.add(course)
        db.session.commit()
        return f"Module cree: {course.title}"

    if any(word in text for word in ("inscrire", "inscription", "enroll")):
        title = _extract_course_title(message)
        course = Course.query.filter(Course.title.ilike(f"%{title}%")).first()
        if not course:
            course = Course.query.first()
        if not course:
            return "Aucun cours disponible pour l'inscription."

        existing = db.session.get(Enrollment, {"user_id": str(user_id), "course_id": str(course.id)})
        if existing:
            return f"Vous etes deja inscrit au cours: {course.title}"

        db.session.add(Enrollment(user_id=str(user_id), course_id=str(course.id)))
        db.session.commit()
        return f"Inscription effectuee au cours: {course.title}"

    if any(word in text for word in ("demande", "request", "support")):
        return "Votre demande a ete prise en compte. Un administrateur pourra la traiter."

    return None


def action_node(state: AgentState) -> AgentState:
    action_result = _execute_action(state)
    if action_result:
        return {
            **state,
            "agent_used": "action",
            "response": action_result,
        }

    llm = get_langchain_groq_action()
    response = llm.invoke(
        [
            {"role": "system", "content": ACTION_SYSTEM},
            {"role": "user", "content": state["user_message"]},
        ]
    )
    return {
        **state,
        "agent_used": "action",
        "response": response.content.strip(),
    }
