# ComfoClime Data Models

This document describes the dataclasses in `models.py` and their usage.

## Overview

The `models.py` module provides structured data models with validation for the ComfoClime integration. These models use Python dataclasses with features like:

- **`slots=True`**: Memory efficiency by preventing dynamic attribute creation
- **`frozen=True`**: Immutability for configuration data
- **`__post_init__`**: Validation on initialization
- **Type hints**: Full type safety

## Models

### DeviceConfig

Immutable configuration for a connected device.

**Features:**
- `frozen=True`: Cannot be modified after creation
- `slots=True`: Memory-efficient
- Validates UUID is not empty
- Validates model_type_id is non-negative

**Usage:**
```python
from custom_components.comfoclime.models import DeviceConfig

# Create a device configuration
config = DeviceConfig(
    uuid="abc123",
    model_type_id=1,
    display_name="Heat Pump",
    version="1.0.0"
)

# Access fields
print(config.uuid)  # "abc123"

# Cannot modify (frozen)
# config.uuid = "new"  # Raises AttributeError
```

### TelemetryReading

A telemetry reading from a device with automatic scaling.

**Features:**
- `slots=True`: Memory-efficient
- Validates device_uuid and telemetry_id are not empty
- Validates faktor is positive
- Validates byte_count is 1 or 2
- Provides `scaled_value` property for automatic calculation

**Usage:**
```python
from custom_components.comfoclime.models import TelemetryReading

# Create a reading
reading = TelemetryReading(
    device_uuid="abc123",
    telemetry_id="10",
    raw_value=250,
    faktor=0.1,
    signed=False,
    byte_count=2
)

# Get scaled value
print(reading.scaled_value)  # 25.0

# Handle signed values
signed_reading = TelemetryReading(
    device_uuid="abc123",
    telemetry_id="10",
    raw_value=65535,  # -1 in signed 16-bit
    faktor=1.0,
    signed=True,
    byte_count=2
)
print(signed_reading.scaled_value)  # -1.0
```

### PropertyReading

Similar to TelemetryReading but for property-based data access.

**Features:**
- `slots=True`: Memory-efficient
- Validates device_uuid and path are not empty
- Validates faktor is positive
- Provides `scaled_value` property

**Usage:**
```python
from custom_components.comfoclime.models import PropertyReading

# Create a property reading
reading = PropertyReading(
    device_uuid="abc123",
    path="29/1/10",
    raw_value=100,
    faktor=0.5,
    signed=True,
    byte_count=2
)

print(reading.scaled_value)  # 50.0
```

### DashboardData

Dashboard data from the ComfoClime device.

**Features:**
- `slots=True`: Memory-efficient
- Mutable (not frozen) to allow updates from coordinator
- Validates fan_speed is between 0-100
- All fields optional with None defaults

**Usage:**
```python
from custom_components.comfoclime.models import DashboardData

# Create dashboard data
data = DashboardData(
    temperature=22.5,
    target_temperature=21.0,
    fan_speed=50,
    season="heating",
    hp_standby=False
)

# Access fields
print(data.temperature)  # 22.5

# Can be modified (not frozen)
data.temperature = 23.0
print(data.temperature)  # 23.0

# Create with defaults
empty_data = DashboardData()
print(empty_data.temperature)  # None
```

## Why Not Pydantic?

While Pydantic provides powerful validation features, we chose standard Python dataclasses for this integration because:

1. **Minimal Dependencies**: Home Assistant integrations should minimize external dependencies. The manifest currently only requires `aiohttp`.

2. **Sufficient Validation**: Python dataclasses with `__post_init__` provide adequate validation for our use cases.

3. **Performance**: Standard dataclasses with `slots=True` are very memory-efficient without the overhead of Pydantic.

4. **Home Assistant Best Practices**: Many Home Assistant core integrations use standard dataclasses rather than Pydantic.

If more complex validation becomes necessary (e.g., API response parsing with nested structures, regex validation, etc.), Pydantic can be reconsidered.

## Migration from Dict-based Data

These models are designed to gradually replace dict-based data structures. They can be used:

1. **As return types**: Methods can return these dataclasses instead of dicts
2. **For validation**: Parse API responses into dataclasses to validate structure
3. **For type safety**: Enable IDE autocomplete and type checking

### Example Migration

Before:
```python
def get_device_config(self, device_data: dict) -> dict:
    return {
        "uuid": device_data.get("uuid", ""),
        "model_type_id": device_data.get("modelTypeId", 0),
        "display_name": device_data.get("displayName", "Unknown")
    }
```

After:
```python
def get_device_config(self, device_data: dict) -> DeviceConfig:
    return DeviceConfig(
        uuid=device_data.get("uuid", ""),
        model_type_id=device_data.get("modelTypeId", 0),
        display_name=device_data.get("displayName", "Unknown Device")
    )
```

Benefits:
- Validation happens automatically
- Type hints work in IDE
- Cannot accidentally typo field names
- Immutable config prevents bugs

## Testing

Tests for these models are in `tests/test_models.py`. They verify:

- Normal creation works
- Validation catches invalid inputs
- Immutability (frozen) works correctly
- Mutability works where expected
- Slots prevent attribute additions
- Scaled value calculations are correct

Run tests with:
```bash
pytest tests/test_models.py -v
```
