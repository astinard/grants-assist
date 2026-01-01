"""Pytest fixtures for API tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db, GrantProgram, GrantCategory


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user registration data."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123"
    }


@pytest.fixture
def auth_headers(client, test_user_data):
    """Register a user and return auth headers."""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_program(db_session):
    """Create a sample grant program."""
    program = GrantProgram(
        id="test_program_1",
        name="Test Grant Program",
        agency="Test Agency",
        category=GrantCategory.SMALL_BUSINESS,
        min_award=1000.0,
        max_award=50000.0,
        description="A test grant program for small businesses",
        eligibility_summary="Must be a small business",
        rolling_deadline=True,
        is_active=True,
    )
    db_session.add(program)
    db_session.commit()
    db_session.refresh(program)
    return program
