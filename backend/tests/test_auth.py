"""Tests for authentication endpoints."""
import pytest


class TestRegistration:
    """Tests for user registration."""

    def test_register_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user_data["email"]

    def test_register_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email returns 409."""
        client.post("/api/auth/register", json=test_user_data)
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "TestPassword123"
        })
        assert response.status_code == 422


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, test_user_data):
        """Test successful login."""
        # Register first
        client.post("/api/auth/register", json=test_user_data)

        # Login
        response = client.post("/api/auth/token", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user_data["email"]

    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password."""
        client.post("/api/auth/register", json=test_user_data)

        response = client.post("/api/auth/token", data={
            "username": test_user_data["email"],
            "password": "WrongPassword"
        })
        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Bearer"

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/api/auth/token", data={
            "username": "nonexistent@example.com",
            "password": "SomePassword123"
        })
        assert response.status_code == 401


class TestMe:
    """Tests for /me endpoint."""

    def test_get_me_authenticated(self, client, auth_headers, test_user_data):
        """Test getting current user info."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user_data["email"]

    def test_get_me_unauthenticated(self, client):
        """Test getting current user without auth."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
