"""Tests for ComfoClime fan entity."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from custom_components.comfoclime.fan import (
    ComfoClimeFan,
    async_setup_entry,
)
from custom_components.comfoclime.constants import FanSpeed


class TestComfoClimeFan:
    """Test ComfoClimeFan class."""

    def test_fan_initialization(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
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

    def test_fan_is_on_when_speed_positive(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
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

    def test_fan_is_off_when_speed_zero(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
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

    @pytest.mark.parametrize(
        "speed,expected_percentage",
        [
            (FanSpeed.OFF, 0),
            (FanSpeed.LOW, 33),
            (FanSpeed.MEDIUM, 66),
            (FanSpeed.HIGH, 100),
        ],
        ids=["speed_0", "speed_1", "speed_2", "speed_3"],
    )
    def test_fan_percentage_calculation(
        self, speed, expected_percentage, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test fan percentage calculation for various speeds."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        fan._current_speed = speed
        assert fan.percentage == expected_percentage

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "percentage,expected_step",
        [
            (0, 0),
            (33, 1),
            (50, 2),  # Rounds to nearest
            (66, 2),
            (100, 3),
        ],
        ids=["0%", "33%", "50%", "66%", "100%"],
    )
    async def test_fan_percentage_to_step_conversion(
        self, percentage, expected_step, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test percentage to step conversion for various inputs."""
        mock_hass.add_job = MagicMock()

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        fan.hass = mock_hass
        fan.async_write_ha_state = MagicMock()

        await fan.async_set_percentage(percentage)

        # Verify API was called with correct step
        calls = mock_api.get_calls("async_update_dashboard")
        assert len(calls) == 1
        _, kwargs = calls[0]
        assert kwargs["fan_speed"] == expected_step
        assert fan._current_speed == expected_step

    @pytest.mark.asyncio
    async def test_fan_set_percentage_edge_cases(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test setting fan percentage at edge cases."""
        mock_hass.add_job = MagicMock()

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        fan.hass = mock_hass
        fan.async_write_ha_state = MagicMock()

        # Test setting speed and clearing call history
        await fan.async_set_percentage(0)
        assert fan._current_speed == 0
        mock_api._call_history.clear()  # Clear for next test

        # Test another value
        await fan.async_set_percentage(40)
        calls = mock_api.get_calls("async_update_dashboard")
        assert len(calls) == 1
        _, kwargs = calls[0]
        assert kwargs["fan_speed"] in [1, 2]  # 40/33 ≈ 1.2, could round to 1 or 2

    def test_fan_coordinator_update(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test fan coordinator update."""
        mock_coordinator.data = {"fanSpeed": 3}

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        fan.hass = mock_hass
        fan.async_write_ha_state = MagicMock()

        fan._handle_coordinator_update()

        assert fan._current_speed == 3

    def test_fan_coordinator_update_string_value(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test fan coordinator update with string value."""
        mock_coordinator.data = {"fanSpeed": "2"}

        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        fan.hass = mock_hass
        fan.async_write_ha_state = MagicMock()

        fan._handle_coordinator_update()

        assert fan._current_speed == 2

    def test_fan_device_info(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
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
async def test_async_setup_entry(
    mock_hass, mock_config_entry, mock_coordinator, mock_device, mock_api
):
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

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entity was added
    assert async_add_entities.called


@pytest.mark.asyncio
async def test_async_setup_entry_no_main_device(
    mock_hass, mock_config_entry, mock_api, mock_coordinator
):
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
