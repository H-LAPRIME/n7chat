"""
Persisted in-app notifications.
"""

import uuid
from sqlalchemy import Boolean, Column, DateTime, String, Text, func

from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(40), default="info")
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self) -> dict:
        timestamp = self.created_at.isoformat() if self.created_at else None
        return {
            "id": self.id,
            "user_id": self.user_id or "all",
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "timestamp": timestamp,
            "created_at": timestamp,
        }
