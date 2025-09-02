
# GitHub Copilot Anweisungen für ComfoClime

## API-Integration nach ComfoClimeAPI.md

Die Integration basiert auf der offiziellen [ComfoClimeAPI Dokumentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md). Die wichtigsten Vorgaben für die Entwicklung und Nutzung der API sind:

### Authentifizierung
- Die API verwendet einen Token-Mechanismus. Der Token wird über `/api/auth` abgerufen und muss für alle weiteren Requests im Header `Authorization: Bearer <token>` gesetzt werden.
- Token-Handling und Erneuerung sind zentral im Coordinator zu implementieren.

### Endpunkte und Methoden
- **Status abfragen:**
    - `GET /api/status` → Liefert alle aktuellen Werte und Zustände als JSON.
- **Temperatur setzen:**
    - `POST /api/temperature` mit Payload `{ "temperature": <float>, "season": "heating|cooling" }`
- **HVAC-Modus setzen:**
    - `POST /api/hvac_mode` mit Payload `{ "mode": "heat|cool|off|fan_only" }`
- **Preset-Modus setzen:**
    - `POST /api/preset` mit Payload `{ "preset": "comfort|eco|power" }`
- **Lüfterstufe setzen:**
    - `POST /api/fan_speed` mit Payload `{ "speed": <int> }`
- **Weitere Endpunkte:** Siehe ComfoClimeAPI.md für alle verfügbaren Methoden und deren Payloads.

### Fehlerbehandlung
- Prüfe alle Responses auf HTTP-Status und Fehlercodes.
- Implementiere ein zentrales Exception-Handling für Netzwerkfehler, Authentifizierungsfehler und ungültige Payloads.
- Nutze die Fehlerklassen aus der API-Doku (`ComfoClimeConnectionError`, `ComfoClimeTimeoutError`, etc.).

### Datenmodell
- Die API liefert alle Werte als JSON. Die Zuordnung zu Home Assistant-Entitäten erfolgt im Coordinator.
- Verwende die in der Doku beschriebenen Keys und Werte für Sensoren, Climate, Switches etc.
- Beispiel für Status-Response:
    ```json
    {
        "temperature": 21.5,
        "season": "heating",
        "hvac_mode": "heat",
        "preset": "comfort",
        "fan_speed": 2,
        ...
    }
    ```

### Best Practices
- Alle API-Calls sind asynchron (`async def`).
- Token-Handling und API-Fehlerbehandlung sind zentral im Coordinator.
- Nutze die in der Doku empfohlenen Payloads und Response-Keys.
- Dokumentiere alle API-Mappings im Code.

---

## Ergänzende Hinweise für Copilot

- Die Implementierung muss sich strikt an die Endpunkt- und Payload-Vorgaben aus [ComfoClimeAPI.md](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md) halten.
- Neue Entitäten oder Funktionen müssen vorab mit der API-Doku abgeglichen werden.
- Bei Unsicherheiten immer die API-Doku referenzieren.
- Die Authentifizierung ist Pflicht für alle Requests.
- Fehlerbehandlung und Logging sind zentral zu implementieren.
- Die Zuordnung von API-Keys zu Home Assistant-Attributen ist im Code zu dokumentieren.

---

## Ressourcen
- [ComfoClimeAPI.md](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)
- `CLIMATE_IMPLEMENTATION.md` – Implementierungsdetails
- `CLIMATE_USAGE_GUIDE.md` – Benutzeranleitung
- Home Assistant Developer Docs

---

## Beispiel: API-Call mit Authentifizierung

```python
import aiohttp

async def get_status(token: str, host: str) -> dict:
        url = f"http://{host}/api/status"
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
```

---

## Commit- und PR-Konventionen
- Commit-Messages und PRs müssen die API-Änderungen klar benennen.
- API-relevante Änderungen immer mit Link zur Doku versehen.

---

## Testing
- Mocke API-Calls mit gültigen und ungültigen Responses laut Doku.
- Teste Authentifizierungs- und Fehlerfälle explizit.

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
