"""Data models for ComfoClime integration.

This module provides Pydantic models for structured data representation
with validation and type safety. Also includes utility functions for
byte conversion and temperature value processing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .infrastructure.validation import validate_byte_value, validate_property_path


# Base model for all ComfoClime data models
class ComfoClimeModel(BaseModel):
    """Base model for all ComfoClime data structures.

    Provides common configuration and utilities for all Pydantic models
    used in the ComfoClime integration.
    """

    model_config = {"validate_assignment": True, "populate_by_name": True}


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


class DeviceConfig(ComfoClimeModel):
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

    model_config = {"frozen": True}

    uuid: str = Field(..., min_length=1, description="Device unique identifier")
    model_type_id: int = Field(..., ge=0, description="Model type identifier (numeric)")
    display_name: str = Field(default="Unknown Device", description="Human-readable device name")
    version: str | None = Field(default=None, description="Optional firmware version")

    @classmethod
    def from_api_dict(cls, device_dict: dict) -> DeviceConfig | None:
        """Parse a device entry from the API into a DeviceConfig."""
        try:
            return cls(
                uuid=device_dict.get("uuid", ""),
                model_type_id=int(device_dict.get("modelTypeId", 0)),
                display_name=device_dict.get("displayName", "Unknown Device"),
                version=device_dict.get("version"),
            )
        except (KeyError, ValueError, TypeError):
            return None


class ConnectedDevicesResponse(ComfoClimeModel):
    """Response model for /system/{uuid}/devices."""

    model_config = {"frozen": True}

    devices: list[DeviceConfig] = Field(default_factory=list, description="Connected devices")

    @classmethod
    def from_api(cls, response_data: dict | None) -> ConnectedDevicesResponse:
        """Build a devices response from the raw API payload."""
        raw_devices = response_data.get("devices", []) if isinstance(response_data, dict) else []
        device_configs = []
        for device_dict in raw_devices:
            device_config = DeviceConfig.from_api_dict(device_dict)
            if device_config is not None:
                device_configs.append(device_config)
        return cls(devices=device_configs)


class DeviceDefinitionData(ComfoClimeModel):
    """Device definition payload from /device/{device_uuid}/definition.

    The response shape varies by device model. Known temperature fields are
    modeled explicitly and all other fields are preserved via extra=allow.
    """

    model_config = {"extra": "allow"}

    indoor_temperature: float | None = Field(default=None, alias="indoorTemperature")
    outdoor_temperature: float | None = Field(default=None, alias="outdoorTemperature")
    extract_temperature: float | None = Field(default=None, alias="extractTemperature")
    supply_temperature: float | None = Field(default=None, alias="supplyTemperature")
    exhaust_temperature: float | None = Field(default=None, alias="exhaustTemperature")


class TelemetryReading(ComfoClimeModel):
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

    @classmethod
    def from_cached_value(
        cls,
        *,
        device_uuid: str,
        telemetry_id: str,
        cached_value: int | float | None,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> TelemetryReading | None:
        """Create a telemetry reading from a cached scaled value.

        Returns None when the cached value is missing or non-numeric.
        """
        if cached_value is None or not isinstance(cached_value, (int, float)):
            return None

        if faktor == 0:
            return None

        if byte_count is None:
            byte_count = 2

        estimated_raw = int(round(cached_value / faktor))
        return cls(
            device_uuid=device_uuid,
            telemetry_id=str(telemetry_id),
            raw_value=estimated_raw,
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )

    @classmethod
    def from_raw_bytes(
        cls,
        *,
        device_uuid: str,
        telemetry_id: str,
        data: list,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> TelemetryReading | None:
        """Create a telemetry reading from raw API bytes."""
        if not data:
            return None

        if byte_count is None:
            byte_count = len(data)

        raw_value = bytes_to_signed_int(data, byte_count, signed)
        return cls(
            device_uuid=device_uuid,
            telemetry_id=str(telemetry_id),
            raw_value=raw_value,
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )


class PropertyReading(ComfoClimeModel):
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

    @classmethod
    def from_cached_value(
        cls,
        *,
        device_uuid: str,
        path: str,
        cached_value: int | float | None,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> PropertyReading | None:
        """Create a property reading from a cached value.

        Returns None when the cached value is missing or non-numeric.
        """
        if cached_value is None or not isinstance(cached_value, (int, float)):
            return None

        if faktor == 0:
            return None

        if byte_count is None:
            byte_count = 2

        estimated_raw = int(round(cached_value / faktor))
        return cls(
            device_uuid=device_uuid,
            path=path,
            raw_value=estimated_raw,
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )


class PropertyReadResult(ComfoClimeModel):
    """Parsed result for a property read operation."""

    model_config = {"frozen": True}

    reading: PropertyReading | None = Field(default=None)
    cache_value: int | float | str | None = Field(default=None)

    @classmethod
    def from_raw_bytes(
        cls,
        *,
        device_uuid: str,
        path: str,
        data: list,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> PropertyReadResult:
        """Parse raw property bytes into a result suitable for caching."""
        if not data:
            return cls(reading=None, cache_value=None)

        if byte_count is None:
            byte_count = len(data)

        if byte_count in (1, 2):
            reading = PropertyReading(
                device_uuid=device_uuid,
                path=path,
                raw_value=bytes_to_signed_int(data, byte_count, signed),
                faktor=faktor,
                signed=signed,
                byte_count=byte_count,
            )
            return cls(reading=reading, cache_value=reading.scaled_value)

        if byte_count > 2:
            if len(data) != byte_count:
                raise ValueError(f"Unerwartete Byte-Anzahl: erwartet {byte_count}, erhalten {len(data)}")
            result = "".join(chr(byte) for byte in data if byte != 0)
            return cls(reading=None, cache_value=result)

        raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")


class DashboardData(ComfoClimeModel):
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


class MonitoringPing(ComfoClimeModel):
    """Monitoring ping response from device.

    Normalizes common uptime field names returned by different firmware
    variants and exposes a consistent `up_time_seconds` attribute.
    """

    model_config = {"frozen": True, "extra": "allow"}

    uuid: str | None = Field(default=None, description="Device UUID")
    up_time_seconds: int | None = Field(default=None, description="Device uptime in seconds")
    timestamp: int | None = Field(default=None, description="Timestamp from device")

    @model_validator(mode="before")
    @classmethod
    def _normalize_uptime(cls, v):
        # Accept multiple possible uptime field names and normalize to up_time_seconds
        if isinstance(v, dict):
            if "up_time_seconds" not in v:
                if "uptime" in v:
                    v["up_time_seconds"] = v.get("uptime")
                elif "upTimeSeconds" in v:
                    v["up_time_seconds"] = v.get("upTimeSeconds")

            # Convert ISO timestamp string to Unix timestamp integer
            if "timestamp" in v and isinstance(v["timestamp"], str):
                try:
                    # Parse ISO format and convert to Unix timestamp
                    # Handle both with and without milliseconds, and with 'Z' suffix
                    timestamp_str = v["timestamp"].replace(".0Z", "Z").replace("Z", "+00:00")
                    dt = datetime.fromisoformat(timestamp_str)
                    v["timestamp"] = int(dt.timestamp())
                except (ValueError, AttributeError):
                    # Remove invalid timestamp to avoid validation error
                    v.pop("timestamp", None)
        return v


class PropertyWriteRequest(ComfoClimeModel):
    """Request to write a device property."""

    model_config = {"frozen": True}

    device_uuid: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    value: float
    byte_count: Literal[1, 2, 4] = Field(default=2)
    signed: bool = Field(default=True)
    faktor: float = Field(default=1.0, gt=0)

    def to_wire_data(self) -> tuple[int, int, int, list[int]]:
        """Validate and convert this request to wire format components."""
        is_valid, error_message = validate_property_path(self.path)
        if not is_valid:
            raise ValueError(f"Invalid property path: {error_message}")

        if self.byte_count not in (1, 2):
            raise ValueError("Nur 1 oder 2 Byte unterstützt")

        raw_value = round(self.value / self.faktor)
        is_valid, error_message = validate_byte_value(raw_value, self.byte_count, self.signed)
        if not is_valid:
            raise ValueError(
                f"Invalid value for byte_count={self.byte_count}, signed={self.signed}: {error_message}"
            )

        data = signed_int_to_bytes(raw_value, self.byte_count, self.signed)
        x, y, z = map(int, self.path.split("/"))
        return x, y, z, data


class SeasonData(ComfoClimeModel):
    """Season configuration within thermal profile."""

    model_config = {"frozen": True}

    status: int = Field(default=1, ge=0, le=1, description="Mode (0=Manual, 1=Auto)")
    season: int = Field(default=0, ge=0, le=2, description="Season (0=Transition, 1=Heating, 2=Cooling)")
    heating_threshold_temperature: float = Field(
        default=14.0,
        alias="heatingThresholdTemperature",
        description="Heating threshold temperature",
    )
    cooling_threshold_temperature: float = Field(
        default=17.0,
        alias="coolingThresholdTemperature",
        description="Cooling threshold temperature",
    )


class TemperatureControlData(ComfoClimeModel):
    """Temperature control settings."""

    model_config = {"frozen": True}

    status: int = Field(default=1, ge=0, le=1, description="Mode (0=Manual, 1=Auto)")
    manual_temperature: float = Field(
        default=21.0,
        alias="manualTemperature",
        description="Manual setpoint temperature",
    )


class ThermalProfileSeasonData(ComfoClimeModel):
    """Season-specific parameters (heating or cooling)."""

    model_config = {"frozen": True}

    comfort_temperature: float = Field(default=21.0, alias="comfortTemperature")
    knee_point_temperature: float = Field(default=12.0, alias="kneePointTemperature")
    reduction_delta_temperature: float | None = Field(default=None, alias="reductionDeltaTemperature")
    temperature_limit: float | None = Field(default=None, alias="temperatureLimit")


class ThermalProfileData(ComfoClimeModel):
    """Full thermal profile from device."""

    season: SeasonData = Field(default_factory=lambda: SeasonData(status=1, season=0))
    temperature: TemperatureControlData = Field(default_factory=TemperatureControlData)
    temperature_profile: int = Field(default=0, ge=0, le=2, alias="temperatureProfile")
    heating_thermal_profile_season_data: ThermalProfileSeasonData = Field(
        default_factory=ThermalProfileSeasonData,
        alias="heatingThermalProfileSeasonData",
    )
    cooling_thermal_profile_season_data: ThermalProfileSeasonData = Field(
        default_factory=ThermalProfileSeasonData,
        alias="coolingThermalProfileSeasonData",
    )

    @property
    def is_heating_season(self) -> bool:
        """Check if current active season is heating."""
        return self.season.season == 1

    @property
    def is_cooling_season(self) -> bool:
        """Check if current active season is cooling."""
        return self.season.season == 2

    @property
    def is_automatic_season(self) -> bool:
        """Check if season control is automatic."""
        return self.season.status == 1

    @property
    def is_automatic_temperature(self) -> bool:
        """Check if temperature control is automatic."""
        return self.temperature.status == 1


class ThermalProfileUpdate(ComfoClimeModel):
    """Model for partial thermal profile updates."""

    season_status: int | None = None
    season_value: int | None = None
    heating_threshold_temperature: float | None = None
    cooling_threshold_temperature: float | None = None
    temperature_status: int | None = None
    manual_temperature: float | None = None
    temperature_profile: int | None = None
    heating_comfort_temperature: float | None = None
    heating_knee_point_temperature: float | None = None
    heating_reduction_delta_temperature: float | None = None
    cooling_comfort_temperature: float | None = None
    cooling_knee_point_temperature: float | None = None
    cooling_temperature_limit: float | None = None

    def to_api_payload(self) -> dict[str, Any]:
        """Convert flat fields to nested API format."""
        payload: dict[str, Any] = {}

        # Season
        if any(
            v is not None
            for v in [
                self.season_status,
                self.season_value,
                self.heating_threshold_temperature,
                self.cooling_threshold_temperature,
            ]
        ):
            payload["season"] = {
                k: v
                for k, v in {
                    "status": self.season_status,
                    "season": self.season_value,
                    "heatingThresholdTemperature": self.heating_threshold_temperature,
                    "coolingThresholdTemperature": self.cooling_threshold_temperature,
                }.items()
                if v is not None
            }

        # Temperature
        if any(v is not None for v in [self.temperature_status, self.manual_temperature]):
            payload["temperature"] = {
                k: v
                for k, v in {
                    "status": self.temperature_status,
                    "manualTemperature": self.manual_temperature,
                }.items()
                if v is not None
            }

        # Profile
        if self.temperature_profile is not None:
            payload["temperatureProfile"] = self.temperature_profile

        # Heating details
        if any(
            v is not None
            for v in [
                self.heating_comfort_temperature,
                self.heating_knee_point_temperature,
                self.heating_reduction_delta_temperature,
            ]
        ):
            payload["heatingThermalProfileSeasonData"] = {
                k: v
                for k, v in {
                    "comfortTemperature": self.heating_comfort_temperature,
                    "kneePointTemperature": self.heating_knee_point_temperature,
                    "reductionDeltaTemperature": self.heating_reduction_delta_temperature,
                }.items()
                if v is not None
            }

        # Cooling details
        if any(
            v is not None
            for v in [
                self.cooling_comfort_temperature,
                self.cooling_knee_point_temperature,
                self.cooling_temperature_limit,
            ]
        ):
            payload["coolingThermalProfileSeasonData"] = {
                k: v
                for k, v in {
                    "comfortTemperature": self.cooling_comfort_temperature,
                    "kneePointTemperature": self.cooling_knee_point_temperature,
                    "temperatureLimit": self.cooling_temperature_limit,
                }.items()
                if v is not None
            }

        return payload

    @classmethod
    def from_dict(cls, updates: dict[str, Any]) -> ThermalProfileUpdate:
        """Convert nested legacy dict to flat update model."""
        flat_updates: dict[str, Any] = {}

        if "season" in updates:
            s = updates["season"]
            if "status" in s:
                flat_updates["season_status"] = s["status"]
            if "season" in s:
                flat_updates["season_value"] = s["season"]
            if "heatingThresholdTemperature" in s:
                flat_updates["heating_threshold_temperature"] = s["heatingThresholdTemperature"]
            if "coolingThresholdTemperature" in s:
                flat_updates["cooling_threshold_temperature"] = s["coolingThresholdTemperature"]

        if "temperature" in updates:
            t = updates["temperature"]
            if "status" in t:
                flat_updates["temperature_status"] = t["status"]
            if "manualTemperature" in t:
                flat_updates["manual_temperature"] = t["manualTemperature"]

        if "temperatureProfile" in updates:
            flat_updates["temperature_profile"] = updates["temperatureProfile"]

        if "heatingThermalProfileSeasonData" in updates:
            h = updates["heatingThermalProfileSeasonData"]
            if "comfortTemperature" in h:
                flat_updates["heating_comfort_temperature"] = h["comfortTemperature"]
            if "kneePointTemperature" in h:
                flat_updates["heating_knee_point_temperature"] = h["kneePointTemperature"]
            if "reductionDeltaTemperature" in h:
                flat_updates["heating_reduction_delta_temperature"] = h["reductionDeltaTemperature"]

        if "coolingThermalProfileSeasonData" in updates:
            c = updates["coolingThermalProfileSeasonData"]
            if "comfortTemperature" in c:
                flat_updates["cooling_comfort_temperature"] = c["comfortTemperature"]
            if "kneePointTemperature" in c:
                flat_updates["cooling_knee_point_temperature"] = c["kneePointTemperature"]
            if "temperatureLimit" in c:
                flat_updates["cooling_temperature_limit"] = c["temperatureLimit"]

        return cls(**flat_updates)


class DashboardUpdate(ComfoClimeModel):
    """Model for partial dashboard updates."""

    set_point_temperature: float | None = Field(default=None, alias="setPointTemperature")
    fan_speed: int | None = Field(default=None, ge=0, le=3, alias="fanSpeed")
    season: int | None = Field(default=None, ge=0, le=2)
    hp_standby: bool | None = Field(default=None, alias="hpStandby")
    schedule: int | None = None
    temperature_profile: int | None = Field(default=None, ge=0, le=2, alias="temperatureProfile")
    season_profile: int | None = Field(default=None, ge=0, le=2, alias="seasonProfile")
    status: int | None = Field(default=None, ge=0, le=1)
    scenario: int | None = None
    scenario_time_left: int | None = Field(default=None, alias="scenarioTimeLeft")
    scenario_start_delay: int | None = Field(default=None, alias="scenarioStartDelay")

    def to_api_payload(self, include_timestamp: bool = False) -> dict[str, Any]:
        """Convert flat fields to API payload.

        Timestamp is usually added by the @api_put decorator.
        """
        payload = {
            self.model_fields[field].alias or field: value
            for field, value in self.model_dump(exclude_none=True).items()
            if field != "timestamp" or include_timestamp
        }
        return payload


# API Response Models
class DashboardUpdateResponse(ComfoClimeModel):
    """Response model from dashboard update endpoint.

    Represents the server's acknowledgment of a dashboard update request.
    Contains the status code and any returned fields.
    """

    model_config = {"extra": "allow"}

    status: int | str | None = Field(default=200, description="HTTP status code from API")


class ThermalProfileUpdateResponse(ComfoClimeModel):
    """Response model from thermal profile update endpoint.

    Represents the server's acknowledgment of a thermal profile update.
    Contains status and any returned fields.
    """

    model_config = {"extra": "allow"}

    status: int | str | None = Field(default=200, description="HTTP status code from API")


class PropertyWriteResponse(ComfoClimeModel):
    """Response model from property write endpoint.

    Represents the server's acknowledgment of a property write request.
    May contain the written value or status information.
    """

    model_config = {"extra": "allow"}

    status: int | str | None = Field(default=200, description="HTTP status code from API")
    data: list[int] | None = Field(default=None, description="Response data bytes if any")


class TelemetryDataResponse(ComfoClimeModel):
    """Structured response model for batch telemetry readings.

    Maps device UUIDs to their telemetry readings.
    """

    model_config = {"extra": "allow"}

    readings: dict[str, dict[str, TelemetryReading]] = Field(
        default_factory=dict, description="Device UUID -> Telemetry readings"
    )


class PropertyDataResponse(ComfoClimeModel):
    """Structured response model for batch property readings.

    Maps device UUIDs to their property readings.
    """

    model_config = {"extra": "allow"}

    readings: dict[str, dict[str, PropertyReading]] = Field(
        default_factory=dict, description="Device UUID -> Property readings"
    )


class EntityCategoriesResponse(ComfoClimeModel):
    """Response model for entity category organization.

    Maps entity types to categories to entity definitions.
    """

    model_config = {"extra": "allow"}

    categories: dict[str, dict[str, list[str]]] = Field(
        default_factory=dict, description="Category structure for entities"
    )


class SelectionOption(ComfoClimeModel):
    """A single option in a selection dropdown.

    Represents one choice in a select entity.
    """

    label: str = Field(description="Human-readable label for the option")
    value: str = Field(description="Internal value associated with the option")


# Registry Models for Coordinator Data Structures
class TelemetryRegistryEntry(ComfoClimeModel):
    """Single telemetry metadata entry in the telemetry registry.

    Stores configuration for a single telemetry sensor that the coordinator
    will fetch during updates. Contains scaling and interpretation parameters.

    Attributes:
        faktor: Multiplicative scaling factor for raw values (must be > 0)
        signed: Whether to interpret raw values as signed integers
        byte_count: Number of bytes to read (1 or 2, or None for auto-detection)

    Example:
        >>> entry = TelemetryRegistryEntry(
        ...     faktor=0.1,
        ...     signed=True,
        ...     byte_count=2
        ... )
    """

    model_config = {"frozen": True}

    faktor: float = Field(default=1.0, gt=0, description="Multiplicative scaling factor (must be > 0)")
    signed: bool = Field(default=True, description="Whether to interpret raw values as signed")
    byte_count: int | None = Field(default=None, description="Number of bytes to read (1, 2, or None)")


class PropertyRegistryEntry(ComfoClimeModel):
    """Single property metadata entry in the property registry.

    Stores configuration for a single property that the coordinator
    will fetch during updates. Contains scaling and interpretation parameters.

    Attributes:
        faktor: Multiplicative scaling factor for numeric values (must be > 0)
        signed: Whether to interpret numeric values as signed integers
        byte_count: Number of bytes to read (varies by property type)

    Example:
        >>> entry = PropertyRegistryEntry(
        ...     faktor=0.1,
        ...     signed=True,
        ...     byte_count=2
        ... )
    """

    model_config = {"frozen": True}

    faktor: float = Field(default=1.0, gt=0, description="Multiplicative scaling factor (must be > 0)")
    signed: bool = Field(default=True, description="Whether to interpret numeric values as signed")
    byte_count: int | None = Field(default=None, description="Number of bytes (1-2 for numeric, 3+ for string)")


class TelemetryRegistry(ComfoClimeModel):
    """Full telemetry registry for the coordinator.

    Maps device UUIDs to their registered telemetry sensors.
    Inner dict maps telemetry IDs (as strings) to their configuration entries.

    Attributes:
        entries: Nested dict structure mapping device_uuid -> telemetry_id -> entry

    Example:
        >>> registry = TelemetryRegistry()
        >>> registry.entries["device123"] = {
        ...     "4145": TelemetryRegistryEntry(faktor=0.1, signed=True)
        ... }
    """

    model_config = {"frozen": True}

    entries: dict[str, dict[str, TelemetryRegistryEntry]] = Field(
        default_factory=dict, description="device_uuid -> telemetry_id -> entry"
    )


class PropertyRegistry(ComfoClimeModel):
    """Full property registry for the coordinator.

    Maps device UUIDs to their registered properties.
    Inner dict maps property paths (e.g., "29/1/10") to their configuration entries.

    Attributes:
        entries: Nested dict structure mapping device_uuid -> path -> entry

    Example:
        >>> registry = PropertyRegistry()
        >>> registry.entries["device123"] = {
        ...     "29/1/10": PropertyRegistryEntry(faktor=0.1, signed=True, byte_count=2)
        ... }
    """

    model_config = {"frozen": True}

    entries: dict[str, dict[str, PropertyRegistryEntry]] = Field(
        default_factory=dict, description="device_uuid -> path -> entry"
    )
