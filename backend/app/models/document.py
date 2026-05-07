"""
backend/app/models/document.py
────────────────────────────────
SQLAlchemy Document metadata model (for the STRUCTUR DB).
"""

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func

from app import db
from app.models.types import GUID


class Document(db.Model):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    doc_type = Column(String, default="autre")   # reglements | cours | autre
    uploaded_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "filename": self.filename,
            "doc_type": self.doc_type,
            "uploaded_by": str(self.uploaded_by) if self.uploaded_by else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "created_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
