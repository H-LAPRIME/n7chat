"""
tests/test_rag.py
───────────────────
Unit tests for the RAG retrieval pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRAGRetrieval:
    @patch("agents.retrieval_agent.search_index")
    @patch("agents.retrieval_agent.get_langchain_groq")
    def test_retrieval_with_context(self, mock_groq, mock_search):
        mock_search.return_value = [
            {
                "doc_id": "d1",
                "filename": "python_course.pdf",
                "page": 3,
                "chunk_index": 0,
                "text": "Python is a high-level programming language.",
                "score": 0.95,
            }
        ]
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="Python is a high-level programming language used for data science."
        )
        mock_groq.return_value = mock_llm

        from agents.retrieval_agent import retrieval_node
        state = {
            "user_message": "What is Python?",
            "session_id": "s", "user_id": "u", "role": "student",
            "intent": "doc_search", "short_term_history": [],
            "long_term_summary": "", "agent_used": "", "response": "",
            "sources": [], "messages": [],
        }
        result = retrieval_node(state)
        assert result["agent_used"] == "retrieval"
        assert len(result["sources"]) > 0
        assert result["sources"][0]["doc"] == "python_course.pdf"

    @patch("agents.retrieval_agent.search_index")
    def test_retrieval_no_results(self, mock_search):
        mock_search.return_value = []

        from agents.retrieval_agent import retrieval_node
        state = {
            "user_message": "Unknown question",
            "session_id": "s", "user_id": "u", "role": "student",
            "intent": "doc_search", "short_term_history": [],
            "long_term_summary": "", "agent_used": "", "response": "",
            "sources": [], "messages": [],
        }
        result = retrieval_node(state)
        assert result["sources"] == []
        assert "trouvé" in result["response"].lower() or "found" in result["response"].lower()
