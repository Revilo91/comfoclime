## Ziel

Kurze, präzise Hinweise für KI-Coding-Agenten, damit sie sofort produktiv an der ComfoClime Home‑Assistant‑Integration arbeiten können.

## Big picture (Architektur)
- Integration als Home Assistant custom_component unter `custom_components/comfoclime/`.
- Data flow: ComfoClimeAPI (async aiohttp‑Client) → 5 Coordinators (`coordinator.py`) → Entities (`climate.py`, `sensor.py`, `switch.py`, `fan.py`, `number.py`, `select.py`).
- API ist lokal (iot_class: `local_polling`, `manifest.json` requires `aiohttp`).
- Coordinators pollen alle 60s: Dashboard, Thermalprofile, Telemetry (batched), Property (batched), Definition.

## Key files to read first
- `ComfoClimeAPI.md` — ausführliche API‑Dokumentation und decoding/examples (goldmine für protocol details).
- `custom_components/comfoclime/comfoclime_api.py` — zentrale async API mit aiohttp; rate limiting, caching (30s TTL), retry logic, session management.
- `custom_components/comfoclime/coordinator.py` — 5 coordinators (Dashboard, Thermalprofile, Telemetry, Property, Definition) mit 60s update interval.
- `custom_components/comfoclime/climate.py` — climate entity mit HVAC modes, preset modes (inkl. scenario modes: cooking/party/away/boost).
- `custom_components/comfoclime/entities/*.py` — sensor/switch/number/select definitions (separate definition files).
- `custom_components/comfoclime/services.yaml` — services: set_property, reset_system, set_scenario_mode.
- `.devcontainer/README.md` — development workflow (Codespace/Dev Container, Home Assistant on port 8123).
- `SCENARIO_MODES.md` — documentation for scenario modes feature.

## Important patterns & conventions (project-specific)
- API is fully async with aiohttp; all methods are async (use `await`). Session managed via `_get_session()` and must be closed in `async_unload_entry`.
- Rate limiting: MIN_REQUEST_INTERVAL=0.1s, WRITE_COOLDOWN=2.0s, REQUEST_DEBOUNCE=0.3s. API enforces waits via `_request_lock` (asyncio.Lock).
- Caching: Telemetry/property reads cached 30s (CACHE_TTL). Check `_telemetry_cache` / `_property_cache` before API calls.
- Property path format: "X/Y/Z" (e.g. `29/1/10`) translates to PUT URL parts. Services expect this exact format.
- Byte handling: telemetry/property readers accept `byte_count`, `signed`, `faktor` (multiplicative scaling). Set in `entities/*_definitions.py`.
- Dashboard updates: use `api.async_update_dashboard(**fields)` — dynamically includes only provided fields.
- Entity unique_id: `f"{entry.entry_id}_<type>_<id>"` for deterministic ids.
- Batched coordinators: TelemetryCoordinator and PropertyCoordinator batch requests from all entities in single update cycle (reduces API load).
- Scenario modes: Cooking (4), Party (5), Away (7), Boost (8) — see SCENARIO_MODES.md. Activated via climate presets or `set_scenario_mode` service.

## How to add a telemetry or property sensor
- Telemetry: add entry to `CONNECTED_DEVICE_SENSORS[model_id]` in `entities/sensor_definitions.py` with `telemetry_id`, `faktor`, `signed`, `byte_count`, `unit`, `device_class`, `state_class`.
- Property: add to `CONNECTED_DEVICE_PROPERTIES[model_id]` with `path: "X/Y/Z"`, `byte_count`, `faktor`, `signed`.
- Entities auto-register with TelemetryCoordinator/PropertyCoordinator for batched fetching.
- No manual wiring needed — `sensor.py` instantiates sensors automatically based on detected devices.

## Services
- `comfoclime.set_property` — set device property. Required: `device_id`, `path` (X/Y/Z), `value`, `byte_count` (1 or 2). Optional: `signed`, `faktor`.
- `comfoclime.reset_system` — reboot ComfoClime device.
- `comfoclime.set_scenario_mode` — activate scenario mode with custom duration. Required: `entity_id`, `scenario` (cooking/party/away/boost). Optional: `duration` (minutes), `start_delay`.

## Development & debugging
- **Python-Umgebung**: Alle Ausführungen (Tests, Skripte, API-Aufrufe) müssen in der `.venv` virtuellen Umgebung laufen. Vor jedem Projekt-Start aktivieren: `source .venv/bin/activate`.
- Use provided Codespace/Dev Container — Home Assistant boots automatically on port 8123 (see `.devcontainer/README.md`).
- Debug logging: `.devcontainer/configuration.yaml` enables debug for `custom_components.comfoclime`.
- Fast iteration: `container restart` after code changes (not full devcontainer rebuild).
- Tests: Run with `pytest tests/ -v` (requirements in `requirements_test.txt`). Comprehensive test suite covers all entity types, API, caching, timeout/retry.

## Pitfalls & gotchas
- API is local and unauthenticated; tests require on-network device or mocked endpoints (see `tests/conftest.py` for fixtures).
- aiohttp session must be closed on unload: `api.close()` in `async_unload_entry`.
- Multi-byte values use little-endian with explicit signed handling (see ComfoClimeAPI.md).
- Rate limiting enforced — rapid requests may hit waits. Coordinators batch to minimize load.

## Quick references
- Add sensors: `entities/sensor_definitions.py` (Telemetry → `CONNECTED_DEVICE_SENSORS`, Properties → `CONNECTED_DEVICE_PROPERTIES`).
- Add switches/numbers/selects: `entities/switch_definitions.py`, `entities/number_definitions.py`, `entities/select_definitions.py`.
- API methods: `comfoclime_api.py` (async_get_dashboard_data, async_update_dashboard, async_get_thermal_profile, async_read_telemetry_for_device, async_read_property_for_device, async_set_property_for_device).
- Coordinators: Dashboard (dashboard data), Thermalprofile (thermal settings), Telemetry (batched telemetry reads), Property (batched property reads), Definition (device definitions).
- Entity examples: `climate.py` (HVAC/presets/scenario modes), `sensor.py` (coordinator + telemetry/property sensors), `switch.py`, `number.py`, `select.py`, `fan.py`.
