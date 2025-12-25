"""
Tests for Supabase client utilities
"""
import pytest
from unittest.mock import Mock
from fastapi import HTTPException
from database.supabase import (
    get_supabase_client,
    get_supabase_admin_client
)


class TestGetSupabaseClient:
    """Test get_supabase_client function"""

    def test_returns_client_when_exists(self):
        """Should return supabase_client from app state"""
        mock_request = Mock()
        mock_client = Mock()
        mock_request.app.state.supabase_client = mock_client

        result = get_supabase_client(mock_request)
        assert result == mock_client

    def test_raises_http_exception_when_client_is_none(self):
        """Should raise HTTPException when client is None"""
        mock_request = Mock()
        mock_request.app.state.supabase_client = None

        with pytest.raises(HTTPException) as exc_info:
            get_supabase_client(mock_request)
        assert exc_info.value.status_code == 500
        assert "not initialized" in exc_info.value.detail


class TestGetSupabaseAdminClient:
    """Test get_supabase_admin_client function"""

    def test_returns_client_when_exists(self):
        """Should return supabase_admin_client from app state"""
        mock_request = Mock()
        mock_client = Mock()
        mock_request.app.state.supabase_admin_client = mock_client

        result = get_supabase_admin_client(mock_request)
        assert result == mock_client
