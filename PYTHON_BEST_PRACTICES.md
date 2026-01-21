# 🐍 Python Best Practices für ComfoClime

> **Analyse aus der Perspektive eines Senior Python-Entwicklers**
> 
> Dieses Dokument zeigt Verbesserungspotenziale im ComfoClime-Projekt auf und erklärt die empfohlenen Python-Patterns.

---

## Inhaltsverzeichnis

1. [Type Hints & Typing](#1-type-hints--typing)
2. [Exception Handling](#2-exception-handling)
3. [Logging Best Practices](#3-logging-best-practices)
4. [Code Organization & Architecture](#4-code-organization--architecture)
5. [Dataclasses & Pydantic](#5-dataclasses--pydantic)
6. [Async/Await Patterns](#6-asyncawait-patterns)
7. [Constants & Enums](#7-constants--enums)
8. [Testing Patterns](#8-testing-patterns)
9. [Documentation](#9-documentation)
10. [Sicherheit & Validierung](#10-sicherheit--validierung)

---

## 1. Type Hints & Typing

### ❌ Aktueller Code (Problem)

```python
# coordinator.py
def __init__(
    self,
    hass,
    api,
    polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS,
    access_tracker:  "AccessTracker | None" = None,
):
    # hass und api haben keine Type Hints
```

```python
# sensor.py
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]  # data ist untypisiert
    api = data["api"]  # Keine Typinformation
```

### ✅ Verbesserter Code

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from . comfoclime_api import ComfoClimeAPI
    from .access_tracker import AccessTracker

class ComfoClimeDashboardCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for fetching dashboard data from the ComfoClime device."""

    def __init__(
        self,
        hass:  HomeAssistant,
        api: ComfoClimeAPI,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker:  AccessTracker | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Dashboard",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api:  ComfoClimeAPI = api
        self._access_tracker: AccessTracker | None = access_tracker
```

### 🎓 Warum ist das besser?

1. **IDE-Unterstützung**: Autocomplete funktioniert korrekt
2. **Frühe Fehlererkennung**: `mypy` findet Typfehler vor Runtime
3. **Selbstdokumentierend**: Code erklärt sich selbst
4. **Refactoring-Sicherheit**: Änderungen werden geprüft

---

## 2. Exception Handling

### ❌ Aktueller Code (Problem)

```python
# coordinator.py
async def _async_update_data(self):
    try:
        result = await self.api.async_get_dashboard_data()
        return result
    except Exception as e: 
        _LOGGER.debug(f"Error fetching dashboard data: {e}")
        raise UpdateFailed(f"Error fetching dashboard data: {e}") from e
```

```python
# fan.py
async def async_set_percentage(self, percentage: int) -> None:
    try:
        await self._api.async_update_dashboard(fan_speed=step)
        # ... 
    except Exception: 
        _LOGGER.exception("Fehler beim Setzen zvon fanSpeed")  # Typo:  "zvon"
```

### ✅ Verbesserter Code

```python
from aiohttp import ClientError, ClientResponseError
from asyncio import TimeoutError as AsyncTimeoutError

class ComfoClimeConnectionError(Exception):
    """Raised when connection to ComfoClime device fails."""

class ComfoClimeAPIError(Exception):
    """Raised when API returns an error."""

class ComfoClimeTimeoutError(Exception):
    """Raised when request times out."""


async def _async_update_data(self) -> dict[str, Any]: 
    """Fetch dashboard data from the API. 
    
    Returns:
        Dictionary containing dashboard data.
        
    Raises:
        UpdateFailed: When data fetch fails after retries.
    """
    try:
        result = await self.api.async_get_dashboard_data()
        if self._access_tracker:
            self._access_tracker.record_access("Dashboard")
        return result
    except (ClientError, AsyncTimeoutError) as err:
        _LOGGER.warning(
            "Connection error fetching dashboard data: %s", 
            err,
            exc_info=_LOGGER.isEnabledFor(logging.DEBUG)
        )
        raise UpdateFailed(f"Connection error:  {err}") from err
    except ComfoClimeAPIError as err: 
        _LOGGER.error("API error fetching dashboard data: %s", err)
        raise UpdateFailed(f"API error: {err}") from err
```

### 🎓 Warum ist das besser? 

1. **Spezifische Exceptions**: Unterschiedliche Fehlertypen werden unterschiedlich behandelt
2. **Keine blanken `except Exception`**: Versteckt keine unerwarteten Bugs
3. **Strukturiertes Logging**: `%s` statt f-strings für bessere Performance
4. **Custom Exceptions**: Klare Fehlerdomäne für die Integration

---

## 3. Logging Best Practices

### ❌ Aktueller Code (Problem)

```python
# Verschiedene Dateien
_LOGGER. debug(f"Error fetching dashboard data: {e}")
_LOGGER.warning(f"Fehler beim Abrufen von fanSpeed via dashboard: {e}")
_LOGGER.debug(f"Found {len(number_properties)} number properties for model_id {model_id}")
_LOGGER.exception("Fehler beim Setzen zvon fanSpeed")  # Gemischte Sprachen
```

### ✅ Verbesserter Code

```python
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class ComfoClimeLogger:
    """Structured logging helper for ComfoClime."""
    
    @staticmethod
    def api_request(method: str, url: str, **context: Any) -> None:
        """Log API request."""
        _LOGGER.debug(
            "API %s request to %s",
            method,
            url,
            extra={"comfoclime_context": context}
        )
    
    @staticmethod
    def api_response(url: str, status:  int, duration_ms: float) -> None:
        """Log API response."""
        _LOGGER.debug(
            "API response from %s: status=%d, duration=%.2fms",
            url,
            status,
            duration_ms
        )
    
    @staticmethod
    def entity_update(entity_id: str, old_value: Any, new_value: Any) -> None:
        """Log entity state update."""
        if old_value != new_value: 
            _LOGGER.debug(
                "Entity %s updated:  %s -> %s",
                entity_id,
                old_value,
                new_value
            )


# Verwendung: 
ComfoClimeLogger.api_request("GET", url, device_uuid=device_uuid)
ComfoClimeLogger.api_response(url, response. status, duration)
```

### 🎓 Best Practices für Logging

```python
# ❌ FALSCH:  f-strings in logging (String wird immer erstellt)
_LOGGER.debug(f"Processing {len(items)} items for {user}")

# ✅ RICHTIG: %-formatting (String nur erstellt wenn Level aktiv)
_LOGGER.debug("Processing %d items for %s", len(items), user)

# ❌ FALSCH: Exception ohne Traceback
except Exception as e:
    _LOGGER.error(f"Error:  {e}")

# ✅ RICHTIG: exception() für automatischen Traceback
except Exception: 
    _LOGGER.exception("Unexpected error during processing")

# ✅ RICHTIG: Konditionaler Traceback für niedrigere Level
except ClientError as err:
    _LOGGER.warning(
        "Connection failed: %s",
        err,
        exc_info=_LOGGER.isEnabledFor(logging.DEBUG)
    )
```

---

## 4. Code Organization & Architecture

### ❌ Aktueller Code (Problem)

```python
# sensor_definitions.py - Große verschachtelte Dictionaries
DASHBOARD_SENSORS = [
    {
        "key": "indoorTemperature",
        "name": "Indoor Temperature",
        "translation_key": "indoor_temperature",
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    # ... viele weitere Einträge
]
```

### ✅ Verbesserter Code mit Dataclasses

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant. const import EntityCategory


class SensorCategory(Enum):
    """Categories of sensors in the integration."""
    DASHBOARD = auto()
    THERMALPROFILE = auto()
    MONITORING = auto()
    TELEMETRY = auto()
    PROPERTY = auto()


@dataclass(frozen=True, slots=True)
class SensorDefinition:
    """Definition of a sensor entity. 
    
    Attributes:
        key:  Unique identifier for the sensor in API responses.
        translation_key: Key for i18n translations.
        unit: Unit of measurement (e.g., "°C", "m³/h").
        device_class: Home Assistant device class.
        state_class: Home Assistant state class.
        entity_category: Entity category (None, diagnostic, config).
        icon: MDI icon name.
        suggested_display_precision: Decimal places for display.
    """
    key: str
    translation_key: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None
    icon: str | None = None
    suggested_display_precision: int | None = None
    
    @property
    def name(self) -> str:
        """Generate display name from translation key."""
        return self. translation_key.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class TelemetrySensorDefinition(SensorDefinition):
    """Definition for telemetry-based sensors."""
    telemetry_id: str = ""
    faktor: float = 1.0
    signed: bool = False
    byte_count: int = 1


# Sensor Registry
class SensorRegistry:
    """Central registry for all sensor definitions."""
    
    _dashboard_sensors: list[SensorDefinition] = [
        SensorDefinition(
            key="indoorTemperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        SensorDefinition(
            key="outdoorTemperature",
            translation_key="outdoor_temperature",
            unit="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass. MEASUREMENT,
            suggested_display_precision=1,
        ),
    ]
    
    @classmethod
    def get_sensors(cls, category: SensorCategory) -> list[SensorDefinition]:
        """Get sensor definitions by category."""
        mapping = {
            SensorCategory. DASHBOARD: cls._dashboard_sensors,
            # ... weitere Kategorien
        }
        return mapping.get(category, [])
    
    @classmethod
    def get_sensor_by_key(cls, key: str) -> SensorDefinition | None:
        """Find a sensor definition by its key."""
        for sensors in [cls._dashboard_sensors]:   # Alle Listen
            for sensor in sensors:
                if sensor.key == key:
                    return sensor
        return None
```

### 🎓 Vorteile der Dataclass-Architektur

| Feature | Dict-Approach | Dataclass-Approach |
|---------|--------------|-------------------|
| Type Safety | ❌ Runtime Errors | ✅ Static Checking |
| IDE Support | ❌ Keine | ✅ Vollständig |
| Immutability | ❌ Mutable | ✅ `frozen=True` |
| Memory | ❌ Dict overhead | ✅ `slots=True` |
| Validation | ❌ Manual | ✅ `__post_init__` |
| Documentation | ❌ Implizit | ✅ Docstrings |

---

## 5. Dataclasses & Pydantic

### ❌ Aktueller Code (Problem)

```python
# access_tracker.py
@dataclass
class CoordinatorStats:
    """Statistics for a single coordinator's API accesses."""
    access_timestamps:  Deque[float] = field(default_factory=deque)
    total_count: int = 0
    last_access_time: float = 0.0
```

### ✅ Verbesserter Code mit Validierung

```python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass(slots=True)
class CoordinatorStats:
    """Statistics for a single coordinator's API accesses. 
    
    Tracks access timestamps, counts, and timing for monitoring
    API usage patterns.
    
    Attributes:
        access_timestamps:  FIFO queue of access timestamps (monotonic time).
        total_count: Total number of accesses since creation.
        last_access_time:  Timestamp of most recent access.
        
    Example:
        >>> stats = CoordinatorStats()
        >>> stats.record_access(time. monotonic())
        >>> stats.total_count
        1
    """
    access_timestamps: Deque[float] = field(default_factory=deque)
    total_count: int = field(default=0)
    last_access_time: float = field(default=0.0)
    
    def __post_init__(self) -> None:
        """Validate initial state."""
        if self.total_count < 0:
            raise ValueError("total_count cannot be negative")
        if self.last_access_time < 0:
            raise ValueError("last_access_time cannot be negative")
    
    def record_access(self, timestamp: float) -> None:
        """Record a new API access. 
        
        Args:
            timestamp: Monotonic timestamp of the access.
        """
        self.access_timestamps.append(timestamp)
        self.total_count += 1
        self.last_access_time = timestamp
    
    def cleanup_old_entries(self, cutoff:  float) -> int:
        """Remove entries older than cutoff. 
        
        Args:
            cutoff: Timestamp threshold; entries before this are removed.
            
        Returns:
            Number of entries removed. 
        """
        removed = 0
        while self.access_timestamps and self.access_timestamps[0] < cutoff:
            self.access_timestamps.popleft()
            removed += 1
        return removed
```

### 🎓 Für komplexere Validierung:  Pydantic

```python
from pydantic import BaseModel, Field, validator
from typing import Literal


class DeviceConfig(BaseModel):
    """Configuration for a connected device. 
    
    Validates device configuration from API responses.
    """
    uuid: str = Field(..., min_length=1, description="Device unique identifier")
    model_type_id: int = Field(..., ge=0, alias="modelTypeId")
    display_name: str = Field(default="Unknown Device", alias="displayName")
    version: str | None = None
    
    class Config:
        populate_by_name = True  # Erlaubt sowohl alias als auch Feldname
        frozen = True  # Immutable nach Erstellung
    
    @validator("uuid")
    def uuid_not_null(cls, v:  str) -> str:
        """Ensure UUID is not the literal 'NULL' string."""
        if v. upper() == "NULL":
            raise ValueError("UUID cannot be 'NULL'")
        return v


class TelemetryReading(BaseModel):
    """A single telemetry reading from a device."""
    device_uuid: str
    telemetry_id: str
    raw_value: int
    faktor: float = Field(default=1.0, gt=0)
    signed: bool = False
    byte_count:  Literal[1, 2] = 1
    
    @property
    def scaled_value(self) -> float:
        """Calculate the scaled value."""
        value = self.raw_value
        if self.signed and self.byte_count == 2 and value > 32767:
            value -= 65536
        return value * self.faktor
```

---

## 6. Async/Await Patterns

### ❌ Aktueller Code (Problem)

```python
# __init__.py
async def async_setup_entry(hass:  HomeAssistant, entry: ConfigEntry):
    # ... viele sequentielle awaits
    await dashboard_coordinator.async_config_entry_first_refresh()
    await thermalprofile_coordinator.async_config_entry_first_refresh()
    await monitoring_coordinator.async_config_entry_first_refresh()
    await definitioncoordinator.async_config_entry_first_refresh()
```

```python
# fan.py
async def async_set_percentage(self, percentage: int) -> None:
    # ...
    self._hass.add_job(self.coordinator.async_request_refresh)  # Nicht awaited
```

### ✅ Verbesserter Code

```python
import asyncio
from typing import Any


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ComfoClime from a config entry. 
    
    Uses asyncio. gather for parallel initialization where possible.
    """
    # ... API und Coordinator Erstellung ... 
    
    # Parallele Initialisierung unabhängiger Coordinators
    await asyncio.gather(
        dashboard_coordinator.async_config_entry_first_refresh(),
        thermalprofile_coordinator.async_config_entry_first_refresh(),
        monitoring_coordinator.async_config_entry_first_refresh(),
        definitioncoordinator. async_config_entry_first_refresh(),
        return_exceptions=True,  # Fehler nicht die anderen abbrechen lassen
    )
    
    # Abhängige Coordinators danach
    await asyncio.gather(
        tlcoordinator.async_config_entry_first_refresh(),
        propcoordinator.async_config_entry_first_refresh(),
    )
    
    return True


class ComfoClimeFan(CoordinatorEntity[ComfoClimeDashboardCoordinator], FanEntity):
    """Fan entity with proper async handling."""
    
    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage. 
        
        Args:
            percentage: Target percentage (0-100).
        """
        step = self._percentage_to_step(percentage)
        
        try:
            await self._api.async_update_dashboard(fan_speed=step)
        except (ClientError, AsyncTimeoutError) as err:
            raise HomeAssistantError(f"Failed to set fan speed: {err}") from err
        
        self._current_speed = step
        self.async_write_ha_state()
        
        # Proper async refresh scheduling
        await self. coordinator.async_request_refresh()
    
    @staticmethod
    def _percentage_to_step(percentage: int) -> int:
        """Convert percentage to discrete step. 
        
        Args:
            percentage: Value 0-100.
            
        Returns:
            Step value 0-3. 
        """
        return max(0, min(3, round(percentage / 33)))
```

### 🎓 Async Best Practices

```python
# ❌ FALSCH:  Blocking call in async context
import requests
async def fetch_data():
    response = requests.get(url)  # BLOCKING! 

# ✅ RICHTIG: Async HTTP client
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


# ❌ FALSCH: Fire-and-forget ohne Error Handling
hass.add_job(some_async_func())

# ✅ RICHTIG: Proper task management
async def safe_background_task():
    """Background task with error handling."""
    try:
        await some_async_func()
    except Exception: 
        _LOGGER.exception("Background task failed")

hass.async_create_task(safe_background_task())


# ❌ FALSCH: Sequential awaits für unabhängige Operationen
result1 = await fetch_device_1()
result2 = await fetch_device_2()
result3 = await fetch_device_3()

# ✅ RICHTIG: Parallel execution
results = await asyncio.gather(
    fetch_device_1(),
    fetch_device_2(),
    fetch_device_3(),
)


# ✅ RICHTIG: Timeout für externe Calls
async with asyncio.timeout(10):
    result = await api.fetch_data()
```

---

## 7. Constants & Enums

### ❌ Aktueller Code (Problem)

```python
# climate. py
SCENARIO_COOKING = 4  # Kochen - 30 minutes high ventilation
SCENARIO_PARTY = 5  # Party - 30 minutes high ventilation
SCENARIO_HOLIDAY = 7  # Urlaub - 24 hours reduced mode
SCENARIO_BOOST_MODE = 8  # Boost - 30 minutes maximum power

PRESET_SCENARIO_COOKING = "cooking"
PRESET_SCENARIO_PARTY = "party"
PRESET_SCENARIO_AWAY = "away"
PRESET_SCENARIO_BOOST = "scenario_boost"

# Magic numbers verstreut
SCENARIO_DEFAULT_DURATIONS = {
    SCENARIO_COOKING: 30,
    SCENARIO_PARTY:  30,
    SCENARIO_HOLIDAY: 1440,  # Was bedeutet 1440? 
    SCENARIO_BOOST_MODE: 30,
}
```

### ✅ Verbesserter Code

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from typing import Final


class ScenarioMode(IntEnum):
    """Scenario modes supported by ComfoClime. 
    
    These modes temporarily override normal operation.
    """
    COOKING = 4
    PARTY = 5
    HOLIDAY = 7
    BOOST = 8
    
    @property
    def default_duration_minutes(self) -> int:
        """Get default duration in minutes for this scenario."""
        durations = {
            ScenarioMode. COOKING: 30,
            ScenarioMode.PARTY: 30,
            ScenarioMode.HOLIDAY: 24 * 60,  # 24 hours
            ScenarioMode.BOOST: 30,
        }
        return durations[self]
    
    @property
    def preset_name(self) -> str:
        """Get Home Assistant preset name for this scenario."""
        names = {
            ScenarioMode.COOKING: "cooking",
            ScenarioMode. PARTY: "party",
            ScenarioMode.HOLIDAY:  "away",
            ScenarioMode. BOOST: "scenario_boost",
        }
        return names[self]
    
    @classmethod
    def from_preset_name(cls, name: str) -> ScenarioMode | None:
        """Get ScenarioMode from preset name."""
        for mode in cls:
            if mode.preset_name == name:
                return mode
        return None


class Season(IntEnum):
    """Season modes for heating/cooling control."""
    TRANSITIONAL = 0
    HEATING = 1
    COOLING = 2


class TemperatureProfile(IntEnum):
    """Temperature profile presets."""
    COMFORT = 0
    POWER = 1
    ECO = 2


class FanSpeed(IntEnum):
    """Discrete fan speed levels."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    
    def to_percentage(self) -> int:
        """Convert to percentage (0-100)."""
        if self == FanSpeed.HIGH:
            return 100
        return self.value * 33


# Typed Constants
@dataclass(frozen=True)
class APIDefaults:
    """Default values for API configuration."""
    READ_TIMEOUT: Final[int] = 10
    WRITE_TIMEOUT: Final[int] = 30
    CACHE_TTL: Final[float] = 30.0
    MAX_RETRIES: Final[int] = 3
    MIN_REQUEST_INTERVAL: Final[float] = 0.1
    WRITE_COOLDOWN: Final[float] = 2.0
    REQUEST_DEBOUNCE:  Final[float] = 0.3
    POLLING_INTERVAL: Final[int] = 60


# Verwendung
scenario = ScenarioMode. COOKING
print(f"Scenario {scenario.name} dauert {scenario.default_duration_minutes} Minuten")
# Output: Scenario COOKING dauert 30 Minuten

fan = FanSpeed.HIGH
print(f"Fan auf {fan.to_percentage()}%")
# Output: Fan auf 100%
```

---

## 8. Testing Patterns

### ❌ Aktueller Code (Problem)

```python
# conftest.py
@pytest.fixture
def mock_api():
    """Create a mock ComfoClimeAPI instance."""
    api = MagicMock()
    api.uuid = "test-uuid-12345"
    api.async_get_uuid = AsyncMock(return_value="test-uuid-12345")
    # ... viele manuelle Mock-Definitionen
    return api
```

### ✅ Verbesserter Code

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant


@dataclass
class MockAPIResponses:
    """Configurable responses for API mock."""
    uuid: str = "test-uuid-12345"
    dashboard_data: dict[str, Any] = field(default_factory=lambda: {
        "indoorTemperature": 22.5,
        "outdoorTemperature": 15.0,
        "fanSpeed": 2,
        "season": 1,
        "temperatureProfile": 0,
    })
    devices: list[dict[str, Any]] = field(default_factory=list)
    thermal_profile: dict[str, Any] = field(default_factory=lambda: {
        "temperature": {"status": 0, "manualTemperature": 22.0},
        "season": {"status": 0},
    })


class MockComfoClimeAPI:
    """Realistic mock of ComfoClimeAPI for testing. 
    
    Provides configurable responses and tracks calls.
    """
    
    def __init__(self, responses: MockAPIResponses | None = None) -> None:
        self.responses = responses or MockAPIResponses()
        self.uuid = self.responses.uuid
        self._call_history:  list[tuple[str, tuple, dict]] = []
    
    def _record_call(self, method: str, *args:  Any, **kwargs: Any) -> None:
        """Record a method call for verification."""
        self._call_history.append((method, args, kwargs))
    
    async def async_get_uuid(self) -> str:
        self._record_call("async_get_uuid")
        return self. responses.uuid
    
    async def async_get_dashboard_data(self) -> dict[str, Any]:
        self._record_call("async_get_dashboard_data")
        return self.responses.dashboard_data. copy()
    
    async def async_get_connected_devices(self) -> list[dict[str, Any]]: 
        self._record_call("async_get_connected_devices")
        return self.responses.devices. copy()
    
    async def async_update_dashboard(self, **kwargs:  Any) -> None:
        self._record_call("async_update_dashboard", **kwargs)
        # Simulate updating the state
        self.responses.dashboard_data. update(kwargs)
    
    def get_calls(self, method: str) -> list[tuple[tuple, dict]]:
        """Get all calls to a specific method."""
        return [(args, kwargs) for m, args, kwargs in self._call_history if m == method]
    
    def assert_called_once(self, method: str) -> None:
        """Assert a method was called exactly once."""
        calls = self.get_calls(method)
        assert len(calls) == 1, f"Expected 1 call to {method}, got {len(calls)}"


@pytest.fixture
def mock_api_responses() -> MockAPIResponses:
    """Fixture for configurable API responses."""
    return MockAPIResponses()


@pytest.fixture
def mock_api(mock_api_responses:  MockAPIResponses) -> MockComfoClimeAPI:
    """Create a realistic mock API."""
    return MockComfoClimeAPI(mock_api_responses)


@pytest.fixture
def mock_api_with_devices() -> MockComfoClimeAPI: 
    """Create mock API with sample devices."""
    responses = MockAPIResponses(
        devices=[
            {
                "uuid": "device-1-uuid",
                "modelTypeId": 1,
                "displayName": "ComfoAirQ",
                "@modelType": "ComfoAirQ",
            },
            {
                "uuid": "device-2-uuid", 
                "modelTypeId":  20,
                "displayName": "ComfoClime",
                "@modelType": "ComfoClime",
            },
        ]
    )
    return MockComfoClimeAPI(responses)


class TestComfoClimeFan:
    """Tests for ComfoClimeFan entity."""
    
    @pytest.mark.asyncio
    async def test_set_percentage_updates_api(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
        mock_api:  MockComfoClimeAPI,
        mock_device:  dict,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that setting percentage calls API with correct value."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        
        await fan.async_set_percentage(66)
        
        # Verify API was called correctly
        mock_api.assert_called_once("async_update_dashboard")
        calls = mock_api.get_calls("async_update_dashboard")
        assert calls[0][1] == {"fan_speed": 2}
    
    @pytest. mark.asyncio
    @pytest.mark.parametrize(
        "percentage,expected_step",
        [
            (0, 0),
            (33, 1),
            (50, 2),  # Rounds to nearest
            (66, 2),
            (100, 3),
        ],
    )
    async def test_percentage_to_step_conversion(
        self,
        percentage: int,
        expected_step: int,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
        mock_api: MockComfoClimeAPI,
        mock_device: dict,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test percentage to step conversion for various inputs."""
        fan = ComfoClimeFan(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            device=mock_device,
            entry=mock_config_entry,
        )
        
        await fan.async_set_percentage(percentage)
        
        calls = mock_api.get_calls("async_update_dashboard")
        assert calls[0][1]["fan_speed"] == expected_step
```

### 🎓 Testing Best Practices

```python
# Strukturierte Test-Organisation
tests/
├── conftest.py              # Shared fixtures
├── fixtures/
│   ├── api_responses.py     # API response fixtures
│   └── entities. py          # Entity fixtures
├── unit/
│   ├── test_api.py
│   ├── test_coordinator.py
│   └── test_entities/
│       ├── test_climate. py
│       ├── test_fan.py
│       └── test_sensor.py
└── integration/
    └── test_full_flow.py

# Parametrisierte Tests für umfassende Coverage
@pytest.mark.parametrize(
    "input_value,expected,description",
    [
        (0, FanSpeed.OFF, "Zero should be OFF"),
        (1, FanSpeed.LOW, "One should be LOW"),
        (2, FanSpeed.MEDIUM, "Two should be MEDIUM"),
        (3, FanSpeed. HIGH, "Three should be HIGH"),
    ],
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_fan_speed_mapping(input_value, expected, description):
    """Test fan speed value mapping."""
    result = FanSpeed(input_value)
    assert result == expected, description
```

---

## 9. Documentation

### ❌ Aktueller Code (Problem)

```python
# comfoclime_api.py
async def _get_session(self):
    # Keine Dokumentation
```

```python
# Inkonsistente Docstrings
def _friendly_model_name(model_id) -> str:
    """Return a human-friendly model name for a model_id, safe for strings/ints. 

    If the model_id exists in MODEL_TYPE_NAMES, return that.  Otherwise return
    a fallback 'Model {model_id}'. 
    """
```

### ✅ Verbesserter Code

```python
"""ComfoClime API Client. 

This module provides the async API client for communicating with
ComfoClime devices over the local network. 

Example: 
    >>> api = ComfoClimeAPI("http://192.168.1.100")
    >>> async with api: 
    ...     data = await api.async_get_dashboard_data()
    ...     print(f"Indoor temp: {data['indoorTemperature']}°C")

Note:
    The API is local and unauthenticated.  Ensure your network is secure. 
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Final

import aiohttp

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER: Final = logging.getLogger(__name__)


class ComfoClimeAPI:
    """Async API client for ComfoClime devices. 
    
    Handles all communication with the ComfoClime Airduino board,
    including rate limiting, caching, and retry logic.
    
    Attributes:
        base_url: Base URL of the ComfoClime device. 
        uuid: Device UUID, fetched on first request.
        read_timeout:  Timeout for GET requests in seconds.
        write_timeout: Timeout for PUT requests in seconds.
        
    Example:
        >>> api = ComfoClimeAPI("http://comfoclime.local")
        >>> await api.async_get_dashboard_data()
        {'indoorTemperature': 22.5, 'outdoorTemperature': 15.0, ... }
    """
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session. 
        
        Creates a new session if one doesn't exist, using the configured
        timeouts.  The session is reused for all requests to enable
        connection pooling.
        
        Returns:
            The aiohttp ClientSession instance.
            
        Note:
            The session must be closed by calling : meth:`close` when done.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.read_timeout,
                connect=5,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def async_get_dashboard_data(self) -> dict[str, Any]:
        """Fetch current dashboard data from the device.
        
        Returns real-time status including temperatures, fan speed,
        and operating mode.
        
        Returns:
            Dictionary containing: 
                - indoorTemperature (float): Current indoor temperature in °C. 
                - outdoorTemperature (float): Current outdoor temperature in °C.
                - fanSpeed (int): Current fan speed level (0-3).
                - season (int): Current season mode (0=transitional, 1=heating, 2=cooling).
                - temperatureProfile (int): Active profile (0=comfort, 1=power, 2=eco).
                - hpStandby (bool): Whether heat pump is in standby. 
                
        Raises:
            ComfoClimeConnectionError: If connection to device fails.
            ComfoClimeAPIError: If device returns an error response.
            
        Example:
            >>> data = await api.async_get_dashboard_data()
            >>> if data['season'] == 1:
            ...     print("Heating mode active")
        """
        ... 
    
    async def close(self) -> None:
        """Close the API session and release resources.
        
        Should be called when the API client is no longer needed,
        typically in async_unload_entry. 
        
        Example:
            >>> api = ComfoClimeAPI("http://192.168.1.100")
            >>> try:
            ...     data = await api.async_get_dashboard_data()
            ... finally:
            ...     await api.close()
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
```

---

## 10. Sicherheit & Validierung

### ❌ Aktueller Code (Problem)

```python
# config_flow.py
async def async_step_user(self, user_input=None):
    if user_input is not None:
        host = user_input["host"]
        url = f"http://{host}/monitoring/ping"
        # Keine Validierung des Hosts! 
```

```python
# services. yaml verwendet, aber Validierung fehlt
# set_property service - keine Input-Validierung
```

### ✅ Verbesserter Code

```python
import ipaddress
import re
from urllib.parse import urlparse


def validate_host(host: str) -> tuple[bool, str | None]: 
    """Validate a host string for safety and correctness.
    
    Args:
        host:  Hostname or IP address to validate. 
        
    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.
        
    Example:
        >>> validate_host("192.168.1.100")
        (True, None)
        >>> validate_host("evil.com; rm -rf /")
        (False, "Invalid hostname format")
    """
    # Remove any whitespace
    host = host.strip()
    
    # Check for empty
    if not host:
        return False, "Host cannot be empty"
    
    # Check for dangerous characters (command injection prevention)
    if re.search(r'[;&|`$]', host):
        return False, "Invalid characters in hostname"
    
    # Check for URL scheme (should be just host)
    if "://" in host:
        return False, "Host should not include URL scheme"
    
    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(host)
        # Reject dangerous IP ranges
        if ip. is_loopback or ip.is_link_local or ip.is_multicast: 
            return False, "Invalid IP address range"
        return True, None
    except ValueError:
        pass
    
    # Validate as hostname
    hostname_pattern = re.compile(
        r'^(? ! -)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\. ?$'
    )
    if not hostname_pattern.match(host):
        return False, "Invalid hostname format"
    
    return True, None


def validate_property_path(path: str) -> tuple[bool, str | None]:
    """Validate a property path format (X/Y/Z).
    
    Args:
        path: Property path string.
        
    Returns:
        Tuple of (is_valid, error_message).
        
    Example:
        >>> validate_property_path("29/1/10")
        (True, None)
        >>> validate_property_path("invalid")
        (False, "Path must be in format X/Y/Z")
    """
    if not path:
        return False, "Path cannot be empty"
    
    parts = path.split("/")
    if len(parts) != 3:
        return False, "Path must be in format X/Y/Z"
    
    for part in parts:
        if not part. isdigit():
            return False, "Path components must be numeric"
        if int(part) < 0 or int(part) > 255:
            return False, "Path components must be 0-255"
    
    return True, None


def validate_byte_value(
    value: int,
    byte_count: int,
    signed: bool = False,
) -> tuple[bool, str | None]:
    """Validate a value fits in the specified byte count.
    
    Args:
        value: The integer value to validate.
        byte_count: Number of bytes (1 or 2).
        signed: Whether the value is signed. 
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    if byte_count not in (1, 2):
        return False, "byte_count must be 1 or 2"
    
    if signed:
        min_val = -(2 ** (byte_count * 8 - 1))
        max_val = 2 ** (byte_count * 8 - 1) - 1
    else:
        min_val = 0
        max_val = 2 ** (byte_count * 8) - 1
    
    if not min_val <= value <= max_val:
        return False, f"Value must be between {min_val} and {max_val}"
    
    return True, None


# Verwendung in config_flow.py
async def async_step_user(self, user_input:  dict[str, Any] | None = None):
    errors:  dict[str, str] = {}
    
    if user_input is not None:
        host = user_input["host"]
        
        # Validate host first
        is_valid, error = validate_host(host)
        if not is_valid:
            errors["host"] = "invalid_host"
            _LOGGER.warning("Invalid host provided: %s - %s", host, error)
        else:
            # Proceed with connection test
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"http://{host}/monitoring/ping"
                    async with asyncio.timeout(5):
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "uuid" in data:
                                    return self.async_create_entry(
                                        title=f"ComfoClime @ {host}",
                                        data={"host": host},
                                    )
                            errors["host"] = "no_uuid"
            except asyncio.TimeoutError:
                errors["host"] = "timeout"
            except aiohttp.ClientError:
                errors["host"] = "cannot_connect"
    
    return self.async_show_form(
        step_id="user",
        data_schema=vol.Schema({
            vol.Required("host", default="comfoclime.local"): str
        }),
        errors=errors,
    )
```

---

## Zusammenfassung

| Bereich | Priorität | Aufwand | Impact |
|---------|-----------|---------|--------|
| Type Hints | 🔴 Hoch | Medium | Hoch |
| Exception Handling | 🔴 Hoch | Niedrig | Hoch |
| Logging | 🟡 Mittel | Niedrig | Mittel |
| Dataclasses | 🟡 Mittel | Medium | Hoch |
| Enums | 🟢 Niedrig | Niedrig | Mittel |
| Testing | 🔴 Hoch | Hoch | Sehr Hoch |
| Documentation | 🟡 Mittel | Medium | Mittel |
| Validation | 🔴 Hoch | Medium | Hoch |

### Quick Wins (sofort umsetzbar)

1. **f-strings in Logging durch %-formatting ersetzen**
2. **Spezifische Exceptions statt blankem `except Exception`**
3. **Type Hints zu allen public methods hinzufügen**
4. **Enums für Magic Numbers einführen**

### Langfristige Verbesserungen

1. **Sensor Definitions auf Dataclasses migrieren**
2. **Pydantic für API Response Validation**
3. **Umfassende Test Suite mit parametrisierten Tests**
4. **Input Validation für alle User-Eingaben**

---

> **Hinweis**: Diese Analyse basiert auf dem aktuellen Stand des Repositories.  Einige Dateien konnten nur teilweise analysiert werden.  Für die vollständige Codebase siehe:  [github.com/Revilo91/comfoclime](https://github.com/Revilo91/comfoclime)