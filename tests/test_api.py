"""Tests for ComfoClime API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI


class TestComfoClimeAPI:
    """Test ComfoClimeAPI class."""

    def test_api_initialization(self):
        """Test API initialization."""
        api = ComfoClimeAPI("http://192.168.1.100")

        assert api.base_url == "http://192.168.1.100"
        assert api.uuid is None
        assert api._last_request_time == 0.0
        assert api._last_write_time == 0.0
        assert api.read_timeout == 10  # Default value
        assert api.write_timeout == 30  # Default value
        assert api.cache_ttl == 30.0  # Default value
        assert api.max_retries == 3  # Default value
        assert api.min_request_interval == 0.1  # Default value
        assert api.write_cooldown == 2.0  # Default value
        assert api.request_debounce == 0.3  # Default value

    def test_api_initialization_with_custom_timeouts(self):
        """Test API initialization with custom timeout values."""
        api = ComfoClimeAPI(
            "http://192.168.1.100",
            read_timeout=20,
            write_timeout=60,
            cache_ttl=45,
            max_retries=5,
            min_request_interval=0.2,
            write_cooldown=3.0,
            request_debounce=0.5,
        )

        assert api.base_url == "http://192.168.1.100"
        assert api.read_timeout == 20
        assert api.write_timeout == 60
        assert api.cache_ttl == 45
        assert api.max_retries == 5
        assert api.min_request_interval == 0.2
        assert api.write_cooldown == 3.0
        assert api.request_debounce == 0.5

    def test_api_initialization_strips_trailing_slash(self):
        """Test API initialization strips trailing slash."""
        api = ComfoClimeAPI("http://192.168.1.100/")

        assert api.base_url == "http://192.168.1.100"

    @pytest.mark.asyncio
    async def test_async_get_uuid(self):
        """Test async getting UUID."""
        api = ComfoClimeAPI("http://192.168.1.100")

        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"uuid": "test-uuid-456"})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            uuid = await api.async_get_uuid()

        assert uuid == "test-uuid-456"
        assert api.uuid == "test-uuid-456"

    @pytest.mark.asyncio
    async def test_async_get_dashboard_data(self):
        """Test async getting dashboard data."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "indoorTemperature": 22.5,
                "outdoorTemperature": 15.0,
                "fanSpeed": 2,
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            data = await api.async_get_dashboard_data()

        assert data["indoorTemperature"] == 22.5
        assert data["fanSpeed"] == 2

    @pytest.mark.asyncio
    async def test_async_get_connected_devices(self):
        """Test async getting connected devices."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "devices": [
                    {"uuid": "device-1", "modelTypeId": 20},
                    {"uuid": "device-2", "modelTypeId": 21},
                ]
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            devices = await api.async_get_connected_devices()

        assert len(devices) == 2
        assert devices[0]["uuid"] == "device-1"

    @pytest.mark.asyncio
    async def test_async_get_device_definition(self):
        """Test async getting device definition."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "deviceType": "ComfoAirQ",
                "modelTypeId": 1,
                "firmwareVersion": "1.2.3",
                "serialNumber": "SIT14276877",
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            definition = await api.async_get_device_definition("SIT14276877")

        assert definition["deviceType"] == "ComfoAirQ"
        assert definition["modelTypeId"] == 1

    @pytest.mark.asyncio
    async def test_async_read_telemetry_1_byte_unsigned(self):
        """Test reading 1-byte unsigned telemetry."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [100]})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_telemetry_for_device(
                "device-uuid", "123", faktor=1.0, signed=False, byte_count=1
            )

        assert value == 100

    @pytest.mark.asyncio
    async def test_async_read_telemetry_1_byte_signed_positive(self):
        """Test reading 1-byte signed telemetry (positive)."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [50]})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_telemetry_for_device(
                "device-uuid", "123", faktor=1.0, signed=True, byte_count=1
            )

        assert value == 50

    @pytest.mark.asyncio
    async def test_async_read_telemetry_1_byte_signed_negative(self):
        """Test reading 1-byte signed telemetry (negative)."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [200]})  # > 0x80
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_telemetry_for_device(
                "device-uuid", "123", faktor=1.0, signed=True, byte_count=1
            )

        # 200 - 256 = -56
        assert value == -56

    @pytest.mark.asyncio
    async def test_async_read_telemetry_2_byte_unsigned(self):
        """Test reading 2-byte unsigned telemetry."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [0x12, 0x34]})  # LSB, MSB
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_telemetry_for_device(
                "device-uuid", "123", faktor=1.0, signed=False, byte_count=2
            )

        # 0x12 + (0x34 << 8) = 18 + 13312 = 13330
        assert value == 13330

    @pytest.mark.asyncio
    async def test_async_read_telemetry_with_factor(self):
        """Test reading telemetry with factor."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [225]})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_telemetry_for_device(
                "device-uuid", "123", faktor=0.1, signed=False, byte_count=1
            )

        assert value == 22.5  # 225 * 0.1


class TestComfoClimeAPIReadProperty:
    """Test ComfoClimeAPI property reading."""

    @pytest.mark.asyncio
    async def test_async_read_property(self):
        """Test async reading property."""
        api = ComfoClimeAPI("http://192.168.1.100")

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"data": [1]})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            value = await api.async_read_property_for_device(
                "device-uuid", "29/1/10", byte_count=1
            )

        assert value == 1


class TestComfoClimeAPIWriteOperations:
    """Test ComfoClimeAPI write operations."""

    @pytest.mark.asyncio
    async def test_async_update_dashboard(self):
        """Test async updating dashboard."""
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
            result = await api.async_update_dashboard(fan_speed=3)

        assert result == {"status": "ok"}


class TestComfoClimeAPIRateLimiting:
    """Test ComfoClimeAPI rate limiting functionality."""

    def test_rate_limit_constants(self):
        """Test that rate limiting constants are defined."""
        from custom_components.comfoclime.comfoclime_api import (
            MIN_REQUEST_INTERVAL,
            REQUEST_DEBOUNCE,
            WRITE_COOLDOWN,
        )

        assert MIN_REQUEST_INTERVAL == 0.1
        assert WRITE_COOLDOWN == 2.0
        assert REQUEST_DEBOUNCE == 0.3

    @pytest.mark.asyncio
    async def test_rate_limit_updates_last_request_time(self):
        """Test that rate limiting updates last request time."""
        api = ComfoClimeAPI("http://192.168.1.100")

        # Initial state
        assert api._last_request_time == 0.0

        # Mock session to avoid actual HTTP calls
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"uuid": "test"})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            await api.async_get_uuid()

        # After request, last_request_time should be updated
        assert api._last_request_time > 0.0

    @pytest.mark.asyncio
    async def test_write_operation_updates_write_time(self):
        """Test that write operations update last write time."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        api.hass = MagicMock()
        api.hass.config.time_zone = "Europe/Berlin"

        # Initial state
        assert api._last_write_time == 0.0

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.put = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            await api.async_update_dashboard(fan_speed=2)

        # After write, last_write_time should be updated
        assert api._last_write_time > 0.0


class TestComfoClimeAPIByteConversion:
    """Test byte conversion utility methods."""

    def test_bytes_to_signed_int_1_byte_positive(self):
        """Test 1-byte positive conversion."""
        result = ComfoClimeAPI.bytes_to_signed_int([50], byte_count=1, signed=True)
        assert result == 50

    def test_bytes_to_signed_int_1_byte_negative(self):
        """Test 1-byte negative conversion."""
        result = ComfoClimeAPI.bytes_to_signed_int([200], byte_count=1, signed=True)
        assert result == -56

    def test_bytes_to_signed_int_2_byte_little_endian(self):
        """Test 2-byte little-endian conversion."""
        result = ComfoClimeAPI.bytes_to_signed_int(
            [0x12, 0x34], byte_count=2, signed=False
        )
        assert result == 13330

    def test_signed_int_to_bytes_1_byte(self):
        """Test converting int to 1 byte."""
        result = ComfoClimeAPI.signed_int_to_bytes(100, byte_count=1, signed=False)
        assert result == [100]

    def test_signed_int_to_bytes_2_byte(self):
        """Test converting int to 2 bytes."""
        result = ComfoClimeAPI.signed_int_to_bytes(13330, byte_count=2, signed=False)
        assert result == [0x12, 0x34]

    def test_bytes_to_signed_int_invalid_data(self):
        """Test that non-list data raises ValueError."""
        with pytest.raises(ValueError, match="'data' is not a list"):
            ComfoClimeAPI.bytes_to_signed_int("not a list", byte_count=1)

    def test_bytes_to_signed_int_invalid_byte_count(self):
        """Test that invalid byte count raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported byte count"):
            ComfoClimeAPI.bytes_to_signed_int([1, 2, 3], byte_count=3)


class TestComfoClimeAPIFixSignedTemperature:
    """Test fix_signed_temperature utility method."""

    def test_fix_signed_temperature_positive_value(self):
        """Test that positive temperature values pass through unchanged."""
        result = ComfoClimeAPI.fix_signed_temperature(22.5)
        assert result == 22.5

    def test_fix_signed_temperature_zero(self):
        """Test that zero passes through unchanged."""
        result = ComfoClimeAPI.fix_signed_temperature(0.0)
        assert result == 0.0

    def test_fix_signed_temperature_negative_as_unsigned(self):
        """Test that unsigned representation of negative temperature is fixed.

        Conversion for -0.5°C:
        - Temperature: -0.5°C
        - Raw value (scaled by 10): -5
        - As signed int16: -5 = 0xFFFB in little endian = [251, 255]
        - As unsigned int16: 65531
        - API returns: 65531 / 10 = 6553.1
        - fix_signed_temperature(6553.1) should return -0.5
        """
        result = ComfoClimeAPI.fix_signed_temperature(6553.1)
        assert result == -0.5

    def test_fix_signed_temperature_large_negative(self):
        """Test fixing a larger negative temperature like -10.0°C.

        -100 as signed int16 = 65436 as unsigned = 6543.6 when divided by 10
        """
        result = ComfoClimeAPI.fix_signed_temperature(6543.6)
        assert result == -10.0


class TestComfoClimeAPIDashboardSignedTemperatures:
    """Test that async_get_dashboard_data fixes signed temperatures."""

    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_fixes_temperature_values(self):
        """Test that temperature values in dashboard data are fixed for signed interpretation."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        # Simulate API returning unsigned representation of negative temperature
        # outdoorTemperature: 6553.1 represents -0.5°C
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "indoorTemperature": 22.5,
                "outdoorTemperature": 6553.1,  # This should become -0.5
                "fanSpeed": 2,
                "season": 1,
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            data = await api.async_get_dashboard_data()

        # Temperature values should be fixed
        assert data["indoorTemperature"] == 22.5  # Positive stays same
        assert data["outdoorTemperature"] == -0.5  # Converted from unsigned
        # Non-temperature values should be unchanged
        assert data["fanSpeed"] == 2
        assert data["season"] == 1

    @pytest.mark.asyncio
    async def test_async_get_dashboard_data_handles_none_temperature(self):
        """Test that None temperature values are handled gracefully."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "indoorTemperature": 22.5,
                "outdoorTemperature": None,  # None should be skipped
                "setPointTemperature": None,  # Also None
                "fanSpeed": 2,
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            data = await api.async_get_dashboard_data()

        assert data["indoorTemperature"] == 22.5
        assert data["outdoorTemperature"] is None  # None stays None
        assert data["setPointTemperature"] is None
        assert data["fanSpeed"] == 2


class TestComfoClimeAPIFixSignedTemperaturesInDict:
    """Test fix_signed_temperatures_in_dict utility method."""

    def test_fix_signed_temperatures_flat_dict(self):
        """Test fixing temperatures in a flat dictionary."""
        data = {
            "indoorTemperature": 22.5,
            "outdoorTemperature": 6553.1,  # -0.5°C as unsigned
            "fanSpeed": 2,
        }
        result = ComfoClimeAPI.fix_signed_temperatures_in_dict(data)
        assert result["indoorTemperature"] == 22.5
        assert result["outdoorTemperature"] == -0.5
        assert result["fanSpeed"] == 2

    def test_fix_signed_temperatures_nested_dict(self):
        """Test fixing temperatures in a nested dictionary (like thermal profile)."""
        data = {
            "season": {
                "status": 1,
                "heatingThresholdTemperature": 14.0,
                "coolingThresholdTemperature": 17.0,
            },
            "temperature": {
                "status": 0,
                "manualTemperature": 6553.1,  # -0.5°C as unsigned
            },
            "heatingThermalProfileSeasonData": {
                "comfortTemperature": 21.5,
                "kneePointTemperature": 12.5,
            },
        }
        result = ComfoClimeAPI.fix_signed_temperatures_in_dict(data)

        # Check nested temperature values are fixed
        assert result["season"]["heatingThresholdTemperature"] == 14.0
        assert result["season"]["coolingThresholdTemperature"] == 17.0
        assert result["temperature"]["manualTemperature"] == -0.5
        assert result["heatingThermalProfileSeasonData"]["comfortTemperature"] == 21.5
        assert result["heatingThermalProfileSeasonData"]["kneePointTemperature"] == 12.5
        # Check non-temperature values unchanged
        assert result["season"]["status"] == 1
        assert result["temperature"]["status"] == 0

    def test_fix_signed_temperatures_with_none_values(self):
        """Test that None values are handled gracefully in nested dicts."""
        data = {
            "temperature": {
                "manualTemperature": None,
            },
            "setPointTemperature": None,
        }
        result = ComfoClimeAPI.fix_signed_temperatures_in_dict(data)
        assert result["temperature"]["manualTemperature"] is None
        assert result["setPointTemperature"] is None


class TestComfoClimeAPIThermalProfileSignedTemperatures:
    """Test that async_get_thermal_profile fixes signed temperatures."""

    @pytest.mark.asyncio
    async def test_async_get_thermal_profile_fixes_temperature_values(self):
        """Test that temperature values in thermal profile data are fixed."""
        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        # Simulate API returning unsigned representation of negative temperature
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "season": {
                    "status": 1,
                    "season": 2,
                    "heatingThresholdTemperature": 14.0,
                    "coolingThresholdTemperature": 6553.1,  # -0.5°C as unsigned
                },
                "temperature": {
                    "status": 1,
                    "manualTemperature": 22.0,
                },
                "temperatureProfile": 0,
                "heatingThermalProfileSeasonData": {
                    "comfortTemperature": 21.5,
                    "kneePointTemperature": 12.5,
                    "reductionDeltaTemperature": 1.5,
                },
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch.object(api, "_get_session", AsyncMock(return_value=mock_session)):
            data = await api.async_get_thermal_profile()

        # Temperature values should be fixed
        assert data["season"]["heatingThresholdTemperature"] == 14.0
        assert data["season"]["coolingThresholdTemperature"] == -0.5  # Fixed from unsigned
        assert data["temperature"]["manualTemperature"] == 22.0
        assert data["heatingThermalProfileSeasonData"]["comfortTemperature"] == 21.5
        # Non-temperature values should be unchanged
        assert data["season"]["status"] == 1
        assert data["temperatureProfile"] == 0
