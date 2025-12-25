"""
Tests for service/image_requester.py
"""
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from service.image_requester import images_paginated, image_generation_request
from database.image_schemas import ImageCreationRequest, ImageGenerationResponse


class TestImagesPaginated:
    """Test images_paginated function"""

    @pytest.mark.asyncio
    async def test_successfully_returns_image_list(self):
        """Should return list of ImageRecord objects"""
        from datetime import datetime

        # Setup mocks
        mock_user = Mock()
        mock_user.id = "user-123"

        mock_db = Mock()
        mock_response = Mock()
        # Use valid datetime objects instead of strings
        mock_response.data = [
            {
                "id": uuid.uuid4(),
                "user_id": uuid.UUID("00000000-0000-0000-0000-000000000123"),
                "image_url": "https://example.com/img1.jpg",
                "prompt": "a cat",
                "guidance_scale": 7.5,
                "num_inference_steps": 30,
                "width": 1024,
                "height": 1024,
                "seed": 123,
                "created_at": datetime(2025, 1, 1)
            },
            {
                "id": uuid.uuid4(),
                "user_id": uuid.UUID("00000000-0000-0000-0000-000000000123"),
                "image_url": "https://example.com/img2.jpg",
                "prompt": "a dog",
                "guidance_scale": 7.0,
                "num_inference_steps": 28,
                "width": 512,
                "height": 512,
                "seed": 456,
                "created_at": datetime(2025, 1, 2)
            }
        ]

        # Chain method calls
        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = mock_response
        mock_db.from_.return_value = mock_query

        mock_logger = Mock()

        # Call function
        result = await images_paginated(
            user=mock_user,
            db=mock_db,
            page=1,
            limit=10,
            logger=mock_logger
        )

        # Assertions
        assert len(result) == 2
        assert result[0].prompt == "a cat"
        assert result[1].prompt == "a dog"
        mock_db.from_.assert_called_once_with("images")
        mock_query.eq.assert_called_once_with('user_id', "user-123")
        mock_query.range.assert_called_once_with(0, 9)  # page 1, limit 10 -> 0-9

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_exception(self):
        """Should return empty list when exception occurs"""
        # Setup mocks
        mock_user = Mock()
        mock_user.id = "user-456"

        mock_db = Mock()
        mock_db.from_.side_effect = Exception("Database error")

        mock_logger = Mock()

        # Call function
        result = await images_paginated(
            user=mock_user,
            db=mock_db,
            page=1,
            limit=10,
            logger=mock_logger
        )

        # Assertions
        assert result == []
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_pagination_calculation(self):
        """Should correctly calculate pagination indices"""
        # Setup mocks
        mock_user = Mock()
        mock_user.id = "user-789"

        mock_db = Mock()
        mock_response = Mock()
        mock_response.data = []

        mock_query = Mock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.execute.return_value = mock_response
        mock_db.from_.return_value = mock_query

        mock_logger = Mock()

        # Call function with page=3, limit=20
        result = await images_paginated(
            user=mock_user,
            db=mock_db,
            page=3,
            limit=20,
            logger=mock_logger
        )

        # Assertions
        # page=3, limit=20 -> start_index=40, end_index=59
        mock_query.range.assert_called_once_with(40, 59)


class TestImageGenerationRequest:
    """Test image_generation_request function"""

    @pytest.mark.asyncio
    async def test_raises_500_when_ai_server_address_not_configured(self):
        """Should raise 500 when AI server address is missing"""
        # Setup mocks
        request_data = ImageCreationRequest(prompt="test")
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_db = Mock()
        manager_config = {"ADDRESS": {}}  # No SERVER_IP_ADDRESS
        server_config = {}
        mock_logger = Mock()

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await image_generation_request(
                request_data=request_data,
                user=mock_user,
                db=mock_db,
                manager_config=manager_config,
                server_config=server_config,
                logger=mock_logger
            )

        # Assertions
        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('service.image_requester.grpc.aio.insecure_channel')
    async def test_raises_503_on_grpc_error(self, mock_channel):
        """Should raise 503 when gRPC call fails"""
        # Setup mocks
        request_data = ImageCreationRequest(prompt="test image")
        mock_user = Mock()
        mock_user.id = "user-456"
        mock_db = Mock()
        manager_config = {"ADDRESS": {"SERVER_IP_ADDRESS": "localhost:50051"}}
        server_config = {}
        mock_logger = Mock()

        # Create a proper exception that inherits from Exception
        class MockGrpcError(Exception):
            def details(self):
                return "Connection refused"

        mock_stub = AsyncMock()
        mock_stub.GenerateImage.side_effect = MockGrpcError()

        mock_channel_instance = AsyncMock()
        mock_channel_instance.__aenter__.return_value = mock_channel_instance
        mock_channel_instance.__aexit__.return_value = None
        mock_channel.return_value = mock_channel_instance

        with patch('service.image_requester.diffusion_processing_pb2_grpc.ImageGeneratorStub', return_value=mock_stub):
            with patch('service.image_requester.grpc.aio.AioRpcError', MockGrpcError):
                # Call function and expect exception
                with pytest.raises(HTTPException) as exc_info:
                    await image_generation_request(
                        request_data=request_data,
                        user=mock_user,
                        db=mock_db,
                        manager_config=manager_config,
                        server_config=server_config,
                        logger=mock_logger
                    )

        # Assertions
        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('service.image_requester.grpc.aio.insecure_channel')
    @patch('service.image_requester.diffusion_processing_pb2')
    async def test_raises_500_when_ai_server_returns_failure(self, mock_pb2, mock_channel):
        """Should raise 500 when AI server returns FAILURE status"""
        # Setup mocks
        request_data = ImageCreationRequest(prompt="failing image")
        mock_user = Mock()
        mock_user.id = "user-789"
        mock_db = Mock()
        manager_config = {"ADDRESS": {"SERVER_IP_ADDRESS": "localhost:50051"}}
        server_config = {}
        mock_logger = Mock()

        # Mock gRPC response with FAILURE status
        mock_response = Mock()
        mock_response.status = mock_pb2.GenerationResponse.Status.FAILURE
        mock_response.error_message = "GPU out of memory"

        mock_stub = AsyncMock()
        mock_stub.GenerateImage.return_value = mock_response

        mock_channel_instance = AsyncMock()
        mock_channel_instance.__aenter__.return_value = mock_channel_instance
        mock_channel_instance.__aexit__.return_value = None
        mock_channel.return_value = mock_channel_instance

        with patch('service.image_requester.diffusion_processing_pb2_grpc.ImageGeneratorStub', return_value=mock_stub):
            # Call function and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await image_generation_request(
                    request_data=request_data,
                    user=mock_user,
                    db=mock_db,
                    manager_config=manager_config,
                    server_config=server_config,
                    logger=mock_logger
                )

        # Assertions
        assert exc_info.value.status_code == 500
        assert "GPU out of memory" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('service.image_requester.grpc.aio.insecure_channel')
    @patch('service.image_requester.diffusion_processing_pb2')
    async def test_raises_500_on_storage_upload_failure(self, mock_pb2, mock_channel):
        """Should raise 500 when Supabase storage upload fails"""
        # Setup mocks
        request_data = ImageCreationRequest(prompt="test image")
        mock_user = Mock()
        mock_user.id = "user-abc"
        mock_db = Mock()
        manager_config = {"ADDRESS": {"SERVER_IP_ADDRESS": "localhost:50051"}}
        server_config = {}
        mock_logger = Mock()

        # Mock successful gRPC response
        mock_response = Mock()
        mock_response.status = mock_pb2.GenerationResponse.Status.SUCCESS
        mock_response.image_data = b"fake_image_data"
        mock_response.used_seed = 12345
        mock_response.request_id = str(uuid.uuid4())

        mock_stub = AsyncMock()
        mock_stub.GenerateImage.return_value = mock_response

        mock_channel_instance = AsyncMock()
        mock_channel_instance.__aenter__.return_value = mock_channel_instance
        mock_channel_instance.__aexit__.return_value = None
        mock_channel.return_value = mock_channel_instance

        # Mock storage upload to fail
        mock_storage = Mock()
        mock_storage.from_.return_value.upload.side_effect = Exception("Storage error")
        mock_db.storage = mock_storage

        with patch('service.image_requester.diffusion_processing_pb2_grpc.ImageGeneratorStub', return_value=mock_stub):
            # Call function and expect exception
            with pytest.raises(HTTPException) as exc_info:
                await image_generation_request(
                    request_data=request_data,
                    user=mock_user,
                    db=mock_db,
                    manager_config=manager_config,
                    server_config=server_config,
                    logger=mock_logger
                )

        # Assertions
        assert exc_info.value.status_code == 500
        assert "upload image to storage" in exc_info.value.detail
