from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="UUID of an existing conversation.")
    message: str = Field(..., min_length=1, max_length=8000)


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Nouvelle conversation", max_length=255)


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
