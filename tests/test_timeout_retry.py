"""Tests for timeout and retry handling in ComfoClime API."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
from custom_components.comfoclime.constants import API_DEFAULTS


class TestTimeoutConfiguration:
    """Test timeout configuration."""

    def test_timeout_constants_defined(self):
        """Test that timeout constants are properly defined."""
        assert API_DEFAULTS.READ_TIMEOUT == 10
        assert API_DEFAULTS.WRITE_TIMEOUT == 30
        assert API_DEFAULTS.MAX_RETRIES == 3


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
        mock_session.put = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

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
        timeout_response.__aenter__ = AsyncMock(side_effect=TimeoutError())

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
        timeout_response.__aenter__ = AsyncMock(side_effect=TimeoutError())

        mock_session = AsyncMock()
        mock_session.put = MagicMock(return_value=timeout_response)

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            with pytest.raises(asyncio.TimeoutError):
                await api.async_update_dashboard(set_point_temperature=22.0)

        # Should be called API_DEFAULTS.MAX_RETRIES + 1 times (4 total: initial + 3 retries)
        assert mock_session.put.call_count == API_DEFAULTS.MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_dashboard_update_retries_on_client_error(self):
        """Test dashboard update retries on client errors."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # First call has network error, second succeeds
        error_response = AsyncMock()
        error_response.__aenter__ = AsyncMock(side_effect=aiohttp.ClientConnectionError())

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

    @pytest.mark.asyncio
    async def test_dashboard_update_propagates_cancelled_error(self):
        """Test dashboard update propagates CancelledError immediately without retry.

        CancelledError indicates the operation was cancelled (e.g., by Home Assistant
        during setup timeout) and should not be retried.
        """
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # Call gets cancelled
        cancelled_response = AsyncMock()
        cancelled_response.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError())

        mock_session = AsyncMock()
        mock_session.put = MagicMock(return_value=cancelled_response)

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            with pytest.raises(asyncio.CancelledError):
                await api.async_update_dashboard(set_point_temperature=22.0)

        # Should only be called once (no retries on CancelledError)
        assert mock_session.put.call_count == 1


class TestThermalProfileUpdateRetry:
    """Test retry logic for thermal profile updates."""

    @pytest.mark.asyncio
    async def test_thermal_profile_update_retries_on_timeout(self):
        """Test thermal profile update retries on timeout."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        # First call times out, second succeeds
        timeout_response = AsyncMock()
        timeout_response.__aenter__ = AsyncMock(side_effect=TimeoutError())

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
        timeout_response.__aenter__ = AsyncMock(side_effect=TimeoutError())

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
        timeout_response.__aenter__ = AsyncMock(side_effect=TimeoutError())

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

        # Should be called API_DEFAULTS.MAX_RETRIES + 1 times (4 total: initial + 3 retries)
        assert mock_session.put.call_count == API_DEFAULTS.MAX_RETRIES + 1


class TestCancelledErrorPropagation:
    """Test that CancelledError is properly propagated and not retried."""

    @pytest.mark.asyncio
    async def test_rate_limiter_propagates_cancelled_error(self):
        """Test that CancelledError from asyncio.sleep in rate limiter is propagated."""
        from custom_components.comfoclime.rate_limiter_cache import RateLimiterCache

        rate_limiter = RateLimiterCache(
            min_request_interval=1.0,  # Set a long interval to force sleep
            write_cooldown=2.0,
            request_debounce=0.3,
            cache_ttl=30.0,
        )

        # Trigger a rate limit by making a first "request"
        rate_limiter._last_request_time = rate_limiter._get_current_time()

        async def test_wait():
            # This should sleep for 1 second due to min_request_interval
            await rate_limiter.wait_for_rate_limit(is_write=False)

        # Create a task and cancel it while it's sleeping
        task = asyncio.create_task(test_wait())
        await asyncio.sleep(0.1)  # Give it time to start sleeping
        task.cancel()

        # The task should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_yield_to_writes_propagates_cancelled_error(self):
        """Test that CancelledError from asyncio.sleep in yield_to_writes is propagated."""
        from custom_components.comfoclime.rate_limiter_cache import RateLimiterCache

        rate_limiter = RateLimiterCache()

        # Signal a pending write to force yield_to_writes to sleep
        rate_limiter.signal_write_pending()

        async def test_yield():
            await rate_limiter.yield_to_writes()

        # Create a task and cancel it while it's sleeping
        task = asyncio.create_task(test_yield())
        await asyncio.sleep(0.05)  # Give it time to start sleeping
        task.cancel()

        # The task should raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_api_get_propagates_cancelled_error_from_rate_limiter(self):
        """Test that CancelledError from rate limiter is propagated through api_get decorator."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        # Trigger rate limiting by setting last request time very recently
        api._rate_limiter._last_request_time = api._rate_limiter._get_current_time()
        api._rate_limiter.min_request_interval = 1.0  # Force a long wait

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            # Create task and cancel it while waiting for rate limit
            task = asyncio.create_task(api.async_get_dashboard_data())
            await asyncio.sleep(0.1)  # Give it time to start waiting
            task.cancel()

            # Should propagate CancelledError
            with pytest.raises(asyncio.CancelledError):
                await task
