"""Tests for eligibility endpoints."""
import pytest

from app.models.database import GrantProgram, GrantCategory


@pytest.fixture
def eligibility_programs(db_session):
    """Create programs for eligibility testing."""
    programs = [
        GrantProgram(
            id="sba_small_biz",
            name="SBA Small Business Grant",
            agency="SBA",
            category=GrantCategory.SMALL_BUSINESS,
            is_active=True,
        ),
        GrantProgram(
            id="usda_rural",
            name="USDA Rural Development",
            agency="USDA",
            category=GrantCategory.AGRICULTURE,
            is_active=True,
        ),
    ]
    db_session.add_all(programs)
    db_session.commit()
    return programs


class TestCheckEligibility:
    """Tests for checking eligibility."""

    def test_check_eligibility_no_profile(self, client, auth_headers, eligibility_programs):
        """Test eligibility check with no profile returns empty results."""
        response = client.get("/api/eligibility/check", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_programs"] == 0
        assert data["eligible_count"] == 0

    def test_check_eligibility_with_profile(self, client, auth_headers, eligibility_programs):
        """Test eligibility check with profile data."""
        # Create a profile first
        client.patch(
            "/api/users/profile",
            json={
                "full_name": "John Doe",
                "organization_name": "Small Biz Inc",
                "address": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "zip_code": "78701",
                "ein": "12-3456789",
                "annual_revenue": 500000,
                "employee_count": 10,
            },
            headers=auth_headers
        )

        response = client.get("/api/eligibility/check", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_programs"] == 2
        assert len(data["programs"]) == 2
        # Each program should have eligibility info
        for program in data["programs"]:
            assert "program_id" in program
            assert "eligible" in program
            assert "match_score" in program
            assert "missing_requirements" in program

    def test_check_eligibility_sorted_by_score(self, client, auth_headers, eligibility_programs):
        """Test that results are sorted by match score descending."""
        # Create profile
        client.patch(
            "/api/users/profile",
            json={
                "full_name": "Jane Doe",
                "organization_name": "Test Org",
                "address": "456 Oak Ave",
                "city": "Dallas",
                "state": "TX",
                "zip_code": "75001",
            },
            headers=auth_headers
        )

        response = client.get("/api/eligibility/check", headers=auth_headers)
        assert response.status_code == 200
        programs = response.json()["programs"]

        # Verify sorted by match_score descending
        scores = [p["match_score"] for p in programs]
        assert scores == sorted(scores, reverse=True)

    def test_check_eligibility_unauthenticated(self, client):
        """Test that unauthenticated users cannot check eligibility."""
        response = client.get("/api/eligibility/check")
        assert response.status_code == 401


class TestCheckProgramEligibility:
    """Tests for checking eligibility for a specific program."""

    def test_check_program_eligibility(self, client, auth_headers, eligibility_programs):
        """Test checking eligibility for a specific program."""
        # Create profile
        client.patch(
            "/api/users/profile",
            json={
                "full_name": "Test User",
                "organization_name": "Test Business",
                "address": "789 Pine St",
                "city": "Houston",
                "state": "TX",
                "zip_code": "77001",
                "ein": "98-7654321",
            },
            headers=auth_headers
        )

        response = client.get(
            f"/api/eligibility/check/{eligibility_programs[0].id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program_id"] == eligibility_programs[0].id
        assert "eligible" in data
        assert "match_score" in data
        assert "missing_requirements" in data

    def test_check_program_eligibility_no_profile(self, client, auth_headers, eligibility_programs):
        """Test checking program eligibility with no profile."""
        response = client.get(
            f"/api/eligibility/check/{eligibility_programs[0].id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False
        assert data["match_score"] == 0
        assert "complete your profile" in data["missing_requirements"][0].lower()

    def test_check_program_eligibility_not_found(self, client, auth_headers):
        """Test checking eligibility for non-existent program."""
        response = client.get(
            "/api/eligibility/check/nonexistent",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_check_program_eligibility_unauthenticated(self, client, eligibility_programs):
        """Test that unauthenticated users cannot check program eligibility."""
        response = client.get(f"/api/eligibility/check/{eligibility_programs[0].id}")
        assert response.status_code == 401
