"""
Tests for core/lifespan.py
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import FastAPI
import os


class TestLifespan:
    """Test lifespan context manager"""

    @pytest.mark.asyncio
    @patch('core.lifespan.create_client')
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_successful_startup_and_shutdown(
        self, mock_manager_config, mock_path, mock_setup_logger, mock_create_client
    ):
        """Should successfully start up and shut down"""
        # Setup mocks
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': 'test_url', 'KEY': 'test_key', 'SERVICE_KEY': 'test_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_supabase_client = Mock()
        mock_supabase_admin_client = Mock()
        mock_create_client.side_effect = [mock_supabase_client, mock_supabase_admin_client]

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.parent.mkdir = Mock()

        # Create app and use lifespan
        app = FastAPI()
        from core.lifespan import lifespan

        async with lifespan(app):
            # Verify startup
            mock_path_instance.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_setup_logger.assert_called_once_with('/test/log.log')
            assert mock_create_client.call_count == 2

            # Verify app.state is set correctly
            assert app.state.logger == mock_logger
            assert app.state.manager_config == mock_manager_config
            assert app.state.supabase_client == mock_supabase_client
            assert app.state.supabase_admin_client == mock_supabase_admin_client

        # Verify shutdown logging
        assert mock_logger.info.call_count >= 2  # Startup and shutdown logs

    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        'SUPABASE_URL': 'env_url',
        'SUPABASE_KEY': 'env_key',
        'SUPABASE_SERVICE_KEY': 'env_service_key'
    })
    @patch('core.lifespan.create_client')
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_uses_environment_variables(
        self, mock_manager_config, mock_path, mock_setup_logger, mock_create_client
    ):
        """Should use environment variables over config values"""
        # Setup mocks
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': 'config_url', 'KEY': 'config_key', 'SERVICE_KEY': 'config_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_supabase_client = Mock()
        mock_supabase_admin_client = Mock()
        mock_create_client.side_effect = [mock_supabase_client, mock_supabase_admin_client]

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        # Create app and use lifespan
        app = FastAPI()
        from core.lifespan import lifespan

        async with lifespan(app):
            # Verify environment variables were used
            calls = mock_create_client.call_args_list
            assert calls[0][0] == ('env_url', 'env_key')
            assert calls[1][0] == ('env_url', 'env_service_key')

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_raises_error_when_supabase_url_missing(
        self, mock_manager_config, mock_path, mock_setup_logger
    ):
        """Should raise ValueError when SUPABASE_URL is missing"""
        # Setup mocks - missing URL
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': '', 'KEY': 'test_key', 'SERVICE_KEY': 'test_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        # Create app
        app = FastAPI()
        from core.lifespan import lifespan

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            async with lifespan(app):
                pass

        assert "Supabase URL, Key, and Service Key must be set" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_raises_error_when_supabase_key_missing(
        self, mock_manager_config, mock_path, mock_setup_logger
    ):
        """Should raise ValueError when SUPABASE_KEY is missing"""
        # Setup mocks - missing KEY
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': 'test_url', 'KEY': '', 'SERVICE_KEY': 'test_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        # Create app
        app = FastAPI()
        from core.lifespan import lifespan

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            async with lifespan(app):
                pass

        assert "Supabase URL, Key, and Service Key must be set" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_raises_error_when_service_key_missing(
        self, mock_manager_config, mock_path, mock_setup_logger
    ):
        """Should raise ValueError when SUPABASE_SERVICE_KEY is missing"""
        # Setup mocks - missing SERVICE_KEY
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': 'test_url', 'KEY': 'test_key', 'SERVICE_KEY': ''}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        # Create app
        app = FastAPI()
        from core.lifespan import lifespan

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            async with lifespan(app):
                pass

        assert "Supabase URL, Key, and Service Key must be set" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('core.lifespan.create_client')
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    @patch('core.lifespan.server_config')
    async def test_stores_server_config_in_app_state(
        self, mock_server_config, mock_manager_config, mock_path, mock_setup_logger, mock_create_client
    ):
        """Should store server_config in app.state"""
        # Setup mocks
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/log.log'},
            'SUPABASE': {'URL': 'test_url', 'KEY': 'test_key', 'SERVICE_KEY': 'test_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_supabase_client = Mock()
        mock_supabase_admin_client = Mock()
        mock_create_client.side_effect = [mock_supabase_client, mock_supabase_admin_client]

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance

        # Create app and use lifespan
        app = FastAPI()
        from core.lifespan import lifespan

        async with lifespan(app):
            # Verify server_config is stored
            assert app.state.server_config == mock_server_config

    @pytest.mark.asyncio
    @patch('core.lifespan.create_client')
    @patch('core.lifespan.setup_logger')
    @patch('core.lifespan.Path')
    @patch('core.lifespan.manager_config')
    async def test_creates_log_directory_if_not_exists(
        self, mock_manager_config, mock_path, mock_setup_logger, mock_create_client
    ):
        """Should create log directory if it doesn't exist"""
        # Setup mocks
        mock_manager_config.__getitem__ = Mock(side_effect=lambda key: {
            'ENV': {'LOG_PATH': '/test/logs/app.log'},
            'SUPABASE': {'URL': 'test_url', 'KEY': 'test_key', 'SERVICE_KEY': 'test_service_key'}
        }[key])

        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger

        mock_supabase_client = Mock()
        mock_supabase_admin_client = Mock()
        mock_create_client.side_effect = [mock_supabase_client, mock_supabase_admin_client]

        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_parent = Mock()
        mock_path_instance.parent = mock_parent

        # Create app and use lifespan
        app = FastAPI()
        from core.lifespan import lifespan

        async with lifespan(app):
            # Verify directory creation
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
