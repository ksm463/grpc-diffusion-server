"""
Pytest fixtures for ai-server tests.

This module provides common fixtures used across all tests.
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncGenerator
import multiprocessing


# GPU-dependent test files that should be skipped in CPU-only environments
GPU_TEST_FILES = {
    'test_lifecycle.py',
    'test_watchdog.py',
    'test_diffusion_service.py',
    'test_server_setup.py',
    'test_adapter.py',
    'test_worker_utility.py',
}


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to handle GPU-dependent tests.

    When running with '-m "not gpu"', we skip GPU test files entirely
    to avoid import errors from torch dependencies.
    """
    # Check if we're excluding GPU tests
    markexpr = config.getoption("-m", default="")
    if "not gpu" in markexpr:
        # Remove items from GPU test files
        skip_gpu = pytest.mark.skip(reason="GPU test skipped in CPU-only environment")
        for item in items:
            test_file = Path(item.fspath).name
            if test_file in GPU_TEST_FILES:
                item.add_marker(skip_gpu)


def pytest_ignore_collect(collection_path, config):
    """
    Ignore GPU test files during collection if running without GPU.

    This prevents import errors from torch dependencies in CI environments.
    """
    # Check if we're excluding GPU tests
    markexpr = config.getoption("-m", default="")
    if "not gpu" in markexpr:
        # Skip collection of GPU test files entirely
        if collection_path.name in GPU_TEST_FILES:
            return True
    return False


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
