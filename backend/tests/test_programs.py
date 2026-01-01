"""Tests for grant programs endpoints."""
import pytest

from app.models.database import GrantProgram, GrantCategory


class TestListPrograms:
    """Tests for listing grant programs."""

    def test_list_programs_empty(self, client):
        """Test listing programs when none exist."""
        response = client.get("/api/programs/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["programs"] == []

    def test_list_programs_with_data(self, client, db_session, sample_program):
        """Test listing programs with data."""
        response = client.get("/api/programs/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["programs"]) == 1
        assert data["programs"][0]["id"] == sample_program.id
        assert data["programs"][0]["name"] == sample_program.name

    def test_list_programs_filter_by_category(self, client, db_session):
        """Test filtering programs by category."""
        # Create programs in different categories
        program1 = GrantProgram(
            id="healthcare_1",
            name="Healthcare Grant",
            category=GrantCategory.HEALTHCARE,
            is_active=True,
        )
        program2 = GrantProgram(
            id="education_1",
            name="Education Grant",
            category=GrantCategory.EDUCATION,
            is_active=True,
        )
        db_session.add_all([program1, program2])
        db_session.commit()

        response = client.get("/api/programs/?category=healthcare")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["programs"][0]["category"] == "healthcare"

    def test_list_programs_search(self, client, db_session):
        """Test searching programs."""
        program = GrantProgram(
            id="unique_grant",
            name="Unique Agriculture Grant",
            description="For farmers only",
            category=GrantCategory.AGRICULTURE,
            is_active=True,
        )
        db_session.add(program)
        db_session.commit()

        response = client.get("/api/programs/?search=agriculture")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Agriculture" in data["programs"][0]["name"]

    def test_list_programs_active_only(self, client, db_session):
        """Test that inactive programs are filtered by default."""
        active = GrantProgram(
            id="active_1",
            name="Active Grant",
            category=GrantCategory.TECHNOLOGY,
            is_active=True,
        )
        inactive = GrantProgram(
            id="inactive_1",
            name="Inactive Grant",
            category=GrantCategory.TECHNOLOGY,
            is_active=False,
        )
        db_session.add_all([active, inactive])
        db_session.commit()

        response = client.get("/api/programs/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["programs"][0]["id"] == "active_1"


class TestGetProgram:
    """Tests for getting a single program."""

    def test_get_program_success(self, client, db_session, sample_program):
        """Test getting a program by ID."""
        response = client.get(f"/api/programs/{sample_program.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_program.id
        assert data["name"] == sample_program.name
        assert data["agency"] == sample_program.agency

    def test_get_program_not_found(self, client):
        """Test getting a non-existent program."""
        response = client.get("/api/programs/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestCategories:
    """Tests for categories endpoint."""

    def test_list_categories(self, client):
        """Test listing all categories."""
        response = client.get("/api/programs/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        # Check that each category has id and name
        for cat in data["categories"]:
            assert "id" in cat
            assert "name" in cat
