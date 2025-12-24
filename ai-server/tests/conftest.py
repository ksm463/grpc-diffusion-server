"""
Pytest fixtures for ai-server tests.

This module provides common fixtures used across all tests.
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncGenerator
import multiprocessing


@pytest.fixture
async def redis_client():
    """
    Mock Redis client using fakeredis.

    Returns:
        FakeRedis: A fake Redis client for testing.
    """
    from fakeredis import aioredis as fake_aioredis

    client = fake_aioredis.FakeRedis(decode_responses=False)
    yield client
    await client.close()


@pytest.fixture
def mock_worker_process():
    """
    Mock worker process for testing lifecycle management.

    Returns:
        Mock: A mock multiprocessing.Process object.
    """
    mock_process = Mock(spec=multiprocessing.Process)
    mock_process.pid = 12345
    mock_process.is_alive = Mock(return_value=True)
    mock_process.start = Mock()
    mock_process.terminate = Mock()
    mock_process.kill = Mock()
    mock_process.join = Mock()
    mock_process.exitcode = None
    return mock_process


@pytest.fixture
def mock_grpc_context():
    """
    Mock gRPC context for servicer testing.

    Returns:
        Mock: A mock gRPC context.
    """
    mock_context = Mock()
    mock_context.set_code = Mock()
    mock_context.set_details = Mock()
    mock_context.abort = Mock()
    return mock_context


@pytest.fixture
def sample_image_request_proto():
    """
    Sample image generation request in proto format.

    Returns:
        dict: Sample request data that can be used to create proto message.
    """
    return {
        "prompt": "a cat sitting on a table",
        "negative_prompt": "blurry, low quality",
        "width": 512,
        "height": 512,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
        "seed": 42,
    }


@pytest.fixture
def mock_stable_diffusion_pipeline():
    """
    Mock Stable Diffusion pipeline for testing worker.

    Returns:
        Mock: A mock StableDiffusionPipeline.
    """
    mock_pipeline = Mock()
    mock_pipeline.__call__ = Mock(return_value=Mock(images=[Mock()]))
    return mock_pipeline


@pytest.fixture
async def mock_queue():
    """
    Mock multiprocessing Queue for watchdog testing.

    Returns:
        Mock: A mock Queue object.
    """
    mock_q = Mock(spec=multiprocessing.Queue)
    mock_q.put = Mock()
    mock_q.get = Mock()
    mock_q.empty = Mock(return_value=False)
    return mock_q


@pytest.fixture
def sample_server_config():
    """
    Sample server configuration for testing.

    Returns:
        dict: Configuration dictionary.
    """
    return {
        "SERVER": {
            "HOST": "0.0.0.0",
            "PORT": "50051",
        },
        "REDIS": {
            "SOCKET_PATH": "/tmp/redis.sock",
            "TIMEOUT": "5",
        },
        "WORKER": {
            "MAX_WORKER": "2",
        },
        "LIFECYCLE": {
            "MAX_STARTUP_RETRIES": "10",
            "INITIAL_DELAY": "0.1",
            "MAX_DELAY": "5.0",
            "GRACE_PERIOD": "10",
        },
    }
