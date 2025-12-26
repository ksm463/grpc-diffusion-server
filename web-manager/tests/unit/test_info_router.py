"""
Tests for router/info_router.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path
from router.info_router import info_router


@pytest.fixture
def app():
    """Create FastAPI app with info_router"""
    app = FastAPI()
    app.include_router(info_router)
    return app


@pytest.fixture
def client(app):
    """Create TestClient"""
    return TestClient(app)


@pytest.fixture
def mock_logger():
    """Mock logger"""
    return Mock()


class TestGetHostSystemInformation:
    """Test /api/info/host_system_info endpoint"""

    def test_returns_host_info_from_env_vars(self, client, mock_logger, monkeypatch):
        """Should return host system information from environment variables"""
        # Setup environment variables
        monkeypatch.setenv("HOST_IP", "192.168.1.100")
        monkeypatch.setenv("HOST_OS_VERSION", "Ubuntu 24.04")
        monkeypatch.setenv("HOST_TIMEZONE", "Asia/Seoul")

        # Override logger dependency
        from router.info_router import get_logger
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/api/info/host_system_info")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["host_ip_address"] == "192.168.1.100"
        assert data["host_os_version"] == "Ubuntu 24.04"
        assert data["host_timezone"] == "Asia/Seoul"

    def test_returns_default_values_when_env_vars_not_set(self, client, mock_logger, monkeypatch):
        """Should return N/A when environment variables are not set"""
        # Remove environment variables
        monkeypatch.delenv("HOST_IP", raising=False)
        monkeypatch.delenv("HOST_OS_VERSION", raising=False)
        monkeypatch.delenv("HOST_TIMEZONE", raising=False)

        # Override logger dependency
        from router.info_router import get_logger
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/api/info/host_system_info")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["host_ip_address"] == "N/A"
        assert "N/A" in data["host_os_version"]
        assert data["host_timezone"] == "N/A"


class TestGetClientIpAddress:
    """Test /api/info/client_ip endpoint"""

    def test_returns_client_ip(self, client, mock_logger):
        """Should return client IP address"""
        # Override logger dependency
        from router.info_router import get_logger
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request
        response = client.get("/api/info/client_ip")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "client_ip" in data
        # TestClient uses 'testclient' as default host
        assert data["client_ip"] == "testclient"


class TestGetGrpcInfo:
    """Test /api/info/grpc_info endpoint"""

    def test_returns_grpc_info(self, client, mock_logger):
        """Should return gRPC server information"""
        # Mock server config
        mock_server_config = {
            "grpc": {
                "port": "50051"
            }
        }

        # Override dependencies
        from router.info_router import get_logger, get_server_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_server_config] = lambda: mock_server_config

        # Make request
        response = client.get("/api/info/grpc_info")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["grpc_port"] == "50051"
        assert data["server_status"] == "Running (Temporary Data)"
        assert "temporary" in data["message"].lower()


class TestGetProtoContent:
    """Test /api/info/proto endpoint"""

    def test_returns_proto_file_content(self, client, mock_logger, tmp_path):
        """Should return proto file content when file exists"""
        # Create temporary proto file
        proto_file = tmp_path / "test.proto"
        proto_content = 'syntax = "proto3";\nservice TestService {}'
        proto_file.write_text(proto_content, encoding='utf-8')

        # Mock manager config
        mock_manager_config = {
            "ENV": {
                "PROTO_BUFF_PATH": str(proto_file)
            }
        }

        # Override dependencies
        from router.info_router import get_logger, get_manager_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_manager_config] = lambda: mock_manager_config

        # Make request
        response = client.get("/api/info/proto")

        # Assertions
        assert response.status_code == 200
        assert response.text == proto_content
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.headers["cache-control"] == "no-store"

    def test_raises_500_when_proto_path_not_in_config(self, client, mock_logger):
        """Should raise 500 when PROTO_BUFF_PATH not in config"""
        # Mock manager config without PROTO_BUFF_PATH
        mock_manager_config = {
            "ENV": {}
        }

        # Override dependencies
        from router.info_router import get_logger, get_manager_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_manager_config] = lambda: mock_manager_config

        # Make request
        response = client.get("/api/info/proto")

        # Assertions
        assert response.status_code == 500
        assert "configuration error" in response.json()["detail"].lower()

    def test_raises_404_when_proto_file_not_found(self, client, mock_logger, tmp_path):
        """Should raise 404 when proto file doesn't exist"""
        # Mock manager config with non-existent file path
        mock_manager_config = {
            "ENV": {
                "PROTO_BUFF_PATH": str(tmp_path / "nonexistent.proto")
            }
        }

        # Override dependencies
        from router.info_router import get_logger, get_manager_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_manager_config] = lambda: mock_manager_config

        # Make request
        response = client.get("/api/info/proto")

        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_raises_400_when_proto_path_is_directory(self, client, mock_logger, tmp_path):
        """Should raise 400 when proto path points to directory"""
        # Create directory instead of file
        proto_dir = tmp_path / "proto_dir"
        proto_dir.mkdir()

        # Mock manager config with directory path
        mock_manager_config = {
            "ENV": {
                "PROTO_BUFF_PATH": str(proto_dir)
            }
        }

        # Override dependencies
        from router.info_router import get_logger, get_manager_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_manager_config] = lambda: mock_manager_config

        # Make request
        response = client.get("/api/info/proto")

        # Assertions
        assert response.status_code == 400
        assert "directory" in response.json()["detail"].lower()

    def test_raises_500_when_file_read_error(self, client, mock_logger, tmp_path):
        """Should raise 500 when error occurs reading file"""
        # Create proto file
        proto_file = tmp_path / "test.proto"
        proto_file.write_text("test content")

        # Mock manager config
        mock_manager_config = {
            "ENV": {
                "PROTO_BUFF_PATH": str(proto_file)
            }
        }

        # Override dependencies
        from router.info_router import get_logger, get_manager_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger
        client.app.dependency_overrides[get_manager_config] = lambda: mock_manager_config

        # Mock Path.read_text to raise exception
        with patch.object(Path, 'read_text', side_effect=Exception("Read error")):
            # Make request
            response = client.get("/api/info/proto")

        # Assertions
        assert response.status_code == 500
        assert "error reading" in response.json()["detail"].lower()
