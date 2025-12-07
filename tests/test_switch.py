"""Tests for ComfoClime switch entities."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.comfoclime.switch import (
    ComfoClimeModeSwitch,
    ComfoClimeStandbySwitch,
    async_setup_entry,
)


class TestComfoClimeModeSwitch:
    """Test ComfoClimeModeSwitch class."""

    def test_mode_switch_initialization(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test mode switch initialization."""
        switch = ComfoClimeModeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="season_automatic",
            name="Season Automatic",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert switch._key_path == ["season", "status"]
        assert switch._name == "Season Automatic"
        assert switch._attr_unique_id == "test_entry_id_switch_season.status"

    def test_mode_switch_state_update(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test mode switch state update from coordinator."""
        mock_thermalprofile_coordinator.data = {
            "season": {"status": 1},
        }

        switch = ComfoClimeModeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="season_automatic",
            name="Season Automatic",
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # Status 1 should result in is_on = True
        assert switch._state is True

    def test_mode_switch_turn_on(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test turning on mode switch."""
        mock_hass.create_task = MagicMock()

        switch = ComfoClimeModeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="season_automatic",
            name="Season Automatic",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.turn_on()

        # Verify API was called with correct parameters
        mock_api.update_thermal_profile.assert_called_once()
        call_args = mock_api.update_thermal_profile.call_args[0][0]
        assert call_args["season"]["status"] == 1

    def test_mode_switch_turn_off(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test turning off mode switch."""
        mock_hass.create_task = MagicMock()

        switch = ComfoClimeModeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="temperature.status",
            translation_key="temperature_automatic",
            name="Temperature Automatic",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.turn_off()

        # Verify API was called with correct parameters
        mock_api.update_thermal_profile.assert_called_once()
        call_args = mock_api.update_thermal_profile.call_args[0][0]
        assert call_args["temperature"]["status"] == 0

    def test_mode_switch_device_info(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test mode switch device info."""
        switch = ComfoClimeModeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="season_automatic",
            name="Season Automatic",
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = switch.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]
        assert device_info["name"] == "ComfoClime Test"


class TestComfoClimeStandbySwitch:
    """Test ComfoClimeStandbySwitch class."""

    def test_standby_switch_initialization(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test standby switch initialization."""
        switch = ComfoClimeStandbySwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert switch._key_path == "hpstandby"
        assert switch._name == "Heatpump on/off"
        assert switch._attr_unique_id == "test_entry_id_switch_hpstandby"

    def test_standby_switch_state_update_on(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test standby switch state update when heatpump is on."""
        # hpStandby = False means heatpump is ON
        mock_coordinator.data = {"hpStandby": False}

        switch = ComfoClimeStandbySwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # When hpStandby is False, the switch should be on (heatpump running)
        # The logic inverts: val = False -> val = True -> val == 1 -> True
        assert switch._state is True

    def test_standby_switch_state_update_off(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test standby switch state update when heatpump is off."""
        # hpStandby = True means heatpump is in standby (OFF)
        mock_coordinator.data = {"hpStandby": True}

        switch = ComfoClimeStandbySwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # When hpStandby is True, the switch should be off
        assert switch._state is False

    def test_standby_switch_turn_on(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test turning on standby switch (turn on heatpump)."""
        mock_hass.create_task = MagicMock()

        switch = ComfoClimeStandbySwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.turn_on()

        # Turning on means setting hp_standby=False
        mock_api.update_dashboard.assert_called_once_with(hp_standby=False)

    def test_standby_switch_turn_off(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test turning off standby switch (put heatpump in standby)."""
        mock_hass.create_task = MagicMock()

        switch = ComfoClimeStandbySwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.turn_off()

        # Turning off means setting hp_standby=True
        mock_api.update_dashboard.assert_called_once_with(hp_standby=True)


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_coordinator, mock_thermalprofile_coordinator, mock_device):
    """Test async_setup_entry for switches."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": MagicMock(),
                "coordinator": mock_coordinator,
                "tpcoordinator": mock_thermalprofile_coordinator,
                "devices": [mock_device],
                "main_device": mock_device,
            }
        }
    }

    # Mock the API class to return our mock API
    with patch("custom_components.comfoclime.switch.ComfoClimeAPI") as mock_api_class:
        mock_api_instance = MagicMock()
        mock_api_instance.async_get_uuid = AsyncMock(return_value="test-uuid")
        mock_api_class.return_value = mock_api_instance

        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        # Verify entities were added
        assert async_add_entities.called
