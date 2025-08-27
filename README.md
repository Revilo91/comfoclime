# comfoclime

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

HomeAssistant integration of Zehnder ComfoClime (and all devices in ComfoNet bus like the ComfoAir Q) 

## Features
ComfoClime is a HVAC solution as additional device for the ComfoAir Q series. It comes with its own app and an propietary JSON API. The ComfoClime unit is connected to the local network via WiFi/WLAN, the API is available only local via HTTP requests without authentication. The integration can also control the ventilation main unit ComfoAir Q. It currently offers:

* reading the dashboard data similar to the official app (sensors)
* **climate control entity with HVAC modes (heat/cool/fan_only/off) and preset modes (comfort/power/eco)**
* writing the active temperature profile (select)
* setting the ventilation fan speed (fan)
* reading and writing the thermalprofile (sensors, selects and numbers)
* reading additional telemetry values of *all* connected devices (sensors; known already from ComfoConnect integration)
* arranging telemetry and property values into different devices
* reading additional property values of *all* connected devices (sensors)
* writing additional property values of *all* connected devices (service, numbers)
* restarting the ComfoClime unit via service call
* configuration via config flow by host/ip
* locals in english and german

All reverse engineered knowledge about the API is found here: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md
Feel free to extend!

## Installation

* add this repository via HACS (user defined repositories, URL: `https://github.com/msfuture/comfoclime`)
* install the "Zehnder ComfoClime" integration in HACS
* restart Home Assistant
* add the ComfoClime device (connected devices like the ComfoAir Q are detected and added automatically)

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

## Current ToDo / development
There are many more telemetry and property values, that make sense to be offered by the integration. The ComfoClime unit itself is fully integrated but there are some missing sensors, switches and numbers of the ComfoAirQ unit to be added in the future. You are missing one? The definitions are in seperate files in the entities folder, so you can try them yourself. If they are working you can open an issue or directly open a pull request.

Also I appreciate any suggestions or pull requests that clean up my messy code 😊

Feel free to participate! 🙋‍♂️

## Thanks to...

@michaelarnauts and his integration of ComfoConnect, where I discovered a lot of telemetries and properties of the ventilation unit:
https://github.com/michaelarnauts/aiocomfoconnect 
