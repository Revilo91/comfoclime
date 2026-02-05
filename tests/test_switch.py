"""Tests for ComfoClime switch entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.comfoclime.models import DashboardData
from custom_components.comfoclime.switch import ComfoClimeSwitch, async_setup_entry


class TestComfoClimeSwitch:
    """Test ComfoClimeSwitch class."""

    def test_switch_initialization_thermal_profile(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test switch initialization for thermal profile endpoint."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="automatic_season_detection",
            name="Automatic Season Detection",
            invert=False,
            endpoint="thermal_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert switch._key_path == ["season", "status"]
        assert switch._name == "Automatic Season Detection"
        assert switch._endpoint == "thermal_profile"
        assert switch._invert is False
        assert switch._attr_unique_id == "test_entry_id_switch_season.status"

    def test_switch_initialization_dashboard_inverted(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test switch initialization for dashboard endpoint with inverted logic."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="hpstandby",
            translation_key="heatpump_onoff",
            name="Heatpump on/off",
            invert=True,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert switch._key_path == ["hpstandby"]
        assert switch._name == "Heatpump on/off"
        assert switch._endpoint == "dashboard"
        assert switch._invert is True
        assert switch._attr_unique_id == "test_entry_id_switch_hpstandby"

    def test_switch_state_update_thermal_profile(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test switch state update from thermal profile coordinator."""
        mock_thermalprofile_coordinator.data = {
            "season": {"status": 1},
        }

        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="automatic_season_detection",
            name="Automatic Season Detection",
            invert=False,
            endpoint="thermal_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # Status 1 should result in is_on = True
        assert switch._state is True

    def test_switch_state_update_dashboard_not_inverted(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test switch state update from dashboard without inversion."""
        mock_coordinator.data = DashboardData(fan_speed=1)

        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="some_field",
            translation_key="some_field",
            name="Some Field",
            invert=False,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # Value 1 without inversion = True
        assert switch._state is True

    def test_switch_state_update_dashboard_inverted_bool(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test switch state update from dashboard with inverted logic (boolean)."""
        # hpStandby = False means heatpump is ON
        mock_coordinator.data = DashboardData(hp_standby=False)

        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="hpstandby",
            translation_key="heatpump_onoff",
            name="Heatpump on/off",
            invert=True,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # Boolean False with invert=True -> not False = True
        assert switch._state is True

    def test_switch_state_update_dashboard_inverted_int(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test switch state update from dashboard with inverted logic (integer)."""
        # hpStandby = 1 means heatpump is in standby (OFF)
        mock_coordinator.data = DashboardData(hp_standby=True)

        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="hpstandby",
            translation_key="heatpump_onoff",
            name="Heatpump on/off",
            invert=True,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        switch.async_write_ha_state = MagicMock()

        switch._handle_coordinator_update()

        # Integer 1 with invert=True -> 1 != 1 = False
        assert switch._state is False

    @pytest.mark.asyncio
    async def test_switch_turn_on_thermal_profile(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning on thermal profile switch."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="automatic_season_detection",
            name="Automatic Season Detection",
            invert=False,
            endpoint="thermal_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        mock_thermalprofile_coordinator.async_request_refresh = AsyncMock()
        mock_api.async_update_thermal_profile = AsyncMock()

        await switch.async_turn_on()

        # Verify API was called
        mock_api.async_update_thermal_profile.assert_called_once()
        call_kwargs = mock_api.async_update_thermal_profile.call_args[1]
        assert call_kwargs["season_status"] == 1

    @pytest.mark.asyncio
    async def test_switch_turn_off_thermal_profile(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning off thermal profile switch."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="temperature.status",
            translation_key="automatic_comfort_temperature",
            name="Automatic Comfort Temperature",
            invert=False,
            endpoint="thermal_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        mock_thermalprofile_coordinator.async_request_refresh = AsyncMock()
        mock_api.async_update_thermal_profile = AsyncMock()

        await switch.async_turn_off()

        # Verify API was called with 0
        mock_api.async_update_thermal_profile.assert_called_once()
        call_kwargs = mock_api.async_update_thermal_profile.call_args[1]
        assert call_kwargs["temperature_status"] == 0

    @pytest.mark.asyncio
    async def test_switch_turn_on_dashboard_inverted(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test turning on inverted dashboard switch (heatpump on)."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="hpstandby",
            translation_key="heatpump_onoff",
            name="Heatpump on/off",
            invert=True,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_api.async_update_dashboard = AsyncMock()

        await switch.async_turn_on()

        # With invert=True, turn_on sends 0 (heatpump active)
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["hpstandby"] == 0

    @pytest.mark.asyncio
    async def test_switch_turn_off_dashboard_inverted(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test turning off inverted dashboard switch (heatpump standby)."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            key="hpstandby",
            translation_key="heatpump_onoff",
            name="Heatpump on/off",
            invert=True,
            endpoint="dashboard",
            device=mock_device,
            entry=mock_config_entry,
        )

        switch.hass = mock_hass
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_api.async_update_dashboard = AsyncMock()

        await switch.async_turn_off()

        # With invert=True, turn_off sends 1 (heatpump standby)
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["hpstandby"] == 1

    def test_switch_device_info(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test switch device info."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="automatic_season_detection",
            name="Automatic Season Detection",
            invert=False,
            endpoint="thermal_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = switch.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]
        assert device_info["name"] == "ComfoClime Test"

    def test_switch_device_info_none(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_config_entry):
        """Test switch device info when device is None."""
        switch = ComfoClimeSwitch(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            key="season.status",
            translation_key="automatic_season_detection",
            name="Automatic Season Detection",
            invert=False,
            endpoint="thermal_profile",
            device=None,
            entry=mock_config_entry,
        )

        device_info = switch.device_info

        assert device_info is None


@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_hass,
    mock_config_entry,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_device,
):
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

    mock_thermalprofile_coordinator.async_config_entry_first_refresh = AsyncMock()

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
    # Should add 3 entities: season.status, temperature.status, hpstandby
    call_args = async_add_entities.call_args[0]
    entities = call_args[0]
    assert len(entities) == 3

    # Verify entity types and properties
    assert all(isinstance(e, ComfoClimeSwitch) for e in entities)
    assert entities[0]._endpoint == "thermal_profile"
    assert entities[1]._endpoint == "thermal_profile"
    assert entities[2]._endpoint == "dashboard"
    assert entities[2]._invert is True
