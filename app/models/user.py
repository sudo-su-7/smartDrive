"""User model — wraps MongoDB document for Flask-Login."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId
import bcrypt
from flask_login import UserMixin


class User(UserMixin):
    """Thin wrapper around a MongoDB users document."""

    def __init__(self, doc: dict):
        self._doc = doc

    # ── Flask-Login interface ─────────────────────────────────────────────────

    def get_id(self) -> str:
        return str(self._doc["_id"])

    @property
    def is_active(self) -> bool:
        return self._doc.get("is_active", True)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def id(self) -> str:
        return str(self._doc["_id"])

    @property
    def name(self) -> str:
        return self._doc.get("name", "")

    @property
    def email(self) -> str:
        return self._doc.get("email", "")

    @property
    def role(self) -> str:
        return self._doc.get("role", "user")

    @property
    def phone(self) -> str:
        return self._doc.get("phone", "")

    @property
    def email_verified(self) -> bool:
        return self._doc.get("email_verified", False)

    @property
    def created_at(self) -> datetime:
        return self._doc.get("created_at", datetime.now(timezone.utc))

    def is_admin(self) -> bool:
        return self.role == "admin"

    # ── Password helpers ──────────────────────────────────────────────────────

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

    def check_password(self, plain: str) -> bool:
        stored = self._doc.get("password_hash", "").encode()
        return bcrypt.checkpw(plain.encode(), stored)

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def from_db(cls, doc: dict | None) -> "User | None":
        if doc is None:
            return None
        return cls(doc)

    @staticmethod
    def make_document(name: str, email: str, password: str, phone: str = "") -> dict:
        now = datetime.now(timezone.utc)
        return {
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": User.hash_password(password),
            "role": "user",
            "is_active": True,
            "email_verified": False,
            "phone": phone.strip(),
            "created_at": now,
            "updated_at": now,
        }
