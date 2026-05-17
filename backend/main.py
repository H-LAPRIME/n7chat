
from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth, chat, courses, documents, events, profile

app = FastAPI(title="University Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/auth",    tags=["auth"])
app.include_router(chat.router,    prefix="/chat",    tags=["chat"])
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(events.router,  prefix="/events",  tags=["events"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
