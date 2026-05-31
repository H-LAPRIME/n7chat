import json

from backend.routers import chat


def test_message_format_detects_markdown_links():
    content = "1. **francais**\n   [Ouvrir le PDF](https://example.test/cours.pdf)"

    assert chat._message_format(content) == "markdown"


def test_load_history_includes_conversation_local_context(monkeypatch):
    def fake_fetch_one(query, params):
        assert params["conv_id"] == "conv-1"
        return {"context_summary": json.dumps({"last_course_context": {"course_titles": ["francais"]}})}

    def fake_fetch_all(query, params):
        assert params["conv_id"] == "conv-1"
        return [{"sender_type": "assistant", "content": "Previous answer"}]

    monkeypatch.setattr(chat, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(chat, "fetch_all", fake_fetch_all)

    history = chat._load_history("conv-1")

    assert history[0]["role"] == "system"
    assert "Conversation-local context" in history[0]["content"]
    assert history[1] == {"role": "assistant", "content": "Previous answer"}


def test_update_conversation_context_stores_only_current_conversation(monkeypatch):
    captured = {}

    def fake_execute(query, params):
        captured["query"] = query
        captured["params"] = params

    monkeypatch.setattr(chat, "execute", fake_execute)

    chat._update_conversation_context(
        "conv-2",
        user_message="cour de francai?",
        assistant_response="**francais**\n[Ouvrir le PDF](https://example.test/fr.pdf)",
    )

    assert captured["params"]["id"] == "conv-2"
    payload = json.loads(captured["params"]["context_summary"])
    assert payload["last_user_message"] == "cour de francai?"
    assert payload["last_course_context"]["course_titles"] == ["francais"]
    assert payload["last_course_context"]["links"][0]["label"] == "Ouvrir le PDF"
