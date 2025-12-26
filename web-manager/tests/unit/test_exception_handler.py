"""
Tests for core/exception_handler.py
"""
import pytest
from unittest.mock import Mock, MagicMock
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.exception_handler import custom_http_exception_handler


@pytest.fixture
def app():
    """Create FastAPI app with exception handler"""
    app = FastAPI()
    app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)

    # Add test routes
    @app.get("/api/test")
    async def api_test():
        raise StarletteHTTPException(status_code=401, detail="Unauthorized API access")

    @app.get("/auth/test")
    async def auth_test():
        raise StarletteHTTPException(status_code=401, detail="Unauthorized auth access")

    @app.get("/users/me")
    async def users_me():
        raise StarletteHTTPException(status_code=401, detail="Unauthorized user access")

    @app.get("/page/test")
    async def page_test():
        raise StarletteHTTPException(status_code=401, detail="Unauthorized page access")

    @app.get("/error/400")
    async def error_400():
        raise StarletteHTTPException(status_code=400, detail="Bad request")

    @app.get("/error/500")
    async def error_500():
        raise StarletteHTTPException(status_code=500, detail="Internal server error")

    return app


@pytest.fixture
def client(app):
    """Create TestClient"""
    # Setup logger in app.state
    mock_logger = Mock()
    app.state.logger = mock_logger
    return TestClient(app)


class TestCustomHttpExceptionHandler:
    """Test custom_http_exception_handler function"""

    def test_401_api_path_returns_json(self, client):
        """Should return JSON for 401 on /api/ paths"""
        response = client.get("/api/test")

        # Assertions
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Unauthorized API access"

    def test_401_auth_path_returns_json(self, client):
        """Should return JSON for 401 on /auth/ paths"""
        response = client.get("/auth/test")

        # Assertions
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Unauthorized auth access"

    def test_401_users_me_path_returns_json(self, client):
        """Should return JSON for 401 on /users/me path"""
        response = client.get("/users/me")

        # Assertions
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Unauthorized user access"

    def test_401_with_json_accept_header_returns_json(self, client):
        """Should return JSON when Accept header contains application/json"""
        response = client.get(
            "/page/test",
            headers={"Accept": "application/json"}
        )

        # Assertions
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"

    def test_401_html_page_redirects_to_login(self, client):
        """Should redirect to /login for 401 on HTML pages"""
        response = client.get("/page/test", follow_redirects=False)

        # Assertions
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    def test_401_with_html_accept_header_redirects(self, client):
        """Should redirect when Accept header contains text/html"""
        response = client.get(
            "/page/test",
            headers={"Accept": "text/html"},
            follow_redirects=False
        )

        # Assertions
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    def test_400_error_returns_json(self, client):
        """Should return JSON for non-401 errors like 400"""
        response = client.get("/error/400")

        # Assertions
        assert response.status_code == 400
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Bad request"

    def test_500_error_returns_json(self, client):
        """Should return JSON for server errors like 500"""
        response = client.get("/error/500")

        # Assertions
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["detail"] == "Internal server error"


class TestExceptionHandlerWithoutLogger:
    """Test exception handler when app.state.logger is not set"""

    @pytest.mark.asyncio
    async def test_handles_exception_without_logger(self):
        """Should handle exception even when logger is not in app.state"""
        # Create mock request without logger
        mock_request = Mock()
        mock_request.app.state = Mock(spec=[])  # Empty state, no logger
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "application/json"

        # Create exception
        exc = StarletteHTTPException(status_code=401, detail="Test error")

        # Call handler
        response = await custom_http_exception_handler(mock_request, exc)

        # Assertions
        assert response.status_code == 401
        assert response.body == b'{"detail":"Test error"}'

    @pytest.mark.asyncio
    async def test_401_redirect_logic_without_logger(self):
        """Should redirect to login for HTML requests even without logger"""
        # Create mock request for HTML page
        mock_request = Mock()
        mock_request.app.state = Mock(spec=[])
        mock_request.url.path = "/dashboard"
        mock_request.headers.get.return_value = "text/html"

        # Create 401 exception
        exc = StarletteHTTPException(status_code=401, detail="Not authenticated")

        # Call handler
        response = await custom_http_exception_handler(mock_request, exc)

        # Assertions
        assert response.status_code == 302
        assert response.headers["location"] == "/login"


class TestExceptionHeaderHandling:
    """Test exception handler preserves custom headers"""

    @pytest.mark.asyncio
    async def test_preserves_custom_headers(self):
        """Should preserve custom headers from exception"""
        # Create mock request
        mock_request = Mock()
        mock_logger = Mock()
        mock_request.app.state.logger = mock_logger
        mock_request.url.path = "/api/test"
        mock_request.headers.get.return_value = "application/json"

        # Create exception with custom headers
        exc = StarletteHTTPException(
            status_code=401,
            detail="Test error",
            headers={"X-Custom-Header": "custom-value"}
        )

        # Call handler
        response = await custom_http_exception_handler(mock_request, exc)

        # Assertions
        assert response.status_code == 401
        assert response.headers.get("X-Custom-Header") == "custom-value"
