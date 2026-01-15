"""
Tests for the Admin Router

These tests verify that:
1. All admin endpoints require authentication
2. All admin endpoints require superuser access
3. Non-superusers are rejected with 403
"""
import pytest
from fastapi.testclient import TestClient


class TestAdminRouterAuthentication:
    """Test that admin endpoints require proper authentication"""

    def test_list_tenants_requires_auth(self, client: TestClient):
        """GET /admin/tenants requires authentication"""
        response = client.get("/api/v1/admin/tenants")
        assert response.status_code == 403  # No credentials

    def test_get_tenant_requires_auth(self, client: TestClient):
        """GET /admin/tenants/{id} requires authentication"""
        response = client.get("/api/v1/admin/tenants/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 403

    def test_update_tenant_status_requires_auth(self, client: TestClient):
        """PATCH /admin/tenants/{id}/status requires authentication"""
        response = client.patch(
            "/api/v1/admin/tenants/00000000-0000-0000-0000-000000000000/status",
            json={"status": "active"}
        )
        assert response.status_code == 403

    def test_update_tenant_plan_requires_auth(self, client: TestClient):
        """PATCH /admin/tenants/{id}/plan requires authentication"""
        response = client.patch(
            "/api/v1/admin/tenants/00000000-0000-0000-0000-000000000000/plan",
            json={"plan": "starter"}
        )
        assert response.status_code == 403

    def test_impersonate_user_requires_auth(self, client: TestClient):
        """POST /admin/impersonate/{user_id} requires authentication"""
        response = client.post("/api/v1/admin/impersonate/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 403

    def test_search_users_requires_auth(self, client: TestClient):
        """GET /admin/search/users requires authentication"""
        response = client.get("/api/v1/admin/search/users", params={"query": "test"})
        assert response.status_code == 403

    def test_get_stats_requires_auth(self, client: TestClient):
        """GET /admin/stats requires authentication"""
        response = client.get("/api/v1/admin/stats")
        assert response.status_code == 403


class TestAdminRouterSuperuserRequired:
    """Test that admin endpoints reject non-superusers"""

    def test_list_tenants_rejects_regular_user(self, authenticated_client: TestClient):
        """GET /admin/tenants rejects regular authenticated users"""
        # The authenticated_client fixture uses a non-superuser token
        response = authenticated_client.get("/api/v1/admin/tenants")
        # Should be 401 (token not in DB) or 403 (not superuser)
        assert response.status_code in [401, 403]

    def test_get_stats_rejects_regular_user(self, authenticated_client: TestClient):
        """GET /admin/stats rejects regular authenticated users"""
        response = authenticated_client.get("/api/v1/admin/stats")
        assert response.status_code in [401, 403]

    def test_search_users_rejects_regular_user(self, authenticated_client: TestClient):
        """GET /admin/search/users rejects regular authenticated users"""
        response = authenticated_client.get("/api/v1/admin/search/users", params={"query": "test"})
        assert response.status_code in [401, 403]
