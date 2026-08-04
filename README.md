# comfoclime

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Tests](https://github.com/Revilo91/comfoclime/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Revilo91/comfoclime/actions/workflows/tests.yml)

HomeAssistant integration of Zehnder ComfoClime (and all devices in ComfoNet bus like the ComfoAir Q)

## Features

ComfoClime is a HVAC solution as additional device for the ComfoAir Q series. It comes with its own app and an propietary JSON API. The ComfoClime unit is connected to the local network via WiFi/WLAN, the API is available only local via HTTP requests without authentication. The integration can also control the ventilation main unit ComfoAir Q. It currently offers:

- reading the dashboard data similar to the official app
- climate control entity with HVAC modes (heat/cool/fan_only/off) and preset modes (comfort/boost/eco)
- scenario modes (cooking, party, away, boost) for special operating situations
- reading and writing the active temperature profile
- setting the ventilation fan speed
- autodiscovering all connected devices
- property (r/w) and telemetry (r/o) values of _all_ connected devices
- service calls for setting properties, restarting the system, and activating scenario modes
- configuration via config flow by host/ip
- locales in english and german

## Requirements

### System Requirements
- **Home Assistant**: ≥ 2026.5.0
- **Python**: ≥ 3.14
- **aiohttp**: ≥ 3.8.0, < 4.0
- **pydantic**: ≥ 2.0.0

### Supported Devices
- Zehnder ComfoClime
- Zehnder ComfoAir Q (ComfoNet Bus)
- Other compatible ComfoNet devices

## Developer Setup

- Clone this repository or open it in a Codespace/Dev Container as described below
- Install dependencies and set up the development environment
- Home Assistant (2026.5.0+) and the integration will be available for local development and testing
- Home Assistant runs automatically on port 8123.
- See [.devcontainer/README.md](.devcontainer/README.md) for detailed instructions.

### Python Version Requirements
This integration requires **Python 3.14.2 or newer**: Home Assistant 2026.3+ declares
`Requires-Python >= 3.14.2`, so an older 3.14 (including release candidates) silently resolves to
Home Assistant 2026.2.x and the integration will fail to import. The Dev Container provides a
compatible environment.

The source also uses [PEP 758](https://peps.python.org/pep-0758/) unparenthesised `except A, B:`
clauses, which `ruff format` produces because the project targets `py314`. On Python 3.13 or older
these are a `SyntaxError` — that means the interpreter is too old, not that the file is broken. Do
not add the parentheses back; the formatter removes them again.

## 📚 Documentation

All developer/AI-agent documentation (architecture, coding conventions, byte-decoding rules,
entity categorization, scenario modes, services, troubleshooting) lives in a single place:

- **[CLAUDE.md](CLAUDE.md)** - the canonical technical reference for this repository

For the full, upstream reverse-engineered API/protocol reference, see:

- **[ComfoClimeAPI.md](https://github.com/Revilo91/comfoclime_api/blob/main/ComfoClimeAPI.md)** - detailed reverse engineered API knowledge
- **[PDO Protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)** - telemetry sensor protocol
- **[RMI Protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md)** - property access protocol

Feel free to extend!

## Development & Testing

Want to test or develop this integration? Use the included **GitHub Codespace** or **Dev Container** setup!

🚀 **Quick Start:**

- Click "Code" → "Codespaces" → "Create codespace" on GitHub
- Or open in VS Code with Dev Containers extension
- Home Assistant runs automatically on port 8123
- See [.devcontainer/README.md](.devcontainer/README.md) for detailed instructions

This provides a complete Home Assistant development environment with debugging support.

## Installation

- add this repository via HACS (user defined repositories, URL: `https://github.com/Revilo91/comfoclime`)
- install the "Zehnder ComfoClime" integration in HACS
- restart Home Assistant
- add the ComfoClime device (connected devices like the ComfoAir Q are detected and added automatically)

## Choosing which entities you see

The integration creates every entity it knows about for the devices it finds, and lets Home
Assistant decide what is shown. Everyday values — temperatures, air flows, fan speed, the climate
and fan entities, the comfort controls — are enabled straight away. Configuration and diagnostic
entities (heating and cooling curve parameters, raw telemetry, API access counters) are created but
**disabled**, so a fresh install is not flooded with a hundred entities.

To turn something on or off, go to **Settings → Devices & services → ComfoClime**, open the device,
and use the entity's own enable/disable toggle. Disabled entities are not polled at all, so
switching off the ones you don't need genuinely reduces the load on the device.

> Missing a sensor you expected? Check the **"+N entities disabled"** link on the device page before
> opening an issue — it is almost always sitting there, disabled by default.

The integration's options dialog only holds connection tuning: timeouts, polling interval and
caching, and request rate limiting. Raise the rate limiting values if you see timeouts or entities
going unavailable; the ComfoClime's Airduino board is easily overwhelmed.

## Climate Control Features

The integration provides a comprehensive climate control entity that unifies all temperature and ventilation control features:

### HVAC Modes

- **Off**: System standby mode
- **Heat**: Heating mode (automatically sets season to heating)
- **Cool**: Cooling mode (automatically sets season to cooling)
- **Fan Only**: Ventilation only mode (season set to transition)

### Preset Modes

- **Manual** (none): Manual temperature control mode
- **Comfort**: Maximum comfort temperature profile
- **Boost**: Power saving temperature profile
- **Eco**: Energy efficient temperature profile

### Scenario Modes (via service call)

Special operating modes activated through the `comfoclime.set_scenario_mode` service:

- **Cooking**: High ventilation for cooking (default: 30 min)
- **Party**: High ventilation for parties (default: 30 min)
- **Away**: Reduced mode for vacation (default: 24 hours)
- **Boost**: Maximum power boost (default: 30 min)

### Temperature Control

- Set target temperature for heating (15-25°C) and cooling (20-28°C) seasons
- Current temperature display from indoor sensor
- Automatic temperature range adjustment based on active season

### Smart Season Detection

The climate entity automatically:

- Detects current season from ComfoClime dashboard
- Adjusts available temperature ranges accordingly
- Shows appropriate HVAC actions (heating/cooling/fan/idle)
- Manages system state based on fan activity

### Heat Pump Status Interpretation

The climate entity uses **bitwise operations** to accurately determine the current HVAC action from the heat pump status code:

- **Bit 1 (0x02)**: Heating mode flag
- **Bit 2 (0x04)**: Cooling mode flag

This ensures correct interpretation of all status codes, including transitional states:

| Status Code | Binary    | HVAC Action | Description                         |
| ----------- | --------- | ----------- | ----------------------------------- |
| 0           | 0000 0000 | Off         | Heat pump is off                    |
| 1           | 0000 0001 | Idle        | Starting up                         |
| 3           | 0000 0011 | Heating     | Actively heating                    |
| 5           | 0000 0101 | Cooling     | Actively cooling                    |
| 17          | 0001 0001 | Idle        | Transitional state                  |
| 19          | 0001 0011 | Heating     | Heating in transitional state       |
| 21          | 0001 0101 | Cooling     | Cooling in transitional state       |
| 67          | 0100 0011 | Heating     | Heating mode (defrosting?)          |
| 75          | 0100 1011 | Heating     | Heating mode (defrosting + drying?) |
| 83          | 0101 0011 | Heating     | Heating mode                        |

## Current ToDo / development

There are many more telemetry and property values, that make sense to be offered by the integration. The ComfoClime unit itself is fully integrated but there are some missing sensors, switches and numbers of the ComfoAirQ unit to be added in the future. You are missing one? The definitions are in seperate files in the entities folder, so you can try them yourself. If they are working you can open an issue or directly open a pull request.

Feel free to participate! 🙋‍♂️

## Thanks to...

@michaelarnauts and his integration of ComfoConnect, where I discovered a lot of telemetries and properties of the ventilation unit:
https://github.com/michaelarnauts/aiocomfoconnect

## Development

### Releasing a New Version

This project uses automated release workflows that handle everything for you:

#### Creating a Stable Release

1. **Trigger the release workflow**:
   - Go to Actions → Release workflow
   - Click "Run workflow"
   - Enter the version number (e.g., `2.1.0`)
   - The workflow will automatically:
  - Update the version in `custom_components/comfoclime/manifest.json`
  - Update the version in `pyproject.toml`
     - Create a pull request with the version change
     - Auto-merge the PR (if branch protection allows)
     - Create and push a git tag
     - Generate a changelog from commits since the last tag
     - Create a GitHub release with the changelog

#### Creating a Pre-Release

Pre-releases are useful for beta testing new features before a stable release:

1. **Trigger the pre-release workflow**:
   - Go to Actions → Pre-Release workflow
   - Click "Run workflow"
   - Enter the pre-release version number (e.g., `2.1.0b1`)
   - Supported format: `X.Y.ZbN`
   - The workflow will automatically:
     - Update the version in `custom_components/comfoclime/manifest.json`
     - Update the version in `pyproject.toml`
     - Create a pull request with the version change
     - Auto-merge the PR (if branch protection allows)
     - Create and push a git tag
     - Generate a changelog from commits since the last tag
     - Create a GitHub pre-release with warning message

**Note:** The workflows create PRs for version updates to comply with branch protection rules. If auto-merge is enabled on the repository, the PRs will be merged automatically. Otherwise, you need to manually approve and merge the PR, then the release will be created.

### Running Tests

The integration includes a comprehensive test suite covering all entity types. To run the tests:

```bash
# Install developer dependencies
uv sync --group dev

# Run all tests
uv run pytest tests/

# Run tests with coverage
uv run pytest tests/ --cov=custom_components/comfoclime --cov-report=html

# Run specific test file
uv run pytest tests/test_sensor.py -v
```

The test suite includes:

- Unit tests for all entity types (sensor, switch, select, number, climate, fan)
- API tests
- Integration setup tests, including the config entry v1 → v2 migration
- Conformance checks of the sensor definitions against the upstream protocol documentation
  (byte counts, signedness and scaling factors), so a wrong decode is caught rather than showing a
  plausible but wrong number
- Consistency checks between entity definitions, the config flow and both translation files
- Mock fixtures for testing without a real device

Tests are automatically run via GitHub Actions on push and pull requests.

## Troubleshooting

Having issues with the integration? Check the "Bekannte Fallstricke" section in
[CLAUDE.md](CLAUDE.md#11-bekannte-fallstricke) for common issues and solutions, including:

- GitHub integration timeout errors (not related to ComfoClime)
- Connection issues with the device
- Entity update problems
- Integration loading failures
- Development environment issues
