"""Climate platform for ComfoClime integration."""
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import ComfoClimeDashboardCoordinator
from .comfoclime_api import (
    ComfoClimeConnectionError,
    ComfoClimeTimeoutError,
    ComfoClimeAuthenticationError,
)

_LOGGER = logging.getLogger(__name__)

# Temperature Profile Presets
PRESET_MAPPING = {
    0: "comfort",
    1: "power",
    2: "eco",
}

PRESET_REVERSE_MAPPING = {v: k for k, v in PRESET_MAPPING.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoClime climate entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api = data["api"]
    dashboard_coordinator = data["coordinator"]
    thermalprofile_coordinator = data["tpcoordinator"]
    main_device = data.get("main_device")

    if not main_device:
        _LOGGER.warning("No main device found - cannot create climate entity")
        return

    climate_entity = ComfoClimeClimate(
        dashboard_coordinator,
        thermalprofile_coordinator,
        api,
        main_device,
        config_entry
    )

    async_add_entities([climate_entity])


class ComfoClimeClimate(CoordinatorEntity[ComfoClimeDashboardCoordinator], ClimateEntity):
    """ComfoClime Climate entity."""

    def __init__(self, dashboard_coordinator, thermalprofile_coordinator, api, device, entry):
        """Initialize the climate entity."""
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
        self._attr_precision = 0.5
        self._attr_target_temperature_step = 0.5

        # HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
        )

        # Preset modes
        self._attr_preset_modes = list(PRESET_REVERSE_MAPPING.keys())

        # Add thermal profile coordinator listener
        self._thermalprofile_coordinator.async_add_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._thermalprofile_coordinator.last_update_success
        )

    @property
    def device_info(self):
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
            return self.coordinator.data.get("indoorTemperature")
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature from thermal profile data.
        
        Returns comfortTemperature when temperature.status=1 (automatic mode).
        Returns manualTemperature when temperature.status=0 (manual mode).
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return None

        temp_data = thermal_data.get("temperature", {})
        
        # When automatic mode is OFF (status=0), always use manual temperature
        if self._get_temperature_status() == 0:
            return temp_data.get("manualTemperature")
        
        # When automatic mode is ON (status=1), use comfort temperature based on season
        season = self._get_current_season()

        if season == 1:  # heating
            heating_data = thermal_data.get("heatingThermalProfileSeasonData", {})
            return heating_data.get("comfortTemperature")
        elif season == 2:  # cooling
            cooling_data = thermal_data.get("coolingThermalProfileSeasonData", {})
            return cooling_data.get("comfortTemperature")

        # Fallback: manual temperature (for transitional season)
        return temp_data.get("manualTemperature")

    @property
    def min_temp(self) -> float:
        """Return minimum temperature as per Copilot instructions."""
        return 10.0

    @property
    def max_temp(self) -> float:
        """Return maximum temperature as per Copilot instructions."""
        return 30.0

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode from thermal profile data."""
        if not self._thermalprofile_coordinator.data:
            return HVACMode.OFF

        season_data = self._thermalprofile_coordinator.data.get("season", {})
        season = self._get_current_season()
        status = season_data.get("status", 1)  # 0=manual, 1=automatic

        # Basierend auf Season - in Übergangszeit ("transitional") ist immer Lüftung aktiv
        if season == 0:  # transitional - always fan_only regardless of status
            return HVACMode.FAN_ONLY

        # Für Heiz-/Kühlsaison: Wenn status=1 (automatic), dann ist das System "aus"
        if status == 1:
            return HVACMode.OFF

        # Basierend auf Season für manuelle Modi
        if season == 1:  # heating
            return HVACMode.HEAT
        if season == 2:  # cooling
            return HVACMode.COOL

        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        # Fan Speed für Systemaktivität
        fan_speed = self.coordinator.data.get("fanSpeed") if self.coordinator.data else None
        if not self._is_system_active(fan_speed):
            return HVACAction.OFF

        # Season für Art der Aktion
        season_data = self._thermalprofile_coordinator.data.get("season", {}) if self._thermalprofile_coordinator.data else {}
        season = self._get_current_season()
        status = season_data.get("status", 1)

        # In Übergangszeit ist immer Lüftung aktiv, unabhängig vom Status
        if season == 0:  # transitional
            return HVACAction.FAN

        if status == 1:  # automatic = aus für Heiz-/Kühlsaison
            return HVACAction.OFF

        current_temp = self.current_temperature
        target_temp = self.target_temperature

        if current_temp is None or target_temp is None:
            return HVACAction.FAN

        temp_diff = current_temp - target_temp

        if season == 1 and temp_diff < -0.5:  # heating
            return HVACAction.HEATING
        elif season == 2 and temp_diff > 0.5:  # cooling
            return HVACAction.COOLING
        elif season in [1, 2]:
            # Bisher wurde hier IDLE zurückgegeben. Wunsch: Solange der Lüfter läuft
            # (also System aktiv ist) statt "Leerlauf" den Ventilations-Status anzeigen.
            # Daher geben wir FAN zurück. "Leerlauf" (IDLE) taucht damit nur noch auf,
            # wenn der Lüfter tatsächlich steht – dieser Fall wird weiter oben bereits
            # als OFF behandelt. Sollte später ein echter Unterschied zwischen OFF und
            # IDLE nötig sein, kann hier eine differenziertere Logik ergänzt werden.
            return HVACAction.FAN

        return HVACAction.FAN  # fallback (should not be reached)

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode from coordinator data."""
        # Prüfe Dashboard Coordinator (für aktuellen Zustand)
        if self.coordinator.data:
            temp_profile = self.coordinator.data.get("temperatureProfile")
            if isinstance(temp_profile, int):
                return PRESET_MAPPING.get(temp_profile)
            if isinstance(temp_profile, str) and temp_profile.isdigit():
                return PRESET_MAPPING.get(int(temp_profile))

        # Fallback: Prüfe Thermal Profile Coordinator (für Select Entity Änderungen)
        if self._thermalprofile_coordinator.data:
            temp_profile = self._thermalprofile_coordinator.data.get("temperatureProfile")
            if isinstance(temp_profile, int):
                return PRESET_MAPPING.get(temp_profile)
            if isinstance(temp_profile, str) and temp_profile.isdigit():
                return PRESET_MAPPING.get(int(temp_profile))

        return None

    def _is_system_active(self, fan_speed) -> bool:
        """Check if ventilation system is running."""
        if not fan_speed:
            return False

        if isinstance(fan_speed, str):
            return fan_speed not in ["0", "standby", ""]
        if isinstance(fan_speed, int):
            return fan_speed > 0

        return False

    def _get_temperature_status(self) -> int:
        """Get the temperature.status value from thermal profile.
        
        Returns:
            1 if automatic comfort temperature is enabled (default)
            0 if manual temperature mode is active
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return 1  # default to automatic
        
        temp_data = thermal_data.get("temperature", {})
        return temp_data.get("status", 1)
    
    def _get_current_season(self) -> int:
        """Get the current season value from thermal profile.
        
        Returns:
            0 for transitional, 1 for heating, 2 for cooling
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return 0
        
        season_data = thermal_data.get("season", {})
        return season_data.get("season", 0)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature by updating thermal profile.
        
        Respects the temperature.status switch:
        - When temperature.status=1 (automatic ON): Updates comfortTemperature for current season
        - When temperature.status=0 (automatic OFF): Updates manualTemperature only
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.warning("No temperature provided in kwargs")
            return

        try:
            # Get thermal profile data to check temperature.status
            thermal_data = self._thermalprofile_coordinator.data
            if not thermal_data:
                _LOGGER.error("No thermal profile data available")
                return
            
            temp_status = self._get_temperature_status()
            updates = {}
            
            # When automatic comfort temperature switch is OFF (status=0)
            # Only update manual temperature, regardless of HVAC mode
            if temp_status == 0:
                _LOGGER.debug(f"Automatic comfort temperature is OFF - setting manualTemperature to {temperature}")
                updates = {
                    "temperature": {
                        "manualTemperature": temperature
                    }
                }
            else:
                # When automatic comfort temperature switch is ON (status=1)
                # Update the appropriate comfort temperature based on current season/HVAC mode
                hvac_mode = self.hvac_mode
                season = self._get_current_season()
                
                if hvac_mode == HVACMode.HEAT or season == 1:
                    # Update heating comfort temperature
                    _LOGGER.debug(f"Automatic comfort temperature is ON - setting heating comfortTemperature to {temperature}")
                    updates = {
                        "heatingThermalProfileSeasonData": {
                            "comfortTemperature": temperature
                        }
                    }
                elif hvac_mode == HVACMode.COOL or season == 2:
                    # Update cooling comfort temperature
                    _LOGGER.debug(f"Automatic comfort temperature is ON - setting cooling comfortTemperature to {temperature}")
                    updates = {
                        "coolingThermalProfileSeasonData": {
                            "comfortTemperature": temperature
                        }
                    }
                else:
                    # For transitional season or FAN_ONLY/OFF modes, update manual temperature
                    _LOGGER.debug(f"Transitional season or OFF/FAN_ONLY mode - setting manualTemperature to {temperature}")
                    updates = {
                        "temperature": {
                            "manualTemperature": temperature
                        }
                    }

            # Update thermal profile using working API method
            await self.hass.async_add_executor_job(
                self._api.update_thermal_profile, updates
            )

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set temperature to {temperature}")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode by updating season and status."""
        try:
            # Map HVAC modes to season/status values
            if hvac_mode == HVACMode.OFF:
                # Set status to automatic (1) which turns the system off
                updates = {"season": {"status": 1}}
            elif hvac_mode == HVACMode.FAN_ONLY:
                # Set season to transitional (0)
                updates = {"season": {"season": 0, "status": 0}}
            elif hvac_mode == HVACMode.HEAT:
                # Set season to heating (1) and status to manual (0)
                updates = {"season": {"season": 1, "status": 0}}
            elif hvac_mode == HVACMode.COOL:
                # Set season to cooling (2) and status to manual (0)
                updates = {"season": {"season": 2, "status": 0}}
            else:
                _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
                return

            # Update thermal profile using working API method
            await self.hass.async_add_executor_job(
                self._api.update_thermal_profile, updates
            )

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set HVAC mode {hvac_mode}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode by updating temperature profile."""
        if preset_mode not in PRESET_REVERSE_MAPPING:
            _LOGGER.error(f"Unknown preset mode: {preset_mode}")
            return

        try:
            # Map preset mode to temperature profile value
            temperature_profile = PRESET_REVERSE_MAPPING[preset_mode]

            # Use working API method to set device setting
            await self.hass.async_add_executor_job(
                self._api.set_device_setting, temperature_profile
            )

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set preset mode {preset_mode}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debug information as extra state attributes."""
        attrs = {}

        # Add thermal profile data for debugging
        if self._thermalprofile_coordinator.data:
            attrs["thermal_profile"] = self._thermalprofile_coordinator.data

        # Add dashboard data for debugging
        if self.coordinator.data:
            attrs["dashboard_data"] = {
                "indoor_temperature": self.coordinator.data.get("indoorTemperature"),
                "fan_speed": self.coordinator.data.get("fanSpeed"),
                "temperature_profile": self.coordinator.data.get("temperatureProfile"),
            }

        # Add current mappings for debugging
        thermal_data = self._thermalprofile_coordinator.data
        if thermal_data:
            season_data = thermal_data.get("season", {})
            temp_data = thermal_data.get("temperature", {})
            attrs["current_mappings"] = {
                "season_season": season_data.get("season"),
                "season_status": season_data.get("status"),
                "temperature_status": temp_data.get("status"),
                "temperature_profile": thermal_data.get("temperatureProfile"),
                "hvac_mode_calculated": str(self.hvac_mode),
                "preset_mode_calculated": self.preset_mode,
                "temperature_mode": "automatic" if self._get_temperature_status() == 1 else "manual",
            }

        # Add API mapping documentation
        attrs["api_mappings"] = {
            "hvac_modes": {
                "off": "season.status=1 (automatic)",
                "fan_only": "season.season=0 (transitional)",
                "heat": "season.season=1 + season.status=0",
                "cool": "season.season=2 + season.status=0"
            },
            "preset_modes": {
                "comfort": "temperatureProfile=0",
                "power": "temperatureProfile=1",
                "eco": "temperatureProfile=2"
            },
            "temperature_modes": {
                "automatic": "temperature.status=1 (uses comfortTemperature)",
                "manual": "temperature.status=0 (uses manualTemperature)"
            },
            "working_methods": {
                "hvac_mode": "update_thermal_profile(season)",
                "preset_mode": "set_device_setting(temperature_profile)",
                "temperature": "update_thermal_profile(seasonData or temperature)"
            }
        }

        return attrs
