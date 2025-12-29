"""
Tests for process/server_setup.py

NOTE: Marked as GPU-required due to import chain:
process.server_setup -> interface.diffusion_service -> worker.adapter -> sd_worker -> torch
"""
import pytest

pytestmark = pytest.mark.gpu  # Mark entire module as GPU-required
import asyncio
import configparser
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from process.server_setup import (
    connect_to_redis,
    setup_grpc_server,
    wait_for_shutdown,
    cleanup_redis,
    cleanup_partial,
    cleanup_all
)


@pytest.fixture
def sample_config():
    """Create sample config for testing"""
    config = configparser.ConfigParser()

    # Redis config with TCP
    config['REDIS'] = {
        'USE_UDS': 'False',
        'HOST': 'localhost',
        'PORT': '6379',
        'DB': '0',
    }

    # gRPC config
    config['GRPC'] = {
        'PORT': '50051',
        'MAX_MESSAGE_LENGTH': '10485760',  # 10MB
    }

    # Stable Diffusion config
    config['STABLEDIFFUSION'] = {
        'QUEUE_KEY': 'test_queue',
        'RESULT_KEY_PREFIX': 'result:',
        'RESULT_CHANNEL_PREFIX': 'channel:',
        'TIMEOUT': '60',
    }

    return config


@pytest.fixture
def uds_config():
    """Create config for Unix Domain Socket"""
    config = configparser.ConfigParser()

    config['REDIS'] = {
        'USE_UDS': 'True',
        'UDS_PATH': '/tmp/redis.sock',
        'DB': '0',
    }

    config['GRPC'] = {
        'PORT': '50051',
        'MAX_MESSAGE_LENGTH': '10485760',
    }

    config['STABLEDIFFUSION'] = {
        'QUEUE_KEY': 'test_queue',
        'RESULT_KEY_PREFIX': 'result:',
        'RESULT_CHANNEL_PREFIX': 'channel:',
        'TIMEOUT': '60',
    }

    return config


class TestConnectToRedis:
    """Test connect_to_redis function"""

    @pytest.mark.asyncio
    @patch('redis.asyncio.Redis')
    async def test_connects_to_tcp_redis(self, mock_redis_class, sample_config):
        """Should connect to Redis using TCP"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_class.return_value = mock_redis

        result = await connect_to_redis(sample_config)

        # Should create Redis client with TCP config
        mock_redis_class.assert_called_once_with(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=False
        )
        # Should ping Redis
        mock_redis.ping.assert_called_once()
        # Should return client
        assert result == mock_redis

    @pytest.mark.asyncio
    @patch('redis.asyncio.Redis')
    async def test_connects_to_uds_redis(self, mock_redis_class, uds_config):
        """Should connect to Redis using Unix Domain Socket"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_class.return_value = mock_redis

        result = await connect_to_redis(uds_config)

        # Should create Redis client with UDS config
        mock_redis_class.assert_called_once_with(
            unix_socket_path='/tmp/redis.sock',
            db=0
        )
        # Should ping Redis
        mock_redis.ping.assert_called_once()
        # Should return client
        assert result == mock_redis

    @pytest.mark.asyncio
    @patch('redis.asyncio.Redis')
    async def test_pings_redis_to_verify_connection(self, mock_redis_class, sample_config):
        """Should ping Redis to verify connection"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis_class.return_value = mock_redis

        await connect_to_redis(sample_config)

        # Ping should be called to verify connection
        mock_redis.ping.assert_called_once()


class TestSetupGrpcServer:
    """Test setup_grpc_server function"""

    @pytest.mark.asyncio
    @patch('process.server_setup.diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server')
    @patch('process.server_setup.DiffusionProcessingServicer')
    @patch('grpc.aio.server')
    async def test_creates_grpc_server_with_options(self, mock_grpc_server, mock_servicer_class, mock_add_servicer, sample_config):
        """Should create gRPC server with correct options"""
        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.add_insecure_port = Mock()
        mock_grpc_server.return_value = mock_server

        mock_servicer = Mock()
        mock_servicer_class.return_value = mock_servicer

        mock_redis = AsyncMock()

        result = await setup_grpc_server(sample_config, mock_redis)

        # Should create server with message length options
        call_args = mock_grpc_server.call_args
        options = call_args[1]['options']
        assert ('grpc.max_send_message_length', 10485760) in options
        assert ('grpc.max_receive_message_length', 10485760) in options

        # Should return server
        assert result == mock_server

    @pytest.mark.asyncio
    @patch('process.server_setup.diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server')
    @patch('process.server_setup.DiffusionProcessingServicer')
    @patch('grpc.aio.server')
    async def test_creates_diffusion_servicer_with_config(self, mock_grpc_server, mock_servicer_class, mock_add_servicer, sample_config):
        """Should create DiffusionProcessingServicer with config values"""
        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.add_insecure_port = Mock()
        mock_grpc_server.return_value = mock_server

        mock_servicer = Mock()
        mock_servicer_class.return_value = mock_servicer

        mock_redis = AsyncMock()

        await setup_grpc_server(sample_config, mock_redis)

        # Should create servicer with correct config
        mock_servicer_class.assert_called_once_with(
            redis_client=mock_redis,
            queue_key='test_queue',
            result_key_prefix='result:',
            result_channel_prefix='channel:',
            processing_timeout=60
        )

    @pytest.mark.asyncio
    @patch('process.server_setup.diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server')
    @patch('process.server_setup.DiffusionProcessingServicer')
    @patch('grpc.aio.server')
    async def test_adds_servicer_to_server(self, mock_grpc_server, mock_servicer_class, mock_add_servicer, sample_config):
        """Should add servicer to gRPC server"""
        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.add_insecure_port = Mock()
        mock_grpc_server.return_value = mock_server

        mock_servicer = Mock()
        mock_servicer_class.return_value = mock_servicer

        mock_redis = AsyncMock()

        await setup_grpc_server(sample_config, mock_redis)

        # Should add servicer to server
        mock_add_servicer.assert_called_once_with(mock_servicer, mock_server)

    @pytest.mark.asyncio
    @patch('process.server_setup.diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server')
    @patch('process.server_setup.DiffusionProcessingServicer')
    @patch('grpc.aio.server')
    async def test_adds_insecure_port(self, mock_grpc_server, mock_servicer_class, mock_add_servicer, sample_config):
        """Should add insecure port to server"""
        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.add_insecure_port = Mock()
        mock_grpc_server.return_value = mock_server

        mock_servicer = Mock()
        mock_servicer_class.return_value = mock_servicer

        mock_redis = AsyncMock()

        await setup_grpc_server(sample_config, mock_redis)

        # Should add insecure port
        mock_server.add_insecure_port.assert_called_once_with('[::]:50051')

    @pytest.mark.asyncio
    @patch('process.server_setup.diffusion_processing_pb2_grpc.add_ImageGeneratorServicer_to_server')
    @patch('process.server_setup.DiffusionProcessingServicer')
    @patch('grpc.aio.server')
    async def test_starts_server(self, mock_grpc_server, mock_servicer_class, mock_add_servicer, sample_config):
        """Should start gRPC server"""
        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.add_insecure_port = Mock()
        mock_grpc_server.return_value = mock_server

        mock_servicer = Mock()
        mock_servicer_class.return_value = mock_servicer

        mock_redis = AsyncMock()

        await setup_grpc_server(sample_config, mock_redis)

        # Should start server
        mock_server.start.assert_called_once()


class TestWaitForShutdown:
    """Test wait_for_shutdown function"""

    @pytest.mark.asyncio
    async def test_waits_for_shutdown_event(self):
        """Should wait for shutdown event and stop server"""
        mock_server = AsyncMock()
        # Make wait_for_termination wait forever (never complete)
        async def wait_forever():
            await asyncio.Event().wait()
        mock_server.wait_for_termination = wait_forever
        mock_server.stop = AsyncMock()

        shutdown_event = asyncio.Event()

        # Trigger shutdown event after short delay
        async def trigger_shutdown():
            await asyncio.sleep(0.1)
            shutdown_event.set()

        trigger_task = asyncio.create_task(trigger_shutdown())

        await wait_for_shutdown(mock_server, shutdown_event)

        await trigger_task

        # Should stop server with grace period
        mock_server.stop.assert_called_once_with(grace=5)

    @pytest.mark.asyncio
    async def test_cancels_pending_tasks(self):
        """Should cancel pending tasks when one completes"""
        mock_server = AsyncMock()
        mock_server.wait_for_termination = AsyncMock()
        mock_server.stop = AsyncMock()

        shutdown_event = asyncio.Event()

        # Set event immediately
        shutdown_event.set()

        await wait_for_shutdown(mock_server, shutdown_event)

        # Should have attempted to stop server
        mock_server.stop.assert_called_once()


class TestCleanupRedis:
    """Test cleanup_redis function"""

    @pytest.mark.asyncio
    async def test_closes_redis_connection(self):
        """Should close Redis connection"""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()

        await cleanup_redis(mock_redis)

        # Should close connection
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_none_redis_client(self):
        """Should handle None redis client gracefully"""
        # Should not raise exception
        await cleanup_redis(None)

    @pytest.mark.asyncio
    async def test_handles_close_exception(self):
        """Should handle exception during close"""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock(side_effect=Exception("Close error"))

        # Should not raise exception
        await cleanup_redis(mock_redis)


class TestCleanupPartial:
    """Test cleanup_partial function"""

    @pytest.mark.asyncio
    async def test_stops_grpc_server(self):
        """Should stop gRPC server"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_partial(mock_redis, mock_server, mock_lifecycle)

        # Should stop server with grace period
        mock_server.stop.assert_called_once_with(grace=1)

    @pytest.mark.asyncio
    async def test_calls_lifecycle_shutdown(self):
        """Should call lifecycle manager shutdown"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_partial(mock_redis, mock_server, mock_lifecycle)

        # Should shutdown lifecycle manager
        mock_lifecycle.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_redis_connection(self):
        """Should close Redis connection"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_partial(mock_redis, mock_server, mock_lifecycle)

        # Should close Redis
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_server_stop_exception(self):
        """Should handle exception during server stop"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock(side_effect=Exception("Stop error"))
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        # Should not raise exception
        await cleanup_partial(mock_redis, mock_server, mock_lifecycle)

        # Should still continue with other cleanups
        mock_lifecycle.shutdown.assert_called_once()
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_lifecycle_shutdown_exception(self):
        """Should handle exception during lifecycle shutdown"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock(side_effect=Exception("Shutdown error"))

        # Should not raise exception
        await cleanup_partial(mock_redis, mock_server, mock_lifecycle)

        # Should still close Redis
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_none_server(self):
        """Should handle None server gracefully"""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        # Should not raise exception
        await cleanup_partial(mock_redis, None, mock_lifecycle)


class TestCleanupAll:
    """Test cleanup_all function"""

    @pytest.mark.asyncio
    async def test_stops_grpc_server(self):
        """Should stop gRPC server"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_all(mock_server, mock_redis, mock_lifecycle)

        # Should stop server
        mock_server.stop.assert_called_once_with(grace=1)

    @pytest.mark.asyncio
    async def test_calls_lifecycle_shutdown(self):
        """Should call lifecycle manager shutdown"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_all(mock_server, mock_redis, mock_lifecycle)

        # Should shutdown lifecycle manager
        mock_lifecycle.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_redis_connection(self):
        """Should close Redis connection"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        await cleanup_all(mock_server, mock_redis, mock_lifecycle)

        # Should close Redis
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('asyncio.sleep')
    async def test_waits_before_completion(self, mock_sleep):
        """Should wait 0.5 seconds before completing"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        mock_sleep.return_value = asyncio.sleep(0)  # Don't actually wait

        await cleanup_all(mock_server, mock_redis, mock_lifecycle)

        # Should include a sleep with 0.5 seconds (final sleep before completion)
        assert any(call[0][0] == 0.5 for call in mock_sleep.call_args_list)

    @pytest.mark.asyncio
    async def test_handles_none_server(self):
        """Should handle None server gracefully"""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock()

        # Should not raise exception
        await cleanup_all(None, mock_redis, mock_lifecycle)

    @pytest.mark.asyncio
    async def test_handles_exceptions_gracefully(self):
        """Should handle exceptions in all cleanup steps"""
        mock_server = AsyncMock()
        mock_server.stop = AsyncMock(side_effect=Exception("Stop error"))
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock(side_effect=Exception("Close error"))
        mock_lifecycle = AsyncMock()
        mock_lifecycle.shutdown = AsyncMock(side_effect=Exception("Shutdown error"))

        # Should not raise exception
        await cleanup_all(mock_server, mock_redis, mock_lifecycle)

        # All cleanup attempts should have been made
        mock_server.stop.assert_called_once()
        mock_lifecycle.shutdown.assert_called_once()
        mock_redis.close.assert_called_once()
