"""
Conversation history and long-term memory models.
"""

import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.types import JSON, TypeDecorator, CHAR

from app import db
from app.models.types import GUID




class ConversationMessage(db.Model):
    __tablename__ = "conversation_messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), index=True, nullable=False)
    user_id = Column(String(36), index=True, nullable=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent = Column(String(80), nullable=True)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "agent": self.agent,
            "sources": self.sources or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConversationMemory(db.Model):
    __tablename__ = "conversation_memories"

    user_id = Column(String(36), primary_key=True)
    summary = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "summary": self.summary,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
