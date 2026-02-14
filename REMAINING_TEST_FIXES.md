# Verbleibende Test-Reparaturen - Schnell-Anleitung

## 📊 Überblick

**27 fehlgeschlagene Tests** zu 3 Kategorien:

1. **Entity-Setup Tests (14)** - Device-Dicts → DeviceConfig
2. **Coordinator Registry Tests (5)** - `.registry` Property  
3. **Response-Model Mock Tests (8)** - Status integer

---

## 🔧 Kategorie 1: Entity-Setup Tests (14)

### Problem
Tests in `test_climate.py`, `test_fan.py`, `test_number.py`, `test_select.py`, `test_sensor.py`, `test_switch.py` übergeben noch `device: dict` statt `DeviceConfig`.

**Error Pattern**:
```python
'dict' object has no attribute 'uuid'
# oder
AttributeError: 'dict' object has no attribute 'model_type_id'
```

### Lösung

Option A: **Fixtures in conftest.py nutzen**
```python
def test_climate_device_info(mock_device):  # ← use fixture!
    """Test device info property."""
    climate = ComfoClimateSensor(..
    mock_hass.data[DOMAIN] = {
        "devices": [mock_device],  # ← Pass DeviceConfig
    }
```

Option B: **Inline in Tests**
```python
from custom_components.comfoclime.models import DeviceConfig

device = DeviceConfig(
    uuid="test-uuid",
    model_type_id=20,
    display_name="Test"
)
```

### Test-Dateien zu ändern:
- `test_climate.py::test_climate_device_info` - 1 Fix
- `test_fan.py::test_fan_device_info` - 1 Fix
- `test_number.py` (5 Tests):
  - `test_temperature_number_device_info`
  - `test_property_number_initialization`
  - `test_property_number_update`
  - `test_property_number_async_set_value`
  - `test_property_number_device_info`
  - `test_async_setup_entry`
- `test_select.py` (3 Tests):
  - `test_select_device_info`
  - `test_property_select_update`
  - `test_property_select_option`
  - `test_async_setup_entry`
- `test_sensor.py` (2 Tests):
  - `test_sensor_device_info`
  - `test_async_setup_entry`
- `test_switch.py` (1 Test):
  - `test_switch_device_info`

---

## 🔧 Kategorie 2: Coordinator Registry Tests (5)

### Problem
Tests suchen nach `coordinator.registry`, aber Attribut ist `_telemetry_registry` (private).

**Error Pattern**:
```python
AttributeError: 'ComfoClimeTelemetryCoordinator' object has no attribute 'registry'
```

### Lösung

Option A: **Tests auf private Attribute ändern**
```python
# Vorher:
assert isinstance(coordinator.registry, dict)

# Nachher:
assert isinstance(coordinator._telemetry_registry, dict)
```

Option B: **Public Property hinzufügen** (in `coordinator.py`)
```python
@property
def registry(self):
    """Public access to telemetry registry."""
    return self._telemetry_registry
```

### Test-Zeilen zu ändern:
- `test_coordinator.py::TestTelemetryCoordinatorRegistry::test_telemetry_coordinator_registry_entries_are_pydantic_models`
- `test_coordinator.py::TestTelemetryCoordinatorRegistry::test_telemetry_coordinator_multiple_entries_in_registry`
- `test_coordinator.py::TestPropertyCoordinatorRegistry::test_property_coordinator_registry_entries_are_pydantic_models`
- `test_coordinator.py::TestPropertyCoordinatorRegistry::test_property_coordinator_multiple_entries_in_registry`

---

## 🔧 Kategorie 3: Response-Model Mock Tests (8)

### Problem
Mocks returnen `status='ok'` (string), aber Tests und Code erwarten `status=200` (integer).

**Error Patterns**:
```python
# In test_models.py
AssertionError: assert 'ok' == 200
# oder ValidationError beim Erstellen der Response-Modelle

# In test_timeout_retry.py
AssertionError: assert DashboardUpdateResponse(status='ok') == {'status': 'ok'}
```

### Lösung

**In `test_api.py` MockComfoClimeAPI:**
```python
# Zeile ~118
async def _async_update_dashboard(self, update: Any = None, **kwargs: Any):
    self._record_call("async_update_dashboard", update, **kwargs)
    return DashboardUpdateResponse(status=200)  # ← Status als integer!
    # Nicht: return {'status': 'ok'}
```

**In `test_models.py`:**
Die Tests selbst sind OK - sie erwarten status=200. Das Problem ist, dass die Mocks nicht den richtigen Wert liefern.

**In `test_timeout_retry.py`:**
```python
# Zeile ~386
# Vorher: AssertionError - Vergleicht DashboardUpdateResponse mit dict
assert result == DashboardUpdateResponse(status=200)  # ← Vergleiche Modelle, nicht dicts
# Nicht: assert result == {'status': 'ok'}
```

---

## 📋 Schritt-für-Schritt Anleitung

### 1. Entity-Tests reparieren (20 min)

```bash
cd /home/olivers/Dokumente/comfoclime

# Bearbeite folgende Dateien:
# - tests/test_climate.py
# - tests/test_fan.py
# - tests/test_number.py
# - tests/test_select.py
# - tests/test_sensor.py
# - tests/test_switch.py

# Ersetze alle `device: dict`-Instanzen mit `mock_device` Fixture
```

Beispiel-Änderung:
```python
# test_climate.py - Zeile ~160
def test_climate_device_info(mock_device):  # ← Add fixture
    # ... Test-Setup ...
    hass.data[DOMAIN] = {"devices": [mock_device]}  # ← Pass fixture
```

### 2. Coordinator Registry Tests reparieren (10 min)

```bash
# Bearbeite: tests/test_coordinator.py

# Methode A: Schnell - nur Tests ändern
# Ersetze `.registry` mit `._telemetry_registry`, `._property_registry`

# Methode B: Better - Public Properties hinzufügen
# In custom_components/comfoclime/coordinator.py nach __init__:

@property
def registry(self):
    """Public access to registry (telemetry)."""
    return self._telemetry_registry
```

### 3. Response-Model Tests reparieren (15 min)

```bash
# Bearbeite: tests/test_api.py (MockComfoClimeAPI)

# Ändere alle Mock-Returns von dicts zu Response-Modellen:
# return {'status': 'ok'} ← BAD
# return DashboardUpdateResponse(status=200) ← GOOD

# Bearbeite: tests/test_timeout_retry.py
# Ändere Assertions von dict-Vergleiche zu Response-Modell-Vergleiche
```

### 4. Tests durchführen

```bash
# Test Kategorie 1
python -m pytest tests/test_climate.py tests/test_fan.py \
                 tests/test_number.py tests/test_select.py \
                 tests/test_sensor.py tests/test_switch.py -v

# Test Kategorie 2
python -m pytest tests/test_coordinator.py -v

# Test Kategorie 3
python -m pytest tests/test_api.py tests/test_models.py \
                 tests/test_timeout_retry.py -v

# Alle zusammen
python -m pytest tests/ -v --tb=short
```

---

## ✅ Definition of Done

```
- [ ] Entity-Tests: 14 repariert, alle grün
- [ ] Coordinator Tests: 5 repariert, alle grün
- [ ] Response-Mock Tests: 8 repariert, alle grün
- [ ] Gesamt: 403/403 Tests bestehen
- [ ] Keine Warnings oder Fehler in `pytest tests/`
- [ ] Code Review bestanden
- [ ] Dokumentation aktualisiert
```

---

## 🚀 Geschätzte Zeit

| Kategorie | Zeit | Komplexität |
|-----------|------|-------------|
| Entity-Tests (14) | 20 min | Einfach (Copy-Paste) |
| Coordinator (5) | 10 min | Medium (Wahl: Option A oder B) |
| Response-Mocks (8) | 15 min | Einfach (Syntax-Änderung) |
| **Total** | **45 min** | **Einfach** |

---

## 💡 Pro-Tipps

1. **Nutze Find & Replace** für Mass-Änderungen:
   - `device: dict` → `mock_device`
   - `{'status': 'ok'}` → `DashboardUpdateResponse(status=200)`

2. **Führe Tests häufig durch**, um Fortschritt zu sehen:
   ```bash
   pytest tests/test_X.py -v --tb=short
   ```

3. **Git Commits**: Committe jede Kategorie separat für saubere Geschichte:
   ```bash
   git add tests/test_climate.py tests/test_fan.py ...
   git commit -m "fix: Entity-Setup Tests zu DeviceConfig"
   ```

---

**Geschätzer Completion**: Nach allen Änderungen sollte `pytest tests/` 403/403 Tests bestehen berichten.

Viel Erfolg! 🚀
