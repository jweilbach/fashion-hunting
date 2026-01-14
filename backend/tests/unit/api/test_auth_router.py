"""
Tests for the Authentication Router.

These tests verify the auth endpoints work correctly for login,
signup, token management, and password changes.

These tests focus on:
1. Input validation (missing/invalid fields return proper errors)
2. Authentication requirements (401 for unauthenticated requests)
3. Mocked successful paths for core functionality
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import uuid


def create_mock_user(
    user_id=None,
    email="test@example.com",
    password_hash=None,
    tenant_id=None,
    role="admin",
    is_active=True
):
    """Create a mock user object for testing."""
    from api.auth import get_password_hash

    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.password_hash = password_hash or get_password_hash("testpassword123")
    user.tenant_id = tenant_id or uuid.uuid4()
    user.role = role
    user.is_active = is_active
    user.full_name = "Test User"
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.last_login = None
    return user


class TestLoginValidation:
    """Tests for POST /auth/login input validation."""

    def test_login_missing_email_returns_422(self, client):
        """Missing email returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "testpassword"}
        )
        assert response.status_code == 422

    def test_login_missing_password_returns_422(self, client):
        """Missing password returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 422

    def test_login_empty_body_returns_422(self, client):
        """Empty request body returns validation error."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_invalid_email_format_returns_422(self, client):
        """Invalid email format returns validation error."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "testpassword"}
        )
        assert response.status_code == 422


class TestLoginAuthentication:
    """Tests for POST /auth/login authentication logic."""

    def test_login_valid_credentials_returns_token(self, client):
        """Valid credentials return access token and user info."""
        from api.auth import get_password_hash

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_user = create_mock_user(
            user_id=user_id,
            email="test@example.com",
            password_hash=get_password_hash("testpassword123"),
            tenant_id=tenant_id
        )

        with patch('api.routers.auth.authenticate_user', return_value=mock_user):
            with patch('api.routers.auth.UserRepository') as MockUserRepo:
                MockUserRepo.return_value.update_last_login.return_value = None

                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": "test@example.com", "password": "testpassword123"}
                )

                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"
                assert "expires_in" in data
                assert "user" in data
                assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials_returns_401(self, client):
        """Invalid credentials return 401 Unauthorized."""
        with patch('api.routers.auth.authenticate_user', return_value=None):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"}
            )

            assert response.status_code == 401
            assert "Incorrect email or password" in response.json()["detail"]

    def test_login_unknown_user_returns_401(self, client):
        """Non-existent user returns 401 Unauthorized."""
        with patch('api.routers.auth.authenticate_user', return_value=None):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@example.com", "password": "anypassword"}
            )

            assert response.status_code == 401
            assert "Incorrect email or password" in response.json()["detail"]


class TestSignupValidation:
    """Tests for POST /auth/signup input validation."""

    def test_signup_missing_email_returns_400(self, client):
        """Missing email returns 400 Bad Request."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"password": "password", "tenant_name": "Company"}
        )
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_signup_missing_password_returns_400(self, client):
        """Missing password returns 400 Bad Request."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "tenant_name": "Company"}
        )
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()

    def test_signup_missing_tenant_name_returns_400(self, client):
        """Missing tenant_name returns 400 Bad Request."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com", "password": "password"}
        )
        assert response.status_code == 400
        assert "required" in response.json()["detail"].lower()


class TestGetMeEndpoint:
    """Tests for GET /auth/me endpoint."""

    def test_get_me_without_token_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]

    def test_get_me_with_invalid_token_returns_401(self, client):
        """Invalid token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"}
        )
        assert response.status_code == 401

    def test_get_me_with_expired_token_returns_401(self, client):
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
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_get_me_with_malformed_auth_header_returns_error(self, client):
        """Malformed Authorization header returns 401 or 403."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer sometoken"}
        )
        assert response.status_code in [401, 403]


class TestChangePasswordEndpoint:
    """Tests for POST /auth/change-password endpoint."""

    def test_change_password_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "oldpassword",
                "new_password": "newpassword"
            }
        )
        assert response.status_code in [401, 403]


class TestLogoutEndpoint:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_without_auth_returns_error(self, client):
        """Unauthenticated request returns 401 or 403."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code in [401, 403]


class TestOAuth2TokenEndpoint:
    """Tests for POST /auth/token OAuth2 endpoint."""

    def test_oauth2_token_valid_credentials_returns_token(self, client):
        """Valid OAuth2 credentials return access token."""
        from api.auth import get_password_hash

        mock_user = create_mock_user(
            email="oauth@example.com",
            password_hash=get_password_hash("oauthpassword")
        )

        with patch('api.routers.auth.authenticate_user', return_value=mock_user):
            with patch('api.routers.auth.UserRepository') as MockUserRepo:
                MockUserRepo.return_value.update_last_login.return_value = None

                response = client.post(
                    "/api/v1/auth/token",
                    data={
                        "username": "oauth@example.com",
                        "password": "oauthpassword"
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["token_type"] == "bearer"

    def test_oauth2_token_invalid_credentials_returns_401(self, client):
        """Invalid OAuth2 credentials return 401."""
        with patch('api.routers.auth.authenticate_user', return_value=None):
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "username": "nonexistent@example.com",
                    "password": "wrongpassword"
                }
            )
            assert response.status_code == 401
