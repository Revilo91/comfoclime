"""Data models for ComfoClime integration.

This module provides Pydantic models for structured data representation
with validation and type safety. Also includes utility functions for
byte conversion and temperature value processing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# Utility functions for byte and temperature value processing
def bytes_to_signed_int(data: list, byte_count: int | None = None, signed: bool = True) -> int:
    """Convert raw bytes to a signed or unsigned integer value.

    Converts a list of bytes (little-endian) to an integer value.
    Supports 1-byte and 2-byte conversions with optional signed interpretation.

    Args:
        data: List of bytes (integers 0-255) in little-endian order
        byte_count: Number of bytes to read. If None, calculated from data length
        signed: If True, interpret as signed integer; if False, unsigned

    Returns:
        Integer value decoded from bytes.

    Raises:
        ValueError: If data is not a list or byte_count is not 1 or 2.

    Example:
        >>> bytes_to_signed_int([255, 255], 2, signed=True)
        -1
        >>> bytes_to_signed_int([0, 1], 2, signed=False)
        256
    """
    if not isinstance(data, list):
        raise ValueError("'data' is not a list")

    if byte_count is None:
        byte_count = len(data)

    if byte_count not in (1, 2):
        raise ValueError(f"Unsupported byte count: {byte_count}")

    return int.from_bytes(data[:byte_count], byteorder="little", signed=signed)


def signed_int_to_bytes(data: int, byte_count: int = 2, signed: bool = False) -> list:
    """Convert a signed or unsigned integer to a list of bytes.

    Converts an integer value to a list of bytes in little-endian order.
    Supports 1-byte and 2-byte conversions.

    Args:
        data: Integer value to convert
        byte_count: Number of bytes to convert to (1 or 2)
        signed: If True, interpret as signed integer; if False, unsigned

    Returns:
        List of bytes (integers 0-255) in little-endian order.

    Raises:
        ValueError: If byte_count is not 1 or 2.

    Example:
        >>> signed_int_to_bytes(-1, 2, signed=True)
        [255, 255]
        >>> signed_int_to_bytes(256, 2, signed=False)
        [0, 1]
    """
    if byte_count not in (1, 2):
        raise ValueError(f"Unsupported byte count: {byte_count}")

    return list(data.to_bytes(byte_count, byteorder="little", signed=signed))


def fix_signed_temperature(api_value: float) -> float:
    """Fix temperature value by converting through signed 16-bit integer.

    The ComfoClime API returns temperature values that need to be
    interpreted as signed 16-bit integers (scaled by 10). This method
    performs the necessary conversion to handle negative temperatures correctly.

    Args:
        api_value: Temperature value from API (scaled by 10)

    Returns:
        Corrected temperature value in °C.

    Example:
        >>> fix_signed_temperature(6552.3)  # API value for -1.3°C
        -1.3
        >>> fix_signed_temperature(235.0)  # Positive temps remain unchanged
        235.0
    """
    raw_value = int(api_value * 10)
    # Convert to signed 16-bit using Python's built-in byte conversion
    unsigned_value = raw_value & 0xFFFF
    bytes_data = signed_int_to_bytes(unsigned_value, 2)
    signed_value = bytes_to_signed_int(bytes_data, signed=True)
    return signed_value / 10.0


def fix_signed_temperatures_in_dict(data: dict) -> dict:
    """Recursively fix signed temperature values in a dictionary.

    Applies fix_signed_temperature to all keys containing "Temperature"
    in both flat and nested dictionary structures. This is used to
    automatically fix temperature values from API responses.

    Args:
        data: Dictionary potentially containing temperature values

    Returns:
        Dictionary with fixed temperature values.

    Example:
        >>> data = {"indoorTemperature": 6552.3, "outdoor": {"temperature": 235.0}}
        >>> fix_signed_temperatures_in_dict(data)
        {"indoorTemperature": -1.3, "outdoor": {"temperature": 235.0}}
    """
    for key in list(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            # Recursively process nested dictionaries
            data[key] = fix_signed_temperatures_in_dict(val)
        elif "Temperature" in key and val is not None and isinstance(val, (int, float)):
            data[key] = fix_signed_temperature(val)
    return data


class DeviceConfig(BaseModel):
    """Configuration for a connected device.

    Immutable Pydantic model representing device configuration from API responses.

    Attributes:
        uuid: Device unique identifier.
        model_type_id: Model type identifier (numeric).
        display_name: Human-readable device name.
        version: Optional firmware version.

    Example:
        >>> config = DeviceConfig(
        ...     uuid="abc123",
        ...     model_type_id=1,
        ...     display_name="Heat Pump"
        ... )
        >>> config.uuid
        'abc123'
    """

    model_config = {"frozen": True, "validate_assignment": True}

    uuid: str = Field(..., min_length=1, description="Device unique identifier")
    model_type_id: int = Field(..., ge=0, description="Model type identifier (numeric)")
    display_name: str = Field(default="Unknown Device", description="Human-readable device name")
    version: str | None = Field(default=None, description="Optional firmware version")


class TelemetryReading(BaseModel):
    """A single telemetry reading from a device.

    Represents a telemetry value with its metadata for scaling and interpretation.

    Attributes:
        device_uuid: UUID of the device providing the reading.
        telemetry_id: Telemetry identifier (path or ID).
        raw_value: Raw integer value from device.
        faktor: Multiplicative scaling factor (must be > 0).
        signed: Whether the value should be interpreted as signed.
        byte_count: Number of bytes in the value (1 or 2).

    Example:
        >>> reading = TelemetryReading(
        ...     device_uuid="abc123",
        ...     telemetry_id="10",
        ...     raw_value=250,
        ...     faktor=0.1
        ... )
        >>> reading.scaled_value
        25.0
    """

    model_config = {"validate_assignment": True}

    device_uuid: str = Field(..., min_length=1, description="UUID of the device providing the reading")
    telemetry_id: str = Field(..., min_length=1, description="Telemetry identifier (path or ID)")
    raw_value: int = Field(..., description="Raw integer value from device")
    faktor: float = Field(default=1.0, gt=0, description="Multiplicative scaling factor (must be > 0)")
    signed: bool = Field(default=False, description="Whether the value should be interpreted as signed")
    byte_count: Literal[1, 2] = Field(default=2, description="Number of bytes in the value (1 or 2)")

    @property
    def scaled_value(self) -> float:
        """Calculate the scaled value.

        Applies signed interpretation (if needed) and scaling factor.
        Uses the bytes_to_signed_int utility function for proper conversion.

        Returns:
            The scaled telemetry value.
        """
        # Convert raw_value to bytes and back using utility function for proper signed handling
        bytes_data = signed_int_to_bytes(self.raw_value, self.byte_count, signed=False)
        value = bytes_to_signed_int(bytes_data, self.byte_count, signed=self.signed)

        return value * self.faktor


class PropertyReading(BaseModel):
    """A property reading from a device.

    Similar to TelemetryReading but for property-based data access.

    Attributes:
        device_uuid: UUID of the device.
        path: Property path (e.g., "29/1/10").
        raw_value: Raw integer value from device.
        faktor: Multiplicative scaling factor.
        signed: Whether the value is signed.
        byte_count: Number of bytes (1 or 2).

    Example:
        >>> prop = PropertyReading(
        ...     device_uuid="abc123",
        ...     path="29/1/10",
        ...     raw_value=123,
        ...     faktor=1.0
        ... )
        >>> prop.scaled_value
        123.0
    """

    model_config = {"validate_assignment": True}

    device_uuid: str = Field(..., min_length=1, description="UUID of the device")
    path: str = Field(..., min_length=1, description="Property path (e.g., '29/1/10')")
    raw_value: int = Field(..., description="Raw integer value from device")
    faktor: float = Field(default=1.0, gt=0, description="Multiplicative scaling factor")
    signed: bool = Field(default=True, description="Whether the value is signed")
    byte_count: Literal[1, 2] = Field(default=2, description="Number of bytes (1 or 2)")

    @property
    def scaled_value(self) -> float:
        """Calculate the scaled value.

        Applies signed interpretation and scaling factor.
        Uses the bytes_to_signed_int utility function for proper conversion.

        Returns:
            The scaled property value.
        """
        # Convert raw_value to bytes and back using utility function for proper signed handling
        bytes_data = signed_int_to_bytes(self.raw_value, self.byte_count, signed=False)
        value = bytes_to_signed_int(bytes_data, self.byte_count, signed=self.signed)

        return value * self.faktor


class DashboardData(BaseModel):
    """Dashboard data from ComfoClime device.

    Contains key operational data from the device dashboard endpoint.
    Not frozen to allow for mutable updates from coordinator.
    All fields are optional as the API response varies between AUTO and MANUAL mode.

    Attributes:
        indoor_temperature: Current indoor temperature in °C
        outdoor_temperature: Current outdoor temperature in °C
        set_point_temperature: Target temperature in °C (manual mode only)
        exhaust_air_flow: Exhaust air flow in m³/h
        supply_air_flow: Supply air flow in m³/h
        fan_speed: Current fan speed level (0-3)
        season_profile: Season profile (0=comfort, 1=boost, 2=eco)
        temperature_profile: Temperature profile (0=comfort, 1=boost, 2=eco)
        season: Season mode (0=transition, 1=heating, 2=cooling)
        schedule: Schedule mode status
        status: Control mode (0=manual, 1=automatic)
        heat_pump_status: Heat pump operating status code
        hp_standby: Heat pump standby state (True=standby/off, False=active)
        free_cooling_enabled: Free cooling status
        caq_free_cooling_available: ComfoAirQ free cooling availability
        scenario: Active scenario mode (4=cooking, 5=party, 7=away, 8=boost, None=none)
        scenario_time_left: Remaining time in seconds for active scenario

    Example:
        >>> # Parse from API response
        >>> data = DashboardData(
        ...     indoor_temperature=22.5,
        ...     outdoor_temperature=18.0,
        ...     fan_speed=2,
        ...     season=1,
        ...     status=1
        ... )
        >>> data.indoor_temperature
        22.5
        >>> data.is_heating_mode
        True
    """

    model_config = {"validate_assignment": True, "populate_by_name": True}

    # Temperature readings
    indoor_temperature: float | None = Field(
        default=None,
        alias="indoorTemperature",
        description="Current indoor temperature in °C",
    )
    outdoor_temperature: float | None = Field(
        default=None,
        alias="outdoorTemperature",
        description="Current outdoor temperature in °C",
    )
    set_point_temperature: float | None = Field(
        default=None,
        alias="setPointTemperature",
        description="Target temperature in °C (manual mode only)",
    )

    # Air flow
    exhaust_air_flow: int | None = Field(default=None, alias="exhaustAirFlow", description="Exhaust air flow in m³/h")
    supply_air_flow: int | None = Field(default=None, alias="supplyAirFlow", description="Supply air flow in m³/h")

    # Fan and profiles
    fan_speed: int | None = Field(
        default=None,
        ge=0,
        le=3,
        alias="fanSpeed",
        description="Current fan speed level (0-3)",
    )
    season_profile: int | None = Field(
        default=None,
        ge=0,
        le=2,
        alias="seasonProfile",
        description="Season profile (0=comfort, 1=boost, 2=eco)",
    )
    temperature_profile: int | None = Field(
        default=None,
        ge=0,
        le=2,
        alias="temperatureProfile",
        description="Temperature profile (0=comfort, 1=boost, 2=eco)",
    )

    # Operating modes
    season: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Season mode (0=transition, 1=heating, 2=cooling)",
    )
    schedule: int | None = Field(default=None, description="Schedule mode status")
    status: int | None = Field(default=None, ge=0, le=1, description="Control mode (0=manual, 1=automatic)")

    # Heat pump status
    heat_pump_status: int | None = Field(
        default=None,
        alias="heatPumpStatus",
        description="Heat pump operating status code",
    )
    hp_standby: bool | None = Field(
        default=None,
        alias="hpStandby",
        description="Heat pump standby state (True=standby/off, False=active)",
    )

    # Cooling
    free_cooling_enabled: bool | None = Field(
        default=None, alias="freeCoolingEnabled", description="Free cooling status"
    )
    caq_free_cooling_available: bool | None = Field(
        default=None,
        alias="caqFreeCoolingAvailable",
        description="ComfoAirQ free cooling availability",
    )

    # Scenarios
    scenario: int | None = Field(
        default=None,
        description="Active scenario mode (4=cooking, 5=party, 7=away, 8=boost, None=none)",
    )
    scenario_time_left: int | None = Field(
        default=None,
        alias="scenarioTimeLeft",
        description="Remaining time in seconds for active scenario",
    )

    @property
    def is_heating_mode(self) -> bool:
        """Check if system is in heating mode."""
        return self.season == 1

    @property
    def is_cooling_mode(self) -> bool:
        """Check if system is in cooling mode."""
        return self.season == 2

    @property
    def is_manual_mode(self) -> bool:
        """Check if system is in manual temperature control mode."""
        return self.status == 0 or self.set_point_temperature is not None

    @property
    def is_auto_mode(self) -> bool:
        """Check if system is in automatic temperature control mode."""
        return self.status == 1


class SeasonData(BaseModel):
    """Season configuration data for thermal profile.

    Attributes:
        status: Season detection mode (0=manual, 1=automatic)
        season: Current season (0=transition, 1=heating, 2=cooling)
        heating_threshold_temperature: Temperature threshold for heating mode in °C
        cooling_threshold_temperature: Temperature threshold for cooling mode in °C
    """

    model_config = {"frozen": True, "populate_by_name": True}

    status: int | None = Field(default=None, ge=0, le=1, description="Season detection mode (0=manual, 1=automatic)")
    season: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Current season (0=transition, 1=heating, 2=cooling)",
    )
    heating_threshold_temperature: float | None = Field(
        default=None,
        alias="heatingThresholdTemperature",
        description="Temperature threshold for heating mode in °C",
    )
    cooling_threshold_temperature: float | None = Field(
        default=None,
        alias="coolingThresholdTemperature",
        description="Temperature threshold for cooling mode in °C",
    )


class TemperatureControlData(BaseModel):
    """Temperature control configuration data.

    Attributes:
        status: Temperature control mode (0=manual, 1=automatic)
        manual_temperature: Manual target temperature in °C (when status=0)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    status: int | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Temperature control mode (0=manual, 1=automatic)",
    )
    manual_temperature: float | None = Field(
        default=None,
        alias="manualTemperature",
        description="Manual target temperature in °C (when status=0)",
    )


class ThermalProfileSeasonData(BaseModel):
    """Thermal profile configuration for heating or cooling season.

    Attributes:
        comfort_temperature: Comfort target temperature in °C
        knee_point_temperature: Knee point temperature for curve calculation in °C
        reduction_delta_temperature: Temperature reduction delta in °C (heating only)
        temperature_limit: Maximum temperature limit in °C (cooling only)
    """

    model_config = {"frozen": True, "populate_by_name": True}

    comfort_temperature: float | None = Field(
        default=None,
        alias="comfortTemperature",
        description="Comfort target temperature in °C",
    )
    knee_point_temperature: float | None = Field(
        default=None,
        alias="kneePointTemperature",
        description="Knee point temperature for curve calculation in °C",
    )
    reduction_delta_temperature: float | None = Field(
        default=None,
        alias="reductionDeltaTemperature",
        description="Temperature reduction delta in °C (heating only)",
    )
    temperature_limit: float | None = Field(
        default=None,
        alias="temperatureLimit",
        description="Maximum temperature limit in °C (cooling only)",
    )


class ThermalProfileData(BaseModel):
    """Thermal profile configuration from ComfoClime device.

    Contains heating and cooling parameters, season settings, and temperature
    control configuration. Not frozen to allow for mutable updates from coordinator.

    Attributes:
        season: Season configuration (status, season value, thresholds)
        temperature: Temperature control settings (status, manual temperature)
        temperature_profile: Active profile (0=comfort, 1=power, 2=eco)
        heating_thermal_profile_season_data: Heating season parameters
        cooling_thermal_profile_season_data: Cooling season parameters

    Example:
        >>> # Parse from API response
        >>> data = ThermalProfileData(
        ...     season={"status": 1, "season": 1},
        ...     temperature_profile=0,
        ...     heating_thermal_profile_season_data={"comfortTemperature": 21.5}
        ... )
        >>> data.is_heating_season
        True
    """

    model_config = {"validate_assignment": True, "populate_by_name": True}

    season: SeasonData | None = Field(default=None, description="Season configuration")
    temperature: TemperatureControlData | None = Field(default=None, description="Temperature control settings")
    temperature_profile: int | None = Field(
        default=None,
        ge=0,
        le=2,
        alias="temperatureProfile",
        description="Active profile (0=comfort, 1=power, 2=eco)",
    )
    heating_thermal_profile_season_data: ThermalProfileSeasonData | None = Field(
        default=None,
        alias="heatingThermalProfileSeasonData",
        description="Heating season parameters",
    )
    cooling_thermal_profile_season_data: ThermalProfileSeasonData | None = Field(
        default=None,
        alias="coolingThermalProfileSeasonData",
        description="Cooling season parameters",
    )

    @property
    def is_heating_season(self) -> bool:
        """Check if system is in heating season."""
        return self.season is not None and self.season.season == 1

    @property
    def is_cooling_season(self) -> bool:
        """Check if system is in cooling season."""
        return self.season is not None and self.season.season == 2

    @property
    def is_automatic_season(self) -> bool:
        """Check if season detection is automatic."""
        return self.season is not None and self.season.status == 1

    @property
    def is_automatic_temperature(self) -> bool:
        """Check if temperature control is automatic."""
        return self.temperature is not None and self.temperature.status == 1
