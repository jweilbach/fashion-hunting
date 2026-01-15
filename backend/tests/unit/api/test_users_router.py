"""
Tests for the Users Router.

These tests verify the user management endpoints work correctly for
listing, creating, updating roles, and activating/deactivating users.

These tests focus on authentication requirements - verifying that
unauthenticated or improperly authenticated requests are rejected.
"""
import pytest
from datetime import timedelta
import uuid


class TestListUsersAuthentication:
    """Tests for GET /users/ authentication requirements."""

    def test_list_users_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.get("/api/v1/users/")
        assert response.status_code in [401, 403]

    def test_list_users_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_list_users_with_expired_token_returns_401(self, client):
        """Expired token returns 401."""
        from api.auth import create_access_token

        token = create_access_token(
            data={
                "sub": str(uuid.uuid4()),
                "tenant_id": str(uuid.uuid4()),
                "email": "test@example.com",
                "role": "admin"
            },
            expires_delta=timedelta(seconds=-10)  # Already expired
        )

        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_list_users_with_malformed_auth_header_returns_error(self, client):
        """Malformed Authorization header returns 401 or 403."""
        response = client.get(
            "/api/v1/users/",
            headers={"Authorization": "NotBearer sometoken"}
        )
        assert response.status_code in [401, 403]


class TestGetUserAuthentication:
    """Tests for GET /users/{id} authentication requirements."""

    def test_get_user_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.get(f"/api/v1/users/{uuid.uuid4()}")
        assert response.status_code in [401, 403]

    def test_get_user_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.get(
            f"/api/v1/users/{uuid.uuid4()}",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestCreateUserAuthentication:
    """Tests for POST /users/ authentication requirements."""

    def test_create_user_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.post(
            "/api/v1/users/",
            json={"email": "new@example.com"}
        )
        assert response.status_code in [401, 403]

    def test_create_user_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.post(
            "/api/v1/users/",
            json={"email": "new@example.com"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestUpdateRoleAuthentication:
    """Tests for PATCH /users/{id}/role authentication requirements."""

    def test_update_role_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.patch(
            f"/api/v1/users/{uuid.uuid4()}/role",
            json={"role": "editor"}
        )
        assert response.status_code in [401, 403]

    def test_update_role_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.patch(
            f"/api/v1/users/{uuid.uuid4()}/role",
            json={"role": "editor"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestActivateUserAuthentication:
    """Tests for PATCH /users/{id}/activate authentication requirements."""

    def test_activate_user_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.patch(f"/api/v1/users/{uuid.uuid4()}/activate")
        assert response.status_code in [401, 403]

    def test_activate_user_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.patch(
            f"/api/v1/users/{uuid.uuid4()}/activate",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestDeactivateUserAuthentication:
    """Tests for PATCH /users/{id}/deactivate authentication requirements."""

    def test_deactivate_user_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.patch(f"/api/v1/users/{uuid.uuid4()}/deactivate")
        assert response.status_code in [401, 403]

    def test_deactivate_user_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.patch(
            f"/api/v1/users/{uuid.uuid4()}/deactivate",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestDeleteUserAuthentication:
    """Tests for DELETE /users/{id} authentication requirements."""

    def test_delete_user_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.delete(f"/api/v1/users/{uuid.uuid4()}")
        assert response.status_code in [401, 403]

    def test_delete_user_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.delete(
            f"/api/v1/users/{uuid.uuid4()}",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestUserCountAuthentication:
    """Tests for GET /users/count authentication requirements."""

    def test_user_count_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.get("/api/v1/users/count")
        assert response.status_code in [401, 403]

    def test_user_count_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.get(
            "/api/v1/users/count",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
