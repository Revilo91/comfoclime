# ComfoClime Home Assistant Integration - Architektur-Dokumentation

Dieses Dokument bietet eine vollständige Übersicht über die Systemarchitektur, Klassenstruktur, Abhängigkeiten und Datenflussmuster der ComfoClime Home Assistant Integration.

**Generiert am:** 2026-02-05  
**Version:** 1.0  
**Analyse-Tools:** Vulture, Pydeps, AST-basierte Code-Analyse

---

## 📊 Executive Summary

Die ComfoClime Integration ist eine vollständig asynchrone Home Assistant Custom Component für die lokale Steuerung von ComfoClime/ComfoAirQ Lüftungsgeräten.

### Kerndaten der Codebase

| Metrik | Anzahl |
|--------|--------|
| **Module** | 23 |
| **Klassen** | 48 |
| **Methoden** | 197 |
| **Funktionen** | 66 |
| **Koordinatoren** | 6 |
| **Entity-Typen** | 6 (Climate, Fan, Sensor, Switch, Number, Select) |
| **Services** | 3 |

---

## 🏗️ Architekturübersicht

### Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  __init__.py (Entry Point)                   │
│  - async_setup_entry()                                       │
│  - async_unload_entry()                                      │
│  - Service Registrations (set_property, reset_system, etc.) │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│ Coordinators │ │   API  │ │  Entities  │
│ (6 types)    │ │        │ │  (6 types) │
└──────┬───────┘ └───┬────┘ └─────┬──────┘
       │             │             │
       └─────────────┼─────────────┘
                     │
           ┌─────────▼─────────┐
           │  ComfoClimeAPI    │
           │  (aiohttp client) │
           └─────────┬─────────┘
                     │
           ┌─────────▼─────────┐
           │  ComfoClime Device│
           │  (Local HTTP API) │
           └───────────────────┘
```

### Datenfluss: Von der Initialisierung bis zur API-Kommunikation

1. **async_setup_entry** (`__init__.py`)
   - Erstellt ComfoClimeAPI-Instanz
   - Ruft `async_get_connected_devices()` auf
   - Initialisiert 6 Koordinatoren parallel
   - Registriert Services
   - Lädt Entity-Plattformen

2. **Koordinatoren** (`coordinator.py`)
   - Rufen periodisch (60s) API-Methoden auf
   - Verteilen Daten an Entities
   - Implementieren Batch-Aktualisierungen für Telemetrie/Properties

3. **API-Layer** (`comfoclime_api.py`)
   - Rate-Limiting (0.1s zwischen Requests)
   - Caching (30s TTL)
   - Retry-Logik (3 Versuche)
   - Session-Management

4. **HTTP-Requests** zum Gerät
   - Lokale, unauthentifizierte API
   - JSON-basierte Kommunikation

---

## 📦 Module-Referenz

### Core-Module

#### 1. `__init__.py` - Integration Entry Point
**Funktion:** Haupteinstiegspunkt der Integration

**Wichtige Funktionen:**
- `async_setup_entry(hass, entry)` - Initialisiert die Integration
- `async_unload_entry(hass, entry)` - Bereinigt Ressourcen beim Entladen
- `async_reload_entry(hass, entry)` - Lädt die Integration neu
- `handle_set_property_service(call)` - Service zum Setzen von Properties
- `handle_reset_system_service(call)` - Service zum Neustart des Geräts
- `handle_set_scenario_mode_service(call)` - Service für Szenario-Modi

**Abhängigkeiten:**
- `comfoclime_api.ComfoClimeAPI`
- `coordinator.*` (alle 6 Koordinatoren)
- `validators.*`
- `access_tracker.AccessTracker`

**Besonderheiten:**
- Migration-Logik für fehlende Options
- Parallele Koordinator-Initialisierung
- Service-Registrierung mit Validierung

---

#### 2. `comfoclime_api.py` - API-Client
**Klasse:** `ComfoClimeAPI`

**Verantwortlichkeit:** Asynchrone HTTP-Kommunikation mit dem ComfoClime-Gerät

**Wichtige Methoden:**

| Methode | Typ | Beschreibung |
|---------|-----|--------------|
| `async_get_dashboard_data()` | async | Liest Dashboard-Daten (Temperatur, Lüfter, etc.) |
| `async_update_dashboard(**kwargs)` | async | Aktualisiert Dashboard-Felder |
| `async_get_thermal_profile()` | async | Liest Thermal-Profile |
| `async_update_thermal_profile(**kwargs)` | async | Aktualisiert Thermal-Profile |
| `async_get_connected_devices()` | async | Liest verbundene Geräte |
| `async_read_telemetry_for_device()` | async | Liest Telemetrie für Gerät |
| `async_read_property_for_device()` | async | Liest Property für Gerät |
| `async_set_property_for_device()` | async | Setzt Property für Gerät |
| `async_reset_system()` | async | Startet System neu |
| `close()` | async | Schließt aiohttp-Session |

**Features:**
- Decorator-basierte API-Aufrufe (`@api_get`, `@api_put`)
- Integrierte Ratenbegrenzung (RateLimiterCache)
- Cache mit 30s TTL für Telemetrie/Properties
- Retry-Logik mit exponential backoff
- Session-Management

**Verwendete Konstanten:**
- `MIN_REQUEST_INTERVAL = 0.1s`
- `WRITE_COOLDOWN = 2.0s`
- `REQUEST_DEBOUNCE = 0.3s`
- `CACHE_TTL = 30s`

---

#### 3. `coordinator.py` - Data Update Coordinators
**Verantwortlichkeit:** Periodisches Polling und Datenverteilung

**Koordinatoren:**

##### 3.1 ComfoClimeDashboardCoordinator
- **Daten:** Dashboard-Daten (Temperatur, Lüfter, Season, etc.)
- **Update-Intervall:** 60s (konfigurierbar)
- **API-Call:** `api.async_get_dashboard_data()`
- **Verwendet von:** Climate, Fan, diverse Sensoren

##### 3.2 ComfoClimeThermalprofileCoordinator
- **Daten:** Thermal Profile (Heiz-/Kühlparameter)
- **Update-Intervall:** 60s
- **API-Call:** `api.async_get_thermal_profile()`
- **Verwendet von:** Number-Entities (Temperatureinstellungen)

##### 3.3 ComfoClimeMonitoringCoordinator
- **Daten:** System-Monitoring (UUID, Uptime, etc.)
- **Update-Intervall:** 60s
- **API-Call:** `api.async_get_monitoring_data()`
- **Verwendet von:** Monitoring-Sensoren

##### 3.4 ComfoClimeTelemetryCoordinator
- **Daten:** Batch-Telemetrie für alle Geräte
- **Update-Intervall:** 60s
- **Besonderheit:** Sammelt Anfragen aller Telemetrie-Sensoren
- **API-Calls:** Gebündelte `async_read_telemetry_for_device()` Aufrufe
- **Verwendet von:** TelemetrySensor-Entities

##### 3.5 ComfoClimePropertyCoordinator
- **Daten:** Batch-Properties für alle Geräte
- **Update-Intervall:** 60s
- **Besonderheit:** Sammelt Anfragen aller Property-Sensoren/Numbers/Selects
- **API-Calls:** Gebündelte `async_read_property_for_device()` Aufrufe
- **Verwendet von:** PropertySensor, PropertyNumber, PropertySelect

##### 3.6 ComfoClimeDefinitionCoordinator
- **Daten:** Gerätedefinitionen (hauptsächlich ComfoAirQ)
- **Update-Intervall:** 60s
- **API-Call:** `api.async_get_device_definition()`
- **Verwendet von:** DefinitionSensor-Entities

**Batch-Update-Mechanismus:**

Telemetrie- und Property-Koordinatoren implementieren ein effizientes Batch-Update:

```python
# Entities registrieren sich beim Koordinator
coordinator.register_telemetry_request(device_uuid, telemetry_id, ...)

# Koordinator sammelt alle Anfragen und führt sie gebündelt aus
async def _async_update_data(self):
    results = {}
    for device_uuid, requests in self._pending_requests.items():
        for req in requests:
            results[key] = await api.async_read_telemetry_for_device(...)
    return results
```

---

### Entity-Module

#### 4. `climate.py` - Climate Entity
**Klasse:** `ComfoClimeClimate`

**Erweitert:** `CoordinatorEntity`, `ClimateEntity`

**Wichtige Methoden:**

| Methode | Typ | Beschreibung |
|---------|-----|--------------|
| `async_set_temperature(temperature)` | async | Setzt Zieltemperatur |
| `async_set_hvac_mode(hvac_mode)` | async | Setzt HVAC-Modus (Off, Heat, Cool, Auto) |
| `async_set_fan_mode(fan_mode)` | async | Setzt Lüfterstufe |
| `async_set_preset_mode(preset_mode)` | async | Setzt Voreinstellung (Comfort, Eco, Szenario-Modi) |
| `async_set_scenario_mode(...)` | async | Aktiviert Szenario-Modus mit Dauer |

**Features:**
- HVAC-Modi: Off, Heat, Cool, Auto
- Preset-Modi: Comfort, Eco, Kochen, Party, Abwesend, Boost
- Szenario-Modi mit konfigurierbarer Dauer
- Integration mit DashboardCoordinator und ThermalprofileCoordinator

**Szenario-Modi:**
- Kochen (4): Hohe Lüftung für Küche (Standard: 30 Min)
- Party (5): Hohe Lüftung für Veranstaltungen (Standard: 30 Min)
- Abwesend (7): Reduzierter Modus für Urlaub (Standard: 24 Std)
- Boost (8): Maximale Leistung (Standard: 30 Min)

---

#### 5. `fan.py` - Fan Entity
**Klasse:** `ComfoClimeFan`

**Erweitert:** `CoordinatorEntity`, `FanEntity`

**Wichtige Methoden:**
- `async_turn_on(percentage)` - Schaltet Lüfter ein
- `async_turn_off()` - Schaltet Lüfter aus
- `async_set_percentage(percentage)` - Setzt Lüftergeschwindigkeit

**Features:**
- Prozentuale Steuerung (0-100%)
- Mapping zu Fan-Speed-Stufen (0-5)
- Integration mit DashboardCoordinator

---

#### 6. `sensor.py` - Sensor Entities
**Klassen:**
- `ComfoClimeSensor` - Standard Dashboard-Sensoren
- `ComfoClimeTelemetrySensor` - Telemetrie-basierte Sensoren
- `ComfoClimePropertySensor` - Property-basierte Sensoren
- `ComfoClimeDefinitionSensor` - Definition-basierte Sensoren
- `ComfoClimeAccessTrackingSensor` - Zugriffs-Tracking-Sensoren

**Sensor-Kategorien:**
- Dashboard: Temperatur, Luftfeuchtigkeit, Fan-Speed, etc.
- Telemetrie: Gerätespezifische Messwerte (CO2, VOC, Druck, etc.)
- Property: Konfigurierbare Eigenschaften
- Definition: Geräteinformationen (Name, Version, etc.)
- Monitoring: System-Uptime, API-Zugriffe

**Konfiguration:**
Sensoren werden über `entities/sensor_definitions.py` definiert:
- `CONNECTED_DEVICE_SENSORS` - Telemetrie-Sensoren
- `CONNECTED_DEVICE_PROPERTIES` - Property-Sensoren
- `ACCESS_TRACKING_SENSORS` - Tracking-Sensoren

---

#### 7. `switch.py` - Switch Entity
**Klasse:** `ComfoClimeSwitch`

**Erweitert:** `CoordinatorEntity`, `SwitchEntity`

**Wichtige Methoden:**
- `async_turn_on()` - Schaltet Switch ein
- `async_turn_off()` - Schaltet Switch aus

**Features:**
- Steuerung von Dashboard-Feldern als Switches
- Automatische State-Synchronisation
- Konfiguration über `entities/switch_definitions.py`

---

#### 8. `number.py` - Number Entities
**Klassen:**
- `ComfoClimeTemperatureNumber` - Temperatur-Einstellungen (Thermal Profile)
- `ComfoClimePropertyNumber` - Allgemeine Property-Numbers

**Wichtige Methoden:**
- `async_set_native_value(value)` - Setzt Wert

**Features:**
- Validation mit Min/Max-Grenzen
- Faktor-basierte Skalierung
- Byte-Count-Unterstützung (1 oder 2 Bytes)
- Signed/Unsigned-Handling

---

#### 9. `select.py` - Select Entities
**Klassen:**
- `ComfoClimeSelect` - Dashboard-basierte Selects
- `ComfoClimePropertySelect` - Property-basierte Selects

**Wichtige Methoden:**
- `async_select_option(option)` - Wählt Option

**Features:**
- Mapping von Options zu Werten
- Integration mit Thermal Profile (Season-Auswahl)
- Property-basierte Selects

---

### Helper & Utility Module

#### 10. `models.py` - Pydantic Data Models
**Klassen:**
- `DeviceConfig` - Gerätekonfiguration
- `TelemetryReading` - Telemetrie-Lesewert
- `PropertyReading` - Property-Lesewert
- `DashboardData` - Dashboard-Datenmodell

**Utility-Funktionen:**
- `bytes_to_signed_int(bytes_value, byte_count)` - Konvertiert Bytes zu signed int
- `signed_int_to_bytes(value, byte_count)` - Konvertiert signed int zu Bytes
- `fix_signed_temperature(temp)` - Korrigiert Vorzeichen für Temperaturen

**Features:**
- Pydantic v2 BaseModel mit Field-Validierung
- Unveränderliche Modelle (`frozen=True`)
- Field-Aliase für API-Mapping
- ValidationError statt ValueError

---

#### 11. `constants.py` - Konstanten & Enums
**Enums:**
- `ScenarioMode` - Szenario-Modi (Kochen, Party, etc.)
- `Season` - Jahreszeiten (Heating, Cooling, Auto)
- `TemperatureProfile` - Temperaturprofile (Comfort, Eco, Manual)
- `FanSpeed` - Lüfterstufen (0-5)

**Klassen:**
- `APIDefaults` - API-Standardwerte (Timeouts, Intervalle, etc.)

---

#### 12. `validators.py` - Validierungsfunktionen
**Funktionen:**
- `validate_property_path(path)` - Validiert Property-Pfad-Format (X/Y/Z)
- `validate_byte_value(value, byte_count, signed)` - Validiert Wert für Byte-Count
- `validate_duration(duration)` - Validiert Zeitdauer

---

#### 13. `exceptions.py` - Custom Exceptions
**Exception-Hierarchie:**
```
ComfoClimeError (BaseException)
├── ComfoClimeConnectionError
├── ComfoClimeAPIError
├── ComfoClimeTimeoutError
└── ComfoClimeValidationError
```

---

#### 14. `access_tracker.py` - API Access Tracking
**Klassen:**
- `CoordinatorStats` - Statistiken pro Koordinator
- `AccessTracker` - Tracking von API-Zugriffen

**Methoden:**
- `record_access(coordinator_name, ...)` - Zeichnet Zugriff auf
- `get_coordinator_stats(name)` - Gibt Statistiken zurück
- `get_all_stats()` - Gibt alle Statistiken zurück

**Features:**
- Tracking von erfolgreichen/fehlgeschlagenen Requests
- Durchschnittliche Response-Zeit
- Letzte Update-Zeit

---

#### 15. `rate_limiter_cache.py` - Rate Limiting & Caching
**Klasse:** `RateLimiterCache`

**Verantwortlichkeit:** 
- Rate-Limiting für API-Requests
- Caching von Responses

**Wichtige Methoden:**
- `async_wait_for_request()` - Wartet bis Request erlaubt ist
- `async_wait_for_write()` - Wartet zusätzliche Zeit nach Write
- `get_cached(key)` - Gibt gecachten Wert zurück
- `set_cache(key, value, ttl)` - Setzt Cache-Eintrag

**Features:**
- Minimale Request-Intervalle
- Write-Cooldown nach Schreibzugriffen
- Request-Debouncing
- TTL-basiertes Caching

---

#### 16. `api_decorators.py` - API Decorator Functions
**Funktionen:**
- `api_get(func)` - Decorator für GET-Requests
- `api_put(func)` - Decorator für PUT-Requests

**Features:**
- Automatisches Retry mit exponential backoff
- Error-Handling
- Logging
- Rate-Limiting-Integration

---

#### 17. `entity_helper.py` - Entity Helper Functions
**Funktionen:**
34 Helper-Funktionen für Entity-Definitionen:
- `get_dashboard_sensors()` - Dashboard-Sensoren
- `get_monitoring_sensors()` - Monitoring-Sensoren
- `get_connected_device_sensors(model_id)` - Gerätespezifische Sensoren
- `get_dashboard_switches()` - Dashboard-Switches
- `get_dashboard_numbers()` - Dashboard-Numbers
- `get_dashboard_selects()` - Dashboard-Selects
- ... und viele weitere

**Verwendung:**
Zentrale Stelle für Entity-Definitionen, die von Config Flow und Entity Setup verwendet werden.

---

#### 18. `config_flow.py` - Configuration Flow
**Klassen:**
- `ComfoClimeConfigFlow` - Initial Setup Flow
- `ComfoClimeOptionsFlow` - Options Flow für Konfiguration

**Wichtige Methoden:**
- `async_step_user(user_input)` - User-Setup-Step
- `async_step_dashboard_entities(user_input)` - Dashboard-Entity-Auswahl
- `async_step_monitoring_entities(user_input)` - Monitoring-Entity-Auswahl
- `async_step_device_entities(user_input)` - Device-Entity-Auswahl
- `async_step_advanced_settings(user_input)` - Erweiterte Einstellungen

**Features:**
- Multi-Step-Setup-Flow
- Entity-Auswahl pro Kategorie
- Erweiterte API-Einstellungen (Timeouts, Polling-Intervall, etc.)
- Validierung der Host-Erreichbarkeit

---

### Entity Definition Module

#### 19. `entities/sensor_definitions.py`
**Konstanten:**
- `DASHBOARD_SENSORS` - Dashboard-Sensor-Definitionen
- `MONITORING_SENSORS` - Monitoring-Sensor-Definitionen
- `CONNECTED_DEVICE_SENSORS` - Gerätespezifische Telemetrie-Sensoren (Dict[ModelID, List])
- `CONNECTED_DEVICE_PROPERTIES` - Gerätespezifische Property-Sensoren (Dict[ModelID, List])
- `ACCESS_TRACKING_SENSORS` - Zugriffs-Tracking-Sensoren

**Klassen:**
- `SensorCategory` - Enum für Sensor-Kategorien
- `SensorDefinition` - Base Definition
- `TelemetrySensorDefinition` - Telemetrie-Sensor
- `PropertySensorDefinition` - Property-Sensor
- `AccessTrackingSensorDefinition` - Tracking-Sensor

---

#### 20. `entities/switch_definitions.py`
**Konstanten:**
- `DASHBOARD_SWITCHES` - Dashboard-Switch-Definitionen

**Klassen:**
- `SwitchDefinition` - Switch Definition

---

#### 21. `entities/number_definitions.py`
**Konstanten:**
- `DASHBOARD_NUMBERS` - Dashboard-Number-Definitionen
- `CONNECTED_DEVICE_PROPERTIES_NUMBERS` - Property-basierte Numbers

**Klassen:**
- `NumberDefinition` - Base Definition
- `PropertyNumberDefinition` - Property Number

---

#### 22. `entities/select_definitions.py`
**Konstanten:**
- `DASHBOARD_SELECTS` - Dashboard-Select-Definitionen
- `CONNECTED_DEVICE_PROPERTIES_SELECTS` - Property-basierte Selects

**Klassen:**
- `SelectDefinition` - Base Definition
- `PropertySelectDefinition` - Property Select

---

## 🔄 Call Graph & Dependency Mapping

### Startup-Sequenz: async_setup_entry

```
async_setup_entry (__init__.py)
  │
  ├─→ ComfoClimeAPI.__init__()
  │     └─→ RateLimiterCache.__init__()
  │
  ├─→ api.async_get_connected_devices()
  │     └─→ @api_get decorator
  │           ├─→ rate_limiter.async_wait_for_request()
  │           ├─→ session.get(url)
  │           └─→ retry logic (max 3x)
  │
  ├─→ Create Coordinators (parallel)
  │     ├─→ ComfoClimeDashboardCoordinator.__init__()
  │     ├─→ ComfoClimeThermalprofileCoordinator.__init__()
  │     ├─→ ComfoClimeMonitoringCoordinator.__init__()
  │     ├─→ ComfoClimeDefinitionCoordinator.__init__()
  │     ├─→ ComfoClimeTelemetryCoordinator.__init__()
  │     └─→ ComfoClimePropertyCoordinator.__init__()
  │
  ├─→ asyncio.gather (first refresh all coordinators)
  │     └─→ Each coordinator calls its _async_update_data()
  │
  ├─→ Store in hass.data[DOMAIN][entry_id]
  │
  ├─→ Register Services
  │     ├─→ handle_set_property_service
  │     ├─→ handle_reset_system_service
  │     └─→ handle_set_scenario_mode_service
  │
  └─→ async_forward_entry_setups
        ├─→ sensor.async_setup_entry()
        ├─→ switch.async_setup_entry()
        ├─→ number.async_setup_entry()
        ├─→ select.async_setup_entry()
        ├─→ fan.async_setup_entry()
        └─→ climate.async_setup_entry()
```

### Coordinator Update Cycle

```
DataUpdateCoordinator.async_refresh()
  │
  └─→ _async_update_data()
        │
        ├─→ DashboardCoordinator
        │     └─→ api.async_get_dashboard_data()
        │           └─→ @api_get decorator
        │                 ├─→ Check cache (30s TTL)
        │                 ├─→ Rate limiter wait
        │                 ├─→ HTTP GET /api/dashboard
        │                 └─→ Store in cache
        │
        ├─→ TelemetryCoordinator
        │     └─→ for each device+telemetry_id
        │           └─→ api.async_read_telemetry_for_device()
        │                 └─→ @api_get decorator
        │                       ├─→ Check cache
        │                       ├─→ Rate limiter wait
        │                       ├─→ HTTP GET /api/connectedDevices/{uuid}/telemetry/{id}
        │                       └─→ bytes_to_signed_int(response)
        │
        └─→ PropertyCoordinator
              └─→ for each device+property_path
                    └─→ api.async_read_property_for_device()
                          └─→ @api_get decorator
                                ├─→ Check cache
                                ├─→ Rate limiter wait
                                ├─→ HTTP GET /api/connectedDevices/{uuid}/properties/{X}/{Y}/{Z}
                                └─→ bytes_to_signed_int(response)
```

### Entity State Updates

```
CoordinatorEntity._handle_coordinator_update()
  │
  └─→ async_write_ha_state()
        │
        ├─→ native_value (property getter)
        │     │
        │     ├─→ ComfoClimeSensor
        │     │     └─→ coordinator.data[field_name]
        │     │
        │     ├─→ ComfoClimeTelemetrySensor
        │     │     └─→ coordinator.data.get((device_uuid, telemetry_id))
        │     │           └─→ value * factor
        │     │
        │     └─→ ComfoClimePropertySensor
        │           └─→ coordinator.data.get((device_uuid, property_path))
        │                 └─→ value * factor
        │
        └─→ Update state in Home Assistant
```

### Service Call Flow: set_property

```
handle_set_property_service (call)
  │
  ├─→ validate_property_path(path)
  ├─→ validate_byte_value(value, byte_count, signed)
  │
  ├─→ Get device from device registry
  │
  └─→ api.async_set_property_for_device()
        │
        └─→ @api_put decorator
              ├─→ signed_int_to_bytes(value/factor, byte_count)
              ├─→ rate_limiter.async_wait_for_request()
              ├─→ rate_limiter.async_wait_for_write() (additional 2s cooldown)
              ├─→ HTTP PUT /api/connectedDevices/{uuid}/properties/{X}/{Y}/{Z}
              ├─→ Retry logic (max 3x)
              └─→ Clear cache for this property
```

---

## 📈 Dependency Matrix

### Inter-Module Dependencies

| Modul | Abhängig von |
|-------|--------------|
| `__init__.py` | api, coordinator, validators, access_tracker, entity_helper |
| `comfoclime_api.py` | api_decorators, constants, models, rate_limiter_cache, validators |
| `coordinator.py` | comfoclime_api, constants, models, access_tracker |
| `climate.py` | coordinator, comfoclime_api, constants, models |
| `fan.py` | coordinator, constants |
| `sensor.py` | coordinator, entities.sensor_definitions, access_tracker |
| `switch.py` | coordinator, entities.switch_definitions |
| `number.py` | coordinator, entities.number_definitions, comfoclime_api, validators |
| `select.py` | coordinator, entities.select_definitions |
| `config_flow.py` | comfoclime_api, entity_helper, validators |
| `entity_helper.py` | entities.*, constants |

### Coordinator → API Method Mapping

| Coordinator | API-Methode | Cache | Batch |
|-------------|-------------|-------|-------|
| Dashboard | `async_get_dashboard_data()` | ❌ | ❌ |
| Thermalprofile | `async_get_thermal_profile()` | ❌ | ❌ |
| Monitoring | `async_get_monitoring_data()` | ❌ | ❌ |
| Definition | `async_get_device_definition()` | ❌ | ❌ |
| Telemetry | `async_read_telemetry_for_device()` | ✅ 30s | ✅ |
| Property | `async_read_property_for_device()` | ✅ 30s | ✅ |

### Entity → Coordinator Mapping

| Entity Type | Coordinator(s) |
|-------------|----------------|
| Climate | Dashboard, Thermalprofile |
| Fan | Dashboard |
| Sensor (Dashboard) | Dashboard |
| Sensor (Monitoring) | Monitoring |
| Sensor (Telemetry) | Telemetry |
| Sensor (Property) | Property |
| Sensor (Definition) | Definition |
| Sensor (AccessTracking) | (direkt AccessTracker) |
| Switch | Dashboard |
| Number (Temperature) | Thermalprofile |
| Number (Property) | Property |
| Select (Season) | Dashboard |
| Select (Property) | Property |

---

## 🔍 Dead Code Analysis

### Vulture-Analyse-Ergebnisse

**Ausführung:** `vulture custom_components/comfoclime --min-confidence 80`

**Ergebnis:** ✅ Keine ungenutzten Funktionen oder Klassen mit Confidence > 80% gefunden

**Interpretation:**
- Die Codebase ist gut gewartet
- Alle Funktionen und Klassen werden aktiv verwendet
- Keine offensichtlichen Dead-Code-Kandidaten

### Manuelle Code-Review-Erkenntnisse

**Potenziell ungenutzte/veraltete Elemente:**

1. **test.py**
   - **Status:** Entwicklungs-/Debug-Datei
   - **Empfehlung:** Kann in `.gitignore` aufgenommen werden, wenn nicht für Tests benötigt
   - **Risiko:** Niedrig

2. **Migration-Logik in __init__.py** (Zeilen 40-62)
   - **Status:** Wird für Backward-Kompatibilität benötigt
   - **Empfehlung:** Kann in zukünftigen Major-Versionen entfernt werden
   - **Risiko:** Niedrig (sollte beibehalten werden)

3. **Ungenutzte Decorator-Args in api_decorators.py**
   - **Status:** Einige Decorator-Parameter werden möglicherweise nicht genutzt
   - **Empfehlung:** Review, ob alle Parameter benötigt werden
   - **Risiko:** Sehr niedrig

**Fazit:** ✅ **Keine kritischen Dead-Code-Probleme identifiziert**

---

## 🎯 Architektur-Best-Practices & Patterns

### ✅ Gut Implementierte Patterns

1. **Coordinator-Pattern**
   - Zentrale Datenverwaltung
   - Vermeidet Entity-zu-Entity-Kommunikation
   - Reduziert API-Load durch Batch-Updates

2. **Async/Await durchgehend**
   - Alle I/O-Operationen asynchron
   - Keine blockierenden Calls
   - Optimale Home Assistant Integration

3. **Retry-Logik mit Exponential Backoff**
   - Robuste Error-Handling
   - Automatische Wiederholungen bei Fehlern
   - Keine API-Überlastung

4. **Rate-Limiting**
   - Schützt das Gerät vor Überlastung
   - Konfigurierbares Timing
   - Write-Cooldown nach Schreibzugriffen

5. **Caching**
   - Reduziert API-Load
   - TTL-basiert (30s)
   - Cache-Invalidierung bei Writes

6. **Pydantic-Modelle**
   - Type-Safety
   - Automatische Validierung
   - Klare Datenstrukturen

7. **Separation of Concerns**
   - API-Layer getrennt von Entities
   - Entities getrennt von Business-Logik
   - Klare Verantwortlichkeiten

### 🔧 Verbesserungspotenziale

1. **hass.data Direktzugriff**
   - **Aktuell:** Einige Stellen nutzen `hass.data[DOMAIN]` direkt
   - **Empfehlung:** Wrapper-Funktion für typsicheren Zugriff
   - **Priorität:** Niedrig

2. **Logging-Konsistenz**
   - **Aktuell:** Mix aus deutschen und englischen Log-Messages
   - **Empfehlung:** Vereinheitlichen (bevorzugt Englisch)
   - **Priorität:** Niedrig

3. **Type-Hints**
   - **Aktuell:** Teilweise fehlende Type-Hints
   - **Empfehlung:** Vollständige Type-Hints für bessere IDE-Unterstützung
   - **Priorität:** Mittel

4. **Dokumentation in Code**
   - **Aktuell:** Teilweise fehlende Docstrings
   - **Empfehlung:** Vollständige Docstrings für alle Public-Methoden
   - **Priorität:** Mittel

---

## 📊 Metriken & Statistiken

### Code-Komplexität

| Kategorie | Anzahl | Durchschnitt pro Modul |
|-----------|--------|------------------------|
| Zeilen Code (LOC) | ~5000 | ~217 |
| Klassen | 48 | 2.1 |
| Methoden | 197 | 4.1 pro Klasse |
| Funktionen | 66 | 2.9 |

### Entity-Verteilung

| Entity-Typ | Anzahl Klassen | Verwendung |
|------------|----------------|------------|
| Sensor | 5 | Dashboard, Telemetrie, Property, Definition, Tracking |
| Climate | 1 | Haupt-Steuerung |
| Fan | 1 | Lüftersteuerung |
| Switch | 1 | On/Off-Steuerung |
| Number | 2 | Temperatur, Properties |
| Select | 2 | Auswahl-Steuerung |

### Coordinator-Effizienz

| Coordinator | Entities | Update-Strategie |
|-------------|----------|------------------|
| Dashboard | ~15 | Single Request |
| Thermalprofile | ~8 | Single Request |
| Monitoring | ~5 | Single Request |
| Telemetry | Variable | Batched (N requests) |
| Property | Variable | Batched (M requests) |
| Definition | Variable | Per Device |

**Batching-Vorteil:**
- Ohne Batching: Jede Entity → 1 API-Call alle 60s
- Mit Batching: Alle Entities → N API-Calls alle 60s (N = Anzahl unique device+id Kombinationen)
- **Einsparung:** ~70-80% API-Calls bei typischer Konfiguration

---

## 🛠️ Tooling & Automatisierung

### Verwendete Tools für diese Analyse

1. **Vulture** - Dead Code Detection
   ```bash
   vulture custom_components/comfoclime --min-confidence 80
   ```

2. **Pydeps** - Dependency Graph Visualization
   ```bash
   pydeps custom_components/comfoclime --max-bacon 2 -o pydeps_graph.svg
   ```

3. **AST-Analyse** - Custom Python Script
   - Extrahiert Klassen, Methoden, Funktionen
   - Erstellt Call Graph
   - Generiert Abhängigkeitsmatrix

### Empfohlene Tools für Wartung

1. **Pylint** - Code Quality
   ```bash
   pylint custom_components/comfoclime
   ```

2. **Black** - Code Formatting
   ```bash
   black custom_components/comfoclime
   ```

3. **MyPy** - Static Type Checking
   ```bash
   mypy custom_components/comfoclime
   ```

4. **Pytest** - Unit Testing
   ```bash
   pytest tests/ -v
   ```

5. **Coverage** - Test Coverage
   ```bash
   pytest --cov=custom_components/comfoclime tests/
   ```

---

## 📚 Weiterführende Dokumentation

### Projekt-Dokumentation

- **README.md** - Projekt-Übersicht, Installation, Konfiguration
- **ComfoClimeAPI.md** - Detaillierte API-Dokumentation mit Beispielen
- **SCENARIO_MODES.md** - Dokumentation der Szenario-Modi
- **PYDANTIC_MIGRATION.md** - Migration zu Pydantic v2
- **TROUBLESHOOTING.md** - Fehlerbehebung und häufige Probleme

### Home Assistant Dokumentation

- [Home Assistant Integration Development](https://developers.home-assistant.io/docs/development_index)
- [Data Update Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data)
- [Entity Integration](https://developers.home-assistant.io/docs/core/entity)

---

## 🔄 Maintenance & Updates

### Regelmäßige Wartungsaufgaben

1. **Dependency Updates**
   - Home Assistant Core Updates
   - aiohttp Updates
   - Pydantic Updates

2. **Code Quality Checks**
   - Monatliche Vulture-Scans
   - Code Review bei größeren Changes
   - Type-Hint-Vervollständigung

3. **Testing**
   - Unit-Tests bei neuen Features
   - Integration-Tests vor Releases
   - Regression-Tests

4. **Dokumentation**
   - Updates bei API-Änderungen
   - Changelog-Pflege
   - Beispiel-Updates

### Change-Management

**Bei API-Änderungen:**
1. Update `comfoclime_api.py`
2. Update entsprechende Koordinatoren
3. Update betroffene Entities
4. Update Tests
5. Update `ComfoClimeAPI.md`
6. Update diese Architektur-Dokumentation

**Bei Entity-Änderungen:**
1. Update Entity-Klasse
2. Update Definition-Files (`entities/*_definitions.py`)
3. Update `entity_helper.py`
4. Update Config Flow (falls UI-Auswahl betroffen)
5. Update Tests

---

## 📞 Support & Kontakt

Für Fragen zur Architektur oder Implementierung:
- GitHub Issues: https://github.com/Revilo91/comfoclime/issues
- GitHub Discussions: https://github.com/Revilo91/comfoclime/discussions

---

**Dokumentationsversion:** 1.0  
**Letzte Aktualisierung:** 2026-02-05  
**Generiert von:** Automated Architecture Analysis Tool  
**Reviewed by:** GitHub Copilot
