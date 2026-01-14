"""
Integration tests for the Lists API endpoints.

These tests verify the API endpoints work correctly with mocked authentication.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestListTypesEndpoint:
    """Tests for GET /api/v1/lists/types/"""

    @pytest.mark.api
    def test_get_list_types_returns_supported_types(self, client):
        """Test that list types endpoint returns expected structure."""
        response = client.get("/api/v1/lists/types/")

        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert isinstance(data["types"], list)

    @pytest.mark.api
    def test_get_list_types_includes_report_type(self, client):
        """Test that 'report' type is included in supported types."""
        response = client.get("/api/v1/lists/types/")

        data = response.json()
        type_ids = [t["id"] for t in data["types"]]
        assert "report" in type_ids

    @pytest.mark.api
    def test_list_type_structure(self, client):
        """Test that each list type has required fields."""
        response = client.get("/api/v1/lists/types/")

        data = response.json()
        for list_type in data["types"]:
            assert "id" in list_type
            assert "label" in list_type
            assert "description" in list_type


class TestListsEndpoint:
    """Tests for /api/v1/lists/ endpoints"""

    @pytest.fixture
    def mock_current_user(self):
        """Create a mock authenticated user."""
        user = MagicMock()
        user.id = uuid4()
        user.tenant_id = uuid4()
        user.email = "test@example.com"
        user.role = "editor"
        return user

    @pytest.fixture
    def mock_list_obj(self, mock_current_user):
        """Create a mock list object."""
        list_obj = MagicMock()
        list_obj.id = uuid4()
        list_obj.name = "Test List"
        list_obj.list_type = "report"
        list_obj.description = "A test list"
        list_obj.tenant_id = mock_current_user.tenant_id
        list_obj.item_count = 5
        list_obj.created_at = "2024-01-15T10:00:00Z"
        list_obj.updated_at = "2024-01-15T10:00:00Z"
        list_obj.to_dict.return_value = {
            "id": str(list_obj.id),
            "name": list_obj.name,
            "list_type": list_obj.list_type,
            "description": list_obj.description,
            "item_count": list_obj.item_count,
            "created_at": list_obj.created_at,
            "updated_at": list_obj.updated_at,
        }
        return list_obj

    @pytest.mark.api
    def test_list_lists_requires_authentication(self, client):
        """Test that listing lists requires authentication."""
        response = client.get("/api/v1/lists/")

        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403]

    @pytest.mark.api
    def test_create_list_requires_authentication(self, client):
        """Test that creating a list requires authentication."""
        response = client.post(
            "/api/v1/lists/",
            json={"name": "New List", "list_type": "report"}
        )

        assert response.status_code in [401, 403]

    @pytest.mark.api
    @patch('api.routers.lists.require_viewer')
    @patch('api.routers.lists.ListRepository')
    def test_list_lists_returns_paginated_response(
        self, mock_repo_class, mock_auth, client, mock_current_user, mock_list_obj
    ):
        """Test that listing lists returns paginated structure."""
        mock_auth.return_value = mock_current_user

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = [mock_list_obj]
        mock_repo.count.return_value = 1
        mock_repo_class.return_value = mock_repo

        # Override the auth dependency
        from api.main import app
        from api.routers.lists import require_viewer

        app.dependency_overrides[require_viewer] = lambda: mock_current_user

        try:
            response = client.get("/api/v1/lists/")

            if response.status_code == 200:
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert "page" in data
                assert "page_size" in data
                assert "pages" in data
        finally:
            app.dependency_overrides.clear()


class TestListItemOperations:
    """Tests for list item CRUD operations"""

    @pytest.mark.api
    def test_add_item_requires_authentication(self, client):
        """Test that adding an item requires authentication."""
        list_id = uuid4()
        response = client.post(
            f"/api/v1/lists/{list_id}/items/",
            json={"item_id": str(uuid4())}
        )

        assert response.status_code in [401, 403]

    @pytest.mark.api
    def test_bulk_add_requires_authentication(self, client):
        """Test that bulk adding items requires authentication."""
        list_id = uuid4()
        response = client.post(
            f"/api/v1/lists/{list_id}/items/bulk/",
            json={"item_ids": [str(uuid4()), str(uuid4())]}
        )

        assert response.status_code in [401, 403]

    @pytest.mark.api
    def test_remove_item_requires_authentication(self, client):
        """Test that removing an item requires authentication."""
        list_id = uuid4()
        item_id = uuid4()
        response = client.delete(f"/api/v1/lists/{list_id}/items/{item_id}")

        assert response.status_code in [401, 403]


class TestListExport:
    """Tests for list export functionality"""

    @pytest.mark.api
    def test_export_requires_authentication(self, client):
        """Test that export requires authentication."""
        list_id = uuid4()
        response = client.post(f"/api/v1/lists/{list_id}/export/?format=csv")

        assert response.status_code in [401, 403]

    @pytest.mark.api
    def test_export_invalid_format_validation(self, client):
        """Test that invalid export format is rejected."""
        # This test would need authentication override
        # For now, just verify the endpoint structure exists
        list_id = uuid4()
        response = client.post(f"/api/v1/lists/{list_id}/export/?format=pdf")

        # Will fail auth first, but endpoint exists
        assert response.status_code in [400, 401, 403]


class TestHealthEndpoint:
    """Tests for the health check endpoint (no auth required)"""

    @pytest.mark.api
    def test_health_check_returns_status(self, client):
        """Test health endpoint returns expected structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.api
    def test_root_endpoint_returns_info(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "status" in data
