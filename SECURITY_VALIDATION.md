# Security & Input Validation

## Overview

This document describes the security and input validation measures implemented in the ComfoClime Home Assistant integration.

## Validation Functions

All validation functions are located in `custom_components/comfoclime/validators.py` and return a tuple of `(is_valid: bool, error_message: str | None)`.

### 1. Host Validation (`validate_host`)

**Purpose**: Prevents command injection and validates hostname/IP format.

**Security Checks**:
- Rejects command injection characters: `;`, `&`, `|`, `` ` ``, `$`
- Rejects URL schemes (`http://`, `https://`)
- Rejects dangerous IP ranges:
  - Loopback addresses (127.0.0.1, ::1)
  - Link-local addresses (169.254.0.0/16)
  - Multicast addresses (224.0.0.0/4)
- Validates hostname format (RFC 1123)

**Example**:
```python
from validators import validate_host

# Valid
is_valid, error = validate_host("192.168.1.100")  # (True, None)
is_valid, error = validate_host("comfoclime.local")  # (True, None)

# Invalid
is_valid, error = validate_host("127.0.0.1")  # (False, "Invalid IP address range")
is_valid, error = validate_host("evil.com; rm -rf /")  # (False, "Invalid characters in hostname")
```

### 2. Property Path Validation (`validate_property_path`)

**Purpose**: Ensures property paths follow the X/Y/Z format with valid ranges.

**Security Checks**:
- Must have exactly 3 numeric parts separated by `/`
- Each part must be 0-255 (single byte range)
- Prevents path traversal attacks

**Example**:
```python
from validators import validate_property_path

# Valid
is_valid, error = validate_property_path("29/1/10")  # (True, None)
is_valid, error = validate_property_path("0/0/0")  # (True, None)

# Invalid
is_valid, error = validate_property_path("../../etc/passwd")  # (False, "Path must be in format X/Y/Z")
is_valid, error = validate_property_path("256/1/10")  # (False, "Path components must be 0-255")
```

### 3. Byte Value Validation (`validate_byte_value`)

**Purpose**: Validates that values fit within specified byte counts.

**Security Checks**:
- Validates byte_count is 1 or 2
- Checks value fits in signed/unsigned range
- Prevents integer overflow/underflow

**Example**:
```python
from validators import validate_byte_value

# Valid
is_valid, error = validate_byte_value(100, 1, signed=False)  # (True, None)
is_valid, error = validate_byte_value(-10, 1, signed=True)  # (True, None)

# Invalid
is_valid, error = validate_byte_value(300, 1, signed=False)  # (False, "Value must be between 0 and 255")
is_valid, error = validate_byte_value(-200, 1, signed=True)  # (False, "Value must be between -128 and 127")
```

### 4. Duration Validation (`validate_duration`)

**Purpose**: Ensures scenario mode durations are positive values.

**Security Checks**:
- Rejects zero and negative values
- Supports both integer and float durations

**Example**:
```python
from validators import validate_duration

# Valid
is_valid, error = validate_duration(30)  # (True, None)
is_valid, error = validate_duration(1.5)  # (True, None)

# Invalid
is_valid, error = validate_duration(0)  # (False, "Duration must be positive")
is_valid, error = validate_duration(-10)  # (False, "Duration must be positive")
```

## Integration Points

### Config Flow (`config_flow.py`)

Host validation is performed before making API calls during setup:

```python
from .validators import validate_host

async def async_step_user(self, user_input=None):
    if user_input is not None:
        host = user_input["host"]
        
        # Validate host first for security
        is_valid, error_message = validate_host(host)
        if not is_valid:
            errors["host"] = "invalid_host"
            _LOGGER.warning("Invalid host provided: %s - %s", host, error_message)
        else:
            # Proceed with API call
            ...
```

### Services (`__init__.py`)

#### set_property Service

Validates property path, byte count, and value before setting:

```python
from .validators import validate_property_path, validate_byte_value

async def handle_set_property_service(call: ServiceCall):
    path = call.data["path"]
    value = call.data["value"]
    byte_count = call.data["byte_count"]
    signed = call.data.get("signed", True)
    faktor = call.data.get("faktor", 1.0)
    
    # Validate property path format
    is_valid, error_message = validate_property_path(path)
    if not is_valid:
        raise HomeAssistantError(f"Ungültiger Property-Pfad: {error_message}")
    
    # Validate byte count
    if byte_count not in (1, 2):
        raise HomeAssistantError("byte_count muss 1 oder 2 sein")
    
    # Validate value fits in byte count
    actual_value = int(value / faktor)
    is_valid, error_message = validate_byte_value(actual_value, byte_count, signed)
    if not is_valid:
        raise HomeAssistantError(f"Ungültiger Wert: {error_message}")
```

#### set_scenario_mode Service

Validates duration parameter:

```python
from .validators import validate_duration

async def handle_set_scenario_mode_service(call: ServiceCall):
    duration = call.data.get("duration")
    
    # Validate duration if provided
    if duration is not None:
        is_valid, error_message = validate_duration(duration)
        if not is_valid:
            raise HomeAssistantError(f"Ungültige Dauer: {error_message}")
```

### API Layer (`comfoclime_api.py`)

Final validation at the API level:

```python
from .validators import validate_property_path, validate_byte_value

async def async_set_property_for_device(
    self,
    device_uuid: str,
    property_path: str,
    value: float,
    *,
    byte_count: int,
    signed: bool = True,
    faktor: float = 1.0,
):
    # Validate property path format
    is_valid, error_message = validate_property_path(property_path)
    if not is_valid:
        raise ValueError(f"Invalid property path: {error_message}")
    
    # Validate byte count
    if byte_count not in (1, 2):
        raise ValueError("Nur 1 oder 2 Byte unterstützt")

    # Calculate raw value and validate it fits in byte count
    raw_value = int(round(value / faktor))
    is_valid, error_message = validate_byte_value(raw_value, byte_count, signed)
    if not is_valid:
        raise ValueError(f"Invalid value for byte_count={byte_count}, signed={signed}: {error_message}")
```

## Testing

Comprehensive tests are provided in `tests/test_validators.py` covering:

- Valid inputs for all validators
- Security attack scenarios (command injection, path traversal)
- Edge cases and boundary values
- Integration scenarios

Run tests with:
```bash
pytest tests/test_validators.py -v
```

## Security Considerations

1. **Defense in Depth**: Validation is performed at multiple layers (config flow, services, API)
2. **Fail-Safe**: Invalid inputs are rejected with clear error messages
3. **No Bypass**: All user-facing entry points perform validation
4. **Logging**: Invalid inputs are logged for security monitoring

## References

- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [CWE-190: Integer Overflow](https://cwe.mitre.org/data/definitions/190.html)
- PYTHON_BEST_PRACTICES.md Section 10: Sicherheit & Validierung
