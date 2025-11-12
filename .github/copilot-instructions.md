## Ziel

Kurze, präzise Hinweise für KI-Coding-Agenten, damit sie sofort produktiv an der ComfoClime Home‑Assistant‑Integration arbeiten können.

## Big picture (Architektur)
- Integration als Home Assistant custom_component unter `custom_components/comfoclime/`.
- Data flow: ComfoClimeAPI (synchroner requests‑Client) → Coordinator(s) (`coordinator.py`) → Entities (`climate.py`, `sensor.py`, `switch.py`, `fan.py`, `number.py`, `select.py`).
- API ist lokal (iot_class: `local_polling`, `manifest.json` requires `requests`).
- Coordinators pollen alle 30s (siehe `ComfoClimeDashboardCoordinator` / `ComfoClimeThermalprofileCoordinator`).

## Key files to read first
- `ComfoClimeAPI.md` — ausführliche API‑Dokumentation und decoding/examples (goldmine für protocol details).
- `custom_components/comfoclime/comfoclime_api.py` — zentrale API‑wrappers; note: sync requests executed in HA threadpool via `hass.async_add_executor_job` and protected by `self._request_lock` (asyncio.Lock).
- `custom_components/comfoclime/coordinator.py` — update interval and error handling patterns.
- `custom_components/comfoclime/climate.py` — example of mapping between device fields and HA entity API (hvac_mode, hvac_action, preset, fan modes).
- `custom_components/comfoclime/sensor.py` und `entities/sensor_definitions.py` — canonical way to add telemetry/property sensors.
- `custom_components/comfoclime/services.yaml` — service names and parameter conventions (notably property path format X/Y/Z).
- `.devcontainer/README.md` — development & debugging workflow (Codespace/Dev Container, Home Assistant on port 8123).

## Important patterns & conventions (project-specific)
- API concurrency: all public async API functions acquire `self._request_lock` and delegate to sync implementations via `hass.async_add_executor_job`. Do not call the sync `requests` functions directly from async code — use the async wrappers.
- Property path format: properties are referenced as "X/Y/Z" (e.g. `29/1/10`) and translated to PUT URL parts in `set_property_for_device` (x, y, z). Services expect this exact format.
- Byte handling: telemetry/property readers accept `byte_count`, `signed` and `faktor` (multiplicative scaling). When adding sensors, set `faktor` and `byte_count` in `entities/sensor_definitions.py`.
- Dashboard updates: use `ComfoClimeAPI.update_dashboard` (or `async_update_dashboard`) — it dynamically includes only provided fields; prefer these helpers to avoid sending malformed payloads.
- Atomic HVAC season changes: use `async_set_hvac_season` to set season and hpStandby in one locked operation to avoid races.
- Entity unique_id pattern: most entities use `f"{entry.entry_id}_<type>_<id>"` (see `sensor.py`) — follow this for deterministic ids.
- Translation & naming: translations live in `custom_components/comfoclime/translations/` and many entities use `translation_key` in definitions.

## How to add a telemetry or property sensor (concrete example)
- Telemetry: add an entry to `CONNECTED_DEVICE_SENSORS[model_id]` in `entities/sensor_definitions.py` with `telemetry_id`, `faktor`, `signed`, `byte_count`, `unit`, `device_class`, `state_class`.
  Example (supply air temp): telemetry_id 4193, faktor 0.1, byte_count 2.
- Property sensor: add to `CONNECTED_DEVICE_PROPERTIES[model_id]` with `path: "X/Y/Z"`, `byte_count`, `faktor`, `signed`.
- After changing definitions, no further wiring is necessary — `sensor.py` will instantiate sensors automatically based on `devices` detected at runtime.

## Services & examples
- `comfoclime.set_property` — sets property on a device. Required fields: `device_id` (HA device registry id), `path` (X/Y/Z), `value`, `byte_count` (1 or 2). `signed` and `faktor` optional. See `custom_components/comfoclime/services.yaml` for schema.
- `comfoclime.reset_system` — triggers device reboot.
- Example to set a 1‑byte unsigned property at path `29/1/10`: use the service `comfoclime.set_property` with `byte_count: 1`, `signed: false`.

## Development & debugging workflow
- Use the provided Codespace / Dev Container — Home Assistant boots automatically on port 8123. See `.devcontainer/README.md` for container helper commands (`container restart`, `container logs`, `container enter`).
- Debug logging: `.devcontainer/configuration.yaml` enables debug for `custom_components.comfoclime` by default. Check the container logs or HA UI logs.
- Fast iteration: after code changes do a Home Assistant restart inside the container (`container restart`) — not a full devcontainer rebuild.

## Tests & quick scripts
- `custom_components/comfoclime/test.py` contains a small standalone script demonstrating `ComfoClimeAPI.async_set_property_for_device` usage. It is useful for low‑level API validation (not full unit tests).

## Pitfalls & gotchas to watch for
- Network access: the device API is local and unauthenticated; tests require an on‑network device or mocked endpoints.
- Many functions raise `requests` exceptions — callers usually catch and log; keep error messages in the existing style (mix of English/German logging exists in repo).
- When encoding/decoding multi‑byte values use little‑endian and the repo uses explicit signed handling (see ComfoClimeAPI and ComfoClimeAPI.md).

## Useful quick references for the agent
- Add sensors: `entities/sensor_definitions.py` (Telemetry → `CONNECTED_DEVICE_SENSORS`, Properties → `CONNECTED_DEVICE_PROPERTIES`).
- API helpers: `comfoclime_api.py` (async wrappers, update_dashboard, update_thermal_profile, set_property_for_device).
- Entity examples: `climate.py` (mapping HVAC/presets), `sensor.py` (coordinator + telemetry/property sensors).

If any section is unclear or you'd like me to include short code snippets showing how to add a sensor or a unit test, tell me which part to expand.
