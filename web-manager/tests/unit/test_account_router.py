"""
Tests for router/account_router.py
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gotrue.errors import AuthApiError
from router.account_router import account_router


@pytest.fixture
def app():
    """Create FastAPI app with account_router"""
    app = FastAPI()
    app.include_router(account_router)
    return app


@pytest.fixture
def client(app):
    """Create TestClient"""
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return Mock()


@pytest.fixture
def mock_logger():
    """Mock logger"""
    return Mock()


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.email_confirmed_at = "2025-01-01T00:00:00Z"
    user.created_at = "2025-01-01T00:00:00Z"
    user.user_metadata = {}
    return user


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    user = Mock()
    user.id = "admin-123"
    user.email = "admin@example.com"
    user.email_confirmed_at = "2025-01-01T00:00:00Z"
    user.created_at = "2025-01-01T00:00:00Z"
    user.user_metadata = {"role": "admin"}
    return user


class TestSignup:
    """Test POST /auth/register endpoint"""

    def test_successfully_registers_user(self, client, mock_supabase, mock_logger):
        """Should successfully register new user"""
        # Mock signup response
        mock_response = Mock()
        mock_response.user = Mock()
        mock_response.user.email = "newuser@example.com"
        mock_supabase.auth.sign_up.return_value = mock_response

        # Override dependencies
        from router.account_router import get_supabase_client, get_logger
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123"
            }
        )

        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert "successfully" in data["message"].lower()
        mock_supabase.auth.sign_up.assert_called_once()

    def test_returns_400_on_duplicate_email(self, client, mock_supabase, mock_logger):
        """Should return 400 when email already exists"""
        # Mock sign_up to raise exception
        mock_supabase.auth.sign_up.side_effect = Exception("User already exists")

        # Override dependencies
        from router.account_router import get_supabase_client, get_logger
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.post(
            "/auth/register",
            json={
                "email": "existing@example.com",
                "password": "password123"
            }
        )

        # Assertions
        assert response.status_code == 400


class TestLogin:
    """Test POST /auth/db/login endpoint"""

    def test_successfully_logs_in_user(self, client, mock_supabase, mock_logger):
        """Should successfully login user and return tokens"""
        # Mock login response
        mock_session = Mock()
        mock_session.access_token = "access_token_123"
        mock_session.refresh_token = "refresh_token_456"

        mock_response = Mock()
        mock_response.user = Mock()
        mock_response.user.email = "test@example.com"
        mock_response.session = mock_session

        mock_supabase.auth.sign_in_with_password.return_value = mock_response

        # Override dependencies
        from router.account_router import get_supabase_client, get_logger
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.post(
            "/auth/db/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "access_token_123"
        assert data["refresh_token"] == "refresh_token_456"
        assert data["token_type"] == "bearer"
        assert "access_token" in response.cookies

    def test_returns_401_on_invalid_credentials(self, client, mock_supabase, mock_logger):
        """Should return 401 when credentials are invalid"""
        # Mock sign_in to raise exception
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")

        # Override dependencies
        from router.account_router import get_supabase_client, get_logger
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.post(
            "/auth/db/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpassword"
            }
        )

        # Assertions
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()


class TestLogout:
    """Test POST /auth/logout endpoint"""

    def test_successfully_logs_out_user(self, client, mock_supabase, mock_logger, mock_user):
        """Should successfully log out authenticated user"""
        # Override dependencies
        from router.account_router import get_current_user, get_supabase_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request with token in header
        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer test_token_123"}
        )

        # Assertions
        assert response.status_code == 204
        mock_supabase.auth.sign_out.assert_called_once()

    def test_returns_401_when_no_token(self, client, mock_supabase, mock_logger, mock_user):
        """Should return 401 when no token provided"""
        # Override dependencies
        from router.account_router import get_current_user, get_supabase_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request without token
        response = client.post("/auth/logout")

        # Assertions
        assert response.status_code == 401

    def test_returns_500_when_logout_fails(self, client, mock_supabase, mock_logger, mock_user):
        """Should return 500 when sign_out raises exception"""
        # Mock sign_out to raise exception
        mock_supabase.auth.sign_out.side_effect = Exception("Logout failed")

        # Override dependencies
        from router.account_router import get_current_user, get_supabase_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer test_token_123"}
        )

        # Assertions
        assert response.status_code == 500
        assert "sign out" in response.json()["detail"].lower()


class TestAuthenticatedRoute:
    """Test GET /authenticated-route endpoint"""

    def test_returns_greeting_for_authenticated_user(self, client, mock_logger, mock_user):
        """Should return greeting for authenticated user"""
        # Override dependencies
        from router.account_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/authenticated-route")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert mock_user.email in data["message"]


class TestGetMyInfo:
    """Test GET /users/me endpoint"""

    def test_returns_current_user_info(self, client, mock_logger, mock_user):
        """Should return current user information"""
        # Override dependencies
        from router.account_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/users/me")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "test-user-123"
        assert data["is_verified"] is True
        assert data["is_superuser"] is False

    def test_returns_admin_user_info(self, client, mock_logger, mock_admin_user):
        """Should correctly identify admin user"""
        # Override dependencies
        from router.account_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/users/me")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["is_superuser"] is True


class TestUpdateMyPassword:
    """Test PATCH /users/me/password endpoint"""

    def test_successfully_updates_password(self, client, mock_user, mock_supabase, mock_logger):
        """Should successfully update user password"""
        # Mock admin client
        mock_admin = Mock()
        mock_admin.auth.admin.update_user_by_id = Mock()

        # Override dependencies
        from router.account_router import get_current_user, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.patch(
            "/users/me/password",
            json={"new_password": "newpassword123"}
        )

        # Assertions
        assert response.status_code == 204
        mock_admin.auth.admin.update_user_by_id.assert_called_once()

    def test_rejects_short_password(self, client, mock_user, mock_logger):
        """Should reject password shorter than 6 characters"""
        # Mock admin client (needed even for validation error)
        mock_admin = Mock()

        # Override dependencies
        from router.account_router import get_current_user, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request with short password
        response = client.patch(
            "/users/me/password",
            json={"new_password": "short"}
        )

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_returns_400_when_update_fails(self, client, mock_user, mock_logger):
        """Should return 400 when password update fails"""
        # Mock admin client to raise exception
        mock_admin = Mock()
        mock_admin.auth.admin.update_user_by_id.side_effect = Exception("Update failed")

        # Override dependencies
        from router.account_router import get_current_user, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.patch(
            "/users/me/password",
            json={"new_password": "newpassword123"}
        )

        # Assertions
        assert response.status_code == 400
        assert "Update failed" in response.json()["detail"]


class TestListAllUsers:
    """Test GET /users/ endpoint (admin only)"""

    def test_admin_can_list_users(self, client, mock_admin_user, mock_logger):
        """Should allow admin to list all users"""
        # Mock admin client
        mock_admin = Mock()
        # Return list directly (matching actual Supabase behavior)
        mock_users_response = [
            {
                "id": "user-1",
                "email": "user1@example.com",
                "phone": "",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "confirmed_at": "2025-01-01T00:00:00Z",
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "phone_confirmed_at": None,
                "last_sign_in_at": "2025-01-01T00:00:00Z",
                "user_metadata": {},
                "app_metadata": {"provider": "email", "providers": ["email"]},
                "aud": "authenticated",
                "role": "authenticated",
                "is_anonymous": False,
                "confirmation_sent_at": None,
                "recovery_sent_at": None,
                "email_change_sent_at": None,
                "new_email": None,
                "new_phone": None,
                "invited_at": None,
                "action_link": None,
                "identities": None,
                "factors": None
            },
            {
                "id": "user-2",
                "email": "user2@example.com",
                "phone": "",
                "created_at": "2025-01-02T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "confirmed_at": "2025-01-02T00:00:00Z",
                "email_confirmed_at": "2025-01-02T00:00:00Z",
                "phone_confirmed_at": None,
                "last_sign_in_at": "2025-01-02T00:00:00Z",
                "user_metadata": {},
                "app_metadata": {"provider": "email", "providers": ["email"]},
                "aud": "authenticated",
                "role": "authenticated",
                "is_anonymous": False,
                "confirmation_sent_at": None,
                "recovery_sent_at": None,
                "email_change_sent_at": None,
                "new_email": None,
                "new_phone": None,
                "invited_at": None,
                "action_link": None,
                "identities": None,
                "factors": None
            }
        ]
        mock_admin.auth.admin.list_users.return_value = mock_users_response

        # Override dependencies
        from router.account_router import get_current_superuser, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_superuser] = lambda: mock_admin_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/users/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "user-1"
        assert data[1]["id"] == "user-2"
        mock_admin.auth.admin.list_users.assert_called_once()

    def test_returns_500_when_list_users_fails(self, client, mock_admin_user, mock_logger):
        """Should return 500 when listing users fails"""
        # Mock admin client to raise exception
        mock_admin = Mock()
        mock_admin.auth.admin.list_users.side_effect = Exception("Database error")

        # Override dependencies
        from router.account_router import get_current_superuser, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_superuser] = lambda: mock_admin_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/users/")

        # Assertions
        assert response.status_code == 500
        assert "Could not retrieve users list" in response.json()["detail"]


class TestDeleteUserByAdmin:
    """Test DELETE /users/{user_id} endpoint (admin only)"""

    def test_admin_can_delete_user(self, client, mock_admin_user, mock_logger):
        """Should allow admin to delete other users"""
        # Mock admin client
        mock_admin = Mock()
        mock_admin.auth.admin.delete_user = Mock()

        # Override dependencies
        from router.account_router import get_current_superuser, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_superuser] = lambda: mock_admin_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.delete("/users/other-user-123")

        # Assertions
        assert response.status_code == 204
        mock_admin.auth.admin.delete_user.assert_called_once_with("other-user-123")

    def test_admin_cannot_delete_own_account(self, client, mock_admin_user, mock_logger):
        """Should prevent admin from deleting their own account"""
        # Mock admin client
        mock_admin = Mock()

        # Override dependencies
        from router.account_router import get_current_superuser, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_superuser] = lambda: mock_admin_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request to delete own account
        response = client.delete(f"/users/{mock_admin_user.id}")

        # Assertions
        assert response.status_code == 400
        assert "cannot delete their own" in response.json()["detail"].lower()

    def test_returns_404_when_user_not_found(self, client, mock_admin_user, mock_logger):
        """Should return 404 when user to delete is not found"""
        # Mock admin client to raise AuthApiError
        mock_admin = Mock()
        # Create AuthApiError with proper message attribute
        auth_error = AuthApiError("User not found", code="404", status=404)
        mock_admin.auth.admin.delete_user.side_effect = auth_error

        # Override dependencies
        from router.account_router import get_current_superuser, get_supabase_admin_client, get_logger
        client.app.dependency_overrides[get_current_superuser] = lambda: mock_admin_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_admin
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.delete("/users/nonexistent-user-123")

        # Assertions
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
