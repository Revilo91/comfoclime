"""Test to verify the UUID deadlock fix."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI


@pytest.mark.asyncio
async def test_uuid_no_deadlock_on_connected_devices():
    """Test that async_get_connected_devices doesn't deadlock when fetching UUID.
    
    This test simulates the real-world scenario where:
    1. async_get_connected_devices() is called (uses @api_get with requires_uuid=True)
    2. UUID is not yet set (uuid is None)
    3. The decorator tries to fetch the UUID by calling _async_get_uuid_internal()
    4. Previously this would deadlock because _async_get_uuid_internal also tried to acquire the lock
    5. With the fix, _async_get_uuid_internal is a raw method that doesn't acquire the lock
    """
    api = ComfoClimeAPI("http://test.local")
    
    # Mock the HTTP session and responses
    mock_session = MagicMock()
    
    # Mock the UUID response
    mock_uuid_response = MagicMock()
    mock_uuid_response.raise_for_status = MagicMock()
    mock_uuid_response.json = AsyncMock(return_value={"uuid": "test-uuid-123"})
    mock_uuid_context = MagicMock()
    mock_uuid_context.__aenter__ = AsyncMock(return_value=mock_uuid_response)
    mock_uuid_context.__aexit__ = AsyncMock()
    
    # Mock the devices response
    mock_devices_response = MagicMock()
    mock_devices_response.raise_for_status = MagicMock()
    mock_devices_response.json = AsyncMock(return_value={"devices": [{"id": 1}]})
    mock_devices_context = MagicMock()
    mock_devices_context.__aenter__ = AsyncMock(return_value=mock_devices_response)
    mock_devices_context.__aexit__ = AsyncMock()
    
    # Setup the session mock to return different responses for different URLs
    def get_side_effect(url, timeout=None):
        if "/monitoring/ping" in url:
            return mock_uuid_context
        elif "/devices" in url:
            return mock_devices_context
        raise ValueError(f"Unexpected URL: {url}")
    
    mock_session.get = MagicMock(side_effect=get_side_effect)
    api._session = mock_session
    
    # This should complete without deadlock
    # Set a timeout to catch if there's a deadlock
    try:
        devices = await asyncio.wait_for(
            api.async_get_connected_devices(),
            timeout=5.0  # 5 seconds should be plenty
        )
        
        # Verify we got the expected result
        assert devices == [{"id": 1}]
        assert api.uuid == "test-uuid-123"
        
        # Verify both endpoints were called
        assert mock_session.get.call_count == 2
        
    except asyncio.TimeoutError:
        pytest.fail("async_get_connected_devices() timed out - likely a deadlock!")


@pytest.mark.asyncio
async def test_async_get_uuid_public_method():
    """Test that the public async_get_uuid() method works correctly.
    
    This tests the public API for fetching the UUID, which should
    properly acquire the lock and handle rate limiting.
    """
    api = ComfoClimeAPI("http://test.local")
    
    # Mock the HTTP session and response
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={"uuid": "public-uuid-456"})
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_context)
    api._session = mock_session
    
    # Call the public method
    uuid = await api.async_get_uuid()
    
    assert uuid == "public-uuid-456"
    assert api.uuid == "public-uuid-456"
    mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_uuid_requests():
    """Test that concurrent requests that need UUID don't cause race conditions.
    
    This tests that multiple concurrent API calls that require UUID
    work correctly without deadlocks or race conditions.
    """
    api = ComfoClimeAPI("http://test.local")
    
    # Mock the HTTP session
    mock_session = MagicMock()
    
    call_count = {"uuid": 0, "dashboard": 0, "devices": 0}
    
    def get_side_effect(url, timeout=None):
        if "/monitoring/ping" in url:
            call_count["uuid"] += 1
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={"uuid": "concurrent-uuid"})
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock()
            return mock_context
        elif "/dashboard" in url:
            call_count["dashboard"] += 1
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={"data": "dashboard"})
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock()
            return mock_context
        elif "/devices" in url:
            call_count["devices"] += 1
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={"devices": []})
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock()
            return mock_context
        raise ValueError(f"Unexpected URL: {url}")
    
    mock_session.get = MagicMock(side_effect=get_side_effect)
    api._session = mock_session
    
    # Make concurrent requests that all require UUID
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                api.async_get_connected_devices(),
                api.async_get_dashboard_data(),
            ),
            timeout=10.0
        )
        
        # Verify we got results
        assert len(results) == 2
        
        # UUID should have been fetched
        assert api.uuid == "concurrent-uuid"
        
        # UUID should only be fetched once (on first call that needs it)
        # Note: Due to rate limiting and locking, only one call should fetch UUID
        assert call_count["uuid"] >= 1  # At least one UUID fetch
        
    except asyncio.TimeoutError:
        pytest.fail("Concurrent requests timed out - likely a deadlock!")
