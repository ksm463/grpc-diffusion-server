"""
Pytest fixtures for web-manager tests.

This module provides common fixtures used across all tests.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator


@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client for testing.

    Returns:
        Mock: A mock Supabase client with common methods.
    """
    mock_client = Mock()
    mock_client.auth = Mock()
    mock_client.auth.sign_in_with_password = AsyncMock()
    mock_client.auth.sign_up = AsyncMock()
    mock_client.auth.sign_out = AsyncMock()
    mock_client.storage = Mock()
    mock_client.table = Mock(return_value=Mock())
    return mock_client


@pytest.fixture
def mock_grpc_stub():
    """
    Mock gRPC stub for AI server communication.

    Returns:
        Mock: A mock gRPC stub.
    """
    mock_stub = Mock()
    mock_stub.GenerateImage = AsyncMock()
    return mock_stub


@pytest.fixture
async def test_user_data():
    """
    Sample user data for testing.

    Returns:
        dict: User data dictionary.
    """
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "username": "testuser",
    }


@pytest.fixture
def sample_image_request():
    """
    Sample image generation request data.

    Returns:
        dict: Valid image generation request.
    """
    return {
        "prompt": "a beautiful sunset over mountains",
        "width": 512,
        "height": 512,
        "num_inference_steps": 20,
        "guidance_scale": 7.5,
    }


@pytest.fixture
def invalid_image_request():
    """
    Invalid image generation request for testing validation.

    Returns:
        dict: Invalid image generation request.
    """
    return {
        "prompt": "",  # Empty prompt
        "width": 100,  # Too small
        "height": 100,  # Too small
    }
