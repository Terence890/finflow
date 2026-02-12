from __future__ import annotations

from typing import Optional, Tuple

from finflow.app import db
from finflow.auth.model import User


def get_user_by_email(email: str) -> Optional[User]:
    """
    Return a User object for the given email or None if not found.
    """
    if not email:
        return None
    return User.query.filter_by(email=email.lower().strip()).first()


def register_user(
    name: str, email: str, password: str
) -> Tuple[Optional[User], Optional[str]]:
    """
    Register a new user.

    Returns a tuple (user, error). If registration succeeds, error is None.
    If it fails, user is None and error contains a short message.
    """
    if not (name and email and password):
        return None, "Name, email and password are required."

    email_clean = email.lower().strip()
    existing = get_user_by_email(email_clean)
    if existing:
        return None, "A user with this email already exists."

    user = User(name=name.strip(), email=email_clean)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as exc:  # pragma: no cover - surface DB errors to caller
        db.session.rollback()
        return None, f"Database error: {exc}"


def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Validate credentials. Returns the User if authentication succeeds, otherwise None.
    """
    if not (email and password):
        return None

    user = get_user_by_email(email)
    if not user:
        return None

    if user.check_password(password):
        return user

    return None
