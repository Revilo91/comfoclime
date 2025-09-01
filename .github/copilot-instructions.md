# ComfoClime Home Assistant Integration

Always follow these instructions first and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.

## Working Effectively

Bootstrap and validate the repository:
- `pip3 install homeassistant voluptuous aiohttp` -- installs core Home Assistant dependencies (takes 2-3 minutes). NEVER CANCEL: Wait for completion.
- `pip3 install flake8 black isort` -- installs Python linting tools (takes 30 seconds)
- `pip3 install pytest pytest-homeassistant-custom-component` -- installs testing framework (takes 1-2 minutes). NEVER CANCEL: Wait for completion.
- `python3 -c "from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI; print('✓ Import successful')"` -- validates basic functionality (takes <1 second)
- `flake8 custom_components/comfoclime --max-line-length=120 --ignore=E203,W503` -- runs linting (takes <1 second)
- `python3 -m py_compile custom_components/comfoclime/*.py` -- validates Python syntax (takes <1 second)

## Validation

Always run these validation steps after making changes:
- `python3 -m py_compile custom_components/comfoclime/*.py` -- check Python syntax for all files (takes <1 second)
- `flake8 custom_components/comfoclime --max-line-length=120 --ignore=E203,W503` -- check code style (takes <1 second)
- `black --check custom_components/comfoclime --line-length=120` -- check code formatting (takes <1 second)
- `python3 -c "import json; manifest = json.load(open('custom_components/comfoclime/manifest.json')); print('✓ Manifest valid')"` -- validate manifest (takes <1 second)
- Run complete validation scenario to verify all modules work together (takes <1 second)

Always test a complete integration scenario:
```python
# Complete validation test - copy this to /tmp/validate.py and run it
from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
from custom_components.comfoclime.config_flow import ComfoClimeConfigFlow, DOMAIN
from custom_components.comfoclime.entities.sensor_definitions import DASHBOARD_SENSORS, CONNECTED_DEVICE_PROPERTIES
from custom_components.comfoclime.entities.number_definitions import NUMBER_ENTITIES
from custom_components.comfoclime.entities.select_definitions import SELECT_ENTITIES
from custom_components.comfoclime.entities.switch_definitions import SWITCHES

# Verify all modules import without errors
api = ComfoClimeAPI('http://example.com')
config_flow = ComfoClimeConfigFlow()

# Validate expected entity counts (update if definitions change)
assert len(DASHBOARD_SENSORS) == 12, f"Expected 12 dashboard sensors, got {len(DASHBOARD_SENSORS)}"
assert len(CONNECTED_DEVICE_PROPERTIES) == 1, f"Expected 1 device properties definition, got {len(CONNECTED_DEVICE_PROPERTIES)}"
assert len(NUMBER_ENTITIES) == 9, f"Expected 9 number entities, got {len(NUMBER_ENTITIES)}"
assert len(SELECT_ENTITIES) == 2, f"Expected 2 select entities, got {len(SELECT_ENTITIES)}"
assert len(SWITCHES) == 2, f"Expected 2 switch entities, got {len(SWITCHES)}"

print("✅ All integration validation tests passed!")
```

The GitHub Actions workflows (.github/workflows/main.yml and validate.yml) run hassfest and HACS validation automatically on push/PR. These validate the integration structure and metadata.

## Project Structure

This is a Home Assistant custom integration for Zehnder ComfoClime HVAC systems. Key locations:

### Repository Root
- `README.md` -- installation and usage instructions
- `hacs.json` -- HACS (Home Assistant Community Store) configuration
- `.github/workflows/` -- CI validation workflows

### Integration Code (`custom_components/comfoclime/`)
- `__init__.py` -- integration setup, services registration (107 lines)
- `manifest.json` -- integration metadata (domain: comfoclime, requires: requests, version: 1.3.0)
- `comfoclime_api.py` -- API client for ComfoClime device HTTP API (326 lines)
- `config_flow.py` -- setup flow for adding devices via UI (77 lines)
- `coordinator.py` -- data update coordinators (30-second intervals)
- Entity platforms: `sensor.py` (379 lines), `switch.py` (136 lines), `number.py` (232 lines), `select.py` (202 lines), `fan.py` (109 lines)

### Entity Definitions (`custom_components/comfoclime/entities/`)
- `sensor_definitions.py` -- 12 dashboard sensors + telemetry definitions (360 lines)
- `number_definitions.py` -- 9 temperature control entities (125 lines)
- `select_definitions.py` -- 2 selection entities (31 lines)
- `switch_definitions.py` -- 2 boolean control entities (12 lines)

### Translations (`custom_components/comfoclime/translations/`)
- `en.json` -- English translations (33 sensor, 13 number, 4 select, 1 fan, 2 switch translations)
- `de.json` -- German translations (matching English structure)

### Services (`custom_components/comfoclime/services.yaml`)
- `set_property` -- service for writing device properties
- `reset_system` -- service for restarting ComfoClime device

## Common Tasks

### Adding New Entities
Entity definitions are in the `entities/` folder. Each file contains configuration dictionaries for their entity type.
Example sensor definition:
```python
{
    "telemetry_id": 275,
    "name": "Exhaust Temperature",
    "translation_key": "exhaust_temperature",
    "unit": "°C",
    "faktor": 0.1,
    "signed": True,
    "byte_count": 2,
    "device_class": "temperature",
    "state_class": "measurement",
}
```

### Testing API Communication
Use the existing `test.py` file as a template. Update the IP address and device UUID for actual testing:
```python
api = ComfoClimeAPI("http://YOUR_DEVICE_IP")
await api.async_get_uuid(None)
```

For quick API validation without a real device:
```python
from custom_components.comfoclime.comfoclime_api import ComfoClimeAPI
api = ComfoClimeAPI('http://10.0.10.95')  # Example IP
print(f'API ready for device at: {api.base_url}')  # Validates instantiation
```

### Code Style
- Follow Home Assistant coding standards
- Use 120 character line length
- Import order: standard library, third-party, Home Assistant, local
- Always add translation keys for new entities
- Document complex API interactions

## Limitations

**Building/Testing:**
- No traditional "build" process -- this is a Python integration loaded by Home Assistant
- Cannot test against real ComfoClime hardware without physical device
- The `test.py` file requires actual device IP and UUID to function
- Integration testing requires Home Assistant development environment or container

**Development Environment:**
- This integration is designed for Home Assistant 2023.0.0+
- Requires network access to ComfoClime device for full functionality
- API communication is HTTP-based, no authentication required
- Device discovery uses `http://comfoclime.local/monitoring/ping` endpoint

**CI/CD:**
- GitHub Actions run hassfest validation and HACS validation automatically
- Linting issues must be fixed before CI passes (currently 4 flake8 issues exist)
- No automated integration tests against real hardware

## API and Architecture Notes

The ComfoClime API is a proprietary JSON HTTP API:
- Base endpoint: `http://DEVICE_IP/`
- Key endpoints: `/monitoring/ping`, `/system/{uuid}/dashboard`, `/system/{uuid}/thermalprofile`
- No authentication required
- Polling-based updates every 30 seconds via coordinators
- Device UUID obtained from ping endpoint
- Property and telemetry values read/written via specific endpoints

The integration creates multiple Home Assistant devices:
- Main ComfoClime device (from dashboard data)
- Connected ComfoAir Q devices (from telemetry data)
- Entities are distributed across devices based on their source

Always check the ComfoClime API documentation at: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md