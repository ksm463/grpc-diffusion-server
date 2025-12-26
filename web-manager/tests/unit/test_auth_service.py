"""
Tests for service/auth_service.py
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException
from service.auth_service import get_current_user, get_current_superuser


class TestGetCurrentUser:
    """Test get_current_user function"""

    @pytest.mark.asyncio
    async def test_valid_token_from_header_returns_user(self):
        """Should return user when valid token in header"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = None

        mock_supabase = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"

        mock_user_response = Mock()
        mock_user_response.user = mock_user
        mock_supabase.auth.get_user.return_value = mock_user_response

        mock_logger = Mock()

        token = "valid_jwt_token"

        # Call function
        result = await get_current_user(
            request=mock_request,
            token_from_header=token,
            supabase=mock_supabase,
            logger=mock_logger
        )

        # Assertions
        assert result == mock_user
        mock_supabase.auth.get_user.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_valid_token_from_cookie_returns_user(self):
        """Should return user when valid token in cookie (header is None)"""
        # Setup mocks
        mock_request = Mock()
        cookie_token = "cookie_jwt_token"
        mock_request.cookies.get.return_value = cookie_token

        mock_supabase = Mock()
        mock_user = Mock()
        mock_user.id = "user-456"

        mock_user_response = Mock()
        mock_user_response.user = mock_user
        mock_supabase.auth.get_user.return_value = mock_user_response

        mock_logger = Mock()

        # Call function (token_from_header is None)
        result = await get_current_user(
            request=mock_request,
            token_from_header=None,
            supabase=mock_supabase,
            logger=mock_logger
        )

        # Assertions
        assert result == mock_user
        mock_request.cookies.get.assert_called_once_with("access_token")
        mock_supabase.auth.get_user.assert_called_once_with(cookie_token)

    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        """Should raise 401 when no token in header or cookie"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = None

        mock_supabase = Mock()
        mock_logger = Mock()

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                token_from_header=None,
                supabase=mock_supabase,
                logger=mock_logger
            )

        # Assertions
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Should raise 401 when token is invalid"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = None

        mock_supabase = Mock()
        mock_supabase.auth.get_user.side_effect = Exception("Invalid token")

        mock_logger = Mock()

        token = "invalid_token"

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                token_from_header=token,
                supabase=mock_supabase,
                logger=mock_logger
            )

        # Assertions
        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_response_none_raises_401(self):
        """Should raise 401 when user_response is None"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = None

        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = None

        mock_logger = Mock()

        token = "valid_token"

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                token_from_header=token,
                supabase=mock_supabase,
                logger=mock_logger
            )

        # Assertions
        assert exc_info.value.status_code == 401
        # When user_response is None, accessing .user triggers exception -> goes to except block
        assert "Invalid authentication credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_response_user_none_raises_401(self):
        """Should raise 401 when user_response.user is None"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = None

        mock_supabase = Mock()
        mock_user_response = Mock()
        mock_user_response.user = None
        mock_supabase.auth.get_user.return_value = mock_user_response

        mock_logger = Mock()

        token = "valid_token"

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                token_from_header=token,
                supabase=mock_supabase,
                logger=mock_logger
            )

        # Assertions
        assert exc_info.value.status_code == 401
        # HTTPException raised in try block is caught by except block
        assert "Invalid authentication credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_header_token_preferred_over_cookie(self):
        """Should prefer header token when both header and cookie exist"""
        # Setup mocks
        mock_request = Mock()
        mock_request.cookies.get.return_value = "cookie_token"

        mock_supabase = Mock()
        mock_user = Mock()
        mock_user.id = "user-789"

        mock_user_response = Mock()
        mock_user_response.user = mock_user
        mock_supabase.auth.get_user.return_value = mock_user_response

        mock_logger = Mock()

        header_token = "header_token"

        # Call function
        result = await get_current_user(
            request=mock_request,
            token_from_header=header_token,
            supabase=mock_supabase,
            logger=mock_logger
        )

        # Assertions - should use header token, not cookie
        assert result == mock_user
        mock_supabase.auth.get_user.assert_called_once_with(header_token)
        # Cookie should not be accessed when header token exists
        mock_request.cookies.get.assert_not_called()


class TestGetCurrentSuperuser:
    """Test get_current_superuser function"""

    @pytest.mark.asyncio
    async def test_admin_user_returns_user(self):
        """Should return user when user has admin role"""
        # Setup mock user with admin role
        mock_user = Mock()
        mock_user.id = "admin-123"
        mock_user.user_metadata = {"role": "admin"}

        # Call function
        result = await get_current_superuser(current_user=mock_user)

        # Assertions
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_non_admin_user_raises_403(self):
        """Should raise 403 when user is not admin"""
        # Setup mock user without admin role
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.user_metadata = {"role": "user"}

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(current_user=mock_user)

        # Assertions
        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_without_metadata_raises_403(self):
        """Should raise 403 when user has no metadata"""
        # Setup mock user without metadata
        mock_user = Mock()
        mock_user.id = "user-456"
        mock_user.user_metadata = None

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(current_user=mock_user)

        # Assertions
        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_with_empty_metadata_raises_403(self):
        """Should raise 403 when user has empty metadata"""
        # Setup mock user with empty metadata
        mock_user = Mock()
        mock_user.id = "user-789"
        mock_user.user_metadata = {}

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(current_user=mock_user)

        # Assertions
        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_with_different_role_raises_403(self):
        """Should raise 403 when user has role other than admin"""
        # Setup mock user with moderator role
        mock_user = Mock()
        mock_user.id = "mod-123"
        mock_user.user_metadata = {"role": "moderator"}

        # Call function and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await get_current_superuser(current_user=mock_user)

        # Assertions
        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail
