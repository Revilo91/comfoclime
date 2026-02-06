"""Constants and Enums for ComfoClime integration."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, Field

# Integration Domain
DOMAIN = "comfoclime"

# Supported Platforms
PLATFORMS = ["sensor", "switch", "number", "select", "fan", "climate"]

# Mapping for thermal profile updates (API payload structure)
# Maps kwargs parameters to (section, key) in the API payload
# key=None means top-level field in the section
THERMAL_PROFILE_MAPPING: dict[str, tuple[str, str | None]] = {
    # season fields
    "season_status": ("season", "status"),
    "season_value": ("season", "season"),
    "heating_threshold_temperature": ("season", "heatingThresholdTemperature"),
    "cooling_threshold_temperature": ("season", "coolingThresholdTemperature"),
    # temperature fields
    "temperature_status": ("temperature", "status"),
    "manual_temperature": ("temperature", "manualTemperature"),
    # top-level fields
    "temperature_profile": ("temperatureProfile", None),
    # heating profile fields
    "heating_comfort_temperature": (
        "heatingThermalProfileSeasonData",
        "comfortTemperature",
    ),
    "heating_knee_point_temperature": (
        "heatingThermalProfileSeasonData",
        "kneePointTemperature",
    ),
    "heating_reduction_delta_temperature": (
        "heatingThermalProfileSeasonData",
        "reductionDeltaTemperature",
    ),
    # cooling profile fields
    "cooling_comfort_temperature": (
        "coolingThermalProfileSeasonData",
        "comfortTemperature",
    ),
    "cooling_knee_point_temperature": (
        "coolingThermalProfileSeasonData",
        "kneePointTemperature",
    ),
    "cooling_temperature_limit": (
        "coolingThermalProfileSeasonData",
        "temperatureLimit",
    ),
}


class ScenarioMode(IntEnum):
    """Scenario modes supported by ComfoClime.

    These modes temporarily override normal operation for specific use cases.
    Each mode has a default duration and can be activated via climate presets
    or the set_scenario_mode service.
    """

    COOKING = 4
    PARTY = 5
    HOLIDAY = 7
    BOOST = 8

    @property
    def default_duration_minutes(self) -> int:
        """Get default duration in minutes for this scenario.

        Returns:
            Default duration in minutes for the scenario mode.
        """
        durations = {
            ScenarioMode.COOKING: 30,
            ScenarioMode.PARTY: 30,
            ScenarioMode.HOLIDAY: 24 * 60,  # 24 hours
            ScenarioMode.BOOST: 30,
        }
        return durations[self]

    @property
    def preset_name(self) -> str:
        """Get Home Assistant preset name for this scenario.

        Returns:
            Home Assistant preset name string.
        """
        names = {
            ScenarioMode.COOKING: "cooking",
            ScenarioMode.PARTY: "party",
            ScenarioMode.HOLIDAY: "away",
            ScenarioMode.BOOST: "scenario_boost",
        }
        return names[self]

    @classmethod
    def from_preset_name(cls, name: str) -> ScenarioMode | None:
        """Get ScenarioMode from preset name.

        Args:
            name: Home Assistant preset name.

        Returns:
            ScenarioMode instance or None if not found.
        """
        for mode in cls:
            if mode.preset_name == name:
                return mode
        return None


class Season(IntEnum):
    """Season modes for heating/cooling control.

    Determines the operating mode of the heat pump:
    - TRANSITIONAL: Fan only, no heating or cooling
    - HEATING: Heating mode active
    - COOLING: Cooling mode active
    """

    TRANSITIONAL = 0
    HEATING = 1
    COOLING = 2


class TemperatureProfile(IntEnum):
    """Temperature profile presets.

    Predefined temperature profiles for automatic mode:
    - COMFORT: Comfort temperature settings
    - POWER: Power/Boost temperature settings
    - ECO: Energy-saving temperature settings
    """

    COMFORT = 0
    POWER = 1
    ECO = 2


class FanSpeed(IntEnum):
    """Discrete fan speed levels.

    Fan speed levels supported by ComfoClime:
    - OFF: Fan disabled
    - LOW: Low fan speed
    - MEDIUM: Medium fan speed
    - HIGH: High fan speed
    """

    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def to_percentage(self) -> int:
        """Convert fan speed to percentage (0-100).

        Returns:
            Fan speed as percentage (0, 33, 66, 100).
        """
        if self == FanSpeed.HIGH:
            return 100
        return self.value * 33

    @classmethod
    def from_percentage(cls, percentage: int) -> FanSpeed:
        """Convert percentage to fan speed level.

        Args:
            percentage: Fan speed as percentage (0-100).

        Returns:
            Corresponding FanSpeed level.
        """
        step = round(percentage / 33)
        step = max(0, min(step, 3))  # Clamp to 0-3
        return cls(step)


class APIDefaults(BaseModel):
    """Default values for API configuration.

    Immutable configuration values for API timeouts, caching, and rate limiting.
    These values can be overridden when instantiating ComfoClimeAPI.

    Note: frozen=True provides immutability at the instance level. Final type hints
    are not needed with Pydantic as the frozen configuration prevents reassignment.
    """

    model_config = {"frozen": True}

    READ_TIMEOUT: int = Field(default=10, description="Timeout for read operations (GET) in seconds")
    WRITE_TIMEOUT: int = Field(
        default=30,
        description="Timeout for write operations (PUT) in seconds - longer for dashboard updates",
    )
    CACHE_TTL: float = Field(
        default=30.0,
        description="Cache time-to-live in seconds for telemetry and property reads",
    )
    MAX_RETRIES: int = Field(default=3, description="Number of retries for transient failures")
    MIN_REQUEST_INTERVAL: float = Field(default=0.1, description="Minimum interval between API requests in seconds")
    WRITE_COOLDOWN: float = Field(default=2.0, description="Cooldown period after write operations in seconds")
    REQUEST_DEBOUNCE: float = Field(default=0.3, description="Debounce interval for repeated requests in seconds")
    POLLING_INTERVAL: int = Field(default=60, description="Default polling interval for coordinators in seconds")


# Create a default instance for easy access
API_DEFAULTS = APIDefaults()

# --- Climate Constants ---

# Import HA constants here to keep them centralized if needed,
# or define mappings that use them.
# Note: This requires 'homeassistant' to be available in the environment.
try:
    from homeassistant.components.climate import (
        FAN_HIGH,
        FAN_LOW,
        FAN_MEDIUM,
        FAN_OFF,
        PRESET_BOOST,
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_NONE,
        HVACAction,
        HVACMode,
    )
except ImportError:
    # Fallback for testing/standalone usage
    FAN_HIGH = "high"
    FAN_LOW = "low"
    FAN_MEDIUM = "medium"
    FAN_OFF = "off"
    PRESET_BOOST = "boost"
    PRESET_COMFORT = "comfort"
    PRESET_ECO = "eco"
    PRESET_NONE = "none"

    class HVACAction(IntEnum):
        OFF = 0
        HEATING = 1
        COOLING = 2
        DRYING = 3
        IDLE = 4
        FAN = 5
        DEFROSTING = 6
        PREHEATING = 7

    class HVACMode(IntEnum):
        OFF = 0
        HEAT = 1
        COOL = 2
        HEAT_COOL = 3
        AUTO = 4
        DRY = 5
        FAN_ONLY = 6


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
SCENARIO_DEFAULT_DURATIONS = {mode: mode.default_duration_minutes for mode in ScenarioMode}

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


# Heat pump status codes
class HeatPumpStatus(IntEnum):
    """Heat pump status codes bitmask."""

    IDLE_1 = 0x01
    HEATING = 0x02
    COOLING = 0x04
    PREHEATING = 0x08
    DRYING = 0x10
    IDLE_2 = 0x20
    DEFROSTING = 0x40
    IDLE_3 = 0x80


HEAT_PUMP_STATUS_MAPPING = {
    HeatPumpStatus.HEATING: HVACAction.HEATING,
    HeatPumpStatus.COOLING: HVACAction.COOLING,
    HeatPumpStatus.PREHEATING: HVACAction.PREHEATING,  # Not sure
    HeatPumpStatus.DRYING: HVACAction.DRYING,  # Not sure
    HeatPumpStatus.IDLE_2: HVACAction.IDLE,  # Unused
    HeatPumpStatus.DEFROSTING: HVACAction.DEFROSTING,  # Not sure
    HeatPumpStatus.IDLE_3: HVACAction.IDLE,  # Unused
}


# Sensor Mappings
VALUE_MAPPINGS = {
    "temperatureProfile": {0: "comfort", 1: "power", 2: "eco"},
    "season": {0: "transitional", 1: "heating", 2: "cooling"},
    "humidityMode": {0: "off", 1: "autoonly", 2: "on"},
    "hpStandby": {False: "false", True: "true"},
    "freeCoolingEnabled": {False: "false", True: "true"},
}


# Entity to API Parameter Mapping
# Maps entity definition keys (dot notation) to API method kwargs parameters
ENTITY_TO_API_PARAM_MAPPING = {
    # top-level fields
    "temperatureProfile": "temperature_profile",
    # season fields
    "season.status": "season_status",
    "season.season": "season_value",
    "season.heatingThresholdTemperature": "heating_threshold_temperature",
    "season.coolingThresholdTemperature": "cooling_threshold_temperature",
    # temperature fields
    "temperature.status": "temperature_status",
    "temperature.manualTemperature": "manual_temperature",
    # heating profile fields
    "heatingThermalProfileSeasonData.comfortTemperature": "heating_comfort_temperature",
    "heatingThermalProfileSeasonData.kneePointTemperature": "heating_knee_point_temperature",
    "heatingThermalProfileSeasonData.reductionDeltaTemperature": "heating_reduction_delta_temperature",
    # cooling profile fields
    "coolingThermalProfileSeasonData.comfortTemperature": "cooling_comfort_temperature",
    "coolingThermalProfileSeasonData.kneePointTemperature": "cooling_knee_point_temperature",
    "coolingThermalProfileSeasonData.temperatureLimit": "cooling_temperature_limit",
}
