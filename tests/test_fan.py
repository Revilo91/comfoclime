"""Tests for ComfoClime fan entity."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.comfoclime.fan import (
    ComfoClimeFan,
    async_setup_entry,
)


class TestComfoClimeFan:
    """Test ComfoClimeFan class."""

    def test_fan_initialization(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan entity initialization."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert fan._attr_unique_id == "test_entry_id_fan_speed"
        assert fan._attr_translation_key == "fan_speed"
        assert fan._attr_speed_count == 3
        assert fan._current_speed == 0

    def test_fan_is_on_when_speed_positive(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan is_on property when speed is positive."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        fan._current_speed = 2

        assert fan.is_on is True

    def test_fan_is_off_when_speed_zero(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan is_on property when speed is zero."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        fan._current_speed = 0

        assert fan.is_on is False

    def test_fan_percentage_calculation(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan percentage calculation."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Speed 0 -> 0%
        fan._current_speed = 0
        assert fan.percentage == 0

        # Speed 1 -> 33%
        fan._current_speed = 1
        assert fan.percentage == 33

        # Speed 2 -> 66%
        fan._current_speed = 2
        assert fan.percentage == 66

        # Speed 3 -> 100%
        fan._current_speed = 3
        assert fan.percentage == 100

    @pytest.mark.asyncio
    async def test_fan_set_percentage(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting fan percentage."""
        mock_hass.add_job = MagicMock()

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        await fan.async_set_percentage(66)

        # 66% should map to speed 2
        mock_api.async_update_dashboard.assert_called_once_with(mock_hass, fan_speed=2)
        assert fan._current_speed == 2

    @pytest.mark.asyncio
    async def test_fan_set_percentage_boundaries(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting fan percentage at boundaries."""
        mock_hass.add_job = MagicMock()

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Test 0%
        await fan.async_set_percentage(0)
        assert fan._current_speed == 0

        # Test 100%
        mock_api.async_update_dashboard.reset_mock()
        await fan.async_set_percentage(100)
        call_args = mock_api.async_update_dashboard.call_args
        assert call_args[1]["fan_speed"] == 3

        # Test mid-range values
        mock_api.async_update_dashboard.reset_mock()
        await fan.async_set_percentage(50)
        call_args = mock_api.async_update_dashboard.call_args
        # 50 / 33 = 1.5, rounded = 2
        assert call_args[1]["fan_speed"] in [1, 2]

    def test_fan_coordinator_update(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan coordinator update."""
        mock_coordinator.data = {"fanSpeed": 3}

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        fan._handle_coordinator_update()

        assert fan._current_speed == 3

    def test_fan_coordinator_update_string_value(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan coordinator update with string value."""
        mock_coordinator.data = {"fanSpeed": "2"}

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        fan._handle_coordinator_update()

        assert fan._current_speed == 2

    def test_fan_device_info(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test fan device info."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = fan.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]
        assert device_info["name"] == "ComfoClime Test"
        assert device_info["manufacturer"] == "Zehnder"


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_api, mock_coordinator, mock_device):
    """Test async_setup_entry for fan entity."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "coordinator": mock_coordinator,
                "devices": [mock_device],
                "main_device": mock_device,
            }
        }
    }

    async_add_entities = MagicMock()

    with patch("custom_components.comfoclime.fan.ComfoClimeFan"):
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entity was added
    assert async_add_entities.called


@pytest.mark.asyncio
async def test_async_setup_entry_no_main_device(mock_hass, mock_config_entry, mock_api, mock_coordinator):
    """Test async_setup_entry when no main device exists."""
    # Setup mock data without main device
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "coordinator": mock_coordinator,
                "devices": [],
                "main_device": None,
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were not added
    assert not async_add_entities.called
