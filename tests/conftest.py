"""Common fixtures for ComfoClime tests."""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@dataclass
class MockAPIResponses:
    """Configurable responses for API mock."""

    uuid: str = "test-uuid-12345"
    dashboard_data: dict[str, Any] = field(
        default_factory=lambda: {
            "indoorTemperature": 22.5,
            "outdoorTemperature": 15.0,
            "fanSpeed": 2,
            "season": 1,
            "temperatureProfile": 0,
            "heatPumpStatus": 3,
            "hpStandby": False,
            "exhaustAirFlow": 200,
            "supplyAirFlow": 200,
        }
    )
    devices: list[dict[str, Any]] = field(default_factory=list)
    thermal_profile: dict[str, Any] = field(
        default_factory=lambda: {
            "temperature": {
                "status": 0,
                "manualTemperature": 22.0,
                "comfortTemperature": 22.0,
                "reducedTemperature": 18.0,
            },
            "season": {"status": 0},
            "temperatureProfile": 0,
        }
    )
    telemetry_data: dict[str, dict[str, float]] = field(default_factory=dict)
    property_data: dict[str, dict[str, int]] = field(default_factory=dict)


class MockComfoClimeAPI:
    """Realistic mock of ComfoClimeAPI for testing.

    Provides configurable responses and tracks calls.
    """

    def __init__(self, responses: MockAPIResponses | None = None) -> None:
        self.responses = responses or MockAPIResponses()
        self.uuid = self.responses.uuid
        self._call_history: list[tuple[str, tuple, dict]] = []

    def _record_call(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Record a method call for verification."""
        self._call_history.append((method, args, kwargs))

    async def async_get_uuid(self) -> str:
        self._record_call("async_get_uuid")
        return self.responses.uuid

    async def async_get_monitoring_ping(self) -> dict[str, Any]:
        self._record_call("async_get_monitoring_ping")
        return {
            "uuid": self.responses.uuid,
            "uptime": 123456,
            "timestamp": "2024-01-15T10:30:00Z",
        }

    async def async_get_dashboard_data(self) -> dict[str, Any]:
        self._record_call("async_get_dashboard_data")
        return self.responses.dashboard_data.copy()

    async def async_get_connected_devices(self) -> list[dict[str, Any]]:
        self._record_call("async_get_connected_devices")
        return self.responses.devices.copy()

    async def async_get_thermal_profile(self) -> dict[str, Any]:
        self._record_call("async_get_thermal_profile")
        return self.responses.thermal_profile.copy()

    async def async_update_dashboard(self, **kwargs: Any) -> None:
        self._record_call("async_update_dashboard", **kwargs)
        # Simulate updating the state
        self.responses.dashboard_data.update(kwargs)

    async def async_update_thermal_profile(self, **kwargs: Any) -> None:
        self._record_call("async_update_thermal_profile", **kwargs)
        # Simulate updating the thermal profile
        for key, value in kwargs.items():
            if isinstance(value, dict):
                self.responses.thermal_profile[key] = value
            else:
                self.responses.thermal_profile[key] = value

    async def async_set_hvac_season(self, season: int, hpStandby: bool) -> None:
        self._record_call("async_set_hvac_season", season=season, hpStandby=hpStandby)
        self.responses.dashboard_data["season"] = season
        self.responses.dashboard_data["hpStandby"] = hpStandby

    async def async_read_telemetry_for_device(
        self, device_uuid: str, telemetry_id: int, **kwargs: Any
    ) -> float:
        self._record_call(
            "async_read_telemetry_for_device",
            device_uuid=device_uuid,
            telemetry_id=telemetry_id,
            **kwargs,
        )
        return self.responses.telemetry_data.get(device_uuid, {}).get(
            str(telemetry_id), 0.0
        )

    async def async_read_property_for_device(
        self, device_uuid: str, path: str, **kwargs: Any
    ) -> int:
        self._record_call(
            "async_read_property_for_device",
            device_uuid=device_uuid,
            path=path,
            **kwargs,
        )
        return self.responses.property_data.get(device_uuid, {}).get(path, 0)

    async def async_set_property_for_device(
        self, device_uuid: str, path: str, value: int, **kwargs: Any
    ) -> None:
        self._record_call(
            "async_set_property_for_device",
            device_uuid=device_uuid,
            path=path,
            value=value,
            **kwargs,
        )
        if device_uuid not in self.responses.property_data:
            self.responses.property_data[device_uuid] = {}
        self.responses.property_data[device_uuid][path] = value

    async def async_reset_system(self) -> None:
        self._record_call("async_reset_system")

    def get_calls(self, method: str) -> list[tuple[tuple, dict]]:
        """Get all calls to a specific method."""
        return [(args, kwargs) for m, args, kwargs in self._call_history if m == method]

    def assert_called_once(self, method: str) -> None:
        """Assert a method was called exactly once."""
        calls = self.get_calls(method)
        assert len(calls) == 1, f"Expected 1 call to {method}, got {len(calls)}"

    def assert_called_with(self, method: str, **expected_kwargs: Any) -> None:
        """Assert a method was called with specific kwargs."""
        calls = self.get_calls(method)
        assert len(calls) > 0, f"Expected at least 1 call to {method}, got 0"
        _, kwargs = calls[-1]  # Check last call
        for key, expected_value in expected_kwargs.items():
            assert (
                key in kwargs
            ), f"Expected kwarg '{key}' not found in call to {method}"
            assert (
                kwargs[key] == expected_value
            ), f"Expected {key}={expected_value}, got {kwargs[key]}"


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.loop = None
    hass.async_create_task = MagicMock()
    hass.add_job = MagicMock()
    hass.async_write_ha_state = MagicMock()

    # Mock platform for entities
    mock_platform = MagicMock()
    mock_platform.platform_name = "comfoclime"
    hass.platform = mock_platform

    return hass


@pytest.fixture
def hass_with_frame_helper(mock_hass):
    """Provide a mock Home Assistant with frame helper initialized."""
    # Patch frame.report_usage to prevent "Frame helper not set up" errors
    with patch("homeassistant.helpers.frame.report_usage"):
        yield mock_hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {"host": "192.168.1.100"}
    entry.options = {}
    return entry


@pytest.fixture
def mock_api_responses() -> MockAPIResponses:
    """Fixture for configurable API responses."""
    return MockAPIResponses()


@pytest.fixture
def mock_api(mock_api_responses: MockAPIResponses) -> MockComfoClimeAPI:
    """Create a realistic mock API with call tracking."""
    return MockComfoClimeAPI(mock_api_responses)


@pytest.fixture
def mock_api_with_devices() -> MockComfoClimeAPI:
    """Create mock API with sample devices."""
    responses = MockAPIResponses(
        devices=[
            {
                "uuid": "device-1-uuid",
                "displayName": "ComfoAir Q",
                "@modelType": "ComfoAir Q350",
                "modelTypeId": 21,
                "version": "2.0.0",
            },
            {
                "uuid": "device-2-uuid",
                "displayName": "ComfoClime",
                "@modelType": "ComfoClime 200",
                "modelTypeId": 20,
                "version": "1.2.3",
            },
        ]
    )
    return MockComfoClimeAPI(responses)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "indoorTemperature": 22.5,
        "outdoorTemperature": 15.0,
        "fanSpeed": 2,
        "season": 1,
        "temperatureProfile": 0,
        "heatPumpStatus": 3,
        "hpStandby": False,
        "exhaustAirFlow": 200,
        "supplyAirFlow": 200,
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_thermalprofile_coordinator():
    """Create a mock thermal profile coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "temperature": {
            "status": 0,
            "manualTemperature": 22.0,
            "comfortTemperature": 22.0,
            "reducedTemperature": 18.0,
        },
        "season": {
            "status": 0,
        },
        "temperatureProfile": 0,
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_telemetry_coordinator():
    """Create a mock telemetry coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "test-device-uuid": {
            "123": 25.5,
            "456": 30.0,
        }
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.last_update_success = True
    coordinator.register_telemetry = AsyncMock()
    coordinator.get_telemetry_value = MagicMock(return_value=25.5)
    return coordinator


@pytest.fixture
def mock_property_coordinator():
    """Create a mock property coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "test-device-uuid": {
            "29/1/10": 100,
            "29/1/6": 1,
        }
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.last_update_success = True
    coordinator.register_property = AsyncMock()
    coordinator.get_property_value = MagicMock(return_value=100)
    return coordinator


@pytest.fixture
def mock_definition_coordinator():
    """Create a mock definition coordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "test-device-uuid": {
            "indoorTemperature": 21.4,
            "outdoorTemperature": 1.1,
            "extractTemperature": 21.4,
            "supplyTemperature": 16.8,
            "exhaustTemperature": 5.6,
        }
    }
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.last_update_success = True
    coordinator.get_definition_data = MagicMock(
        return_value={
            "indoorTemperature": 21.4,
            "outdoorTemperature": 1.1,
            "extractTemperature": 21.4,
            "supplyTemperature": 16.8,
            "exhaustTemperature": 5.6,
        }
    )
    return coordinator


@pytest.fixture
def mock_device():
    """Create a mock ComfoClime device."""
    return {
        "uuid": "test-device-uuid",
        "displayName": "ComfoClime Test",
        "@modelType": "ComfoClime 200",
        "modelTypeId": 20,
        "version": "1.2.3",
    }


@pytest.fixture
def mock_connected_device():
    """Create a mock connected device (e.g., ComfoAir Q)."""
    return {
        "uuid": "connected-device-uuid",
        "displayName": "ComfoAir Q",
        "@modelType": "ComfoAir Q350",
        "modelTypeId": 21,
        "version": "2.0.0",
    }
