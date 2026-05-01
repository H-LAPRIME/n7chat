"""
tests/test_agents.py
──────────────────────
Unit tests for the LangGraph agent pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestIntentClassification:
    @patch("agents.orchestrator.get_langchain_groq")
    def test_classify_doc_search(self, mock_groq):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="doc_search")
        mock_groq.return_value = mock_llm

        from agents.orchestrator import classify_intent_node
        state = {
            "user_message": "Explique le module 2 du cours Python",
            "session_id": "test-session",
            "user_id": "test-user",
            "role": "student",
            "intent": "",
            "short_term_history": [],
            "long_term_summary": "",
            "agent_used": "",
            "response": "",
            "sources": [],
            "messages": [],
        }
        result = classify_intent_node(state)
        assert result["intent"] == "doc_search"

    @patch("agents.orchestrator.get_langchain_groq")
    def test_invalid_intent_falls_back_to_unknown(self, mock_groq):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="INVALID_LABEL")
        mock_groq.return_value = mock_llm

        from agents.orchestrator import classify_intent_node
        state = {
            "user_message": "???",
            "session_id": "s", "user_id": "u", "role": "student",
            "intent": "", "short_term_history": [], "long_term_summary": "",
            "agent_used": "", "response": "", "sources": [], "messages": [],
        }
        result = classify_intent_node(state)
        assert result["intent"] == "unknown_intent"


class TestFaqAgent:
    @patch("agents.faq_agent._get_redis")
    @patch("agents.faq_agent.get_langchain_groq")
    def test_cache_miss_calls_llm(self, mock_groq, mock_redis):
        mock_redis.return_value.get.return_value = None
        mock_redis.return_value.setex.return_value = True

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Paris is the capital of France.")
        mock_groq.return_value = mock_llm

        from agents.faq_agent import faq_node
        state = {
            "user_message": "What is the capital of France?",
            "session_id": "s", "user_id": "u", "role": "student",
            "intent": "quick_answer", "short_term_history": [],
            "long_term_summary": "", "agent_used": "", "response": "",
            "sources": [], "messages": [],
        }
        result = faq_node(state)
        assert "Paris" in result["response"]
        assert result["agent_used"] == "faq"
