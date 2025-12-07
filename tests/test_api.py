"""Tests for ComfoClime API."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI


class TestComfoClimeAPI:
    """Test ComfoClimeAPI class."""

    def test_api_initialization(self):
        """Test API initialization."""
        api = ComfoClimeAPI("http://192.168.1.100")

        assert api.base_url == "http://192.168.1.100"
        assert api.uuid is None

    def test_api_initialization_strips_trailing_slash(self):
        """Test API initialization strips trailing slash."""
        api = ComfoClimeAPI("http://192.168.1.100/")

        assert api.base_url == "http://192.168.1.100"

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_get_uuid(self, mock_get):
        """Test getting UUID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "test-uuid-123"}
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        uuid = api.get_uuid()

        assert uuid == "test-uuid-123"
        assert api.uuid == "test-uuid-123"
        mock_get.assert_called_once_with(
            "http://192.168.1.100/monitoring/ping", timeout=5
        )

    @pytest.mark.asyncio
    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    async def test_async_get_uuid(self, mock_get):
        """Test async getting UUID."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "test-uuid-456"}
        mock_get.return_value = mock_response

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda f: f())

        api = ComfoClimeAPI("http://192.168.1.100")
        uuid = await api.async_get_uuid(mock_hass)

        assert uuid == "test-uuid-456"

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_get_dashboard_data(self, mock_get):
        """Test getting dashboard data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "indoorTemperature": 22.5,
            "outdoorTemperature": 15.0,
            "fanSpeed": 2,
        }
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        data = api.get_dashboard_data()

        assert data["indoorTemperature"] == 22.5
        assert data["fanSpeed"] == 2
        mock_get.assert_called_once_with(
            "http://192.168.1.100/system/test-uuid/dashboard", timeout=5
        )

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_get_connected_devices(self, mock_get):
        """Test getting connected devices."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "devices": [
                {"uuid": "device-1", "modelTypeId": 20},
                {"uuid": "device-2", "modelTypeId": 21},
            ]
        }
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"
        devices = api.get_connected_devices()

        assert len(devices) == 2
        assert devices[0]["uuid"] == "device-1"
        mock_get.assert_called_once_with(
            "http://192.168.1.100/system/test-uuid/devices", timeout=5
        )

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_read_telemetry_1_byte_unsigned(self, mock_get):
        """Test reading 1-byte unsigned telemetry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [100]}
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        value = api.read_telemetry_for_device(
            "device-uuid", 123, faktor=1.0, signed=False, byte_count=1
        )

        assert value == 100

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_read_telemetry_1_byte_signed_positive(self, mock_get):
        """Test reading 1-byte signed telemetry (positive)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [50]}
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        value = api.read_telemetry_for_device(
            "device-uuid", 123, faktor=1.0, signed=True, byte_count=1
        )

        assert value == 50

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_read_telemetry_1_byte_signed_negative(self, mock_get):
        """Test reading 1-byte signed telemetry (negative)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [200]}  # > 0x80
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        value = api.read_telemetry_for_device(
            "device-uuid", 123, faktor=1.0, signed=True, byte_count=1
        )

        # 200 - 256 = -56
        assert value == -56

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_read_telemetry_2_byte_unsigned(self, mock_get):
        """Test reading 2-byte unsigned telemetry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [0x12, 0x34]}  # LSB, MSB
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        value = api.read_telemetry_for_device(
            "device-uuid", 123, faktor=1.0, signed=False, byte_count=2
        )

        # 0x12 + (0x34 << 8) = 18 + 13312 = 13330
        assert value == 13330

    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    def test_read_telemetry_with_factor(self, mock_get):
        """Test reading telemetry with factor."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [225]}
        mock_get.return_value = mock_response

        api = ComfoClimeAPI("http://192.168.1.100")
        value = api.read_telemetry_for_device(
            "device-uuid", 123, faktor=0.1, signed=False, byte_count=1
        )

        assert value == 22.5  # 225 * 0.1


class TestComfoClimeAPIReadProperty:
    """Test ComfoClimeAPI property reading."""

    @pytest.mark.asyncio
    @patch("custom_components.comfoclime.comfoclime_api.requests.get")
    async def test_async_read_property(self, mock_get):
        """Test async reading property."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [1]}
        mock_get.return_value = mock_response

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(
            side_effect=lambda f, *args: f(*args)
        )

        api = ComfoClimeAPI("http://192.168.1.100")
        value = await api.async_read_property_for_device(
            mock_hass, "device-uuid", "29/1/10", byte_count=1
        )

        assert value == 1


class TestComfoClimeAPIWriteOperations:
    """Test ComfoClimeAPI write operations."""

    @pytest.mark.skip(reason="Requires mocking network socket calls")
    @pytest.mark.asyncio
    @patch("custom_components.comfoclime.comfoclime_api.requests.post")
    async def test_async_update_dashboard(self, mock_post):
        """Test async updating dashboard."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(
            side_effect=lambda f, *args, **kwargs: f(*args, **kwargs)
        )

        api = ComfoClimeAPI("http://192.168.1.100")
        api.uuid = "test-uuid"

        await api.async_update_dashboard(mock_hass, fan_speed=3, hp_standby=False)

        assert mock_post.called
