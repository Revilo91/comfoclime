"""Common fixtures for ComfoClime tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


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
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {"host": "192.168.1.100"}
    entry.options = {}
    return entry


@pytest.fixture
def mock_api():
    """Create a mock ComfoClimeAPI instance."""
    api = MagicMock()
    api.uuid = "test-uuid-12345"
    api.async_get_uuid = AsyncMock(return_value="test-uuid-12345")
    api.async_get_connected_devices = AsyncMock(return_value=[])
    api.async_read_telemetry_for_device = AsyncMock(return_value=22.5)
    api.async_read_property_for_device = AsyncMock(return_value=1)
    api.async_set_property_for_device = AsyncMock()
    api.async_update_dashboard = AsyncMock()
    api.async_update_thermal_profile = AsyncMock()
    api.update_thermal_profile = MagicMock()
    api.update_dashboard = MagicMock()
    api.set_property_for_device = MagicMock()
    api.async_set_hvac_season = AsyncMock()
    api.async_reset_system = AsyncMock()
    return api


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
