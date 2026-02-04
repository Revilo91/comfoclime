"""ComfoClime Climate Platform.

This module provides the Home Assistant climate entity for ComfoClime
integration. The climate entity controls HVAC operation including
temperature, fan speed, season mode, and presets.

The climate entity supports:
    - HVAC Modes: Off, Fan Only, Heat, Cool
    - Preset Modes: Manual, Comfort, Boost, Eco, Cooking, Party, Away, Scenario Boost
    - Fan Modes: Off, Low, Medium, High
    - Target Temperature Control
    - Current Temperature Display
    - HVAC Action (Idle, Heating, Cooling, Fan)

Scenario modes (Cooking, Party, Away, Scenario Boost) are special operating
modes with predefined durations. See SCENARIO_MODES.md for details.

Example:
    >>> # In Home Assistant
    >>> climate.set_temperature(entity_id="climate.comfoclime", temperature=22)
    >>> climate.set_hvac_mode(entity_id="climate.comfoclime", hvac_mode="heat")
    >>> climate.set_preset_mode(entity_id="climate.comfoclime", preset_mode="comfort")

Note:
    The climate entity uses two coordinators:
    - DashboardCoordinator: Real-time temp, fan, season data
    - ThermalprofileCoordinator: Thermal profile settings
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.components.climate import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import (
        ComfoClimeDashboardCoordinator,
        ComfoClimeThermalprofileCoordinator,
    )

from .constants import FanSpeed, ScenarioMode, Season, TemperatureProfile
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Temperature Profile Presets
# status=0 (manual mode) maps to PRESET_NONE (Manual)
# status=1 (automatic mode) uses temperatureProfile values:
PRESET_MAPPING = {
    TemperatureProfile.COMFORT: PRESET_COMFORT,
    TemperatureProfile.POWER: PRESET_BOOST,
    TemperatureProfile.ECO: PRESET_ECO,
}

PRESET_REVERSE_MAPPING = {v: k for k, v in PRESET_MAPPING.items()}

# Add manual preset mode (status=0)
PRESET_MANUAL = PRESET_NONE  # "none" preset means manual temperature control

# Scenario mapping - uses unique preset names to avoid conflicts with PRESET_MAPPING
SCENARIO_MAPPING = {
    ScenarioMode.COOKING: ScenarioMode.COOKING.preset_name,
    ScenarioMode.PARTY: ScenarioMode.PARTY.preset_name,
    ScenarioMode.HOLIDAY: ScenarioMode.HOLIDAY.preset_name,
    ScenarioMode.BOOST: ScenarioMode.BOOST.preset_name,
}

SCENARIO_REVERSE_MAPPING = {v: k for k, v in SCENARIO_MAPPING.items()}

# Default durations for scenarios in minutes
SCENARIO_DEFAULT_DURATIONS = {
    mode: mode.default_duration_minutes for mode in ScenarioMode
}

# Fan Mode Mapping (based on fan.py implementation)
# fanSpeed from dashboard: 0, 1, 2, 3
FAN_MODE_MAPPING = {
    FanSpeed.OFF: FAN_OFF,
    FanSpeed.LOW: FAN_LOW,
    FanSpeed.MEDIUM: FAN_MEDIUM,
    FanSpeed.HIGH: FAN_HIGH,
}

FAN_MODE_REVERSE_MAPPING = {v: k for k, v in FAN_MODE_MAPPING.items()}

# HVAC Mode Mapping (season values to HVAC modes)
# Season from dashboard: 0 (transition), 1 (heating), 2 (cooling)
HVAC_MODE_MAPPING = {
    Season.TRANSITIONAL: HVACMode.FAN_ONLY,
    Season.HEATING: HVACMode.HEAT,
    Season.COOLING: HVACMode.COOL,
}

# Reverse mapping for setting HVAC modes
# Maps HVAC mode to season value (0=transition, 1=heating, 2=cooling)
# OFF mode is handled separately via hpStandby field
HVAC_MODE_REVERSE_MAPPING = {
    HVACMode.OFF: None,  # Turn off device via hpStandby=True
    HVACMode.FAN_ONLY: Season.TRANSITIONAL,
    HVACMode.HEAT: Season.HEATING,
    HVACMode.COOL: Season.COOLING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoClime climate entity from a config entry.

    Creates the climate entity for the main ComfoClime device.
    The climate entity controls HVAC operation, temperature, fan speed,
    and preset modes.

    Args:
        hass: Home Assistant instance
        config_entry: Config entry for this integration
        async_add_entities: Callback to add entities

    Note:
        Only one climate entity is created per integration instance,
        representing the main ComfoClime device.
    """
    data = hass.data[DOMAIN][config_entry.entry_id]
    api: ComfoClimeAPI = data["api"]
    dashboard_coordinator: ComfoClimeDashboardCoordinator = data["coordinator"]
    thermalprofile_coordinator: ComfoClimeThermalprofileCoordinator = data[
        "tpcoordinator"
    ]
    main_device: dict[str, Any] | None = data.get("main_device")

    if not main_device:
        _LOGGER.warning("No main device found - cannot create climate entity")
        return

    climate_entity = ComfoClimeClimate(
        dashboard_coordinator,
        thermalprofile_coordinator,
        api,
        main_device,
        config_entry,
    )

    async_add_entities([climate_entity])


class ComfoClimeClimate(CoordinatorEntity, ClimateEntity):
    """ComfoClime Climate entity for HVAC control.

    Provides climate control for the ComfoClime ventilation and heat pump
    system. Supports temperature control, HVAC modes (heating/cooling/fan),
    preset modes (comfort/power/eco/manual), fan speed control, and
    special scenario modes (cooking/party/away/boost).

    The entity monitors two coordinators:
        - DashboardCoordinator: Real-time temperature, fan, and season data
        - ThermalprofileCoordinator: Thermal profile and preset settings

    Attributes:
        hvac_mode: Current HVAC mode (off/fan_only/heat/cool)
        current_temperature: Current indoor temperature in °C
        target_temperature: Target temperature in °C
        preset_mode: Current preset mode
        fan_mode: Current fan speed mode
        hvac_action: Current HVAC action (idle/heating/cooling/fan)

    Example:
        >>> # Set heating mode with comfort preset at 22°C
        >>> await climate.async_set_hvac_mode(HVACMode.HEAT)
        >>> await climate.async_set_preset_mode(PRESET_COMFORT)
        >>> await climate.async_set_temperature(temperature=22.0)
    """

    def __init__(
        self,
        dashboard_coordinator: ComfoClimeDashboardCoordinator,
        thermalprofile_coordinator: ComfoClimeThermalprofileCoordinator,
        api: ComfoClimeAPI,
        device: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
        """Initialize the ComfoClime climate entity.

        Args:
            dashboard_coordinator: Coordinator for dashboard data
            thermalprofile_coordinator: Coordinator for thermal profile data
            api: ComfoClime API instance
            device: Device info dictionary
            entry: Config entry for this integration
        """
        super().__init__(dashboard_coordinator)
        self._api = api
        self._thermalprofile_coordinator = thermalprofile_coordinator
        self._device = device
        self._entry = entry

        # Entity attributes
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_name = None  # Use device name
        self._attr_has_entity_name = True
        self._attr_translation_key = "climate"

        # Temperature settings
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.1
        self._attr_target_temperature_step = 0.5

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        # HVAC modes
        self._attr_hvac_modes = list(HVAC_MODE_REVERSE_MAPPING.keys())

        # Preset modes (automatic profiles + manual mode)
        self._attr_preset_modes = [PRESET_MANUAL] + list(PRESET_REVERSE_MAPPING.keys())

        # Fan modes
        self._attr_fan_modes = list(FAN_MODE_REVERSE_MAPPING.keys())

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, register listeners for both coordinators."""
        await super().async_added_to_hass()

        # Also listen to thermal profile coordinator updates
        # This ensures target_temperature updates are reflected immediately
        self.async_on_remove(
            self._thermalprofile_coordinator.async_add_listener(
                self._handle_coordinator_update
            )
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update internal state from coordinator data
        # This ensures the entity reflects the latest data from ComfoClime
        try:
            if self.coordinator.data:
                _LOGGER.debug("Coordinator update received: %s", self.coordinator.data)
        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.warning("Error processing coordinator data: %s", e)

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Climate entity depends on both dashboard and thermal profile coordinators,
        so we check both for successful updates.
        """
        return (
            self.coordinator.last_update_success
            or self._thermalprofile_coordinator.last_update_success
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device["uuid"])},
            "name": self._device.get("displayName", "ComfoClime"),
            "manufacturer": "Zehnder",
            "model": self._device.get("@modelType", "ComfoClime"),
            "sw_version": self._device.get("version"),
        }

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature from dashboard data."""
        if self.coordinator.data:
            return self.coordinator.data.indoor_temperature
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature for display.

        Uses manualTemperature from thermal profile as the display value.
        This represents the last set temperature.
        """
        tp = self._thermalprofile_coordinator.data or {}
        temp = (tp.get("temperature") or {}).get("manualTemperature")
        if isinstance(temp, (int, float)):
            return temp
        return None

    @property
    def min_temp(self) -> float:
        """Return minimum temperature as per system requirements."""
        return 10.0

    @property
    def max_temp(self) -> float:
        """Return maximum temperature as per system requirements."""
        return 30.0

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode from dashboard data.

        Maps the season field from dashboard to HVAC mode:
        - season 0 (transition) → FAN_ONLY
        - season 1 (heating) → HEAT
        - season 2 (cooling) → COOL
        - season None or unknown → OFF (default fallback)
        - hpStandby true + season None → OFF (device powered off)
        """
        if not self.coordinator.data:
            return HVACMode.OFF

        # Get season and hpStandby values from DashboardData model
        hpStandby = self.coordinator.data.hp_standby
        season = self.coordinator.data.season

        # If device is in standby (powered off), always report OFF regardless of season
        if hpStandby is True:
            return HVACMode.OFF

        # Map season from dashboard to HVAC mode using mapping
        # Falls back to OFF if season is None or unknown
        return HVAC_MODE_MAPPING.get(season, HVACMode.OFF)

    @property
    def hvac_action(self) -> list[HVACAction]:
        """Return current HVAC action based on dashboard heatPumpStatus.

        Heat pump status codes (from API documentation):

        Bit-Mapping:
        Bit         | 7    | 6          | 5    | 4          | 3              | 2       | 1       | 0
        ------------|------|------------|------|------------|----------------|---------|---------|-----
        Value (dec) | 128  | 64         | 32   | 16         | 8              | 4       | 2       | 1
        Value (hex) | 0x80 | 0x40       | 0x20 | 0x10       | 0x08           | 0x04    | 0x02    | 0x01
        Meaning     | IDLE | DEFROSTING | IDLE | DRYING (?) | PREHEATING (?) | COOLING | HEATING | IDLE

        Reference: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes
        """
        if not self.coordinator.data:
            return [HVACAction.OFF]

        heat_pump_status = self.coordinator.data.heat_pump_status

        if heat_pump_status in [None, 0]:
            return [HVACAction.OFF]

        status_mapping = {
            0x02: HVACAction.HEATING,
            0x04: HVACAction.COOLING,
            0x08: HVACAction.PREHEATING,  # Not sure
            0x10: HVACAction.DRYING,  # Not sure
            0x20: HVACAction.IDLE,  # Unused
            0x40: HVACAction.DEFROSTING,  # Not sure
            0x80: HVACAction.IDLE,  # Unused
        }

        active_flags = [
            status for mask, status in status_mapping.items() if heat_pump_status & mask
        ]

        if not active_flags:
            return [HVACAction.IDLE]

        return active_flags

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode from dashboard data.

        Returns PRESET_MANUAL (none) if in manual mode (status=0 or setPointTemperature is set).
        Returns preset name (comfort/boost/eco) if in automatic mode (status=1).
        """
        if not self.coordinator.data:
            return None

        # Check if in manual mode using DashboardData model properties
        set_point = self.coordinator.data.set_point_temperature
        status = self.coordinator.data.status

        # Manual mode: setPointTemperature is set or status=0
        if set_point is not None or status == 0:
            return PRESET_MANUAL

        # Automatic mode: return the temperatureProfile preset
        temp_profile = self.coordinator.data.temperature_profile
        if isinstance(temp_profile, int):
            return PRESET_MAPPING.get(temp_profile)

        return None

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode from dashboard data.

        Maps fanSpeed from dashboard (0-3) to fan mode strings:
        - 0: off
        - 1: low
        - 2: medium
        - 3: high
        """
        if self.coordinator.data:
            fan_speed = self.coordinator.data.fan_speed
            if isinstance(fan_speed, int):
                return FAN_MODE_MAPPING.get(fan_speed)
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return self._attr_fan_modes

    def _get_current_season(self) -> Season:
        """Get the current season value from dashboard.

        Returns:
            Season enum (TRANSITIONAL, HEATING, or COOLING)
        """
        if self.coordinator.data:
            season = self.coordinator.data.season
            if isinstance(season, int) and season in Season._value2member_map_:
                return Season(season)
        return Season.TRANSITIONAL

    async def _async_refresh_coordinators(self, blocking: bool = True) -> None:
        """Refresh both dashboard and thermal profile coordinators.

        Args:
            blocking: If True (default), waits for coordinators to complete refresh.
                     If False, schedules non-blocking refresh in background.

        When blocking=True (default for "set then fetch" pattern):
        - Waits for both coordinators to complete refresh
        - Ensures UI shows actual device state after setting values
        - Prevents stale state display

        When blocking=False:
        - Schedules non-blocking refresh for both coordinators
        - Prevents UI from becoming unresponsive
        - Updates happen in background
        """

        async def safe_refresh(coordinator, name: str) -> None:
            """Safely refresh coordinator with error handling."""
            try:
                await coordinator.async_request_refresh()
            except Exception:
                _LOGGER.exception("Refresh failed for %s", name)

        if blocking:
            # Blocking mode: Wait for both coordinators to complete
            # This ensures "set then fetch" behavior - UI reflects actual device state
            await safe_refresh(self.coordinator, "dashboard")
            await safe_refresh(self._thermalprofile_coordinator, "thermal_profile")
        else:
            # Non-blocking mode: Schedule refresh as background tasks
            self.hass.async_create_task(safe_refresh(self.coordinator, "dashboard"))
            self.hass.async_create_task(
                safe_refresh(self._thermalprofile_coordinator, "thermal_profile")
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature via dashboard API in manual mode.

        Setting a manual temperature activates manual mode (status=0) and replaces
        the preset profiles (seasonProfile, temperatureProfile) with setPointTemperature.
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.warning("No temperature provided in kwargs")
            return

        try:
            _LOGGER.debug(
                "Setting manual temperature to %s°C via dashboard API", temperature
            )

            # Setting setPointTemperature should explicitly switch to manual mode (status=0)
            # and replaces seasonProfile/temperatureProfile. We send status=0 to ensure
            # the device leaves automatic preset control when user changes temperature.
            await self.async_update_dashboard(
                set_point_temperature=temperature,
                status=0,
            )

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout setting temperature to %s°C. "
                "This may indicate network connectivity issues with the device. "
                "The temperature may still be set successfully.",
                temperature,
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error setting temperature to %s°C", temperature)
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception(
                "Invalid data while setting temperature to %s°C", temperature
            )

    async def async_update_dashboard(self, **kwargs: Any) -> None:
        """Update dashboard settings via API.

        Wrapper method that delegates to the API's async_update_dashboard method.
        This ensures all dashboard updates go through the centralized API method.

        Args:
            **kwargs: Dashboard fields to update (set_point_temperature, fan_speed,
                     season, hpStandby, schedule, temperature_profile,
                     season_profile, status)
        """
        await self._api.async_update_dashboard(**kwargs)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode by updating season via thermal profile API.

        The HVAC mode is determined by the season field in the thermal profile:
        - OFF: Sets hpStandby=True via dashboard (device off)
        - FAN_ONLY: Sets season=0 (transition) via thermal profile, hpStandby=False
        - HEAT: Sets season=1 (heating) via thermal profile, hpStandby=False
        - COOL: Sets season=2 (cooling) via thermal profile, hpStandby=False
        """
        try:
            # Use HVAC_MODE_REVERSE_MAPPING to get season value
            if hvac_mode not in HVAC_MODE_REVERSE_MAPPING:
                _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
                return

            season_value = HVAC_MODE_REVERSE_MAPPING[hvac_mode]

            # OFF mode: Set hpStandby=True via dashboard to turn off the device
            if hvac_mode == HVACMode.OFF:
                _LOGGER.debug("Setting HVAC mode to OFF - setting hpStandby=True")
                await self.async_update_dashboard(hpStandby=True)
            else:
                # Active modes: Use atomic operation to set both season and hpStandby
                # This prevents race conditions between thermal profile and dashboard updates
                _LOGGER.debug(
                    "Setting HVAC mode to %s - "
                    "atomically setting season=%s and hpStandby=False",
                    hvac_mode,
                    season_value,
                )
                await self._api.async_set_hvac_season(
                    season=season_value, hpStandby=False
                )

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout setting HVAC mode to %s. "
                "This may indicate network connectivity issues with the device.",
                hvac_mode,
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error setting HVAC mode to %s", hvac_mode)
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception("Invalid data while setting HVAC mode to %s", hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode via dashboard API.

        Setting PRESET_MANUAL (none) switches to manual temperature control mode.
        Setting other presets (comfort/boost/eco) activates automatic mode with
        both seasonProfile and temperatureProfile set to the selected preset value.

        Args:
            preset_mode: The preset mode to activate
        """
        try:
            # Manual mode: User wants to use manual temperature control
            if preset_mode == PRESET_MANUAL:
                _LOGGER.debug(
                    "Switching to manual temperature control mode - "
                    "user needs to set temperature manually"
                )
                # Set status=0 to activate manual mode
                # setPointTemperature should be set separately via async_set_temperature
                await self.async_update_dashboard(status=0)

                # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
                await self._async_refresh_coordinators(blocking=True)
                return

            # Check if this is a scenario mode
            if preset_mode in SCENARIO_REVERSE_MAPPING:
                await self.async_set_scenario_mode(preset_mode)
                return

            # Automatic mode with preset profile
            if preset_mode not in PRESET_REVERSE_MAPPING:
                _LOGGER.error("Unknown preset mode: %s", preset_mode)
                return

            # Map preset mode to profile value (0=comfort, 1=boost, 2=eco)
            profile_value = PRESET_REVERSE_MAPPING[preset_mode]

            _LOGGER.debug(
                "Setting preset mode to %s (profile=%s) "
                "via dashboard API - activates automatic mode",
                preset_mode,
                profile_value,
            )

            # Set both temperatureProfile and seasonProfile to the preset value
            # and activate automatic mode (status=1)
            # This replaces setPointTemperature with preset-based control
            await self.async_update_dashboard(
                temperature_profile=profile_value,
                season_profile=profile_value,
                status=1,
            )

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout setting preset mode to %s. "
                "This may indicate network connectivity issues with the device.",
                preset_mode,
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error setting preset mode to %s", preset_mode)
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception(
                "Invalid data while setting preset mode to %s", preset_mode
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode by updating fan speed via dashboard API.

        Maps fan mode strings to fanSpeed values:
        - off: 0
        - low: 1
        - medium: 2
        - high: 3
        """
        if fan_mode not in FAN_MODE_REVERSE_MAPPING:
            _LOGGER.error("Unknown fan mode: %s", fan_mode)
            return

        try:
            # Map fan mode to fan speed value
            fan_speed = FAN_MODE_REVERSE_MAPPING[fan_mode]

            # Update fan speed via dashboard API
            await self.async_update_dashboard(fan_speed=fan_speed)

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout setting fan mode to %s. "
                "This may indicate network connectivity issues with the device.",
                fan_mode,
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error setting fan mode to %s", fan_mode)
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception("Invalid data while setting fan mode to %s", fan_mode)

    async def async_set_scenario_mode(
        self,
        scenario_mode: str,
        duration: int | float | None = None,
        start_delay: str | None = None,
    ) -> None:
        """Set scenario mode via dashboard API.

        Activates a special operating mode (scenario) on the ComfoClime device.

        Supported scenarios:
        - cooking: High ventilation for cooking (default: 30 min)
        - party: High ventilation for parties (default: 30 min)
        - away: Reduced mode for vacation (default: 24 hours)
        - boost: Maximum power boost (default: 30 min)

        Args:
            scenario_mode: The scenario mode to activate (cooking, party, away, boost)
            duration: Optional duration in minutes. If not provided, uses default.
            start_delay: Optional start delay as datetime string (YYYY-MM-DD HH:MM:SS)
        """
        if scenario_mode not in SCENARIO_REVERSE_MAPPING:
            _LOGGER.error("Unknown scenario mode: %s", scenario_mode)
            return

        try:
            # Map scenario mode to API value
            scenario_value = SCENARIO_REVERSE_MAPPING[scenario_mode]

            # Calculate duration in seconds
            if duration is not None:
                # User provided duration in minutes, convert to seconds
                scenario_time_left = int(duration * 60)
            else:
                # Use default duration from mapping (already in minutes)
                default_duration = SCENARIO_DEFAULT_DURATIONS.get(scenario_value, 30)
                scenario_time_left = default_duration * 60

            # Calculate start delay in seconds if provided
            scenario_start_delay = None
            if start_delay is not None:
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    # Parse the datetime string
                    tz = ZoneInfo(self.hass.config.time_zone)
                    start_time = datetime.strptime(start_delay, "%Y-%m-%d %H:%M:%S")
                    start_time = start_time.replace(tzinfo=tz)
                    now = datetime.now(tz)

                    # Calculate delay in seconds from now
                    delay_seconds = int((start_time - now).total_seconds())
                    if delay_seconds > 0:
                        scenario_start_delay = delay_seconds
                    else:
                        _LOGGER.warning(
                            "Start delay %s is in the past, starting immediately",
                            start_delay,
                        )
                except ValueError:
                    _LOGGER.exception("Invalid start_delay format '%s'", start_delay)
                    raise

            _LOGGER.debug(
                "Setting scenario mode to %s (value=%s) "
                "with duration=%ss, start_delay=%ss",
                scenario_mode,
                scenario_value,
                scenario_time_left,
                scenario_start_delay,
            )

            # Update scenario via dashboard API
            await self.async_update_dashboard(
                scenario=scenario_value,
                scenario_time_left=scenario_time_left,
                scenario_start_delay=scenario_start_delay,
            )

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ValueError,
            KeyError,
            TypeError,
        ):
            _LOGGER.exception("Failed to set scenario mode %s", scenario_mode)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dashboard data as extra state attributes.

        Exposes all available data from the ComfoClime Dashboard API interface:
        - Dashboard data from /system/{UUID}/dashboard
        - Scenario time left (remaining duration of active scenario in seconds)
        """
        attrs = {}

        # Add complete dashboard data from Dashboard API interface
        if self.coordinator.data:
            attrs["dashboard"] = self.coordinator.data

            # Add scenario time left as a separate attribute for easier access
            scenario_time_left = self.coordinator.data.get("scenarioTimeLeft")
            if scenario_time_left is not None:
                attrs["scenario_time_left"] = scenario_time_left
                # Convert to human-readable format
                hours, remainder = divmod(scenario_time_left, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours > 0:
                    attrs["scenario_time_left_formatted"] = (
                        f"{int(hours)}h {int(minutes)}m"
                    )
                elif minutes > 0:
                    attrs["scenario_time_left_formatted"] = (
                        f"{int(minutes)}m {int(seconds)}s"
                    )
                else:
                    attrs["scenario_time_left_formatted"] = f"{int(seconds)}s"

        # For transparency: expose last_manual_temperature from thermal profile if available
        tp = getattr(self._thermalprofile_coordinator, "data", None) or {}
        manual_temp = (tp.get("temperature") or {}).get("manualTemperature")
        if isinstance(manual_temp, (int, float)):
            attrs["last_manual_temperature"] = manual_temp

        return attrs

    async def async_turn_off(self) -> None:
        """Turn the climate device off.

        Sets hpStandby=True via dashboard API to turn off the heat pump.
        This is equivalent to setting HVAC mode to OFF.
        """
        try:
            _LOGGER.debug("Turning off climate device - setting hpStandby=True")
            await self.async_update_dashboard(hpStandby=True)

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout turning off climate device. "
                "This may indicate network connectivity issues with the device."
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error turning off climate device")
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception("Invalid data while turning off climate device")

    async def async_turn_on(self) -> None:
        """Turn the climate device on.

        Sets hpStandby=False via dashboard API to turn on the heat pump.
        The season remains unchanged.
        """
        try:
            _LOGGER.debug("Turning on climate device - setting hpStandby=False")
            await self.async_update_dashboard(hpStandby=False)

            # Wait for coordinators to refresh (blocking) to ensure UI shows actual device state
            await self._async_refresh_coordinators(blocking=True)

        except (asyncio.TimeoutError, asyncio.CancelledError):
            _LOGGER.exception(
                "Timeout turning on climate device. "
                "This may indicate network connectivity issues with the device."
            )
        except aiohttp.ClientError:
            _LOGGER.exception("Network error turning on climate device")
        except (ValueError, KeyError, TypeError):
            _LOGGER.exception("Invalid data while turning on climate device")
