"""backend.tasks – LLM task layer.

Each sub-module holds the raw LLM call (Mistral client + prompt + response
parsing) for one agent, isolated from data-collection and async-wrapping
logic that lives in ``backend.agents``.

Public surface
--------------
orchestrator_llm_task
    ``classify_intent_task`` – synchronous Mistral classification call.
    Also exports shared types: ``Intent``, ``OrchestratorDecision``,
    ``VALID_INTENTS``, ``STATIC_CAPABILITIES``, ``get_orchestrator_context``,
    ``_fallback_intent``, ``_fallback_plan``, ``_normalize_plan``.

sql_llm_task
    ``answer_from_sql_task`` – synchronous Mistral SQL-answer call.

rag_llm_task
    ``answer_from_documents_task`` – synchronous Mistral RAG-answer call.

pdf_llm_task
    ``infer_report_type_task`` – report-type inference (no LLM, pure logic).
    ``build_pdf_answer`` / ``build_pdf_error`` – response assemblers.
"""

from backend.tasks.orchestrator_llm_task import (
    Intent,
    OrchestratorDecision,
    STATIC_CAPABILITIES,
    VALID_INTENTS,
    classify_intent_task,
    get_orchestrator_context,
    _fallback_intent,
    _fallback_plan,
    _fallback_suggest_pdf,
    _normalize_plan,
)
from backend.tasks.sql_llm_task import answer_from_sql_task
from backend.tasks.rag_llm_task import answer_from_documents_task
from backend.tasks.pdf_llm_task import (
    ReportType,
    build_pdf_answer,
    build_pdf_error,
    infer_report_type_task,
)

__all__ = [
    # orchestrator
    "Intent",
    "OrchestratorDecision",
    "STATIC_CAPABILITIES",
    "VALID_INTENTS",
    "classify_intent_task",
    "get_orchestrator_context",
    "_fallback_intent",
    "_fallback_plan",
    "_normalize_plan",
    # sql
    "answer_from_sql_task",
    # rag
    "answer_from_documents_task",
    # pdf
    "ReportType",
    "build_pdf_answer",
    "build_pdf_error",
    "infer_report_type_task",
]
