"""Tests for user profile endpoints."""
import pytest


class TestGetProfile:
    """Tests for getting user profile."""

    def test_get_profile_creates_empty(self, client, auth_headers):
        """Test that getting profile creates an empty one if none exists."""
        response = client.get("/api/users/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["completeness"] == 0.0

    def test_get_profile_unauthenticated(self, client):
        """Test that unauthenticated users cannot get profile."""
        response = client.get("/api/users/profile")
        assert response.status_code == 401


class TestUpdateProfile:
    """Tests for updating user profile."""

    def test_update_profile_basic(self, client, auth_headers):
        """Test updating basic profile fields."""
        update_data = {
            "full_name": "John Doe",
            "organization_name": "Test Corp",
            "city": "Austin",
            "state": "TX"
        }
        response = client.patch(
            "/api/users/profile",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "John Doe"
        assert data["organization_name"] == "Test Corp"
        assert data["city"] == "Austin"
        assert data["state"] == "TX"

    def test_update_profile_completeness(self, client, auth_headers):
        """Test that completeness score updates correctly."""
        # Empty profile should have 0% completeness
        response = client.get("/api/users/profile", headers=auth_headers)
        assert response.json()["completeness"] == 0.0

        # Fill some fields
        update_data = {
            "full_name": "Jane Doe",
            "organization_name": "Acme Inc",
            "address": "123 Main St",
            "city": "Houston",
            "state": "TX",
            "zip_code": "77001",
            "phone": "555-1234",
            "ein": "12-3456789",
            "uei_number": "ABC123456789"
        }
        response = client.patch(
            "/api/users/profile",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        # All 9 fields filled = 100%
        assert response.json()["completeness"] == 100.0

    def test_update_profile_partial(self, client, auth_headers):
        """Test partial profile update preserves existing data."""
        # First update
        client.patch(
            "/api/users/profile",
            json={"full_name": "First Name"},
            headers=auth_headers
        )

        # Second update should not overwrite first
        response = client.patch(
            "/api/users/profile",
            json={"city": "Dallas"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "First Name"
        assert data["city"] == "Dallas"

    def test_update_profile_federal_ids(self, client, auth_headers):
        """Test updating federal ID fields."""
        update_data = {
            "ein": "12-3456789",
            "uei_number": "ABCD12345678",
            "sam_registered": True
        }
        response = client.patch(
            "/api/users/profile",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ein"] == "12-3456789"
        assert data["uei_number"] == "ABCD12345678"
        assert data["sam_registered"] is True

    def test_update_profile_unauthenticated(self, client):
        """Test that unauthenticated users cannot update profile."""
        response = client.patch(
            "/api/users/profile",
            json={"full_name": "Test"}
        )
        assert response.status_code == 401
