"""
Tests for router/image_router.py
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
from router.image_router import image_router
from database.image_schemas import ImageCreationRequest, ImageGenerationResponse, ImageRecord


@pytest.fixture
def app():
    """Create FastAPI app with image_router"""
    app = FastAPI()
    app.include_router(image_router)
    return app


@pytest.fixture
def client(app):
    """Create TestClient"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = Mock()
    user.id = "test-user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_logger():
    """Mock logger"""
    return Mock()


@pytest.fixture
def mock_db():
    """Mock Supabase client"""
    return Mock()


@pytest.fixture
def mock_config():
    """Mock config"""
    return {"test": "config"}


class TestGenerateImage:
    """Test POST /api/studio/generate endpoint"""

    def test_successfully_generates_image(
        self, client, mock_user, mock_db, mock_logger, mock_config
    ):
        """Should successfully generate image when request is valid"""
        # Mock response from image_generation_request
        mock_response = ImageGenerationResponse(
            image_url="https://example.com/image.jpg",
            used_seed=12345,
            message="Image generated successfully"
        )

        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_manager_config,
            get_server_config,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_manager_config] = lambda: mock_config
        client.app.dependency_overrides[get_server_config] = lambda: mock_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Mock image_generation_request service
        with patch('router.image_router.image_generation_request', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_response

            # Make request
            response = client.post(
                "/api/studio/generate",
                json={
                    "prompt": "a beautiful sunset",
                    "width": 1024,
                    "height": 1024,
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "seed": -1
                }
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["used_seed"] == 12345
        assert data["message"] == "Image generated successfully"

        # Verify service was called with correct arguments
        mock_service.assert_called_once()
        call_kwargs = mock_service.call_args.kwargs
        assert call_kwargs["user"] == mock_user
        assert call_kwargs["db"] == mock_db
        assert call_kwargs["manager_config"] == mock_config
        assert call_kwargs["logger"] == mock_logger

    def test_rejects_invalid_request_data(
        self, client, mock_user, mock_db, mock_logger, mock_config
    ):
        """Should reject request with invalid data"""
        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_manager_config,
            get_server_config,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_manager_config] = lambda: mock_config
        client.app.dependency_overrides[get_server_config] = lambda: mock_config
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request with invalid data (width too small)
        response = client.post(
            "/api/studio/generate",
            json={
                "prompt": "test",
                "width": 100,  # Below minimum (512)
                "height": 1024
            }
        )

        # Assertions
        assert response.status_code == 422  # Validation error


class TestGetMyImages:
    """Test GET /api/gallery/my-images endpoint"""

    def test_successfully_returns_image_list(
        self, client, mock_user, mock_db, mock_logger
    ):
        """Should return paginated list of user images"""
        # Mock images from images_paginated service
        mock_images = [
            ImageRecord(
                id=uuid.uuid4(),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000123"),
                image_url="https://example.com/img1.jpg",
                prompt="a cat",
                guidance_scale=7.5,
                num_inference_steps=30,
                width=1024,
                height=1024,
                seed=123,
                created_at=datetime(2025, 1, 1)
            ),
            ImageRecord(
                id=uuid.uuid4(),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000123"),
                image_url="https://example.com/img2.jpg",
                prompt="a dog",
                guidance_scale=7.0,
                num_inference_steps=28,
                width=512,
                height=512,
                seed=456,
                created_at=datetime(2025, 1, 2)
            )
        ]

        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Mock images_paginated service
        with patch('router.image_router.images_paginated', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_images

            # Make request
            response = client.get("/api/gallery/my-images")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["prompt"] == "a cat"
        assert data[1]["prompt"] == "a dog"

        # Verify service was called with default pagination
        mock_service.assert_called_once()
        call_kwargs = mock_service.call_args.kwargs
        assert call_kwargs["user"] == mock_user
        assert call_kwargs["db"] == mock_db
        assert call_kwargs["page"] == 1
        assert call_kwargs["limit"] == 12

    def test_returns_empty_list_when_no_images(
        self, client, mock_user, mock_db, mock_logger
    ):
        """Should return empty list when user has no images"""
        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Mock images_paginated service to return empty list
        with patch('router.image_router.images_paginated', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = []

            # Make request
            response = client.get("/api/gallery/my-images")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_accepts_pagination_parameters(
        self, client, mock_user, mock_db, mock_logger
    ):
        """Should accept and use pagination parameters"""
        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Mock images_paginated service
        with patch('router.image_router.images_paginated', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = []

            # Make request with custom pagination
            response = client.get("/api/gallery/my-images?page=3&limit=24")

        # Assertions
        assert response.status_code == 200

        # Verify service was called with custom pagination
        call_kwargs = mock_service.call_args.kwargs
        assert call_kwargs["page"] == 3
        assert call_kwargs["limit"] == 24

    def test_rejects_invalid_pagination_parameters(
        self, client, mock_user, mock_db, mock_logger
    ):
        """Should reject invalid pagination parameters"""
        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request with invalid page (less than 1)
        response = client.get("/api/gallery/my-images?page=0")

        # Assertions
        assert response.status_code == 422  # Validation error

    def test_rejects_limit_above_maximum(
        self, client, mock_user, mock_db, mock_logger
    ):
        """Should reject limit above 100"""
        # Override dependencies
        from router.image_router import (
            get_current_user,
            get_supabase_admin_client,
            get_logger
        )
        client.app.dependency_overrides[get_current_user] = lambda: mock_user
        client.app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        client.app.dependency_overrides[get_logger] = lambda: mock_logger

        # Make request with limit above maximum (100)
        response = client.get("/api/gallery/my-images?limit=101")

        # Assertions
        assert response.status_code == 422  # Validation error
