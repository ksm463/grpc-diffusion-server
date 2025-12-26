"""
Tests for router/page_router.py
"""
import pytest
from unittest.mock import Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from router.page_router import page_router


@pytest.fixture
def app():
    """Create FastAPI app with page_router"""
    app = FastAPI()
    app.include_router(page_router)
    return app


@pytest.fixture
def client(app):
    """Create TestClient"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_logger():
    """Mock logger"""
    return Mock()


class TestPublicPages:
    """Test public pages that don't require authentication"""

    def test_login_page_returns_html(self, client, mock_logger):
        """Should return login page HTML"""
        # Override logger dependency
        from router.page_router import get_logger
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/login")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_create_account_page_returns_html(self, client, mock_logger):
        """Should return create account page HTML"""
        # Override logger dependency
        from router.page_router import get_logger
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/create_account")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestProtectedPages:
    """Test protected pages that require authentication"""

    def test_root_page_requires_authentication(self, client, mock_logger, mock_user):
        """Should return studio page when authenticated"""
        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_studio_page_returns_html(self, client, mock_logger, mock_user):
        """Should return studio page HTML when authenticated"""
        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/studio")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_info_page_returns_html(self, client, mock_logger, mock_user):
        """Should return info page HTML when authenticated"""
        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/info")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_gallery_page_returns_html(self, client, mock_logger, mock_user):
        """Should return gallery page HTML when authenticated"""
        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/gallery")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_user_manage_page_returns_html(self, client, mock_logger, mock_user):
        """Should return user management page HTML when authenticated"""
        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/user_manage")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestStatusPages:
    """Test status pages with environment variable handling"""

    def test_cpu_status_page_uses_env_variables(self, client, mock_logger, mock_user, monkeypatch):
        """Should use HOST_IP and GRAFANA_PORT from environment"""
        # Set environment variables
        monkeypatch.setenv("HOST_IP", "192.168.1.100")
        monkeypatch.setenv("GRAFANA_PORT", "3000")

        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/status/cpu")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check that the response contains the grafana URL
        assert "192.168.1.100" in response.text
        assert "3000" in response.text

    def test_cpu_status_page_uses_default_values(self, client, mock_logger, mock_user, monkeypatch):
        """Should use default values when env vars not set"""
        # Remove environment variables
        monkeypatch.delenv("HOST_IP", raising=False)
        monkeypatch.delenv("GRAFANA_PORT", raising=False)

        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/status/cpu")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should use default values
        assert "localhost" in response.text
        assert "23000" in response.text

    def test_gpu_status_page_uses_env_variables(self, client, mock_logger, mock_user, monkeypatch):
        """Should use HOST_IP and GRAFANA_PORT from environment"""
        # Set environment variables
        monkeypatch.setenv("HOST_IP", "10.0.0.50")
        monkeypatch.setenv("GRAFANA_PORT", "4000")

        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/status/gpu")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check that the response contains the grafana URL
        assert "10.0.0.50" in response.text
        assert "4000" in response.text

    def test_gpu_status_page_uses_default_values(self, client, mock_logger, mock_user, monkeypatch):
        """Should use default values when env vars not set"""
        # Remove environment variables
        monkeypatch.delenv("HOST_IP", raising=False)
        monkeypatch.delenv("GRAFANA_PORT", raising=False)

        # Override dependencies
        from router.page_router import get_current_user, get_logger
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/status/gpu")

        # Assertions
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should use default values
        assert "localhost" in response.text
        assert "23000" in response.text
