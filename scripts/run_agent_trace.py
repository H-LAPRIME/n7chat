from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from backend.agents.graph import route_from_intent
from backend.agents.orchestrator import run_orchestrator_agent
from backend.agents.pdf_agent import run_pdf_agent
from backend.agents.rag_agent import run_rag_agent
from backend.agents.sql_agent import run_sql_agent


DEFAULT_USER = {
    "user_id": "3ae2e86b-65dc-5939-997a-e69bfa2bcf59",
    "student_id": "59a46832-5d35-5fb2-bea6-3f48a11fc279",
    "filiere_id": "c1e4f716-20d6-5016-8cfd-649828cd03cd",
    "role": "student",
    "semester": 3
}


def _pretty(value: Any, max_chars: int = 6000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + f"\n... truncated {len(text) - max_chars} chars"


def _load_user(args: argparse.Namespace) -> dict[str, Any]:
    user = dict(DEFAULT_USER)
    if args.user_file:
        user.update(json.loads(Path(args.user_file).read_text(encoding="utf-8")))
    if args.user_json:
        user.update(json.loads(args.user_json))
    if args.role:
        user["role"] = args.role
    if args.user_id:
        user["user_id"] = args.user_id
    if args.student_id:
        user["student_id"] = args.student_id
    if args.filiere_id:
        user["filiere_id"] = args.filiere_id
    if args.filiere_name:
        user["filiere_name"] = args.filiere_name
    if args.semester is not None:
        user["semester"] = args.semester
    return user


def _print_step(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


async def run_trace(message: str, user: dict[str, Any], history: list[dict[str, Any]]) -> int:
    _print_step("1. USER MESSAGE")
    print(message)

    _print_step("2. USER CONTEXT SENT TO ORCHESTRATOR")
    print(_pretty(user))

    _print_step("3. ORCHESTRATOR AGENT: CLASSIFY INTENT")
    decision = await run_orchestrator_agent(message=message, history=history, user=user)
    print("Raw orchestrator decision:")
    print(_pretty(decision))

    route = route_from_intent({"intent": decision["intent"]})
    plan = decision.get("plan") or [{"agent": route, "purpose": "Fallback route."}]
    print("\nOrchestrator route decision:")
    print(f"intent = {decision['intent']}")
    print(f"route  = {route}")
    print(f"reason = {decision.get('reason', '')}")
    print("\nOrchestrator multi-agent plan:")
    print(_pretty(plan))

    data_context: dict[str, Any] = {}
    final_result: dict[str, Any] = {}
    for index, step in enumerate(plan, start=1):
        agent = step.get("agent", "general")
        purpose = step.get("purpose", "")
        _print_step(f"4.{index}. CALL AGENT: {agent.upper()}")
        print(f"purpose = {purpose}")

        if agent == "sql":
            result = await run_sql_agent(message=message, intent=decision["intent"], user=user)
            data_context["sql"] = result.get("data", {})
        elif agent == "rag":
            result = await run_rag_agent(message=message, user=user)
            data_context["rag"] = {"context": result.get("context"), "sources": result.get("sources")}
        elif agent == "pdf":
            result = await run_pdf_agent(
                message=message,
                user=user,
                data_context=data_context,
            )
            data_context["pdf"] = result.get("data", {})
        else:
            result = {
                "ok": True,
                "answer": (
                    "Je peux t'aider avec les notes, absences, emploi du temps, cours, "
                    "documents indexes et generation de PDF. Peux-tu preciser ta demande ?"
                ),
                "data": {},
                "error": None,
            }

        print("Raw agent output:")
        print(_pretty(result))
        final_result = result

    _print_step("5. FINAL ANSWER RETURNED TO CHAT")
    print(final_result.get("answer", ""))

    error = final_result.get("error")
    if error:
        _print_step("6. ERROR / DEBUG")
        print(error)
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real n7chat agent flow and print each step.",
    )
    parser.add_argument(
        "--message",
        "-m",
        required=True,
        help="User message to send to the orchestrator.",
    )
    parser.add_argument(
        "--user-json",
        help=(
            "Inline JSON user context. Example: "
            "'{\"role\":\"student\",\"student_id\":\"...\",\"filiere_id\":\"...\"}'"
        ),
    )
    parser.add_argument(
        "--user-file",
        help="Path to a JSON file containing user context.",
    )
    parser.add_argument(
        "--history-json",
        default="[]",
        help="Optional conversation history JSON list.",
    )
    parser.add_argument("--role", help="User role, for example student or teacher.")
    parser.add_argument("--user-id", help="Authenticated user id/sub.")
    parser.add_argument("--student-id", help="Student id for notes, absences, and PDF.")
    parser.add_argument("--filiere-id", help="Filiere id for timetable/module queries.")
    parser.add_argument("--filiere-name", help="Filiere name for RAG filtering.")
    parser.add_argument("--semester", type=int, help="Semester number.")
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / "backend" / ".env")
    args = parse_args()
    user = _load_user(args)
    history = json.loads(args.history_json)
    return asyncio.run(run_trace(args.message, user, history))


if __name__ == "__main__":
    raise SystemExit(main())
