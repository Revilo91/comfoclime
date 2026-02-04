## Ziel

Kurze, präzise Hinweise für KI-Coding-Agenten, damit sie sofort produktiv an der ComfoClime Home-Assistant-Integration arbeiten können.

## Großes Bild (Architektur)
- Integration als Home Assistant custom_component unter `custom_components/comfoclime/`.
- Datenfluss: ComfoClimeAPI (asynchroner aiohttp-Client) → 5 Koordinatoren (`coordinator.py`) → Entitäten (`climate.py`, `sensor.py`, `switch.py`, `fan.py`, `number.py`, `select.py`).
- API ist lokal (iot_class: „local_polling“, „manifest.json“ erfordert „aiohttp“).
- Koordinatoren mit 60s Update-Intervall: Dashboard, Thermalprofile, Telemetrie (gebündelt), Eigenschaft (gebündelt), Definition.

## Wichtige Dateien zum ersten Lesen

- `ComfoClimeAPI.md` – Ausführliche API-Dokumentation und Dekodierungsbeispiele (eine wahre Fundgrube für Protokolldetails).
- `custom_components/comfoclime/comfoclime_api.py` – Zentrale asynchrone API mit aiohttp; Ratenbegrenzung, Caching (30 s TTL), Wiederholungslogik, Sitzungsverwaltung.
- `custom_components/comfoclime/coordinator.py` – 5 Koordinatoren (Dashboard, Thermalprofil, Telemetrie, Eigenschaft, Definition) mit einem Aktualisierungsintervall von 60 s.
- `custom_components/comfoclime/climate.py` – Klima-Entität mit HLK-Modi, voreingestellten Modi (inkl. Szenario-Modi: Kochen/Party/Abwesend/Boost).
- `custom_components/comfoclime/entities/*.py` – Sensor-/Schalter-/Nummern-/Auswahldefinitionen (separate Definitionsdateien).
- `custom_components/comfoclime/services.yaml` – Dienste: set_property, reset_system, set_scenario_mode.
- `.devcontainer/README.md` – Entwicklungs-Workflow (Codespace/Dev Container, Home Assistant auf Port 8123).
- `SCENARIO_MODES.md` – Dokumentation für die Szenario-Modus-Funktion.

## Wichtige Muster & Konventionen (projektspezifisch)

- Die API ist vollständig asynchron mit aiohttp; alle Methoden sind asynchron (verwenden Sie `await`). Die Sitzung wird über `_get_session()` verwaltet und muss in `async_unload_entry` geschlossen werden.
- Ratenbegrenzung: MIN_REQUEST_INTERVAL=0,1s, WRITE_COOLDOWN=2,0s, REQUEST_DEBOUNCE=0,3s. Die API erzwingt Wartezeiten über `_request_lock` (asyncio.Lock).
- Caching: Telemetrie-/Eigenschaftslesevorgänge werden 30 Sekunden lang zwischengespeichert (CACHE_TTL). Prüfen Sie `_telemetry_cache` / `_property_cache` vor API-Aufrufen.
- Pfadformat für Eigenschaften: "X/Y/Z" (z. B. `29/1/10`) wird in die entsprechenden Teile der PUT-URL übersetzt. Dienste erwarten dieses Format.
- Byte-Verarbeitung: Telemetrie-/Eigenschaftslesevorgänge akzeptieren `byte_count`, `signed` und `faktor` (multiplikative Skalierung). Konfiguriert in `entities/*_definitions.py`.
- Dashboard-Aktualisierungen: Verwenden Sie `api.async_update_dashboard(**fields)` – es werden dynamisch nur die angegebenen Felder aktualisiert.
- eindeutige Entitäts-ID: `f"{entry.entry_id}_<type>_<id>"` für deterministische IDs.
- Batch-Koordinatoren: TelemetryCoordinator und PropertyCoordinator bündeln Anfragen aller Entitäten in einem einzigen Aktualisierungszyklus (reduziert die API-Last).
- Szenario-Modi: Kochen (4), Party (5), Abwesenheit (7), Boost (8) – siehe SCENARIO_MODES.md. Aktivierung über Klimavoreinstellungen oder den Dienst `set_scenario_mode`.
- **Pydantic-Modelle**: Alle Datenmodelle verwenden Pydantic v2 BaseModel (siehe `models.py`). Utility-Funktionen (`bytes_to_signed_int`, `signed_int_to_bytes`, `fix_signed_temperature`) sind in `models.py` zentralisiert.
  - Modelle sind mit Field-Constraints validiert (min_length, ge, gt, le, lt)
  - `model_config = {"frozen": True}` für unveränderliche Modelle
  - ValidationError statt ValueError bei ungültigen Daten
  - Field-Aliase unterstützen camelCase (API) und snake_case (Python)

## Hinzufügen eines Telemetrie- oder Eigenschaftssensors

- Telemetrie: Fügen Sie einen Eintrag zu `CONNECTED_DEVICE_SENSORS[model_id]` in `entities/sensor_definitions.py` mit `telemetry_id`, `faktor`, `signed`, `byte_count`, `unit`, `device_class` und `state_class` hinzu.
- Eigenschaft: Fügen Sie einen Eintrag zu `CONNECTED_DEVICE_PROPERTIES[model_id]` mit `path: "X/Y/Z"`, `byte_count`, `faktor` und `signed` hinzu.
- Entitäten registrieren sich automatisch beim TelemetryCoordinator/PropertyCoordinator für den Batch-Abruf.
- Keine manuelle Konfiguration erforderlich – `sensor.py` instanziiert Sensoren automatisch basierend auf erkannten Geräten.

## Dienste

- `comfoclime.set_property` – Geräteeigenschaften festlegen. Erforderlich: `device_id`, `path` (X/Y/Z), `value`, `byte_count` (1 oder 2). Optional: `signed`, `faktor`.
- `comfoclime.reset_system` – ComfoClime-Gerät neu starten.
- `comfoclime.set_scenario_mode` – Szenariomodus mit benutzerdefinierter Dauer aktivieren. Erforderlich: `entity_id`, `scenario` (Kochen/Party/Abwesend/Boost). Optional: `duration` (Minuten), `start_delay`.

## Entwicklung & Debugging

- **Python-Umgebung**: Alle Ausführungen (Tests, Skripte, API-Aufrufe) müssen in der virtuellen Umgebung `.venv` laufen. Vor jedem Projektstart aktivieren: `source .venv/bin/activate`.
- Verwenden Sie den bereitgestellten Codespace/Dev-Container – Home Assistant startet automatisch auf Port 8123 (siehe `.devcontainer/README.md`).
- Debug-Logging: `.devcontainer/configuration.yaml` aktiviert das Debugging für `custom_components.comfoclime`.
- Schnelle Iteration: `container restart` nach Codeänderungen (kein vollständiger Neuaufbau des Dev-Containers).
- Tests: Ausführen mit `pytest tests/ -v` (Anforderungen in `requirements_test.txt`). Die umfassende Testsuite deckt alle Entitätstypen, die API, Caching sowie Timeout/Retry ab.
- **WICHTIG: Testaktualisierung**: Bei JEDER Codeänderung MÜSSEN die entsprechenden Tests aktualisiert oder neue Tests hinzugefügt werden. Keine Code-Änderung ohne Test-Update!
  - Modell-Änderungen → `tests/test_models.py` aktualisieren
  - API-Änderungen → `tests/test_api.py` aktualisieren
  - Koordinator-Änderungen → `tests/test_coordinator.py` aktualisieren
  - Entitäts-Änderungen → entsprechende `tests/test_*.py` Dateien aktualisieren
  - Neue Funktionen → neue Tests hinzufügen
  - Pydantic-Modelle → ValidationError statt ValueError in Tests verwenden

## Fallstricke & Tücken

- Die API ist lokal und nicht authentifiziert; Die Tests benötigen ein Gerät im Netzwerk oder simulierte Endpunkte (siehe `tests/conftest.py` für Testbeispiele).
- Die aiohttp-Sitzung muss beim Entladen geschlossen werden: `api.close()` in `async_unload_entry`.
- Mehrbytewerte werden im Little-Endian-Format mit expliziter Behandlung von Vorzeichen verarbeitet (siehe ComfoClimeAPI.md).
- Die Ratenbegrenzung wird durchgesetzt – schnell aufeinanderfolgende Anfragen können zu Wartezeiten führen. Koordinatoren verarbeiten Anfragen in Batches, um die Last zu minimieren.

## Kurzübersicht

- Sensoren hinzufügen: `entities/sensor_definitions.py` (Telemetrie → `CONNECTED_DEVICE_SENSORS`, Eigenschaften → `CONNECTED_DEVICE_PROPERTIES`).
- Schalter/Nummern/Auswahlfelder hinzufügen: `entities/switch_definitions.py`, `entities/number_definitions.py`, `entities/select_definitions.py`.
- API-Methoden: `comfoclime_api.py` (async_get_dashboard_data, async_update_dashboard, async_get_thermal_profile, async_read_telemetry_for_device, async_read_property_for_device, async_set_property_for_device).
- Koordinatoren: Dashboard (Dashboard-Daten), Thermalprofil (Thermoeinstellungen), Telemetrie (gebündelte Telemetrie-Messwerte), Eigenschaften (gebündelte Eigenschaften-Messwerte), Definition (Gerätedefinitionen).
- Beispiele für Entitäten: `climate.py` (HLK/Voreinstellungen/Szenariomodi), `sensor.py` (Koordinator + Telemetrie-/Eigenschaftssensoren), `switch.py`, `number.py`, `select.py`, `fan.py`.