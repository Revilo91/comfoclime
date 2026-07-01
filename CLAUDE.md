# CLAUDE.md

Diese Datei ist die **einzige** KI-Kontextdatei in diesem Repository. Sie ersetzt alle vorherigen
`AGENTS.md`, `.github/copilot-instructions.md`, `.github/ai-notes.md`, `ARCHITECTURE.md`,
`ComfoClimeAPI.md`, `ENTITY_STRATEGY.md`, `SCENARIO_MODES.md`, `TROUBLESHOOTING.md` und alle
sonstigen über die Zeit angesammelten Markdown-Dateien in `docs/`. Wenn du (Claude oder ein
anderer Coding-Agent) an diesem Repo arbeitest: lies **nur** diese Datei plus `README.md`.

---

## 1. Projektüberblick

Home-Assistant-Integration (`custom_components/comfoclime/`) für Zehnder ComfoClime und alle
Geräte am ComfoNet-Bus (v. a. ComfoAir Q). Kanonisches Repo: **https://github.com/Revilo91/comfoclime**

- Steuert die ComfoClime-HVAC-Einheit sowie die angeschlossene Lüftung (ComfoAir Q)
- Kommunikation ausschließlich lokal über eine unauthentifizierte JSON/HTTP-API
  (`iot_class: local_polling`)
- Autodiscovery aller am Bus angeschlossenen Geräte, inkl. generischer Property-/Telemetrie-Sensoren

## 2. Kompatibilität (verbindliche Quelle: die Dateien selbst, nicht alte Docs)

| | Wert | Quelle |
|---|---|---|
| Home Assistant | ≥ 2026.2.0 | `hacs.json`, `pyproject.toml` (dev-dep `homeassistant>=2026.2.1`) |
| Python | ≥ 3.14 | `pyproject.toml` (`requires-python`) |
| aiohttp | ≥ 3.8.0, < 4.0 | `manifest.json` |
| pydantic | ≥ 2.0.0 | `manifest.json` |
| Integrationsversion | siehe `manifest.json` (`version`) – muss identisch mit `pyproject.toml` sein | |

⚠️ Falls du in Zukunft wieder Doku schreibst, die Versionszahlen enthält: **immer aus
`manifest.json`/`pyproject.toml`/`hacs.json` ableiten**, nicht abschreiben – frühere Docs-Versionen
in diesem Repo widersprachen sich hier bereits mehrfach.

## 3. Architektur

```
Home Assistant Core
        │
__init__.py (async_setup_entry / async_unload_entry / Service-Registrierung)
        │
        ├── ComfoClimeAPI (comfoclime_api.py) ── aiohttp-Client, nutzt infrastructure/
        │
        ├── 6 Koordinatoren (coordinator.py, Update-Intervall 60s)
        │     Dashboard, Monitoring, Thermalprofile, Telemetry (gebündelt),
        │     Property (gebündelt), Definition
        │
        └── Entity-Plattformen: climate, fan, sensor, switch, number, select
```

### Modulübersicht (`custom_components/comfoclime/`)

| Datei/Ordner | Zweck |
|---|---|
| `__init__.py` | Setup/Unload, Service-Registrierung (`set_property`, `reset_system`, `set_scenario_mode`) |
| `comfoclime_api.py` | Öffentlicher async API-Client (`ComfoClimeAPI`), nutzt `infrastructure/` |
| `infrastructure/api.py` | Rate-Limiting & Caching (`RateLimiterCache`), `api_get`/`api_put`/`api_post`-Decorator |
| `infrastructure/validation.py` | Input-Validierung (Host/IP, Property-Pfad `X/Y/Z`, Byte-Werte, Dauer) |
| `infrastructure/tracking.py` | `AccessTracker` – API-Zugriffszähler für Diagnose-Sensoren |
| `infrastructure/errors.py` | Custom Exceptions (`ComfoClimeError`, `ComfoClimeConnectionError`, …) |
| `coordinator.py` | 6 `DataUpdateCoordinator`-Klassen (siehe oben) |
| `models.py` | Pydantic-v2-Modelle für alle API-Responses + Byte/Temperatur-Hilfsfunktionen |
| `constants.py` | `APIDefaults`, `FanSpeed`, `ScenarioMode` (IntEnum) u. a. |
| `entity_base.py` | Gemeinsames Mixin für alle Entity-Klassen (Device-Info, Naming) |
| `entity_helper.py` | Sammelt/selektiert Entity-Definitionen aus `entities/*_definitions.py` |
| `entities/base_definitions.py` | **Aktiv genutzte** Basisklasse `EntityDefinitionBase` für alle Definitionsdateien |
| `entities/*_definitions.py` | Statische Sensor-/Switch-/Number-/Select-Definitionen pro Gerätetyp |
| `climate.py` | Climate-Entity: HVAC-Modi, Presets, Szenario-Modi |
| `config_flow.py` | Config-Flow (Setup per Host/IP) + Options-Flow |
| `services.yaml` / `services.py` | Service-Definitionen und -Handler |

⚠️ **Bekannter toter Code:** `entities/base.py` definiert dieselbe Klasse `EntityDefinitionBase`
wie `entities/base_definitions.py`, wird aber **nirgends importiert** (geprüft per grep). Vermutlich
ein Duplikat aus einer früheren Refactoring-Session. Vor dem nächsten Cleanup-Durchgang entfernen
oder klären, ob es ersetzt werden sollte.

## 4. Wichtige Muster & Konventionen

- **Vollständig async**: alle API-Methoden sind `async`/`await`, aiohttp-Session über
  `_get_session()`; muss in `async_unload_entry` per `api.close()` geschlossen werden.
- **Rate-Limiting**: `MIN_REQUEST_INTERVAL=0.1s`, `WRITE_COOLDOWN=2.0s`, `REQUEST_DEBOUNCE=0.3s`,
  durchgesetzt über `asyncio.Lock` in `infrastructure/api.py`.
- **Caching**: Telemetrie-/Property-Reads werden 30s gecacht (`CACHE_TTL`) – vor jedem API-Call
  prüft `RateLimiterCache` den Cache.
- **Batch-Koordinatoren**: `TelemetryCoordinator` und `PropertyCoordinator` bündeln die Requests
  aller registrierten Entities in einem Update-Zyklus, um die Last auf dem Gerät zu minimieren.
- **Eindeutige Entity-IDs**: `f"{entry.entry_id}_<type>_<id>"`.
- **Property-Pfad-Format**: `"X/Y/Z"` (z. B. `29/1/10`), wird in die PUT-URL übersetzt.
- **Pydantic v2 überall**: `model_config = {"frozen": True}` für unveränderliche Modelle,
  `ValidationError` statt `ValueError`, Field-Aliase für camelCase (API) ↔ snake_case (Python).
  Utility-Funktionen `bytes_to_signed_int`, `signed_int_to_bytes`, `fix_signed_temperature` liegen
  zentral in `models.py`.

### byte_count / Datentypen – **kritisch, häufige Fehlerquelle**

Falsche `byte_count`-Werte führen zu kaputten Sensorwerten. Regeln:

- `UINT8`/`CN_UINT8`/`CN_INT8`/`CN_BOOL` → `byte_count=1`
- `UINT16`/`CN_UINT16`/`CN_INT16` → `byte_count=2`
- `UINT32`/`CN_UINT32` → `byte_count=4`
- Temperaturen (Faktor 0.1) sind fast immer `INT16`, `signed=True`
- Prozentwerte (Fan Duty, Bypass, Humidity) sind fast immer `UINT8`
- Fan Speed (rpm), Power (W), Energy (kWh) sind fast immer `UINT16`
- Mehrbyte-Werte sind **little-endian**.

Bekannte Telemetrie-IDs (ComfoClime, `modelTypeId=20`):

| ID | Bytes | signed | Faktor | Beschreibung |
|----|---|---|---|---|
| 4145 | 2 | ✅ | 0.1 | TPMA-Temperatur |
| 4149 | 1 | ❌ | 1.0 | Betriebsmodus (0=Aus,1=Heizen,2=Kühlen) |
| 4151 | 2 | ✅ | 0.1 | Aktuelle Komforttemperatur |
| 4154 | 2 | ✅ | 0.1 | Innentemperatur |
| 4193/4194 | 2 | ✅ | 0.1 | Zu-/Fortlufttemperatur |
| 4195/4196 | 2 | ✅ | 0.1 | Zu-/Abluft Gastemperatur |
| 4197 | 2 | ✅ | 0.1 | Kompressor-Temperatur |
| 4198 | 1 | ❌ | 1.0 | Wärmepumpe Leistungsfaktor (%) |
| 4201 | 2 | ❌ | 1.0 | Aktuelle Leistung (W) |
| 4202/4205 | 2 | ❌ | 1.0 | Hoch-/Niederdruck (kPa) |
| 4203 | 2 | ❌ | 1.0 | Expansionsventil (%) |
| 4207 | 2 | ❌ | 1.0 | 4-Wege-Ventil-Position |

Bekannte Telemetrie-IDs (ComfoAir, `modelTypeId=1`): 117/118 (Lüfter-Ansteuerung %),
121/122 (Lüfter-Drehzahl rpm), 128–130 (Leistung/Energie), 209 (RMOT °C), 227 (Bypass %),
275/278 (Fort-/Zulufttemperatur °C), 290–294 (Feuchtigkeit %).

**Upstream-Referenzen** (kanonische, ausführliche Protokoll-Doku – dort nachschlagen statt raten):
- ComfoClime-Telemetrie & Properties: https://github.com/Revilo91/comfoclime_api/blob/main/ComfoClimeAPI.md
- ComfoAir-Telemetrie (PDO-Protokoll): https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md
- Property-Zugriff (RMI-Protokoll): https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md

Tests für Byte-Regeln: `tests/test_sensor_definitions.py` – bei jeder Änderung an
Entity-Definitionen erweitern/prüfen.

## 5. Neue Telemetrie-/Property-Entity hinzufügen

1. **Telemetrie**: Eintrag in `CONNECTED_DEVICE_SENSORS[model_id]`
   (`entities/sensor_definitions.py`) mit `telemetry_id`, `faktor`, `signed`, `byte_count`, `unit`,
   `device_class`, `state_class`.
2. **Property**: Eintrag in `CONNECTED_DEVICE_PROPERTIES[model_id]` mit `path: "X/Y/Z"`,
   `byte_count`, `faktor`, `signed`.
3. Keine manuelle Registrierung nötig – Entities registrieren sich automatisch beim
   Telemetry-/Property-Coordinator; `sensor.py` instanziiert sie anhand erkannter Geräte.
4. Passenden Test in `tests/test_sensor_definitions.py` ergänzen.

## 6. Entity-Kategorisierung

Home-Assistant-Standard: **Standard** (immer sichtbar), **Configuration**
(`entity_category="config"`, default disabled), **Diagnostic**
(`entity_category="diagnostic"`, default disabled).

- Standard (~20–30 Entities): Climate, Fan-Speed, Kern-Sensoren (Innen-/Außentemp, Sollwert,
  Luftmengen, Fan-Speed, Profil-Status, Season, Wärmepumpenstatus), Komfort-Number/Switch/Select.
- Configuration (~10–15): Heiz-/Kühlkurven-Parameter (Knickpunkt, Schwelle, RMOT-Schwellen,
  Wärmepumpen-Min/Max), Feuchtigkeitskontrolle.
- Diagnostic (~60–80): alle rohen Dashboard-/Monitoring-/Thermalprofil-Detailwerte, sämtliche
  Telemetrie-Sensoren (ComfoClime + ComfoAir) und alle Access-Tracking-Sensoren
  (`*_accesses_per_minute`/`_per_hour` je Koordinator).

Neue Entity hinzufügen → Kategorie im `*_definitions.py`-Eintrag setzen
(`entity_category="config"|"diagnostic"|None`); `entity_registry_enabled_default` folgt daraus
automatisch (`True` nur wenn `entity_category is None`).

## 7. Szenario-Modi (Climate-Presets)

| Preset | Wert | Standarddauer | Beschreibung |
|---|---|---|---|
| `cooking` (Kochen) | 4 | 30 min | Hohe Lüftung |
| `party` (Party) | 5 | 30 min | Hohe Lüftung |
| `away` (Urlaub) | 7 | 1440 min (24h) | Reduzierter Betrieb |
| `boost` (Boost) | 8 | 30 min | Maximale Leistung |

Aktivierung entweder via Standard-`climate.set_preset_mode` (Standarddauer) oder
`comfoclime.set_scenario_mode` (mit `duration`-Override in Minuten, optional `start_delay`).
Restzeit steht als Climate-Attribut `scenario_time_left` (Sekunden) und
`scenario_time_left_formatted` zur Verfügung. Werte in `constants.py` → `ScenarioMode` (IntEnum)
und `SCENARIO_DEFAULT_DURATIONS`.

HVAC-Modi: `off`/`heat`/`cool`/`fan_only` (Season-gesteuert). Presets: `none` (manuell),
`comfort`/`boost`/`eco` (Temperaturprofil) plus die vier Szenario-Presets oben. Heat-Pump-Status
wird bitweise interpretiert (Bit 0x02 = Heizen, Bit 0x04 = Kühlen), damit auch Übergangs-/
Abtau-Zustände korrekt als heating/cooling/idle erkannt werden – Details siehe `climate.py`.

## 8. Services

| Service | Pflichtfelder | Optional |
|---|---|---|
| `comfoclime.set_property` | `device_id`, `path` (X/Y/Z), `value`, `byte_count` (1–2) | `signed`, `faktor` |
| `comfoclime.reset_system` | – | – |
| `comfoclime.set_scenario_mode` | `entity_id`, `scenario` (cooking/party/away/boost) | `duration` (min), `start_delay` |

## 9. API-Kurzreferenz

- **Base URL**: `http://{DEVICE_IP}`
- **UUID vs Device-ID**: UUID = Geräteseriennummer, per `GET /monitoring/ping` ermittelt, nötig für
  `/system/{UUID}/*`. `modelTypeId` (Device-ID) identifiziert den Gerätetyp am ComfoNet-Bus:
  `1`=ComfoAir Q 350/450/600, `20`=ComfoClime 36, `222`=ComfoHub – genutzt für `/device/{UUID}/*`.
- Wichtigste Endpunkte: `GET /monitoring/ping`, `GET|PUT /system/{UUID}/dashboard`,
  `GET /system/{UUID}/devices`, `GET|PUT /system/{UUID}/thermalprofile`,
  `GET /device/{UUID}/telemetry/{ID}`, `GET /device/{UUID}/property/{UNIT}/{SUBUNIT}/{PROPERTY}`,
  `PUT /device/{UUID}/method/{UNIT}/{SUBUNIT}/3`, `PUT /system/reset`.
- API-Ebene liefert überall Pydantic-Modelle zurück (`DashboardData`, `ThermalProfileData`,
  `MonitoringPing`, `DeviceDefinitionData`, `ConnectedDevicesResponse` mit `.devices`,
  `PropertyWriteRequest` für PUT-Property-Writes).
- Ausführliche Endpoint-Doku mit Beispiel-Requests/-Responses: siehe Upstream-Referenzen in
  Abschnitt 4. Dieses Repo hält bewusst **keine** vollständige Endpoint-Referenz mehr lokal vor –
  das war zuvor dupliziert und driftete auseinander.

## 10. Entwicklung & Tests

```bash
uv sync --group dev                 # Dependencies inkl. Testtools installieren
uv run pytest tests/ -v             # Alle Tests
uv run pytest tests/test_X.py -v    # Gezielt
uv run pytest tests/ --cov=custom_components/comfoclime --cov-report=html
uv run ruff check .                 # Lint
uv run ruff format --check .        # Formatierung prüfen
```

- Dev-Umgebung: GitHub Codespace oder VS Code Dev Container (`.devcontainer/`), Home Assistant
  läuft automatisch auf Port 8123. `setup.sh` installiert `uv`, führt `uv sync` aus und verlinkt
  `/workspaces/comfoclime/custom_components/comfoclime` symbolisch nach
  `/config/custom_components/comfoclime` – im Workspace editieren, nicht unter `/config/`.
  Debug-Logging ist in `.devcontainer/configuration.yaml` für `custom_components.comfoclime`
  aktiviert.
  - Nach Codeänderungen: `container restart` (kein Full-Rebuild nötig). Falls der `container`-Befehl
    nicht verfügbar ist (nicht jedes Devcontainer-Image hat ihn): `bash .devcontainer/start-ha.sh`
    oder `python3 -m homeassistant -c .devcontainer/ha-config`.
  - Logs: `container logs` oder in der HA-UI unter „Einstellungen → System → Protokolle“.
  - Integration im Dev-Container hinzufügen: über die UI (Geräte & Dienste → Integration
    hinzufügen → „ComfoClime“ → IP eingeben) oder manuell in `.devcontainer/configuration.yaml`
    (`comfoclime: host: "<IP>"`).
- **Pflicht bei jeder Codeänderung**: passende Tests aktualisieren/ergänzen – Modelle →
  `tests/test_models.py`, API → `tests/test_api.py`, Koordinatoren → `tests/test_coordinator.py`,
  Entities → jeweilige `tests/test_<platform>.py`. Pydantic-Validierungsfehler in Tests als
  `ValidationError` erwarten, nicht `ValueError`.
- Nach Metadaten-Änderungen (manifest/pyproject/hacs) zusätzlich:
  `uv run pytest tests/test_project_metadata.py -v`.
- Releases laufen komplett über GitHub Actions (Workflow „Release“/„Pre-Release“ in
  Actions-Tab): aktualisiert `manifest.json` + `pyproject.toml`, erstellt PR, Tag und
  GitHub-Release inkl. generiertem Changelog. Es gibt bewusst keine lokale `CHANGELOG.md` mehr –
  Release-Historie lebt ausschließlich in GitHub Releases:
  https://github.com/Revilo91/comfoclime/releases

## 11. Bekannte Fallstricke

- Die Geräte-API ist lokal und **unauthentifiziert** – Tests brauchen ein echtes Gerät im Netz
  oder Mocks (siehe `tests/conftest.py`).
- aiohttp-Session muss beim Unload geschlossen werden (`api.close()` in `async_unload_entry`).
- Rate-Limiting greift aktiv – schnelle Folge-Requests führen zu Wartezeiten; Koordinatoren
  bündeln deshalb bewusst.
- `entities/base.py` ist toter Code (siehe Abschnitt 3) – nicht als Referenz für neue
  Definitionsklassen verwenden, sondern `entities/base_definitions.py`.
- Reauth-Flow ist bewusst **nicht** implementiert – die Geräte-API kennt keine Authentifizierung
  und keine Auth-Fehler. Nur relevant, falls Zehnder das per Firmware-Update ändert.
- **GitHub-Integration-Timeout-Fehler** (`homeassistant.components.github`, `Timeout of 20 reached
  while waiting for https://api.github.com/...`) stammen von Home Assistants eingebauter
  GitHub-Integration und haben **nichts** mit dieser Integration zu tun – sie kommuniziert
  ausschließlich lokal.
- Typische Setup-Probleme (keine Verbindung, Entities „Unavailable“, Integration lädt nicht):
  zuerst `curl http://<IP>/api/dashboard` prüfen, dann Logs unter „Settings → System → Logs“ mit
  Debug-Logging für `custom_components.comfoclime`.

## 12. Dokumentationsregeln

- Es gibt nur noch **zwei** Markdown-Dateien im Repo: diese (`CLAUDE.md`) und `README.md`.
  Bevor du eine neue `.md`-Datei anlegst: prüfe, ob der Inhalt nicht einfach in eine der beiden
  gehört. Neue Dauerdokumentation grundsätzlich hier in `CLAUDE.md` ergänzen, nicht als neue Datei.
- Kanonische Repo-URL für Issues/Discussions/Releases/Badges: `Revilo91/comfoclime` – keine
  Fork- oder Feature-Branch-URLs verwenden.
- Setup-Befehle immer `uv sync --group dev` / `uv run ...` (kein `requirements_test.txt` mehr).
- Versionsangaben (HA-Minimum, Python, Dev-Dependencies) bei Änderungen an einer Stelle in
  `manifest.json`/`hacs.json`/`pyproject.toml` ändern und in `README.md` synchron halten.
- Release-Workflow-Verhalten in `.github/workflows/` muss zu den Angaben in `README.md` passen.

## 13. Optionale Subagent-Rollen

Für größere, arbeitsteilige Sessions (z. B. mit spezialisierten Subagenten) haben sich folgende
Rollen bewährt – bei Bedarf als Rollenbeschreibung für einen Subagenten verwenden:

- **Integrations-Spezialist**: Home-Assistant-Integrationslogik (Coordinator, Entities,
  Config-Flow); Fokus `custom_components/comfoclime/`.
- **QA-Automation**: Testabdeckung, Regressionen, Mock-Fixtures; Fokus `tests/`.
- **Security-Auditor**: unauthentifizierte lokale API, Input-Validierung
  (`infrastructure/validation.py`), Injection-Schutz in Property-Pfaden.
- **Technical Writer**: pflegt `README.md` und diese Datei; sorgt für konsistente Terminologie
  und aktuelle Setup-/Troubleshooting-Angaben.
