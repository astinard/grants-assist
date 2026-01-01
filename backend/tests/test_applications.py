"""Tests for application endpoints."""
import pytest

from app.models.database import GrantProgram, GrantCategory


@pytest.fixture
def program_for_application(db_session):
    """Create a program for application tests."""
    program = GrantProgram(
        id="app_test_program",
        name="Application Test Program",
        agency="Test Agency",
        category=GrantCategory.SMALL_BUSINESS,
        is_active=True,
    )
    db_session.add(program)
    db_session.commit()
    return program


class TestCreateApplication:
    """Tests for creating applications."""

    def test_create_application_success(self, client, auth_headers, program_for_application):
        """Test creating a new application."""
        response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program_id"] == program_for_application.id
        assert data["program_name"] == program_for_application.name
        assert data["status"] == "draft"
        assert data["completeness_score"] == 0

    def test_create_application_duplicate(self, client, auth_headers, program_for_application):
        """Test that duplicate draft applications are rejected."""
        # Create first application
        client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )

        # Try to create another
        response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already have a draft" in response.json()["detail"]

    def test_create_application_invalid_program(self, client, auth_headers):
        """Test creating application for non-existent program."""
        response = client.post(
            "/api/applications/",
            json={"program_id": "nonexistent"},
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_create_application_unauthenticated(self, client, program_for_application):
        """Test that unauthenticated users cannot create applications."""
        response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id}
        )
        assert response.status_code == 401


class TestListApplications:
    """Tests for listing applications."""

    def test_list_applications_empty(self, client, auth_headers):
        """Test listing applications when none exist."""
        response = client.get("/api/applications/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["applications"] == []

    def test_list_applications_with_data(self, client, auth_headers, program_for_application):
        """Test listing applications with data."""
        # Create an application
        client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )

        response = client.get("/api/applications/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["applications"]) == 1

    def test_list_applications_filter_by_status(self, client, auth_headers, program_for_application):
        """Test filtering applications by status."""
        # Create an application (defaults to draft)
        client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )

        # Filter by draft status
        response = client.get("/api/applications/?status=draft", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 1

        # Filter by submitted status (should be empty)
        response = client.get("/api/applications/?status=submitted", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestUpdateApplication:
    """Tests for updating applications."""

    def test_update_application_status(self, client, auth_headers, program_for_application):
        """Test updating application status."""
        # Create application
        create_response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        app_id = create_response.json()["id"]

        # Update status
        response = client.patch(
            f"/api/applications/{app_id}",
            json={"status": "in_progress"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_application_form_data(self, client, auth_headers, program_for_application):
        """Test updating application form data."""
        # Create application
        create_response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        app_id = create_response.json()["id"]

        # Update form data
        response = client.patch(
            f"/api/applications/{app_id}",
            json={"form_data": {"project_title": "My Project"}},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_update_application_not_found(self, client, auth_headers):
        """Test updating non-existent application."""
        response = client.patch(
            "/api/applications/nonexistent",
            json={"status": "in_progress"},
            headers=auth_headers
        )
        assert response.status_code == 404


class TestDeleteApplication:
    """Tests for deleting applications."""

    def test_delete_draft_application(self, client, auth_headers, program_for_application):
        """Test deleting a draft application."""
        # Create application
        create_response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        app_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify it's gone
        list_response = client.get("/api/applications/", headers=auth_headers)
        assert list_response.json()["total"] == 0

    def test_delete_submitted_application_fails(self, client, auth_headers, program_for_application):
        """Test that submitted applications cannot be deleted."""
        # Create and submit application
        create_response = client.post(
            "/api/applications/",
            json={"program_id": program_for_application.id},
            headers=auth_headers
        )
        app_id = create_response.json()["id"]

        # Change status to submitted
        client.patch(
            f"/api/applications/{app_id}",
            json={"status": "submitted"},
            headers=auth_headers
        )

        # Try to delete
        response = client.delete(f"/api/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 400
        assert "draft" in response.json()["detail"].lower()

    def test_delete_application_not_found(self, client, auth_headers):
        """Test deleting non-existent application."""
        response = client.delete("/api/applications/nonexistent", headers=auth_headers)
        assert response.status_code == 404
