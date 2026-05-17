import asyncio
import json
import time
from os import environ
from pathlib import Path

import httpx
import jwt
from dotenv import load_dotenv

# Setup path and env
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
load_dotenv(BACKEND / ".env")

import sys
sys.path.insert(0, str(ROOT))

from backend.db.supabase import fetch_one
from backend.main import app


async def main():
    print("--- Test n7chat SSE Stream ---")
    
    # 1. Fetch Sara's user ID from Supabase
    print("Fetching Sara's user profile...")
    sara_user = fetch_one("SELECT id, email FROM users WHERE email = 'sara.elamrani@n7chat.local'")
    if not sara_user:
        print("Error: Student Sara not found in DB. Did you run seed.py?")
        return
        
    sara_id = str(sara_user["id"])
    print(f"Found Sara: {sara_id}")

    # 2. Generate a valid JWT token
    secret = environ.get("JWT_SECRET")
    token = jwt.encode(
        {"sub": sara_id, "role": "student", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256"
    )

    # 3. Use the AsyncClient to hit the FastAPI app directly (no server needed)
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create a new conversation
        print("\nCreating a new conversation...")
        conv_resp = await client.post(
            "/chat/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Terminal"}
        )
        if conv_resp.status_code != 201:
            print(f"Failed to create conversation: {conv_resp.text}")
            return
            
        conv_id = conv_resp.json()["id"]
        print(f"Conversation created: {conv_id}")

        print(f"\nConversation created: {conv_id} (Type 'quit' to exit)")
        print("-" * 50)

        while True:
            try:
                message = input("\nUser: ").strip()
                if not message:
                    continue
                if message.lower() in ("quit", "exit", "q"):
                    break
            except (EOFError, KeyboardInterrupt):
                break

            print("Assistant: ", end="", flush=True)

            # Stream the chat
            async with client.stream(
                "POST",
                "/chat/stream",
                headers={"Authorization": f"Bearer {token}"},
                json={"conversation_id": conv_id, "message": message},
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    text = await response.aread()
                    print(f"\n[Error: HTTP {response.status_code}] {text.decode()}")
                    continue

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        data = json.loads(data_str)
                        if "chunk" in data:
                            print(data["chunk"], end="", flush=True)
                        elif "error" in data:
                            print(f"\n[LLM Error: {data['error']}]", end="", flush=True)
                    except json.JSONDecodeError:
                        print(f"\n[Decode Error on: {data_str}]", end="", flush=True)
                        
            print() # newline after assistant response

        print("\n\n--- Session finished ---")

if __name__ == "__main__":
    asyncio.run(main())
