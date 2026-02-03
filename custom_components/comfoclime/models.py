"""Data models for ComfoClime integration.

This module provides Pydantic models for structured data representation
with validation and type safety.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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

        Returns:
            The scaled telemetry value.
        """
        value = self.raw_value

        # Handle signed values
        if self.signed:
            if self.byte_count == 1 and value > 127:
                value -= 256
            elif self.byte_count == 2 and value > 32767:
                value -= 65536

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

        Returns:
            The scaled property value.
        """
        value = self.raw_value

        # Handle signed values
        if self.signed:
            if self.byte_count == 1 and value > 127:
                value -= 256
            elif self.byte_count == 2 and value > 32767:
                value -= 65536

        return value * self.faktor


class DashboardData(BaseModel):
    """Dashboard data from ComfoClime device.

    Contains key operational data from the device dashboard.
    Not frozen to allow for mutable updates from coordinator.

    Attributes:
        temperature: Current temperature reading.
        target_temperature: Target temperature setting.
        fan_speed: Current fan speed percentage.
        season: Current season mode (heating/cooling).
        hp_standby: Heat pump standby status.

    Example:
        >>> data = DashboardData(
        ...     temperature=22.5,
        ...     target_temperature=21.0,
        ...     fan_speed=50
        ... )
        >>> data.temperature
        22.5
    """

    model_config = {"validate_assignment": True}

    temperature: float | None = Field(default=None, description="Current temperature reading")
    target_temperature: float | None = Field(default=None, description="Target temperature setting")
    fan_speed: int | None = Field(default=None, ge=0, le=100, description="Current fan speed percentage")
    season: str | None = Field(default=None, description="Current season mode (heating/cooling)")
    hp_standby: bool | None = Field(default=None, description="Heat pump standby status")
