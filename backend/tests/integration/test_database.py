"""
Database integration tests.

These tests verify database connectivity and basic operations.
Run with: pytest tests/integration/test_database.py -m integration

NOTE: These tests require a PostgreSQL database because the models use
PostgreSQL-specific types (JSONB). They will be skipped if PostgreSQL
is not available.
"""
import pytest
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def is_postgres_available():
    """Check if PostgreSQL is available for testing."""
    try:
        import psycopg2
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres",
            connect_timeout=3
        )
        conn.close()
        return True
    except Exception:
        return False


# Skip all tests in this module if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL not available (tests require PostgreSQL for JSONB support)"
)


class TestDatabaseConnection:
    """Tests for database connectivity"""

    @pytest.mark.integration
    def test_database_url_is_configured(self):
        """Verify DATABASE_URL environment variable is set."""
        # In test environment, we use SQLite
        db_url = os.getenv("DATABASE_URL", "")
        assert db_url, "DATABASE_URL should be set"

    @pytest.mark.integration
    def test_can_create_engine(self):
        """Test that we can create a SQLAlchemy engine."""
        from sqlalchemy import create_engine

        db_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
        engine = create_engine(db_url)
        assert engine is not None

        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            assert result.scalar() == 1

    @pytest.mark.integration
    def test_base_metadata_has_tables(self):
        """Verify that model metadata is properly configured."""
        from src.models.base import Base

        # Import models to register them
        from src.models import (
            tenant, report, feed, job, brand, user, analytics, audit, list
        )

        # Check that tables are registered
        table_names = list(Base.metadata.tables.keys())
        assert len(table_names) > 0
        assert "tenants" in table_names or "reports" in table_names


class TestDatabaseModels:
    """Tests for database models"""

    @pytest.mark.integration
    def test_tenant_model_creates_table(self, test_db_engine):
        """Test that Tenant model creates proper table."""
        from src.models.base import Base
        from src.models.tenant import Tenant

        Base.metadata.create_all(bind=test_db_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        assert "tenants" in tables

    @pytest.mark.integration
    def test_report_model_creates_table(self, test_db_engine):
        """Test that Report model creates proper table."""
        from src.models.base import Base
        from src.models.report import Report

        Base.metadata.create_all(bind=test_db_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        assert "reports" in tables

    @pytest.mark.integration
    def test_list_model_creates_tables(self, test_db_engine):
        """Test that List and ListItem models create proper tables."""
        from src.models.base import Base
        from src.models.list import List, ListItem

        Base.metadata.create_all(bind=test_db_engine)

        from sqlalchemy import inspect
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        assert "lists" in tables
        assert "list_items" in tables


class TestDatabaseOperations:
    """Tests for basic CRUD operations"""

    @pytest.mark.integration
    def test_can_create_tenant(self, test_db_session):
        """Test creating a tenant record."""
        from src.models.tenant import Tenant

        tenant = Tenant(
            name="Test Company",
            slug="test-company",
            is_active=True
        )
        test_db_session.add(tenant)
        test_db_session.commit()

        assert tenant.id is not None

        # Verify we can query it back
        retrieved = test_db_session.query(Tenant).filter_by(slug="test-company").first()
        assert retrieved is not None
        assert retrieved.name == "Test Company"

    @pytest.mark.integration
    def test_can_create_list(self, test_db_session):
        """Test creating a list record."""
        from src.models.tenant import Tenant
        from src.models.list import List

        # First create a tenant
        tenant = Tenant(name="Test Co", slug="test-co", is_active=True)
        test_db_session.add(tenant)
        test_db_session.commit()

        # Create a list
        list_obj = List(
            name="My Test List",
            list_type="report",
            description="A test list",
            tenant_id=tenant.id
        )
        test_db_session.add(list_obj)
        test_db_session.commit()

        assert list_obj.id is not None

        # Verify we can query it back
        retrieved = test_db_session.query(List).filter_by(name="My Test List").first()
        assert retrieved is not None
        assert retrieved.list_type == "report"
        assert retrieved.tenant_id == tenant.id
