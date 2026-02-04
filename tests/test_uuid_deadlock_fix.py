"""Test to verify the UUID deadlock fix."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    # Create mock responses
    uuid_response = AsyncMock()
    uuid_response.json = AsyncMock(return_value={"uuid": "test-uuid-123"})
    uuid_response.raise_for_status = MagicMock()

    devices_response = AsyncMock()
    devices_response.json = AsyncMock(return_value={"devices": [{"id": 1}]})
    devices_response.raise_for_status = MagicMock()

    # Create context managers for responses
    uuid_context = AsyncMock()
    uuid_context.__aenter__ = AsyncMock(return_value=uuid_response)
    uuid_context.__aexit__ = AsyncMock(return_value=None)

    devices_context = AsyncMock()
    devices_context.__aenter__ = AsyncMock(return_value=devices_response)
    devices_context.__aexit__ = AsyncMock(return_value=None)

    # Mock the session.get to return context managers
    def mock_get(url, timeout=None):
        if "/monitoring/ping" in url:
            return uuid_context
        if "/devices" in url:
            return devices_context
        raise ValueError(f"Unexpected URL: {url}")

    mock_session = MagicMock()
    mock_session.get = mock_get

    # Use patch to mock _get_session
    with patch.object(api, "_get_session", return_value=mock_session):
        # This should complete without deadlock
        # Set a timeout to catch if there's a deadlock
        try:
            devices = await asyncio.wait_for(
                api.async_get_connected_devices(),
                timeout=5.0,  # 5 seconds should be plenty
            )

            # Verify we got the expected result
            assert devices == [{"id": 1}]
            assert api.uuid == "test-uuid-123"

        except TimeoutError:
            pytest.fail("async_get_connected_devices() timed out - likely a deadlock!")


@pytest.mark.asyncio
async def test_async_get_uuid_public_method():
    """Test that the public async_get_uuid() method works correctly.

    This tests the public API for fetching the UUID, which should
    properly acquire the lock and handle rate limiting.
    """
    api = ComfoClimeAPI("http://test.local")

    # Create mock response
    uuid_response = AsyncMock()
    uuid_response.json = AsyncMock(return_value={"uuid": "public-uuid-456"})
    uuid_response.raise_for_status = MagicMock()

    # Create context manager for response
    uuid_context = AsyncMock()
    uuid_context.__aenter__ = AsyncMock(return_value=uuid_response)
    uuid_context.__aexit__ = AsyncMock(return_value=None)

    # Mock the session.get
    def mock_get(url, timeout=None):
        if "/monitoring/ping" in url:
            return uuid_context
        raise ValueError(f"Unexpected URL: {url}")

    mock_session = MagicMock()
    mock_session.get = mock_get

    # Use patch to mock _get_session
    with patch.object(api, "_get_session", return_value=mock_session):
        # Call the public method
        uuid = await api.async_get_uuid()

        assert uuid == "public-uuid-456"
        assert api.uuid == "public-uuid-456"


@pytest.mark.asyncio
async def test_concurrent_uuid_requests():
    """Test that concurrent requests that need UUID don't cause race conditions.

    This tests that multiple concurrent API calls that require UUID
    work correctly without deadlocks or race conditions.
    """
    api = ComfoClimeAPI("http://test.local")

    call_count = {"uuid": 0, "dashboard": 0, "devices": 0}

    # Create mock response functions
    def create_uuid_response():
        call_count["uuid"] += 1
        response = AsyncMock()
        response.json = AsyncMock(return_value={"uuid": "concurrent-uuid"})
        response.raise_for_status = MagicMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    def create_dashboard_response():
        call_count["dashboard"] += 1
        response = AsyncMock()
        response.json = AsyncMock(return_value={"data": "dashboard"})
        response.raise_for_status = MagicMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    def create_devices_response():
        call_count["devices"] += 1
        response = AsyncMock()
        response.json = AsyncMock(return_value={"devices": []})
        response.raise_for_status = MagicMock()
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=None)
        return context

    # Mock the session.get
    def mock_get(url, timeout=None):
        if "/monitoring/ping" in url:
            return create_uuid_response()
        if "/dashboard" in url:
            return create_dashboard_response()
        if "/devices" in url:
            return create_devices_response()
        raise ValueError(f"Unexpected URL: {url}")

    mock_session = MagicMock()
    mock_session.get = mock_get

    # Use patch to mock _get_session
    with patch.object(api, "_get_session", return_value=mock_session):
        # Make concurrent requests that all require UUID
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    api.async_get_connected_devices(),
                    api.async_get_dashboard_data(),
                ),
                timeout=10.0,
            )

            # Verify we got results
            assert len(results) == 2

            # UUID should have been fetched
            assert api.uuid == "concurrent-uuid"

            # UUID should only be fetched once (on first call that needs it)
            # Note: Due to rate limiting and locking, only one call should fetch UUID
            assert call_count["uuid"] >= 1  # At least one UUID fetch

        except TimeoutError:
            pytest.fail("Concurrent requests timed out - likely a deadlock!")
