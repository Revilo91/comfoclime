"""Constants and Enums for ComfoClime integration."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel, Field


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
