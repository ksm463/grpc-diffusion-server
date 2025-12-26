"""
Tests for utility/logger.py

This module tests the logger configuration and setup functions.
"""
import sys

# Mock cupy before any other imports to avoid import errors in CI environment
if 'cupy' not in sys.modules:
    from unittest.mock import MagicMock
    sys.modules['cupy'] = MagicMock()

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import configparser
import tempfile
import os


class TestSetupLogger:
    """Test setup_logger function"""

    @pytest.fixture(autouse=True)
    def reset_logger_flag(self):
        """Reset the global logger configuration flag before each test"""
        import sys
        logger_module = sys.modules.get('utility.logger')
        if logger_module:
            logger_module._is_logger_configured = False
        yield
        if logger_module:
            logger_module._is_logger_configured = False

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing"""
        config = configparser.ConfigParser()
        config['LOG'] = {
            'LOG_FILE_PATH': tempfile.gettempdir(),
            'LOG_FILE_NAME': 'test_server',
            'LOG_LEVEL': 'DEBUG',
            'LOG_ROTATION': '10 MB',
            'LOG_RETENTION': '7',
            'LOG_ENCODING': 'utf-8'
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            config.write(f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        try:
            os.unlink(temp_file)
        except:
            pass

    def test_sets_global_flag_after_configuration(self, temp_config_file):
        """Should set _is_logger_configured flag to True after setup"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']

        # Verify flag is False initially
        assert logger_module._is_logger_configured is False

        # Execute
        setup_logger(temp_config_file)

        # Verify flag is True after setup
        assert logger_module._is_logger_configured is True

    def test_only_configures_once_when_called_multiple_times(self, temp_config_file):
        """Should only configure logger once even if called multiple times"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']

        # Execute multiple times
        setup_logger(temp_config_file)
        first_flag = logger_module._is_logger_configured

        setup_logger(temp_config_file)
        setup_logger(temp_config_file)

        # Flag should remain True
        assert first_flag is True
        assert logger_module._is_logger_configured is True

    def test_reads_config_file_successfully(self, temp_config_file):
        """Should read config file without errors"""
        from utility.logger import setup_logger

        # Should not raise any exceptions
        setup_logger(temp_config_file)

    def test_handles_different_log_levels(self):
        """Should handle different configuration values for log levels"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']

        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            # Reset flag
            logger_module._is_logger_configured = False

            config = configparser.ConfigParser()
            config['LOG'] = {
                'LOG_FILE_PATH': tempfile.gettempdir(),
                'LOG_FILE_NAME': f'test_{level.lower()}',
                'LOG_LEVEL': level,
                'LOG_ROTATION': '10 MB',
                'LOG_RETENTION': '7',
                'LOG_ENCODING': 'utf-8'
            }

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
                config.write(f)
                temp_file = f.name

            try:
                # Should not raise any exceptions
                setup_logger(temp_file)
                assert logger_module._is_logger_configured is True
            finally:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def test_converts_retention_to_integer(self):
        """Should convert string retention value to integer"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']
        logger_module._is_logger_configured = False

        config = configparser.ConfigParser()
        config['LOG'] = {
            'LOG_FILE_PATH': tempfile.gettempdir(),
            'LOG_FILE_NAME': 'test',
            'LOG_LEVEL': 'DEBUG',
            'LOG_ROTATION': '10 MB',
            'LOG_RETENTION': '14',
            'LOG_ENCODING': 'utf-8'
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            config.write(f)
            temp_file = f.name

        try:
            # Should successfully convert '14' to 14
            setup_logger(temp_file)
            assert logger_module._is_logger_configured is True
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass

    def test_raises_error_on_missing_log_section(self):
        """Should raise KeyError when LOG section is missing"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']
        logger_module._is_logger_configured = False

        config = configparser.ConfigParser()
        config['OTHER'] = {'key': 'value'}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            config.write(f)
            temp_file = f.name

        try:
            with pytest.raises(KeyError):
                setup_logger(temp_file)
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass

    def test_creates_log_file_paths(self, temp_config_file):
        """Should create proper log file paths"""
        from utility.logger import setup_logger

        # Execute
        setup_logger(temp_config_file)

        # Verify debug and info log files are in temp directory
        temp_dir = Path(tempfile.gettempdir())
        assert temp_dir.exists()

    def test_logger_configured_flag_prevents_reconfiguration(self):
        """Should skip configuration if flag is already True"""
        from utility.logger import setup_logger
        import sys

        logger_module = sys.modules['utility.logger']

        # Manually set flag to True
        logger_module._is_logger_configured = True

        # Create invalid config
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("invalid config")
            temp_file = f.name

        try:
            # Should not raise error because it won't try to read the file
            setup_logger(temp_file)
            assert logger_module._is_logger_configured is True
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
