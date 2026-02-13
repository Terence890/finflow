"""
Pytest configuration and fixtures for PinkLedger tests.

Provides:
- Flask app fixture for testing
- Database fixture (in-memory SQLite)
- Client fixture for making requests
- User fixtures for authentication tests
"""

import pytest
from app import create_app, db
from auth.model import User


@pytest.fixture
def app():
    """Create and configure a Flask app instance for testing."""
    app = create_app(
        test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner for testing commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user in the database."""
    user = User(name="Test User", email="test@example.com")
    user.set_password("secure_password_123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Client with authenticated user session."""
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "secure_password_123"},
    )
    return client
