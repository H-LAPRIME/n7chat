"""
backend/app/models/user.py
───────────────────────────
SQLAlchemy User model with bcrypt password hashing.
"""

import uuid
import bcrypt
from sqlalchemy import Column, String, DateTime, func
from app import db
from app.models.types import GUID


class User(db.Model):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")  # 'student' | 'admin'
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Password Reset
    reset_code = Column(String, nullable=True)
    reset_code_expires = Column(DateTime(timezone=True), nullable=True)

    def set_password(self, plain: str) -> None:
        self.password_hash = bcrypt.hashpw(
            plain.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, plain: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), self.password_hash.encode("utf-8"))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
