"""
Pytest configuration and shared fixtures for backend tests.

This file is automatically loaded by pytest and makes fixtures available
to all test files without explicit imports.
"""
import os
import sys
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

# IMPORTANT: Set environment variables BEFORE any imports that might load SQLAlchemy
# This prevents the production database engine from being created with PostgreSQL settings
os.environ["ENV"] = "test"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
# Use PostgreSQL URL format but point to a test database (or use real test DB if available)
# SQLite is problematic for integration tests due to PostgreSQL-specific settings
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "abmc_test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Ensure backend modules are importable
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "src"))


# =============================================================================
# Environment Setup
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run."""
    # Environment is already set above, but this fixture ensures it runs first
    yield


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_db_engine():
    """Create an in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    from src.models.base import Base

    # Create all tables
    Base.metadata.create_all(bind=test_db_engine)

    # Create session
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_db_engine)


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def app():
    """Create a test FastAPI application instance."""
    from api.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def authenticated_client(client, test_user_token) -> TestClient:
    """Create an authenticated test client."""
    client.headers["Authorization"] = f"Bearer {test_user_token}"
    return client


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing without API calls."""
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"sentiment": "positive", "summary": "Test summary", "brands": ["Brand1"]}'
                )
            )
        ]
    )
    return mock


@pytest.fixture
def mock_apify_client():
    """Mock Apify client for testing without API calls."""
    mock = MagicMock()
    mock.actor.return_value.call.return_value = MagicMock(
        wait_for_finish=MagicMock(return_value=None)
    )
    mock.dataset.return_value.list_items.return_value = MagicMock(
        items=[
            {
                "id": "test-item-1",
                "url": "https://example.com/post1",
                "caption": "Test caption",
                "likesCount": 100,
                "commentsCount": 10,
            }
        ]
    )
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "id": "test-tenant-123",
        "name": "Test Tenant",
        "slug": "test-tenant",
        "is_active": True,
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "full_name": "Test User",
        "is_active": True,
        "tenant_id": "test-tenant-123",
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing."""
    return {
        "id": "test-report-123",
        "title": "Test Report Title",
        "link": "https://example.com/article",
        "source": "Test Source",
        "provider": "google_search",
        "timestamp": "2024-01-15T10:00:00Z",
        "summary": "This is a test summary of the article.",
        "sentiment": "positive",
        "brands": ["Brand1", "Brand2"],
        "est_reach": 50000,
        "tenant_id": "test-tenant-123",
    }


@pytest.fixture
def sample_brand_data():
    """Sample brand data for testing."""
    return {
        "id": "test-brand-123",
        "name": "Test Brand",
        "aliases": ["TestBrand", "TB"],
        "is_active": True,
        "tenant_id": "test-tenant-123",
    }


@pytest.fixture
def sample_feed_data():
    """Sample feed configuration data for testing."""
    return {
        "id": "test-feed-123",
        "name": "Test Feed",
        "feed_type": "rss",
        "url": "https://example.com/feed.xml",
        "is_active": True,
        "tenant_id": "test-tenant-123",
    }


@pytest.fixture
def sample_list_data():
    """Sample list data for testing."""
    return {
        "id": "test-list-123",
        "name": "Test List",
        "list_type": "report",
        "description": "A test list",
        "tenant_id": "test-tenant-123",
    }


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def test_user_token():
    """Generate a test JWT token."""
    from datetime import datetime, timedelta
    from jose import jwt

    secret_key = os.getenv("JWT_SECRET_KEY", "test-jwt-secret-key")

    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "tenant_id": "test-tenant-123",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")


# =============================================================================
# Async Fixtures (for async tests)
# =============================================================================

@pytest.fixture
async def async_client(app) -> AsyncGenerator:
    """Create an async test client."""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    def _create_temp_file(content: str, filename: str = "test.txt"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path
    return _create_temp_file


@pytest.fixture
def capture_logs(caplog):
    """Capture log output during tests."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog
