#!/usr/bin/env python3
"""Quick test to verify the caching implementation."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

# Add the project to path
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
from custom_components.comfoclime.sensor import (
    ComfoClimeTelemetrySensor,
)


def test_cache_initialization():
    """Test that cache is properly initialized."""
    api = ComfoClimeAPI("http://test")
    assert isinstance(api._telemetry_cache, dict)
    assert isinstance(api._property_cache, dict)
    assert len(api._telemetry_cache) == 0
    assert len(api._property_cache) == 0
    print("✅ Cache initialization test passed")


def test_cache_key_generation():
    """Test cache key generation."""
    api = ComfoClimeAPI("http://test")
    key = api._get_cache_key("device-123", "telemetry-456")
    assert key == "device-123:telemetry-456"
    print("✅ Cache key generation test passed")


def test_cache_ttl_constant():
    """Test that cache TTL is properly configured."""
    from custom_components.comfoclime.comfoclime_api import CACHE_TTL

    assert CACHE_TTL == 30.0, f"Expected CACHE_TTL=30.0, got {CACHE_TTL}"
    print("✅ Cache TTL constant test passed")


async def test_telemetry_cache():
    """Test telemetry caching."""
    api = AsyncMock(spec=ComfoClimeAPI)
    api.base_url = "http://test"
    api.uuid = "test-uuid"
    api._telemetry_cache = {}
    api._property_cache = {}
    api._request_lock = asyncio.Lock()

    # Create a real API instance for testing
    api = ComfoClimeAPI("http://test")
    api.uuid = "test-uuid"

    # Mock the session
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"data": [100]})
    mock_response.raise_for_status = MagicMock()

    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
    )

    # Patch _get_session
    api._get_session = AsyncMock(return_value=mock_session)

    # First call should hit API
    result1 = await api.async_read_telemetry_for_device(
        device_uuid="device-1",
        telemetry_id="123",
        faktor=1.0,
        signed=False,
        byte_count=1,
    )
    assert result1 == 100
    assert mock_session.get.call_count == 1
    print("✅ First telemetry call hit API")

    # Second call should use cache
    result2 = await api.async_read_telemetry_for_device(
        device_uuid="device-1",
        telemetry_id="123",
        faktor=1.0,
        signed=False,
        byte_count=1,
    )
    assert result2 == 100
    assert mock_session.get.call_count == 1, "Cache hit - no additional API call"
    print("✅ Second telemetry call used cache")


async def test_property_cache():
    """Test property caching."""
    api = ComfoClimeAPI("http://test")
    api.uuid = "test-uuid"

    # Mock the session and _read_property_for_device_raw
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"data": [75]})
    mock_response.raise_for_status = MagicMock()

    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
    )

    api._get_session = AsyncMock(return_value=mock_session)
    api._read_property_for_device_raw = AsyncMock(return_value=[75])

    # First call should hit API
    result1 = await api.async_read_property_for_device(
        device_uuid="device-1", property_path="29/1/10", byte_count=1
    )
    assert result1 == 75
    assert api._read_property_for_device_raw.call_count == 1
    print("✅ First property call hit API")

    # Second call should use cache
    result2 = await api.async_read_property_for_device(
        device_uuid="device-1", property_path="29/1/10", byte_count=1
    )
    assert result2 == 75
    assert api._read_property_for_device_raw.call_count == 1, (
        "Cache hit - no additional API call"
    )
    print("✅ Second property call used cache")


async def test_cache_invalidation():
    """Test that cache is invalidated for a device."""
    api = ComfoClimeAPI("http://test")

    # Manually add some cache entries
    api._set_cache(api._telemetry_cache, "device-1:telemetry-1", 100)
    api._set_cache(api._telemetry_cache, "device-1:telemetry-2", 200)
    api._set_cache(api._telemetry_cache, "device-2:telemetry-1", 300)

    assert len(api._telemetry_cache) == 3

    # Invalidate cache for device-1
    api._invalidate_cache_for_device("device-1")

    # Should have removed device-1 entries
    assert len(api._telemetry_cache) == 1
    assert "device-2:telemetry-1" in str(api._telemetry_cache)
    print("✅ Cache invalidation test passed")


def test_sensor_with_caching():
    """Test that sensor uses coordinator with caching."""
    mock_coordinator = MagicMock()
    mock_coordinator.get_telemetry_value = MagicMock(return_value=25.5)
    mock_device = {"uuid": "test-uuid", "displayName": "Test Device"}
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"

    sensor = ComfoClimeTelemetrySensor(
        hass=MagicMock(),
        coordinator=mock_coordinator,
        telemetry_id=123,
        name="Test Sensor",
        translation_key="test_sensor",
        unit="°C",
        device=mock_device,
        override_device_uuid="test-uuid",
        entry=mock_entry,
    )

    # Verify sensor was initialized
    assert sensor._id == "123"
    print("✅ Sensor initialization with coordinator test passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Caching Implementation")
    print("=" * 60)

    # Synchronous tests
    test_cache_initialization()
    test_cache_key_generation()
    test_cache_ttl_constant()
    test_sensor_with_caching()

    # Async tests
    await test_telemetry_cache()
    await test_property_cache()
    await test_cache_invalidation()

    print("=" * 60)
    print("✅ All caching tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
