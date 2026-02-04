"""Tests for ComfoClime climate entity."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.climate import (
    FAN_HIGH,
    FAN_MEDIUM,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)

from custom_components.comfoclime.climate import (
    ComfoClimeClimate,
    async_setup_entry,
)


class TestComfoClimeClimate:
    """Test ComfoClimeClimate class."""

    def test_climate_initialization(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
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
        # Check that turn_on and turn_off features are supported
        assert (
            climate._attr_supported_features & ClimateEntityFeature.TURN_ON
        ) == ClimateEntityFeature.TURN_ON
        assert (
            climate._attr_supported_features & ClimateEntityFeature.TURN_OFF
        ) == ClimateEntityFeature.TURN_OFF

    def test_climate_current_temperature(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate current temperature from dashboard."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.current_temperature == 22.5

    def test_climate_target_temperature(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate target temperature from thermal profile."""
        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.target_temperature == 22.0

    @pytest.mark.parametrize(
        "season,hpStandby,expected_mode",
        [
            (1, False, HVACMode.HEAT),
            (2, False, HVACMode.COOL),
            (0, False, HVACMode.FAN_ONLY),
            (1, True, HVACMode.OFF),
            (2, True, HVACMode.OFF),
        ],
        ids=["heating", "cooling", "transition", "standby_heat", "standby_cool"],
    )
    def test_climate_hvac_mode_variations(
        self,
        season,
        hpStandby,
        expected_mode,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate HVAC mode for various season and standby combinations."""
        mock_coordinator.data = {
            "season": season,
            "hpStandby": hpStandby,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.hvac_mode == expected_mode

    @pytest.mark.parametrize(
        "heatPumpStatus,expected_action",
        [
            (3, HVACAction.HEATING),  # 0000 0011 - active + heating
            (5, HVACAction.COOLING),  # 0000 0101 - active + cooling
            (1, HVACAction.IDLE),  # 0000 0001 - active but not heating/cooling
            (0, HVACAction.OFF),  # off
        ],
        ids=["heating", "cooling", "idle", "off"],
    )
    def test_climate_hvac_action_variations(
        self,
        heatPumpStatus,
        expected_action,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate HVAC action for various heat pump statuses."""
        mock_coordinator.data = {
            "heatPumpStatus": heatPumpStatus,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert expected_action in climate.hvac_action

    @pytest.mark.parametrize(
        "temperatureProfile,setPointTemperature,expected_preset",
        [
            (0, None, PRESET_COMFORT),
            (1, None, PRESET_BOOST),
            (2, None, PRESET_ECO),
            (0, 22.5, PRESET_NONE),  # Manual mode
        ],
        ids=["comfort", "boost", "eco", "manual"],
    )
    def test_climate_preset_mode_variations(
        self,
        temperatureProfile,
        setPointTemperature,
        expected_preset,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate preset mode for various temperature profiles."""
        mock_coordinator.data = {
            "temperatureProfile": temperatureProfile,
            "setPointTemperature": setPointTemperature,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert climate.preset_mode == expected_preset

    def test_climate_fan_mode(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
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
    async def test_climate_set_temperature(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test setting climate temperature."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        climate.hass = mock_hass

        await climate.async_set_temperature(temperature=23.5)

        # Should call async_update_dashboard with temperature and status
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["set_point_temperature"] == 23.5
        assert call_kwargs["status"] == 0  # Manual mode

    @pytest.mark.asyncio
    async def test_climate_set_hvac_mode_heat(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
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
    async def test_climate_set_hvac_mode_off(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
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
        mock_api.async_update_dashboard.assert_called_once_with(hpStandby=True)

    @pytest.mark.asyncio
    async def test_climate_set_preset_mode_comfort(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test setting climate preset mode to comfort."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        climate.hass = mock_hass

        await climate.async_set_preset_mode(PRESET_COMFORT)

        # Should call async_update_dashboard with profiles and status
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["temperature_profile"] == 0
        assert call_kwargs["season_profile"] == 0
        assert call_kwargs["status"] == 1  # Automatic mode

    @pytest.mark.asyncio
    async def test_climate_set_preset_mode_manual(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test setting climate preset mode to manual."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        climate.hass = mock_hass

        await climate.async_set_preset_mode(PRESET_NONE)

        # Should call async_update_dashboard with status=0
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["status"] == 0  # Manual mode

    @pytest.mark.asyncio
    async def test_climate_set_fan_mode(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test setting climate fan mode."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        climate.hass = mock_hass

        await climate.async_set_fan_mode(FAN_HIGH)

        # Should call async_update_dashboard with fan_speed=3
        mock_api.async_update_dashboard.assert_called_once()
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert call_kwargs["fan_speed"] == 3

    @pytest.mark.asyncio
    async def test_climate_turn_off(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning off climate device."""
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

        await climate.async_turn_off()

        # Should call async_update_dashboard with hpStandby=True
        mock_api.async_update_dashboard.assert_called_once_with(hpStandby=True)

    @pytest.mark.asyncio
    async def test_climate_turn_on_with_heating_season(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning on climate device."""
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

        await climate.async_turn_on()

        # Should call async_update_dashboard with hpStandby=False only
        mock_api.async_update_dashboard.assert_called_once_with(hpStandby=False)

    @pytest.mark.asyncio
    async def test_climate_turn_on_with_cooling_season(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning on climate device does not change season."""
        mock_hass.async_create_task = MagicMock()

        # Set up coordinator with cooling season
        mock_coordinator.data = {
            "season": 2,  # cooling
            "hpStandby": True,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute
        climate.hass = mock_hass

        await climate.async_turn_on()

        # Should call async_update_dashboard with hpStandby=False only, season unchanged
        mock_api.async_update_dashboard.assert_called_once_with(hpStandby=False)

    @pytest.mark.asyncio
    async def test_climate_turn_on_with_transition_season(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test turning on climate device preserves transition season."""
        mock_hass.async_create_task = MagicMock()

        # Set up coordinator with transition season (0)
        mock_coordinator.data = {
            "season": 0,  # transition/fan only
            "hpStandby": True,
        }

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute
        climate.hass = mock_hass

        await climate.async_turn_on()

        # Should call async_update_dashboard with hpStandby=False only, season unchanged
        mock_api.async_update_dashboard.assert_called_once_with(hpStandby=False)

    def test_climate_device_info(
        self,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
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
    @pytest.mark.parametrize(
        "scenario_preset,expected_scenario_id",
        [
            ("cooking", 4),
            ("party", 5),
            ("away", 7),
            ("scenario_boost", 8),
        ],
        ids=["cooking", "party", "away", "boost"],
    )
    async def test_climate_scenario_modes(
        self,
        scenario_preset,
        expected_scenario_id,
        mock_hass,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test climate scenario modes."""
        mock_hass.async_create_task = MagicMock()

        climate = ComfoClimeClimate(
            dashboard_coordinator=mock_coordinator,
            thermalprofile_coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )

        climate.hass = mock_hass

        # Set the scenario preset
        await climate.async_set_preset_mode(scenario_preset)

        # Verify API was called with correct scenario mode
        assert mock_api.async_update_dashboard.called
        call_kwargs = mock_api.async_update_dashboard.call_args[1]
        assert "scenario" in call_kwargs
        assert call_kwargs["scenario"] == expected_scenario_id


@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_hass,
    mock_config_entry,
    mock_api,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_device,
):
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
async def test_async_setup_entry_no_main_device(
    mock_hass,
    mock_config_entry,
    mock_api,
    mock_coordinator,
    mock_thermalprofile_coordinator,
):
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
