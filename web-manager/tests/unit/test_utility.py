"""
Tests for utility functions
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from utility.request import (
    get_manager_config,
    get_server_config,
    get_logger
)
from utility.logger import setup_logger


class TestGetManagerConfig:
    """Test get_manager_config function"""

    def test_returns_config_when_exists(self):
        """Should return manager_config from app state"""
        mock_request = Mock()
        mock_config = {"test": "config"}
        mock_request.app.state.manager_config = mock_config

        result = get_manager_config(mock_request)
        assert result == mock_config

    def test_raises_http_exception_when_config_is_none(self):
        """Should raise HTTPException when config is None"""
        mock_request = Mock()
        mock_request.app.state.manager_config = None

        with pytest.raises(HTTPException) as exc_info:
            get_manager_config(mock_request)
        assert exc_info.value.status_code == 500
        assert "Config not initialized" in exc_info.value.detail

    def test_raises_http_exception_when_attribute_missing(self):
        """Should raise HTTPException when attribute not found"""
        mock_request = Mock()
        del mock_request.app.state.manager_config

        with pytest.raises(HTTPException) as exc_info:
            get_manager_config(mock_request)
        assert exc_info.value.status_code == 500
        assert "Config attribute not found" in exc_info.value.detail


class TestGetServerConfig:
    """Test get_server_config function"""

    def test_returns_config_when_exists(self):
        """Should return server_config from app state"""
        mock_request = Mock()
        mock_config = {"server": "config"}
        mock_request.app.state.server_config = mock_config

        result = get_server_config(mock_request)
        assert result == mock_config

    def test_raises_http_exception_when_config_is_none(self):
        """Should raise HTTPException when config is None"""
        mock_request = Mock()
        mock_request.app.state.server_config = None

        with pytest.raises(HTTPException) as exc_info:
            get_server_config(mock_request)
        assert exc_info.value.status_code == 500
        assert "gRPC Config not initialized" in exc_info.value.detail

    def test_raises_http_exception_when_attribute_missing(self):
        """Should raise HTTPException when attribute not found"""
        mock_request = Mock()
        del mock_request.app.state.server_config

        with pytest.raises(HTTPException) as exc_info:
            get_server_config(mock_request)
        assert exc_info.value.status_code == 500
        assert "gRPCConfig attribute not found" in exc_info.value.detail


class TestGetLogger:
    """Test get_logger function"""

    def test_returns_logger_when_exists(self):
        """Should return logger from app state"""
        mock_request = Mock()
        mock_logger = Mock()
        mock_request.app.state.logger = mock_logger

        result = get_logger(mock_request)
        assert result == mock_logger

    def test_raises_http_exception_when_logger_is_none(self):
        """Should raise HTTPException when logger is None"""
        mock_request = Mock()
        mock_request.app.state.logger = None

        with pytest.raises(HTTPException) as exc_info:
            get_logger(mock_request)
        assert exc_info.value.status_code == 500
        assert "Logger not initialized" in exc_info.value.detail

    def test_raises_http_exception_when_attribute_missing(self):
        """Should raise HTTPException when attribute not found"""
        mock_request = Mock()
        del mock_request.app.state.logger

        with pytest.raises(HTTPException) as exc_info:
            get_logger(mock_request)
        assert exc_info.value.status_code == 500
        assert "Logger attribute not found" in exc_info.value.detail


class TestSetupLogger:
    """Test setup_logger function"""

    @patch('utility.logger.logger')
    def test_setup_logger_returns_logger(self, mock_logger):
        """Should configure and return logger instance"""
        log_path = "/tmp/test.log"

        result = setup_logger(log_path)

        # Verify logger.remove() was called
        mock_logger.remove.assert_called_once()

        # Verify logger.add() was called with correct path
        mock_logger.add.assert_called_once()
        call_args = mock_logger.add.call_args
        assert call_args[0][0] == log_path

        # Verify it returns the logger
        assert result == mock_logger
