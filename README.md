# comfoclime

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

HomeAssistant integration of Zehnder ComfoClime (and all devices in ComfoNet bus like the ComfoAir Q)

## Features
ComfoClime is a HVAC solution as additional device for the ComfoAir Q series. It comes with its own app and an propietary JSON API. The ComfoClime unit is connected to the local network via WiFi/WLAN, the API is available only local via HTTP requests without authentication. The integration can also control the ventilation main unit ComfoAir Q. It currently offers:

* reading the dashboard data similar to the official app
* climate control entity with HVAC modes (heat/cool/fan_only/off) and preset modes (comfort/power/eco)
* reading and writing the active temperature profile
* setting the ventilation fan speed
* autodiscovering all connected devices
* property (r/w) and telemetry (r/o) values of *all* connected devices
* restarting the ComfoClime unit via service call
* configuration via config flow by host/ip
* locals in english and german

## Installation
* add this repository via HACS (user defined repositories, URL: `https://github.com/Revilo91/comfoclime`)
* install the "Zehnder ComfoClime" integration in HACS
* restart Home Assistant
* add the ComfoClime device (connected devices like the ComfoAir Q are detected and added automatically)

## API Documentation

API documentation with practical Python examples:

* **[ComfoClimeAPI.md](ComfoClimeAPI.md)** - Concise API reference with Python code examples
* **[Original documentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)** - Detailed reverse engineered API knowledge
* **[PDO Protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)** - Telemetry sensor protocol
* **[RMI Protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md)** - Property access protocol

Feel free to extend!

## Development & Testing

Want to test or develop this integration? Use the included **GitHub Codespace** or **Dev Container** setup!

🚀 **Quick Start:**
- Click "Code" → "Codespaces" → "Create codespace" on GitHub
- Or open in VS Code with Dev Containers extension
- Home Assistant runs automatically on port 8123
- See [.devcontainer/README.md](.devcontainer/README.md) for detailed instructions

This provides a complete Home Assistant development environment with debugging support.

## Climate Control Features

The integration provides a comprehensive climate control entity that unifies all temperature and ventilation control features:

### HVAC Modes
- **Off**: System standby mode
- **Heat**: Heating mode (automatically sets season to heating)
- **Cool**: Cooling mode (automatically sets season to cooling)
- **Fan Only**: Ventilation only mode (season set to transition)

### Preset Modes
- **Comfort**: Maximum comfort temperature profile
- **Power**: Power saving temperature profile
- **Eco**: Energy efficient temperature profile

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

| Status Code | Binary | HVAC Action | Description |
|-------------|--------|-------------|-------------|
| 0 | 0000 0000 | Off | Heat pump is off |
| 1 | 0000 0001 | Idle | Starting up |
| 3 | 0000 0011 | Heating | Actively heating |
| 5 | 0000 0101 | Cooling | Actively cooling |
| 17 | 0001 0001 | Idle | Transitional state |
| 19 | 0001 0011 | Heating | Heating in transitional state |
| 21 | 0001 0101 | Cooling | Cooling in transitional state |
| 67 | 0100 0011 | Heating | Heating mode (defrosting?) |
| 75 | 0100 1011 | Heating | Heating mode (defrosting + drying?) |
| 83 | 0101 0011 | Heating | Heating mode |

## Current ToDo / development
There are many more telemetry and property values, that make sense to be offered by the integration. The ComfoClime unit itself is fully integrated but there are some missing sensors, switches and numbers of the ComfoAirQ unit to be added in the future. You are missing one? The definitions are in seperate files in the entities folder, so you can try them yourself. If they are working you can open an issue or directly open a pull request.

Feel free to participate! 🙋‍♂️

## Thanks to...

@michaelarnauts and his integration of ComfoConnect, where I discovered a lot of telemetries and properties of the ventilation unit:
https://github.com/michaelarnauts/aiocomfoconnect

## Development

### Running Tests

The integration includes a comprehensive test suite covering all entity types. To run the tests:

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=custom_components/comfoclime --cov-report=html

# Run specific test file
pytest tests/test_sensor.py -v
```

The test suite includes:
- Unit tests for all entity types (sensor, switch, select, number, climate, fan)
- API tests
- Integration setup tests
- Mock fixtures for testing without a real device

Tests are automatically run via GitHub Actions on push and pull requests.
