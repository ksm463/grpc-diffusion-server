"""
Tests for core/config.py
"""
import pytest
from unittest.mock import patch, Mock, mock_open
import configparser
import os


class TestGetManagerConfig:
    """Test get_manager_config function"""

    @patch('core.config.configparser.ConfigParser')
    def test_reads_config_file(self, mock_parser_class):
        """Should read manager_config.ini file"""
        # Clear the cache
        from core.config import get_manager_config
        get_manager_config.cache_clear()

        # Setup mock
        mock_config = Mock()
        mock_parser_class.return_value = mock_config
        mock_config.__getitem__ = Mock(return_value={'URL': 'test_url', 'KEY': 'test_key'})
        mock_config.__contains__ = Mock(return_value=False)

        # Call function
        result = get_manager_config()

        # Assertions
        mock_parser_class.assert_called_once()
        mock_config.read.assert_called_once_with("/web-manager/app/core/manager_config.ini")
        assert result == mock_config

    @patch.dict(os.environ, {'SUPABASE_KEY': 'env_key', 'SUPABASE_SERVICE_KEY': 'env_service_key'})
    @patch('core.config.configparser.ConfigParser')
    def test_overrides_with_environment_variables(self, mock_parser_class):
        """Should override SUPABASE keys with environment variables"""
        # Clear the cache
        from core.config import get_manager_config
        get_manager_config.cache_clear()

        # Setup mock
        mock_config = Mock()
        mock_parser_class.return_value = mock_config
        mock_config.__contains__ = Mock(return_value=True)
        mock_config.__getitem__ = Mock(return_value={'KEY': 'config_key', 'SERVICE_KEY': 'config_service_key'})

        # Call function
        result = get_manager_config()

        # Assertions
        assert 'SUPABASE' in mock_config
        # Check that environment variables were used
        mock_config.__getitem__.assert_called_with('SUPABASE')

    @patch('core.config.configparser.ConfigParser')
    def test_caches_result(self, mock_parser_class):
        """Should cache config result using lru_cache"""
        # Clear the cache
        from core.config import get_manager_config
        get_manager_config.cache_clear()

        # Setup mock
        mock_config = Mock()
        mock_parser_class.return_value = mock_config
        mock_config.__contains__ = Mock(return_value=False)

        # Call function multiple times
        result1 = get_manager_config()
        result2 = get_manager_config()

        # Assertions - ConfigParser should only be called once due to caching
        assert mock_parser_class.call_count == 1
        assert result1 == result2


class TestGetServerConfig:
    """Test get_server_config function"""

    @patch('core.config.configparser.ConfigParser')
    def test_reads_server_config_file(self, mock_parser_class):
        """Should read server_config.ini file"""
        # Clear the cache
        from core.config import get_server_config
        get_server_config.cache_clear()

        # Setup mock
        mock_config = Mock()
        mock_parser_class.return_value = mock_config

        # Call function
        result = get_server_config()

        # Assertions
        mock_parser_class.assert_called_once()
        mock_config.read.assert_called_once_with("/web-manager/ai-server/server_config.ini")
        assert result == mock_config

    @patch('core.config.configparser.ConfigParser')
    def test_caches_result(self, mock_parser_class):
        """Should cache server config result using lru_cache"""
        # Clear the cache
        from core.config import get_server_config
        get_server_config.cache_clear()

        # Setup mock
        mock_config = Mock()
        mock_parser_class.return_value = mock_config

        # Call function multiple times
        result1 = get_server_config()
        result2 = get_server_config()

        # Assertions - ConfigParser should only be called once due to caching
        assert mock_parser_class.call_count == 1
        assert result1 == result2


class TestModuleLevelVariables:
    """Test module-level config variables"""

    def test_manager_config_is_initialized(self):
        """Should initialize manager_config at module level"""
        from core.config import manager_config
        assert manager_config is not None

    def test_server_config_is_initialized(self):
        """Should initialize server_config at module level"""
        from core.config import server_config
        assert server_config is not None
