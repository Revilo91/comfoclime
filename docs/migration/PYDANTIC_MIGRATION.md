# Pydantic Migration Documentation

## Overview

This document describes the migration from Python `dataclasses` to `pydantic` models in the ComfoClime Home Assistant integration.

## Migration Date

February 2026

## Motivation

The migration to Pydantic provides several key benefits:

1. **Enhanced Data Validation**: Automatic validation of field types and constraints at instantiation time
2. **Better Type Safety**: Runtime type checking prevents silent data corruption
3. **Improved Error Messages**: Clear validation errors that specify exactly what went wrong
4. **Field Constraints**: Built-in validators (min/max, regex, etc.) without custom `__post_init__` methods
5. **Better IDE Support**: Enhanced autocomplete and type inference
6. **Serialization**: Built-in JSON serialization/deserialization support

## Files Converted

### Core Models (`models.py`)

All four dataclasses converted to Pydantic BaseModel:

- **DeviceConfig**: Immutable device configuration model
  - Validates: `uuid` (non-empty), `model_type_id` (≥ 0)
  - Configuration: `frozen=True`, `validate_assignment=True`

- **TelemetryReading**: Telemetry data with scaling
  - Validates: `device_uuid`, `telemetry_id` (non-empty), `faktor` (> 0), `byte_count` (1 or 2)
  - Configuration: `validate_assignment=True`
  - Preserved: `scaled_value` property for value calculation

- **PropertyReading**: Property-based data access
  - Validates: Same as TelemetryReading
  - Configuration: `validate_assignment=True`
  - Preserved: `scaled_value` property

- **DashboardData**: Dashboard operational data (mutable)
  - Validates: `fan_speed` (0-100 if provided)
  - Configuration: `validate_assignment=True` (NOT frozen)

### Entity Definitions

All entity definition dataclasses converted to Pydantic BaseModel:

#### `entities/sensor_definitions.py`
- **SensorDefinition**: Dashboard/thermal profile sensors
- **TelemetrySensorDefinition**: Telemetry-based sensors
- **PropertySensorDefinition**: Property-based sensors
- **AccessTrackingSensorDefinition**: API access tracking sensors

Configuration: `frozen=True`, `arbitrary_types_allowed=True` (for Home Assistant enum types)

#### `entities/number_definitions.py`
- **NumberDefinition**: Thermal profile number controls
- **PropertyNumberDefinition**: Device property number controls

Configuration: `frozen=True`

#### `entities/select_definitions.py`
- **SelectDefinition**: Temperature profile/season selects
- **PropertySelectDefinition**: Device property selects

Configuration: `frozen=True`

#### `entities/switch_definitions.py`
- **SwitchDefinition**: Dashboard/thermal profile switches

Configuration: `frozen=True`

### Additional Models

#### `constants.py`
- **APIDefaults**: Immutable API configuration defaults
  - Configuration: `frozen=True`
  - All fields have descriptive Field() declarations

#### `access_tracker.py`
- **CoordinatorStats**: API access statistics tracking
  - Validates: `total_count` (≥ 0), `last_access_time` (≥ 0)
  - Configuration: `validate_assignment=True`, `arbitrary_types_allowed=True`
  - Preserved: `record_access()` and `cleanup_old_entries()` methods

## Key Changes

### 1. Import Changes

**Before:**
```python
from dataclasses import dataclass
```

**After:**
```python
from pydantic import BaseModel, Field
```

### 2. Class Definition

**Before:**
```python
@dataclass(frozen=True, slots=True)
class DeviceConfig:
    uuid: str
    model_type_id: int
    display_name: str = "Unknown Device"
```

**After:**
```python
class DeviceConfig(BaseModel):
    model_config = {"frozen": True, "validate_assignment": True}
    
    uuid: str = Field(..., min_length=1, description="Device unique identifier")
    model_type_id: int = Field(..., ge=0, description="Model type identifier")
    display_name: str = Field(default="Unknown Device", description="Human-readable device name")
```

### 3. Validation Migration

**Before (`__post_init__`):**
```python
def __post_init__(self) -> None:
    if not self.uuid or len(self.uuid) == 0:
        raise ValueError("uuid cannot be empty")
    if self.model_type_id < 0:
        raise ValueError("model_type_id must be non-negative")
```

**After (Field constraints):**
```python
uuid: str = Field(..., min_length=1)
model_type_id: int = Field(..., ge=0)
```

### 4. Configuration Options

Pydantic `model_config` replaces dataclass decorators:

| Dataclass | Pydantic Equivalent |
|-----------|---------------------|
| `frozen=True` | `model_config = {"frozen": True}` |
| `slots=True` | Not needed (Pydantic V2 is memory efficient) |
| n/a | `validate_assignment=True` (validates on field updates) |
| n/a | `arbitrary_types_allowed=True` (for non-standard types) |

## Backward Compatibility

✅ **Fully backward compatible** - All models maintain the same public interface:

- Same field names and types
- Same default values
- Same method signatures (`scaled_value`, `record_access`, etc.)
- Same instantiation syntax

The only differences are:
- More descriptive error messages on validation failures
- Pydantic raises `ValidationError` instead of generic `ValueError`
- Test assertions may need to check for `ValidationError` type

## Benefits Realized

1. **Automatic Validation**: No more manual `__post_init__` validation code
2. **Declarative Constraints**: Field constraints are self-documenting via `Field()`
3. **Type Safety**: Runtime type checking catches bugs early
4. **Better DX**: Enhanced IDE autocomplete and type hints
5. **Less Code**: Removed ~50 lines of manual validation code
6. **Consistent**: All models follow same Pydantic patterns

## Files NOT Converted

The following files were intentionally NOT converted as they don't contain data model classes:

- `climate.py`, `sensor.py`, `number.py`, `select.py`, `switch.py`, `fan.py`: Home Assistant entity implementations (use framework patterns)
- `comfoclime_api.py`: API client (uses `dict[str, Any]` for raw API responses)
- `coordinator.py`: Data coordinators (return raw dicts for Home Assistant)
- `config_flow.py`: Configuration flow (uses Home Assistant's config flow framework)
- `validators.py`: Validation functions (standalone functions, not models)

These files use `dict[str, Any]` appropriately as part of Home Assistant's entity framework patterns.

## Testing

All converted models have been tested to ensure:
- ✅ Instantiation works correctly
- ✅ Validation catches invalid data
- ✅ Immutability works where specified
- ✅ Mutability works where needed (DashboardData, CoordinatorStats)
- ✅ Properties are preserved (`scaled_value`)
- ✅ Methods are preserved (`record_access`, `cleanup_old_entries`)

## Dependencies

Added to requirements:
- `manifest.json`: `"pydantic>=2.0.0"`
- `requirements_test.txt`: `pydantic>=2.0.0`

Pydantic V2 is used for best performance and features.

## Conclusion

The migration to Pydantic successfully modernizes the codebase with enhanced validation and type safety while maintaining 100% backward compatibility with existing code.
