"""
Tests for Pydantic schemas in database/auth_schemas.py
"""
import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError
from database.auth_schemas import (
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
    UpdatePasswordRequest
)


class TestUserCreate:
    """Test UserCreate schema validation"""

    def test_valid_user_create(self):
        """Valid user creation data should pass validation"""
        data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        user = UserCreate(**data)
        assert user.email == "test@example.com"
        assert user.password == "securepassword123"

    def test_invalid_email_format_raises_error(self):
        """Invalid email format should raise ValidationError"""
        data = {
            "email": "notanemail",
            "password": "password123"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "email" in str(exc_info.value).lower()

    def test_missing_email_raises_error(self):
        """Missing email should raise ValidationError"""
        data = {
            "password": "password123"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "email" in str(exc_info.value)

    def test_missing_password_raises_error(self):
        """Missing password should raise ValidationError"""
        data = {
            "email": "test@example.com"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "password" in str(exc_info.value)

    def test_email_normalization(self):
        """Email should be validated as EmailStr"""
        data = {
            "email": "Test.User@Example.COM",
            "password": "password123"
        }
        user = UserCreate(**data)
        # Pydantic's EmailStr normalizes email to lowercase
        assert "@" in user.email
        assert "example.com" in user.email.lower()

    def test_empty_password_accepted(self):
        """Empty password should be accepted (validation done elsewhere)"""
        data = {
            "email": "test@example.com",
            "password": ""
        }
        user = UserCreate(**data)
        assert user.password == ""


class TestUserLogin:
    """Test UserLogin schema validation"""

    def test_valid_user_login(self):
        """Valid login data should pass validation"""
        data = {
            "email": "user@example.com",
            "password": "mypassword"
        }
        login = UserLogin(**data)
        assert login.email == "user@example.com"
        assert login.password == "mypassword"

    def test_invalid_email_format_raises_error(self):
        """Invalid email format should raise ValidationError"""
        data = {
            "email": "invalid-email",
            "password": "password"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)
        assert "email" in str(exc_info.value).lower()

    def test_missing_email_raises_error(self):
        """Missing email should raise ValidationError"""
        data = {
            "password": "password"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)
        assert "email" in str(exc_info.value)

    def test_missing_password_raises_error(self):
        """Missing password should raise ValidationError"""
        data = {
            "email": "test@example.com"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)
        assert "password" in str(exc_info.value)


class TestUserRead:
    """Test UserRead schema validation"""

    def test_valid_user_read(self):
        """Valid user read data should pass validation"""
        user_id = uuid.uuid4()
        created_at = datetime.now()
        data = {
            "id": user_id,
            "email": "read@example.com",
            "created_at": created_at
        }
        user = UserRead(**data)
        assert user.id == user_id
        assert user.email == "read@example.com"
        assert user.created_at == created_at

    def test_missing_id_raises_error(self):
        """Missing id should raise ValidationError"""
        data = {
            "email": "test@example.com",
            "created_at": datetime.now()
        }
        with pytest.raises(ValidationError) as exc_info:
            UserRead(**data)
        assert "id" in str(exc_info.value)

    def test_missing_email_raises_error(self):
        """Missing email should raise ValidationError"""
        data = {
            "id": uuid.uuid4(),
            "created_at": datetime.now()
        }
        with pytest.raises(ValidationError) as exc_info:
            UserRead(**data)
        assert "email" in str(exc_info.value)

    def test_missing_created_at_raises_error(self):
        """Missing created_at should raise ValidationError"""
        data = {
            "id": uuid.uuid4(),
            "email": "test@example.com"
        }
        with pytest.raises(ValidationError) as exc_info:
            UserRead(**data)
        assert "created_at" in str(exc_info.value)

    def test_invalid_uuid_format_raises_error(self):
        """Invalid UUID format should raise ValidationError"""
        data = {
            "id": "not-a-valid-uuid",
            "email": "test@example.com",
            "created_at": datetime.now()
        }
        with pytest.raises(ValidationError) as exc_info:
            UserRead(**data)
        assert "id" in str(exc_info.value).lower()

    def test_from_attributes_config(self):
        """UserRead should have from_attributes=True config"""
        assert UserRead.model_config.get("from_attributes") is True


class TestUserUpdate:
    """Test UserUpdate schema validation"""

    def test_valid_update_with_password_only(self):
        """Valid update with password only should pass"""
        data = {
            "password": "newpassword123"
        }
        update = UserUpdate(**data)
        assert update.password == "newpassword123"
        assert update.data is None

    def test_valid_update_with_data_only(self):
        """Valid update with data only should pass"""
        data = {
            "data": {"theme": "dark", "language": "en"}
        }
        update = UserUpdate(**data)
        assert update.password is None
        assert update.data == {"theme": "dark", "language": "en"}

    def test_valid_update_with_both_fields(self):
        """Valid update with both password and data should pass"""
        data = {
            "password": "newpassword",
            "data": {"notifications": True}
        }
        update = UserUpdate(**data)
        assert update.password == "newpassword"
        assert update.data == {"notifications": True}

    def test_update_with_no_fields(self):
        """Update with no fields should pass (all optional)"""
        data = {}
        update = UserUpdate(**data)
        assert update.password is None
        assert update.data is None

    def test_update_with_null_values(self):
        """Update with explicit None values should pass"""
        data = {
            "password": None,
            "data": None
        }
        update = UserUpdate(**data)
        assert update.password is None
        assert update.data is None

    def test_data_field_accepts_dict(self):
        """Data field should accept any dictionary"""
        data = {
            "data": {
                "nested": {
                    "structure": "works",
                    "number": 42
                }
            }
        }
        update = UserUpdate(**data)
        assert update.data["nested"]["structure"] == "works"
        assert update.data["nested"]["number"] == 42


class TestUpdatePasswordRequest:
    """Test UpdatePasswordRequest schema validation"""

    def test_valid_password_update_request(self):
        """Valid password update request should pass"""
        data = {
            "new_password": "newsecurepass123"
        }
        request = UpdatePasswordRequest(**data)
        assert request.new_password == "newsecurepass123"

    def test_missing_new_password_raises_error(self):
        """Missing new_password should raise ValidationError"""
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            UpdatePasswordRequest(**data)
        assert "new_password" in str(exc_info.value)

    def test_password_below_min_length_raises_error(self):
        """Password below 6 characters should raise ValidationError"""
        data = {
            "new_password": "short"  # 5 characters, min_length=6
        }
        with pytest.raises(ValidationError) as exc_info:
            UpdatePasswordRequest(**data)
        assert "new_password" in str(exc_info.value)

    def test_password_at_min_length_passes(self):
        """Password with exactly 6 characters should pass"""
        data = {
            "new_password": "pass12"  # Exactly 6 characters
        }
        request = UpdatePasswordRequest(**data)
        assert request.new_password == "pass12"

    def test_long_password_passes(self):
        """Long password should pass validation"""
        data = {
            "new_password": "a" * 100
        }
        request = UpdatePasswordRequest(**data)
        assert len(request.new_password) == 100

    def test_empty_password_raises_error(self):
        """Empty password should raise ValidationError"""
        data = {
            "new_password": ""
        }
        with pytest.raises(ValidationError) as exc_info:
            UpdatePasswordRequest(**data)
        assert "new_password" in str(exc_info.value)

    def test_special_characters_in_password(self):
        """Password with special characters should pass"""
        data = {
            "new_password": "P@ssw0rd!#$%"
        }
        request = UpdatePasswordRequest(**data)
        assert request.new_password == "P@ssw0rd!#$%"
