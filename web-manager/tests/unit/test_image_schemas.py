"""
Tests for Pydantic schemas in database/image_schemas.py
"""
import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError
from database.image_schemas import (
    ImageCreationRequest,
    AIServerRequest,
    GenerationStatus,
    AIServerResponse,
    ImageRecordCreate,
    ImageRecord,
    ImageGenerationResponse
)


class TestImageCreationRequest:
    """Test ImageCreationRequest schema validation"""

    def test_valid_request_with_all_fields(self):
        """Valid request with all fields should pass validation"""
        data = {
            "prompt": "a beautiful sunset",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "seed": 123456789
        }
        request = ImageCreationRequest(**data)
        assert request.prompt == "a beautiful sunset"
        assert request.guidance_scale == 7.5
        assert request.num_inference_steps == 30
        assert request.width == 1024
        assert request.height == 1024
        assert request.seed == 123456789

    def test_valid_request_with_defaults(self):
        """Request with only prompt should use default values"""
        data = {"prompt": "a cat"}
        request = ImageCreationRequest(**data)
        assert request.prompt == "a cat"
        assert request.guidance_scale == 7.0  # Default
        assert request.num_inference_steps == 28  # Default
        assert request.width == 1024  # Default
        assert request.height == 1024  # Default
        assert request.seed == -1  # Default

    def test_missing_prompt_raises_error(self):
        """Missing prompt should raise ValidationError"""
        data = {"width": 512, "height": 512}
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "prompt" in str(exc_info.value)

    def test_empty_prompt_raises_error(self):
        """Empty prompt should raise ValidationError (min_length=1)"""
        data = {"prompt": ""}
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "prompt" in str(exc_info.value)

    def test_guidance_scale_below_minimum_raises_error(self):
        """Guidance scale below 1.0 should raise ValidationError"""
        data = {
            "prompt": "test",
            "guidance_scale": 0.5  # Below minimum (ge=1.0)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "guidance_scale" in str(exc_info.value)

    def test_guidance_scale_above_maximum_raises_error(self):
        """Guidance scale above 20.0 should raise ValidationError"""
        data = {
            "prompt": "test",
            "guidance_scale": 25.0  # Above maximum (le=20.0)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "guidance_scale" in str(exc_info.value)

    def test_num_inference_steps_below_minimum_raises_error(self):
        """Num inference steps below 10 should raise ValidationError"""
        data = {
            "prompt": "test",
            "num_inference_steps": 5  # Below minimum (ge=10)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "num_inference_steps" in str(exc_info.value)

    def test_num_inference_steps_above_maximum_raises_error(self):
        """Num inference steps above 50 should raise ValidationError"""
        data = {
            "prompt": "test",
            "num_inference_steps": 60  # Above maximum (le=50)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "num_inference_steps" in str(exc_info.value)

    def test_width_below_minimum_raises_error(self):
        """Width below 512 should raise ValidationError"""
        data = {
            "prompt": "test",
            "width": 256  # Below minimum (ge=512)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "width" in str(exc_info.value)

    def test_width_above_maximum_raises_error(self):
        """Width above 1536 should raise ValidationError"""
        data = {
            "prompt": "test",
            "width": 2048  # Above maximum (le=1536)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "width" in str(exc_info.value)

    def test_height_below_minimum_raises_error(self):
        """Height below 512 should raise ValidationError"""
        data = {
            "prompt": "test",
            "height": 256  # Below minimum (ge=512)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "height" in str(exc_info.value)

    def test_height_above_maximum_raises_error(self):
        """Height above 1536 should raise ValidationError"""
        data = {
            "prompt": "test",
            "height": 2048  # Above maximum (le=1536)
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageCreationRequest(**data)
        assert "height" in str(exc_info.value)

    def test_boundary_values_width_height(self):
        """Boundary values for width and height should pass"""
        # Minimum values
        data_min = {
            "prompt": "test",
            "width": 512,
            "height": 512
        }
        request_min = ImageCreationRequest(**data_min)
        assert request_min.width == 512
        assert request_min.height == 512

        # Maximum values
        data_max = {
            "prompt": "test",
            "width": 1536,
            "height": 1536
        }
        request_max = ImageCreationRequest(**data_max)
        assert request_max.width == 1536
        assert request_max.height == 1536

    def test_boundary_values_guidance_scale(self):
        """Boundary values for guidance_scale should pass"""
        # Minimum value
        data_min = {
            "prompt": "test",
            "guidance_scale": 1.0
        }
        request_min = ImageCreationRequest(**data_min)
        assert request_min.guidance_scale == 1.0

        # Maximum value
        data_max = {
            "prompt": "test",
            "guidance_scale": 20.0
        }
        request_max = ImageCreationRequest(**data_max)
        assert request_max.guidance_scale == 20.0

    def test_boundary_values_num_inference_steps(self):
        """Boundary values for num_inference_steps should pass"""
        # Minimum value
        data_min = {
            "prompt": "test",
            "num_inference_steps": 10
        }
        request_min = ImageCreationRequest(**data_min)
        assert request_min.num_inference_steps == 10

        # Maximum value
        data_max = {
            "prompt": "test",
            "num_inference_steps": 50
        }
        request_max = ImageCreationRequest(**data_max)
        assert request_max.num_inference_steps == 50


class TestAIServerRequest:
    """Test AIServerRequest schema"""

    def test_valid_ai_server_request(self):
        """Valid AI server request should pass validation"""
        request_id = uuid.uuid4()
        data = {
            "request_id": request_id,
            "prompt": "a cat",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "seed": 123456
        }
        request = AIServerRequest(**data)
        assert request.request_id == request_id
        assert request.prompt == "a cat"
        assert request.guidance_scale == 7.5
        assert request.num_inference_steps == 30
        assert request.width == 1024
        assert request.height == 1024
        assert request.seed == 123456

    def test_missing_required_field_raises_error(self):
        """Missing required field should raise ValidationError"""
        data = {
            "prompt": "test",
            "guidance_scale": 7.5,
            # Missing request_id
        }
        with pytest.raises(ValidationError) as exc_info:
            AIServerRequest(**data)
        assert "request_id" in str(exc_info.value)


class TestGenerationStatus:
    """Test GenerationStatus enum"""

    def test_success_status(self):
        """SUCCESS status should be valid"""
        status = GenerationStatus.SUCCESS
        assert status == "SUCCESS"
        assert status.value == "SUCCESS"

    def test_failure_status(self):
        """FAILURE status should be valid"""
        status = GenerationStatus.FAILURE
        assert status == "FAILURE"
        assert status.value == "FAILURE"

    def test_status_comparison(self):
        """Status comparison should work correctly"""
        assert GenerationStatus.SUCCESS != GenerationStatus.FAILURE
        assert GenerationStatus.SUCCESS == GenerationStatus.SUCCESS


class TestAIServerResponse:
    """Test AIServerResponse schema"""

    def test_valid_success_response(self):
        """Valid success response with image data should pass"""
        request_id = uuid.uuid4()
        image_data = b"fake_image_bytes"
        data = {
            "request_id": request_id,
            "status": GenerationStatus.SUCCESS,
            "used_seed": 123456,
            "image_data": image_data
        }
        response = AIServerResponse(**data)
        assert response.request_id == request_id
        assert response.status == GenerationStatus.SUCCESS
        assert response.used_seed == 123456
        assert response.image_data == image_data
        assert response.error_message is None

    def test_valid_failure_response(self):
        """Valid failure response with error message should pass"""
        request_id = uuid.uuid4()
        data = {
            "request_id": request_id,
            "status": GenerationStatus.FAILURE,
            "used_seed": 123456,
            "error_message": "GPU out of memory"
        }
        response = AIServerResponse(**data)
        assert response.request_id == request_id
        assert response.status == GenerationStatus.FAILURE
        assert response.used_seed == 123456
        assert response.image_data is None
        assert response.error_message == "GPU out of memory"

    def test_missing_required_field_raises_error(self):
        """Missing required field should raise ValidationError"""
        data = {
            "request_id": uuid.uuid4(),
            "status": GenerationStatus.SUCCESS,
            # Missing used_seed
        }
        with pytest.raises(ValidationError) as exc_info:
            AIServerResponse(**data)
        assert "used_seed" in str(exc_info.value)


class TestImageRecordCreate:
    """Test ImageRecordCreate schema"""

    def test_valid_image_record_create(self):
        """Valid image record create should pass validation"""
        user_id = uuid.uuid4()
        data = {
            "user_id": user_id,
            "image_url": "https://example.com/image.png",
            "prompt": "a sunset",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "seed": 123456
        }
        record = ImageRecordCreate(**data)
        assert record.user_id == user_id
        assert record.image_url == "https://example.com/image.png"
        assert record.prompt == "a sunset"
        assert record.guidance_scale == 7.5
        assert record.num_inference_steps == 30
        assert record.width == 1024
        assert record.height == 1024
        assert record.seed == 123456

    def test_missing_required_field_raises_error(self):
        """Missing required field should raise ValidationError"""
        data = {
            "user_id": uuid.uuid4(),
            "image_url": "https://example.com/image.png",
            # Missing prompt
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageRecordCreate(**data)
        errors = str(exc_info.value)
        assert "prompt" in errors or "guidance_scale" in errors


class TestImageRecord:
    """Test ImageRecord schema"""

    def test_valid_image_record(self):
        """Valid image record should pass validation"""
        user_id = uuid.uuid4()
        record_id = uuid.uuid4()
        created_at = datetime.now()
        data = {
            "id": record_id,
            "user_id": user_id,
            "image_url": "https://example.com/image.png",
            "prompt": "a sunset",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "seed": 123456,
            "created_at": created_at
        }
        record = ImageRecord(**data)
        assert record.id == record_id
        assert record.user_id == user_id
        assert record.image_url == "https://example.com/image.png"
        assert record.created_at == created_at

    def test_inherits_from_image_record_create(self):
        """ImageRecord should have all fields from ImageRecordCreate"""
        user_id = uuid.uuid4()
        record_id = uuid.uuid4()
        data = {
            "id": record_id,
            "user_id": user_id,
            "image_url": "https://example.com/image.png",
            "prompt": "test",
            "guidance_scale": 7.5,
            "num_inference_steps": 30,
            "width": 1024,
            "height": 1024,
            "seed": 123456,
            "created_at": datetime.now()
        }
        record = ImageRecord(**data)
        # Should have parent class fields
        assert hasattr(record, 'user_id')
        assert hasattr(record, 'image_url')
        assert hasattr(record, 'prompt')
        # And additional fields
        assert hasattr(record, 'id')
        assert hasattr(record, 'created_at')


class TestImageGenerationResponse:
    """Test ImageGenerationResponse schema"""

    def test_valid_generation_response(self):
        """Valid generation response should pass validation"""
        data = {
            "image_url": "https://example.com/generated.png",
            "used_seed": 123456,
            "message": "Image generated successfully"
        }
        response = ImageGenerationResponse(**data)
        assert response.image_url == "https://example.com/generated.png"
        assert response.used_seed == 123456
        assert response.message == "Image generated successfully"

    def test_missing_required_field_raises_error(self):
        """Missing required field should raise ValidationError"""
        data = {
            "image_url": "https://example.com/generated.png",
            # Missing used_seed and message
        }
        with pytest.raises(ValidationError) as exc_info:
            ImageGenerationResponse(**data)
        errors = str(exc_info.value)
        assert "used_seed" in errors or "message" in errors
