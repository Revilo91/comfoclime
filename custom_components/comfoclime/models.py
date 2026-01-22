"""Data models for ComfoClime integration.

This module provides dataclasses for structured data representation
with validation and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    """Configuration for a connected device.

    Immutable dataclass representing device configuration from API responses.

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

    uuid: str
    model_type_id: int
    display_name: str = "Unknown Device"
    version: str | None = None

    def __post_init__(self) -> None:
        """Validate device configuration."""
        if not self.uuid or len(self.uuid) == 0:
            raise ValueError("uuid cannot be empty")
        if self.model_type_id < 0:
            raise ValueError("model_type_id must be non-negative")


@dataclass(slots=True)
class TelemetryReading:
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

    device_uuid: str
    telemetry_id: str
    raw_value: int
    faktor: float = 1.0
    signed: bool = False
    byte_count: Literal[1, 2] = 2

    def __post_init__(self) -> None:
        """Validate telemetry reading."""
        if not self.device_uuid:
            raise ValueError("device_uuid cannot be empty")
        if not self.telemetry_id:
            raise ValueError("telemetry_id cannot be empty")
        if self.faktor <= 0:
            raise ValueError("faktor must be greater than 0")
        if self.byte_count not in (1, 2):
            raise ValueError("byte_count must be 1 or 2")

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


@dataclass(slots=True)
class PropertyReading:
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

    device_uuid: str
    path: str
    raw_value: int
    faktor: float = 1.0
    signed: bool = True
    byte_count: Literal[1, 2] = 2

    def __post_init__(self) -> None:
        """Validate property reading."""
        if not self.device_uuid:
            raise ValueError("device_uuid cannot be empty")
        if not self.path:
            raise ValueError("path cannot be empty")
        if self.faktor <= 0:
            raise ValueError("faktor must be greater than 0")
        if self.byte_count not in (1, 2):
            raise ValueError("byte_count must be 1 or 2")

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


@dataclass(slots=True)
class DashboardData:
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

    temperature: float | None = None
    target_temperature: float | None = None
    fan_speed: int | None = None
    season: str | None = None
    hp_standby: bool | None = None

    def __post_init__(self) -> None:
        """Validate dashboard data."""
        if self.fan_speed is not None and (self.fan_speed < 0 or self.fan_speed > 100):
            raise ValueError("fan_speed must be between 0 and 100")
