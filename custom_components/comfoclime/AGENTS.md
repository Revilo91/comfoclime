# AGENTS

## Scope

This file applies to the Home Assistant integration code under `custom_components/comfoclime/`.

## Architecture

- Main flow: `ComfoClimeAPI` -> coordinators in `coordinator.py` -> entity platforms.
- The API client is async and uses `aiohttp`, request throttling, retries, and short-lived caches.
- Telemetry and property entities rely on batched coordinators; avoid per-entity polling logic.

## Change Rules

- Preserve deterministic unique IDs and current entity naming patterns.
- Keep byte decoding rules aligned with `ComfoClimeAPI.md` and `entities/*_definitions.py`.
- If you change entities, coordinators, models, or API behavior, update the matching tests in `tests/`.
- If you add metadata fields or services, keep `manifest.json`, `services.yaml`, and user-facing docs synchronized.

## Validation

- Focused tests for touched modules.
- Run `uv run pytest tests/test_project_metadata.py -v` after metadata changes.