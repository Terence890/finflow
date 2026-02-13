"""
Tests for authentication routes and services.

Tests cover:
- User registration
- User login
- User logout
- Password hashing
- Login persistence
"""

from auth.model import User


class TestUserModel:
    """Test User model and password handling."""

    def test_set_password(self, app):
        """Test password hashing."""
        with app.app_context():
            user = User(name="John", email="john@example.com")
            user.set_password("secure123")
            assert user.password_hash != "secure123"
            assert user.check_password("secure123")

    def test_check_password_fails(self, app):
        """Test password validation with wrong password."""
        with app.app_context():
            user = User(name="Jane", email="jane@example.com")
            user.set_password("correct")
            assert not user.check_password("wrong")

    def test_user_to_dict(self, test_user):
        """Test user serialization excludes password."""
        data = test_user.to_dict()
        assert "password_hash" not in data
        assert data["email"] == "test@example.com"


class TestAuthRoutes:
    """Test authentication endpoints."""

    def test_register_get(self, client):
        """Test GET /register returns registration form."""
        response = client.get("/register")
        assert response.status_code == 200
        assert b"register" in response.data.lower()

    def test_register_post_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/register",
            data={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "pass123",
                "confirm_password": "pass123",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_register_post_mismatch_password(self, client):
        """Test registration with mismatched passwords."""
        response = client.post(
            "/register",
            data={
                "name": "User",
                "email": "user@example.com",
                "password": "pass123",
                "confirm_password": "pass456",
            },
        )
        assert response.status_code == 200

    def test_login_get(self, client):
        """Test GET /login returns login form."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"login" in response.data.lower()

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "secure_password_123"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_login_invalid_email(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "anypassword"},
        )
        assert response.status_code == 200

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 200

    def test_logout(self, authenticated_client):
        """Test logout functionality."""
        response = authenticated_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200

    def test_authenticated_user_redirect(self, authenticated_client):
        """Test authenticated user redirect from login."""
        response = authenticated_client.get("/login")
        assert response.status_code == 302
