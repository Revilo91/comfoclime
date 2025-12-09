"""Tests for ComfoClime climate entity."""
from unittest.mock import MagicMock

import pytest
from homeassistant.components.climate import (
    FAN_HIGH,
    FAN_MEDIUM,
    PRESET_COMFORT,
    PRESET_NONE,
    HVACAction,
    HVACMode,
)

from custom_components.comfoclime.climate import (
    ComfoClimeClimate,
    async_setup_entry,
)


class TestComfoClimeClimate:
    """Test ComfoClimeClimate class."""

    def test_climate_initialization(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate entity initialization."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate._attr_unique_id == "test_entry_id_climate"
        assert climate._attr_translation_key == "climate"
        assert HVACMode.HEAT in climate._attr_hvac_modes
        assert HVACMode.COOL in climate._attr_hvac_modes
        assert HVACMode.FAN_ONLY in climate._attr_hvac_modes
        assert HVACMode.OFF in climate._attr_hvac_modes

    def test_climate_current_temperature(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate current temperature from dashboard."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.current_temperature == 22.5

    def test_climate_target_temperature(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate target temperature from thermal profile."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.target_temperature == 22.0

    def test_climate_hvac_mode_heat(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC mode when in heating season."""
        mock_coordinator.data = {
            "season": 1,  # heating
            "hpStandby": False,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.hvac_mode == HVACMode.HEAT

    def test_climate_hvac_mode_cool(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC mode when in cooling season."""
        mock_coordinator.data = {
            "season": 2,  # cooling
            "hpStandby": False,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.hvac_mode == HVACMode.COOL

    def test_climate_hvac_mode_fan_only(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC mode when in transition season."""
        mock_coordinator.data = {
            "season": 0,  # transition
            "hpStandby": False,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.hvac_mode == HVACMode.FAN_ONLY

    def test_climate_hvac_mode_off(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC mode when in standby."""
        mock_coordinator.data = {
            "season": 1,
            "hpStandby": True,  # standby
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.hvac_mode == HVACMode.OFF

    def test_climate_hvac_action_heating(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC action when heating."""
        mock_coordinator.data = {
            "heatPumpStatus": 3,  # 0000 0011 - active + heating
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert HVACAction.HEATING in climate.hvac_action

    def test_climate_hvac_action_cooling(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC action when cooling."""
        mock_coordinator.data = {
            "heatPumpStatus": 5,  # 0000 0101 - active + cooling
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert HVACAction.COOLING in climate.hvac_action

    def test_climate_hvac_action_idle(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC action when idle."""
        mock_coordinator.data = {
            "heatPumpStatus": 1,  # 0000 0001 - active but not heating/cooling
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert HVACAction.IDLE in climate.hvac_action

    def test_climate_hvac_action_off(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate HVAC action when off."""
        mock_coordinator.data = {
            "heatPumpStatus": 0,  # off
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert HVACAction.OFF in climate.hvac_action

    def test_climate_preset_mode_comfort(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate preset mode comfort."""
        mock_coordinator.data = {
            "temperatureProfile": 0,  # comfort
            "setPointTemperature": None,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.preset_mode == PRESET_COMFORT

    def test_climate_preset_mode_manual(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate preset mode manual."""
        mock_coordinator.data = {
            "setPointTemperature": 22.5,  # manual mode
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.preset_mode == PRESET_NONE

    def test_climate_fan_mode(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate fan mode."""
        mock_coordinator.data = {"fanSpeed": 2}

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.fan_mode == FAN_MEDIUM

    @pytest.mark.asyncio
    async def test_climate_set_temperature(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate temperature."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        await climate.async_set_temperature(temperature=23.5)

        # Should call async_update_dashboard with temperature and status
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["set_point_temperature"] == 23.5
        assert call_kwargs["status"] == 0  # Manual mode

    @pytest.mark.asyncio
    async def test_climate_set_hvac_mode_heat(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate HVAC mode to heat."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute
        climate.hass = mock_hass

        await climate.async_set_hvac_mode(HVACMode.HEAT)

        # Should call async_set_hvac_season with season=1 and hpStandby=False
        mock_api.async_set_hvac_season.assert_called_once_with(
            season=1, hpStandby=False
        )

    @pytest.mark.asyncio
    async def test_climate_set_hvac_mode_off(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate HVAC mode to off."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute
        climate.hass = mock_hass

        await climate.async_set_hvac_mode(HVACMode.OFF)

        # Should call async_update_dashboard with hpStandby=True
        mock_api.async_update_dashboard.assert_called_once_with(
            hpStandby=True
        )

    @pytest.mark.asyncio
    async def test_climate_set_preset_mode_comfort(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate preset mode to comfort."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        await climate.async_set_preset_mode(PRESET_COMFORT)

        # Should call async_update_dashboard with profiles and status
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["temperature_profile"] == 0
        assert call_kwargs["season_profile"] == 0
        assert call_kwargs["status"] == 1  # Automatic mode

    @pytest.mark.asyncio
    async def test_climate_set_preset_mode_manual(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate preset mode to manual."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        await climate.async_set_preset_mode(PRESET_NONE)

        # Should call async_update_dashboard with status=0
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["status"] == 0  # Manual mode

    @pytest.mark.asyncio
    async def test_climate_set_fan_mode(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test setting climate fan mode."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        await climate.async_set_fan_mode(FAN_HIGH)

        # Should call async_update_dashboard with fan_speed=3
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["fan_speed"] == 3

    def test_climate_device_info(self, mock_hass, mock_coordinator, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test climate device info."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = climate.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]
        assert device_info["name"] == "ComfoClime Test"


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_api, mock_coordinator, mock_thermalprofile_coordinator, mock_device):
    """Test async_setup_entry for climate entity."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "coordinator": mock_coordinator,
                "tpcoordinator": mock_thermalprofile_coordinator,
                "main_device": mock_device,
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entity was added
    assert async_add_entities.called


@pytest.mark.asyncio
async def test_async_setup_entry_no_main_device(mock_hass, mock_config_entry, mock_api, mock_coordinator, mock_thermalprofile_coordinator):
    """Test async_setup_entry when no main device exists."""
    # Setup mock data without main device
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "coordinator": mock_coordinator,
                "tpcoordinator": mock_thermalprofile_coordinator,
                "main_device": None,
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were not added
    assert not async_add_entities.called
