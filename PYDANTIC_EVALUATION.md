# Pydantic Evaluation for ComfoClime

## Decision: Use Standard Dataclasses, Not Pydantic

After evaluating Pydantic for the ComfoClime integration, we decided to use standard Python dataclasses instead.

## Evaluation Criteria

### 1. Dependency Management ✓ (Dataclasses Win)

**Pydantic:**
- Requires adding `pydantic` to `manifest.json` requirements
- Adds external dependency and increases installation size
- May cause version conflicts with Home Assistant's dependencies

**Standard Dataclasses:**
- Built into Python 3.7+
- No external dependencies
- Zero additional installation overhead

**Winner:** Standard dataclasses - Home Assistant best practices favor minimal dependencies.

### 2. Validation Capabilities ✓ (Tie)

**Pydantic:**
- Rich validation with Field constraints (gt, ge, lt, le, min_length, etc.)
- Automatic type coercion
- Custom validators with decorators
- Complex nested validation

**Standard Dataclasses:**
- `__post_init__` for custom validation
- Type hints for basic type checking
- Manual validation logic (more explicit)

**Winner:** Tie - Standard dataclasses with `__post_init__` provide sufficient validation for our use cases.

### 3. Performance ✓ (Dataclasses Win)

**Pydantic:**
- Runtime validation overhead
- More memory usage without custom Config
- Slower initialization

**Standard Dataclasses:**
- `slots=True` for minimal memory usage
- No runtime validation overhead after init
- Faster instantiation

**Winner:** Standard dataclasses with slots - Significant memory savings and performance improvement.

### 4. API Response Parsing ~ (Pydantic Advantage)

**Pydantic:**
- Excellent for parsing complex API responses
- Handles nested structures automatically
- Automatic alias mapping
- Validation errors with detailed messages

**Standard Dataclasses:**
- Requires manual parsing logic
- More boilerplate for nested structures
- Less detailed error messages

**Winner:** Pydantic has advantages here, but our API responses are relatively simple.

### 5. Type Safety ✓ (Tie)

Both provide:
- Full type hints support
- IDE autocomplete
- Static type checking with mypy

**Winner:** Tie - Both provide excellent type safety.

## Current ComfoClime Use Cases

### Simple Validation Needs

Our current models need:
1. ✓ Non-empty string checks
2. ✓ Non-negative number checks
3. ✓ Value range checks (e.g., fan_speed 0-100)
4. ✓ Literal type checks (byte_count must be 1 or 2)

All of these are easily handled by `__post_init__`.

### Simple Data Structures

Our models are:
- Mostly flat (not deeply nested)
- Few fields (3-6 fields per model)
- Straightforward validation rules

### Performance-Critical Paths

- CoordinatorStats is updated frequently (every API call)
- TelemetryReading may be created in batches
- Memory efficiency matters for embedded/low-power HA instances

## Implementation Comparison

### Pydantic Version (NOT USED)

```python
from pydantic import BaseModel, Field

class TelemetryReading(BaseModel):
    device_uuid: str = Field(..., min_length=1)
    telemetry_id: str = Field(..., min_length=1)
    raw_value: int
    faktor: float = Field(default=1.0, gt=0)
    signed: bool = False
    byte_count: Literal[1, 2] = 2
    
    class Config:
        frozen = False
        # No slots support
```

**Pros:**
- Declarative validation
- Rich error messages

**Cons:**
- External dependency
- No slots support (higher memory usage)
- Runtime validation overhead

### Standard Dataclass Version (USED)

```python
@dataclass(slots=True)
class TelemetryReading:
    device_uuid: str
    telemetry_id: str
    raw_value: int
    faktor: float = 1.0
    signed: bool = False
    byte_count: Literal[1, 2] = 2
    
    def __post_init__(self) -> None:
        if not self.device_uuid:
            raise ValueError("device_uuid cannot be empty")
        if not self.telemetry_id:
            raise ValueError("telemetry_id cannot be empty")
        if self.faktor <= 0:
            raise ValueError("faktor must be greater than 0")
        if self.byte_count not in (1, 2):
            raise ValueError("byte_count must be 1 or 2")
```

**Pros:**
- No external dependency
- Slots support (memory efficient)
- Explicit validation (easier to understand)
- Zero runtime overhead after init

**Cons:**
- More verbose validation code
- Less declarative

## When to Reconsider Pydantic

We should reconsider Pydantic if:

1. **Complex API Response Parsing**: If we need to parse deeply nested JSON with many optional fields
2. **Advanced Validation**: If we need regex patterns, complex cross-field validation, or dependent fields
3. **External API Integration**: If we integrate with external APIs that require complex data transformation
4. **Home Assistant Adds Pydantic**: If Home Assistant core starts using Pydantic (reducing concerns about dependencies)

## Conclusion

For the ComfoClime integration, standard Python dataclasses provide:
- ✓ Sufficient validation capabilities
- ✓ Better performance (slots)
- ✓ Minimal dependencies (HA best practice)
- ✓ Simpler codebase (no additional library to learn)

The additional features of Pydantic (declarative validation, automatic coercion, complex parsing) are not needed for our relatively simple data models.

## References

- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)
- [PEP 681 - Data Class Transforms](https://peps.python.org/pep-0681/)
- [Home Assistant Integration Best Practices](https://developers.home-assistant.io/docs/development_integration_quality_scale/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
