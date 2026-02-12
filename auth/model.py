from __future__ import annotations

from datetime import datetime
from typing import Optional

from Finflow.app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model, UserMixin):
    """
    Simple User model for authentication.
    - Keeps fields minimal: id, name, email, password_hash, created_at
    - Provides helpers to set/check password and serialize safe data.
    """

    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(100), nullable=False)
    email: str = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash: str = db.Column(db.String(128), nullable=False)
    created_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )

    def set_password(self, password: str) -> None:
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if the provided password matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Return a safe dict representation (no password)."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """
    Flask-Login user loader callback.
    Expects user_id as a string, returns the corresponding User or None.
    """
    if not user_id:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return User.query.get(uid)
