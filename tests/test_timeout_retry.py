"""Tests for timeout and retry handling in ComfoClime API."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.comfoclime.comfoclime_api import (
    ComfoClimeAPI,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_WRITE_TIMEOUT,
    MAX_RETRIES,
)


class TestTimeoutConfiguration:
    """Test timeout configuration."""

    def test_timeout_constants_defined(self):
        """Test that timeout constants are properly defined."""
        assert DEFAULT_READ_TIMEOUT == 10
        assert DEFAULT_WRITE_TIMEOUT == 15
        assert MAX_RETRIES == 2

    @pytest.mark.asyncio
    async def test_get_session_creates_session_with_default_timeout(self):
        """Test that _get_session creates session with default timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")
        
        session = await api._get_session()
        
        # Session should be created
        assert session is not None
        assert not session.closed
        
        # Clean up
        await api.close()

    @pytest.mark.asyncio
    async def test_get_session_with_custom_timeout(self):
        """Test that _get_session accepts custom timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")
        
        session = await api._get_session(timeout_seconds=30)
        
        # Session should be created
        assert session is not None
        assert not session.closed
        
        # Clean up
        await api.close()


class TestDashboardUpdateRetry:
    """Test retry logic for dashboard updates."""

    @pytest.mark.asyncio
    async def test_dashboard_update_succeeds_first_try(self):
        """Test dashboard update succeeds on first attempt."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            result = await api.async_update_dashboard(set_point_temperature=22.0)

        assert result == {"status": "ok"}
        # Should only be called once (no retries needed)
        assert mock_session.put.call_count == 1

    @pytest.mark.asyncio
    async def test_dashboard_update_retries_on_timeout(self):
        """Test dashboard update retries on timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # First call times out, second succeeds
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        success_response = AsyncMock()
        success_response.json = AsyncMock(return_value={"status": "ok"})
        success_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            side_effect=[
                timeout_response,
                AsyncMock(__aenter__=AsyncMock(return_value=success_response)),
            ]
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            result = await api.async_update_dashboard(set_point_temperature=22.0)

        assert result == {"status": "ok"}
        # Should be called twice (1 failure + 1 success)
        assert mock_session.put.call_count == 2

    @pytest.mark.asyncio
    async def test_dashboard_update_fails_after_max_retries(self):
        """Test dashboard update fails after exhausting retries."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # All calls timeout
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_session = AsyncMock()
        mock_session.put = MagicMock(return_value=timeout_response)

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            with pytest.raises(asyncio.TimeoutError):
                await api.async_update_dashboard(set_point_temperature=22.0)

        # Should be called MAX_RETRIES + 1 times (3 total: initial + 2 retries)
        assert mock_session.put.call_count == MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_dashboard_update_retries_on_client_error(self):
        """Test dashboard update retries on client errors."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # First call has network error, second succeeds
        error_response = AsyncMock()
        error_response.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectionError()
        )

        success_response = AsyncMock()
        success_response.json = AsyncMock(return_value={"status": "ok"})
        success_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            side_effect=[
                error_response,
                AsyncMock(__aenter__=AsyncMock(return_value=success_response)),
            ]
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            result = await api.async_update_dashboard(set_point_temperature=22.0)

        assert result == {"status": "ok"}
        # Should be called twice (1 failure + 1 success)
        assert mock_session.put.call_count == 2


class TestThermalProfileUpdateRetry:
    """Test retry logic for thermal profile updates."""

    @pytest.mark.asyncio
    async def test_thermal_profile_update_retries_on_timeout(self):
        """Test thermal profile update retries on timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        # First call times out, second succeeds
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        success_response = AsyncMock()
        success_response.status = 200
        success_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            side_effect=[
                timeout_response,
                AsyncMock(__aenter__=AsyncMock(return_value=success_response)),
            ]
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            result = await api.async_update_thermal_profile(season_value=1)

        assert result is True
        # Should be called twice (1 failure + 1 success)
        assert mock_session.put.call_count == 2


class TestPropertySetRetry:
    """Test retry logic for property set operations."""

    @pytest.mark.asyncio
    async def test_property_set_retries_on_timeout(self):
        """Test property set retries on timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")

        # First call times out, second succeeds
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        success_response = AsyncMock()
        success_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            side_effect=[
                timeout_response,
                AsyncMock(__aenter__=AsyncMock(return_value=success_response)),
            ]
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            await api.async_set_property_for_device(
                device_uuid="device-123",
                property_path="29/1/10",
                value=1,
                byte_count=1,
                signed=False,
            )

        # Should be called twice (1 failure + 1 success)
        assert mock_session.put.call_count == 2

    @pytest.mark.asyncio
    async def test_property_set_fails_after_max_retries(self):
        """Test property set fails after exhausting retries."""
        api = ComfoClimeAPI("http://192.168.1.100")

        # All calls timeout
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_session = AsyncMock()
        mock_session.put = MagicMock(return_value=timeout_response)

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            with pytest.raises(asyncio.TimeoutError):
                await api.async_set_property_for_device(
                    device_uuid="device-123",
                    property_path="29/1/10",
                    value=1,
                    byte_count=1,
                    signed=False,
                )

        # Should be called MAX_RETRIES + 1 times (3 total: initial + 2 retries)
        assert mock_session.put.call_count == MAX_RETRIES + 1
