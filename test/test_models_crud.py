from datetime import datetime

from backend.models import (
    ChatRequest,
    ConversationUpdate,
    CourseCreate,
    CourseUpdate,
    EventCreate,
    EventUpdate,
    RenameConversationRequest,
)


def test_course_models_cover_create_and_update():
    created = CourseCreate(
        module_id="module-1",
        title="POO",
        description="Intro",
        file_type="pdf",
    )
    updated = CourseUpdate(title="POO avancee", file_url="storage://courses/poo.pdf")

    assert created.module_id == "module-1"
    assert updated.title == "POO avancee"
    assert updated.model_dump(exclude_unset=True) == {
        "title": "POO avancee",
        "file_url": "storage://courses/poo.pdf",
    }


def test_event_models_cover_create_and_update():
    created = EventCreate(
        title="Controle POO",
        event_type="exam",
        start_date=datetime(2026, 6, 1, 9, 0, 0),
    )
    updated = EventUpdate(location="Salle A1", notify_students=True)

    assert created.event_type == "exam"
    assert updated.model_dump(exclude_unset=True) == {
        "location": "Salle A1",
        "notify_students": True,
    }


def test_chat_models_cover_conversation_crud_inputs():
    chat = ChatRequest(conversation_id="conv-1", message="Bonjour")
    created = ConversationUpdate(title="Nouveau titre")
    renamed = RenameConversationRequest(title="Titre propre")

    assert chat.message == "Bonjour"
    assert created.title == "Nouveau titre"
    assert renamed.title == "Titre propre"
