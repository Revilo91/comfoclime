
# GitHub Copilot Anweisungen für ComfoClime

## API-Integration nach ComfoClimeAPI.md

Die Integration basiert auf der offiziellen [ComfoClimeAPI Dokumentation](https://github.com/revilo91/comfoclime_api/blob/main/ComfoClimeAPI.md). Die wichtigsten Vorgaben für die Entwicklung und Nutzung der API sind:

### Authentifizierung
- Die API verwendet keine Token-basierte Authentifizierung
- Alle Endpunkte sind direkt über HTTP GET/PUT Requests erreichbar
- Die IP-Adresse oder der Hostname des ComfoClime-Geräts wird für die Verbindung verwendet

### Hauptendpunkte und Methoden
- **Dashboard-Status abfragen:**
    - `GET /system/{UUID}/dashboard` → Liefert alle aktuellen Werte und Zustände als JSON
    - Beispiel Response:
    ```json
    {
        "indoorTemperature": 25.4,
        "outdoorTemperature": 27.8,
        "exhaustAirFlow": 485,
        "supplyAirFlow": 484,
        "fanSpeed": 2,
        "seasonProfile": 0,
        "temperatureProfile": 0,
        "season": 2,
        "schedule": 0,
        "status": 1,
        "heatPumpStatus": 5,
        "hpStandby": false,
        "freeCoolingEnabled": false,
        "caqFreeCoolingAvailable": true
    }
    ```

- **Geräteinformationen abfragen:**
    - `GET /system/{UUID}/devices` → Liste aller verbundenen Geräte

- **Thermalprofil abfragen:**
    - `GET /system/{UUID}/thermalprofile` → Temperaturprofile und Schwellenwerte

- **Alarme abfragen:**
    - `GET /system/{UUID}/alarms` → Fehlermeldungen aller Geräte

### Property-System für Einstellungen
- **Properties lesen:**
    - `GET /device/{UUID}/property/X/Y/Z` → Liest Eigenschaft von Gerät
    - X = Unit, Y = Subunit, Z = Property

- **Properties schreiben:**
    - `PUT /device/{UUID}/method/X/Y/3` → Schreibt Eigenschaft zu Gerät
    - Body: `{ "data": [property_id, value_bytes...] }`

### Wichtige Properties für ComfoClime
- **Saison (Unit 22, Subunit 1):**
    - Property 2: Season automatic on/off
    - Property 3: Season select (0=transitional, 1=heating, 2=cooling)

- **Temperatur (Unit 22, Subunit 1):**
    - Property 8: Automatic temperature select
    - Property 9: Comfort temp heating
    - Property 10: Comfort temp cooling
    - Property 13: Manual mode target temperature

- **Temperaturprofil (Unit 22, Subunit 1):**
    - Property 29: ComfoClime temp profile (0=Comfort, 1=Power, 2=Eco)

### Sensor-Endpunkte
- **Telemetrie lesen:**
    - `GET /device/{UUID}/telemetry/N` → Liest Sensor N
    - Wichtige Sensoren:
        - 4154: Indoor temperature
        - 4193: Supply temperature
        - 4194: Exhaust temperature
        - 4149: ComfoClime mode (0=off, 1=heating, 2=cooling)

### Fehlerbehandlung
- Prüfe alle Responses auf HTTP-Status und Fehlercodes
- Implementiere ein zentrales Exception-Handling für Netzwerkfehler und ungültige Payloads
- Nutze die Fehlerklassen aus der API-Doku (`ComfoClimeConnectionError`, `ComfoClimeTimeoutError`, etc.)

### Datenmodell
- Die API liefert alle Werte als JSON oder Byte-Arrays
- UUID = Seriennummer des Geräts (wie in der ComfoClime App angezeigt)
- Temperaturwerte in °C als UINT16 (geteilt durch 10 für echte Temperatur)
- Heat Pump Status als Bitfeld (siehe Dokumentation)

### Best Practices
- Alle API-Calls sind asynchron (`async def`)
- Verwende die UUID des ComfoClime-Geräts für alle system/* Endpunkte
- Dokumentiere alle API-Mappings im Code
- Beachte die verschiedenen Betriebsmodi (auto/manual, heating/cooling)

---

## Ergänzende Hinweise für Copilot

- Die Implementierung muss sich strikt an die Endpunkt- und Payload-Vorgaben aus [ComfoClimeAPI.md](https://github.com/revilo91/comfoclime_api/blob/main/ComfoClimeAPI.md) halten.
- Die API verwendet UUID-basierte Endpunkte ohne Token-Authentifizierung
- Neue Entitäten oder Funktionen müssen vorab mit der API-Doku abgeglichen werden.
- Bei Unsicherheiten immer die API-Doku referenzieren.
- Fehlerbehandlung und Logging sind zentral zu implementieren.
- Die Zuordnung von API-Keys zu Home Assistant-Attributen ist im Code zu dokumentieren.
- UUID des ComfoClime-Geräts wird für alle API-Calls benötigt

---

## Ressourcen
- [ComfoClimeAPI.md](https://github.com/revilo91/comfoclime_api/blob/main/ComfoClimeAPI.md)
- `CLIMATE_IMPLEMENTATION.md` – Implementierungsdetails
- `CLIMATE_USAGE_GUIDE.md` – Benutzeranleitung
- Home Assistant Developer Docs

---

## Beispiel: API-Call ohne Authentifizierung

```python
import aiohttp

async def get_dashboard_status(uuid: str, host: str) -> dict:
    """Holt Dashboard-Status vom ComfoClime-Gerät."""
    url = f"http://{host}/system/{uuid}/dashboard"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

async def set_temperature_property(uuid: str, host: str, temp_value: int) -> bool:
    """Setzt Zieltemperatur über Property-System."""
    url = f"http://{host}/device/{uuid}/method/22/1/3"
    # Property 13 = Manual target temperature, Wert als UINT16 (temp * 10)
    data = {"data": [13, temp_value & 0xFF, (temp_value >> 8) & 0xFF]}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=data) as resp:
            resp.raise_for_status()
            return resp.status == 200
```

---

## Commit- und PR-Konventionen
- Commit-Messages und PRs müssen die API-Änderungen klar benennen.
- API-relevante Änderungen immer mit Link zur Doku versehen.

---

## Testing
- Mocke API-Calls mit gültigen und ungültigen Responses laut Doku
- Teste Property-System und Sensor-Endpunkte explizit
- Verwende echte UUID-Strukturen in Tests

---

## Internationalisierung
- Alle Benutzersichtbaren Texte müssen in `translations/` gepflegt werden.

---

## Bei Fragen: Immer die API-Doku konsultieren!

## Entity-Implementierung

### Climate Entity
- **Unterstützte HVAC Modi**: `off`, `heat`, `cool`, `fan_only`
- **Preset Modi**: `comfort`, `power`, `eco`
- **Temperaturbereich**: 10-30°C (abhängig vom Season-Modus)
- **Attribute**: `current_temperature`, `target_temperature`, `hvac_mode`, `preset_mode`

### Sensor Entities
- Verwende `SensorDeviceClass` für korrekte Klassifizierung
- Implementiere `native_unit_of_measurement` für Einheiten
- Nutze `state_class` für historische Daten

### Switch Entities
- Implementiere `turn_on()` und `turn_off()` Methoden
- Verwende `is_on` Property für Status
- Füge Icons über `icon` Property hinzu

## Testing

### Unit Tests
- Alle neuen Funktionen benötigen Tests
- Verwende `pytest` und `pytest-homeassistant-custom-component`
- Mock externe API-Calls mit `aioresponses`

### Beispiel Test-Struktur
```python
async def test_climate_set_temperature(hass, mock_coordinator):
    """Test setting temperature."""
    entity = ComfoClimeClimate(mock_coordinator)

    await entity.async_set_temperature(temperature=22)

    assert mock_coordinator.api.set_temperature.called
    assert mock_coordinator.api.set_temperature.call_args[0][0] == 22
```

### Integration Tests
- Teste mit echten API-Responses (falls möglich)
- Verwende die Testdateien: `test_climate_api.py`, `test_climate_functions.py`

## Debugging

### Logging-Konfiguration
```yaml
logger:
  default: warning
  logs:
    custom_components.comfoclime: debug
    custom_components.comfoclime.climate: debug
    custom_components.comfoclime.coordinator: debug
```

### Debug-Tools
- Verwende `_LOGGER.debug()` für detaillierte Logs
- Implementiere `extra_state_attributes` für Debug-Informationen
- Nutze Home Assistant Developer Tools für Tests

## Dokumentation

### Code-Dokumentation
- Kommentiere komplexe Logik ausführlich
- Verwende Type Hints für bessere Verständlichkeit
- Dokumentiere API-Mapping in separaten Kommentaren

### Benutzer-Dokumentation
- Aktualisiere `CLIMATE_USAGE_GUIDE.md` bei neuen Features
- Füge Beispiele für Service-Calls hinzu
- Dokumentiere Automatisierungsbeispiele

## Versionierung

### Semantic Versioning
- **Major**: Breaking Changes zur API
- **Minor**: Neue Features, abwärtskompatibel
- **Patch**: Bugfixes

### Commit-Format
```
<type>(<scope>): <description>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Spezielle Überlegungen

### Performance
- Minimiere API-Calls durch intelligentes Caching
- Verwende `async_track_time_interval` für periodische Updates
- Implementiere `async_update()` nur wenn notwendig

### Fehlerbehandlung
```python
try:
    await self.coordinator.api.set_temperature(temperature)
except ComfoClimeConnectionError:
    _LOGGER.error("Connection to ComfoClime failed")
    return False
except ComfoClimeTimeoutError:
    _LOGGER.warning("Timeout setting temperature")
    return False
```

### Internationalisierung
- Verwende `translations/` für alle Benutzer-sichtbaren Texte
- Unterstütze mindestens Deutsch (`de.json`) und Englisch (`en.json`)
- Nutze `hass.localize()` für dynamische Übersetzungen

## Nützliche Ressourcen

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [ComfoClime API Dokumentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)
- `CLIMATE_IMPLEMENTATION.md` - Technische Details
- `CLIMATE_USAGE_GUIDE.md` - Benutzeranleitung

## Beispiel-Code für neue Entitäten

```python
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from .coordinator import ComfoClimeDataUpdateCoordinator
from .entity import ComfoClimeEntity

class ComfoClimeTemperatureSensor(ComfoClimeEntity, SensorEntity):
    """ComfoClime temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: ComfoClimeDataUpdateCoordinator,
        description: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description}"
        self._attr_name = f"ComfoClime {description}"

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data.get("temperature")
```

## Entity Definitions Struktur

Das Projekt nutzt separate Definition-Dateien für verschiedene Entity-Types:

- `entities/sensor_definitions.py` - Sensor Entity Definitionen
- `entities/switch_definitions.py` - Switch Entity Definitionen
- `entities/number_definitions.py` - Number Entity Definitionen
- `entities/select_definitions.py` - Select Entity Definitionen

Diese Struktur ermöglicht eine saubere Trennung von Entity-Definitionen und Implementierung.

## Koordinator Pattern

Alle Entitäten verwenden den `ComfoClimeDataUpdateCoordinator` für:
- Zentrale Datenverwaltung
- Periodische Updates
- Fehlerbehandlung
- State Management

```python
class ComfoClimeDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage ComfoClime data updates."""

    def __init__(self, hass: HomeAssistant, api: ComfoClimeAPI):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime",
            update_interval=timedelta(seconds=30),
        )
        self.api = api
```

Bei Fragen oder Unklarheiten, konsultiere die vorhandene Dokumentation oder erstelle ein Issue im Repository.
