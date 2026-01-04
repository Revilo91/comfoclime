# ComfoClime API Reference

A practical guide to the Zehnder ComfoClime REST API with Python examples. The API provides local HTTP access (no authentication required) to control ComfoClime and connected ComfoNet devices.

This documentation is part of the [ComfoClime Home Assistant Integration](https://github.com/Revilo91/comfoclime) and serves both as:

- **API Reference**: Complete REST API documentation for developers
- **Integration Guide**: Examples and patterns used in the Home Assistant integration

**Base URL**: `http://{DEVICE_IP}` or `http://comfoclime.local`

## Quick Start

```python
import requests

# Initialize API
class ComfoClimeAPI:
    def __init__(self, ip_address):
        self.base_url = f"http://{ip_address}"
        self.uuid = None

    def get_uuid(self):
        """Get device UUID (required for most endpoints)"""
        response = requests.get(f"{self.base_url}/monitoring/ping")
        self.uuid = response.json()["uuid"]
        return self.uuid

    def get_dashboard(self):
        """Get current dashboard data"""
        if not self.uuid:
            self.get_uuid()
        response = requests.get(f"{self.base_url}/system/{self.uuid}/dashboard")
        return response.json()

# Usage
api = ComfoClimeAPI("192.168.1.100")
uuid = api.get_uuid()
print(f"Device UUID: {uuid}")

dashboard = api.get_dashboard()
print(f"Indoor temp: {dashboard['indoorTemperature']}°C")
print(f"Fan speed: {dashboard['fanSpeed']}")
```

## Table of Contents

- [Core Concepts](#core-concepts)
- [API Endpoints](#api-endpoints)
  - [Monitoring](#monitoring)
  - [System Data](#system-data)
  - [Device Control](#device-control)
  - [Properties & Telemetry](#properties--telemetry)
- [Protocol Details](#protocol-details)
  - [PDO Protocol (Telemetry)](#pdo-protocol-telemetry)
  - [RMI Protocol (Properties)](#rmi-protocol-properties)
- [Python Examples](#python-examples)
  - [Complete API Client](#complete-api-client)
  - [Async Version (for Home Assistant)](#async-version-for-home-assistant)
  - [Heat Pump Status Decoder](#heat-pump-status-decoder)
  - [Bitwise Heat Pump Status Interpretation](#bitwise-heat-pump-status-interpretation)
- [Home Assistant Integration](#home-assistant-integration)
  - [Climate Control Entity](#climate-control-entity)
  - [Integration Architecture](#integration-architecture)
  - [Integration-Specific API Usage](#integration-specific-api-usage)
  - [Entity Organization](#entity-organization)
  - [Supported Features](#supported-features)

## Core Concepts

### UUID vs Device ID

- **UUID**: Unique identifier = device serial number (e.g., `MBE123123123`)

  - Required for `/system/{UUID}/*` endpoints (ComfoClime only)
  - Obtained from `/monitoring/ping`

- **Device ID (modelTypeId)**: Type identifier on ComfoNet bus
  - `1` = ComfoAir Q 350/450/600
  - `20` = ComfoClime 36
  - `222` = ComfoHub
  - Used with `/device/{UUID}/*` endpoints (all devices)

### Data Encoding

All multi-byte values use **little-endian** format:

```python
def decode_int16(data):
    """Decode 2-byte little-endian value"""
    lsb, msb = data[0], data[1]
    value = lsb + (msb << 8)
    # Handle signed values
    if value >= 0x8000:
        value -= 0x10000
    return value

def encode_int16(value):
    """Encode value to 2-byte little-endian"""
    if value < 0:
        value += 0x10000
    lsb = value & 0xFF
    msb = (value >> 8) & 0xFF
    return [lsb, msb]

# Example: Temperature 21.5°C (factor 0.1)
raw_value = int(21.5 / 0.1)  # 215
encoded = encode_int16(raw_value)  # [215, 0]
decoded = decode_int16(encoded) * 0.1  # 21.5
```

## API Endpoints

### Monitoring

#### GET /monitoring/ping

Get device UUID and status.

```python
response = requests.get("http://192.168.1.100/monitoring/ping")
data = response.json()
# {
#   "uuid": "MBE123123123",
#   "uptime": 1234567,
#   "timestamp": "2024-01-15T10:30:00Z"
# }
```

### System Data

#### GET /system/{UUID}/dashboard

Get dashboard data (temperatures, fan speed, heat pump status).

```python
def get_dashboard(base_url, uuid):
    response = requests.get(f"{base_url}/system/{uuid}/dashboard")
    return response.json()

data = get_dashboard("http://192.168.1.100", uuid)

# Response in AUTO mode:
# {
#   "indoorTemperature": 25.4,
#   "outdoorTemperature": 27.8,
#   "exhaustAirFlow": 485,
#   "supplyAirFlow": 484,
#   "fanSpeed": 2,
#   "seasonProfile": 0,
#   "temperatureProfile": 0,  # 0=Comfort, 1=Power, 2=Eco
#   "season": 2,              # 0=Transition, 1=Heating, 2=Cooling
#   "schedule": 0,
#   "status": 1,
#   "heatPumpStatus": 5,      # See Heat Pump Status Codes
#   "hpStandby": false,
#   "freeCoolingEnabled": false,
#   "caqFreeCoolingAvailable": true
# }

# Response in MANUAL mode includes setPointTemperature instead:
# {
#   "setPointTemperature": 22.0,
#   ...
# }
```

#### PUT /system/{UUID}/dashboard

Set temperature profile, fan speed, season, or other dashboard settings. The modern API uses a flexible payload system.

```python
import datetime

def update_dashboard(base_url, uuid, **kwargs):
    """Modern dashboard update method (flexible parameters).

    The API distinguishes between two temperature control modes:
    - Automatic mode (status=1): Uses preset profiles (seasonProfile, temperatureProfile)
    - Manual mode (status=0): Uses manual temperature (setPointTemperature)

    Args:
        set_point_temperature: Target temperature (°C) - activates manual mode
        fan_speed: Fan speed (0-3)
        season: Season value (0=transition, 1=heating, 2=cooling)
        hpStandby: Heat pump standby state (True=standby/off, False=active)
        schedule: Schedule mode
        temperature_profile: Temperature profile (0=comfort, 1=power, 2=eco)
        season_profile: Season profile (0=comfort, 1=power, 2=eco)
        status: Temperature control mode (0=manual, 1=automatic)
    """
    # Build payload dynamically with only provided fields
    payload = {}

    if kwargs.get("set_point_temperature") is not None:
        payload["setPointTemperature"] = kwargs["set_point_temperature"]
    if kwargs.get("fan_speed") is not None:
        payload["fanSpeed"] = kwargs["fan_speed"]
    if kwargs.get("season") is not None:
        payload["season"] = kwargs["season"]
    if kwargs.get("schedule") is not None:
        payload["schedule"] = kwargs["schedule"]
    if kwargs.get("temperature_profile") is not None:
        payload["temperatureProfile"] = kwargs["temperature_profile"]
    if kwargs.get("season_profile") is not None:
        payload["seasonProfile"] = kwargs["season_profile"]
    if kwargs.get("status") is not None:
        payload["status"] = kwargs["status"]
    if kwargs.get("hpStandby") is not None:
        payload["hpStandby"] = kwargs["hpStandby"]

    # Add timestamp
    payload["timestamp"] = datetime.datetime.now().isoformat()

    response = requests.put(
        f"{base_url}/system/{uuid}/dashboard",
        json=payload,
        headers={"content-type": "application/json; charset=utf-8"}
    )
    return response.status_code == 200

# Examples:

# 1. Set fan speed to level 2
update_dashboard("http://192.168.1.100", uuid, fan_speed=2)

# 2. Set manual temperature to 22°C (activates manual mode)
update_dashboard("http://192.168.1.100", uuid,
                set_point_temperature=22.0,
                status=0)  # 0=manual mode

# 3. Set comfort preset (automatic mode)
update_dashboard("http://192.168.1.100", uuid,
                temperature_profile=0,  # 0=comfort
                status=1)  # 1=automatic mode

# 4. Turn off heat pump (standby mode)
update_dashboard("http://192.168.1.100", uuid, hpStandby=True)

# 5. Set heating mode (activate heat pump and set season)
update_dashboard("http://192.168.1.100", uuid,
                season=1,  # 1=heating
                hpStandby=False)

# 6. Set cooling mode
update_dashboard("http://192.168.1.100", uuid,
                season=2,  # 2=cooling
                hpStandby=False)
```

**Legacy method (still works but less flexible):**

```python
def set_fan_speed(base_url, uuid, fan_speed):
    """Legacy method: Set fan speed (0-3)"""
    payload = {
        "@type": None,
        "name": None,
        "displayName": None,
        "description": None,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": None,
        "setPointTemperature": None,
        "temperatureProfile": None,
        "seasonProfile": None,
        "fanSpeed": fan_speed,
        "scenario": None,
        "scenarioTimeLeft": None,
        "season": None,
        "schedule": None
    }
    response = requests.put(
        f"{base_url}/system/{uuid}/dashboard",
        json=payload,
        headers={"content-type": "application/json; charset=utf-8"}
    )
    return response.status_code == 200

# Set to fan speed 2
set_fan_speed("http://192.168.1.100", uuid, 2)
```

#### GET /system/{UUID}/devices

List all connected ComfoNet devices.

```python
def get_devices(base_url, uuid):
    response = requests.get(f"{base_url}/system/{uuid}/devices")
    return response.json()["devices"]

devices = get_devices("http://192.168.1.100", uuid)
for device in devices:
    print(f"{device['name']}: {device['uuid']} (Type: {device['modelTypeId']})")

# Output:
# ComfoAirQ 600: SIT123123123 (Type: 1)
# ComfoClime 36: MBE123123123 (Type: 20)
# ComfoHub: ENG123123123 (Type: 222)
```

#### GET /system/{UUID}/thermalprofile

Get thermal profile settings.

```python
def get_thermal_profile(base_url, uuid):
    response = requests.get(f"{base_url}/system/{uuid}/thermalprofile")
    return response.json()

profile = get_thermal_profile("http://192.168.1.100", uuid)
# {
#   "season": {
#     "status": 1,
#     "season": 2,
#     "heatingThresholdTemperature": 14.0,
#     "coolingThresholdTemperature": 17.0
#   },
#   "temperature": {
#     "status": 1,
#     "manualTemperature": 26.0
#   },
#   "temperatureProfile": 0,
#   "heatingThermalProfileSeasonData": {
#     "comfortTemperature": 21.5,
#     "kneePointTemperature": 12.5,
#     "reductionDeltaTemperature": 1.5
#   },
#   "coolingThermalProfileSeasonData": {
#     "comfortTemperature": 24.0,
#     "kneePointTemperature": 18.0,
#     "temperatureLimit": 26.0
#   }
# }
```

#### PUT /system/{UUID}/thermalprofile

Update thermal profile settings.

```python
def set_heating_comfort_temp(base_url, uuid, temp):
    """Set heating comfort temperature"""
    payload = {
        "season": {
            "status": None,
            "season": None,
            "heatingThresholdTemperature": None,
            "coolingThresholdTemperature": None
        },
        "temperature": {
            "status": None,
            "manualTemperature": None
        },
        "temperatureProfile": None,
        "heatingThermalProfileSeasonData": {
            "comfortTemperature": temp,
            "kneePointTemperature": None,
            "reductionDeltaTemperature": None
        },
        "coolingThermalProfileSeasonData": {
            "comfortTemperature": None,
            "kneePointTemperature": None,
            "temperatureLimit": None
        }
    }
    response = requests.put(f"{base_url}/system/{uuid}/thermalprofile", json=payload)
    return response.status_code == 200

# Set heating comfort to 21.5°C
set_heating_comfort_temp("http://192.168.1.100", uuid, 21.5)
```

### Device Control

#### GET /device/{DEVICE_UUID}/telemetry/{TELEMETRY_ID}

Read sensor values (PDO protocol). Telemetry IDs are sensor numbers.

```python
def read_telemetry(base_url, device_uuid, telemetry_id, factor=1.0, signed=True):
    """Read telemetry value"""
    response = requests.get(f"{base_url}/device/{device_uuid}/telemetry/{telemetry_id}")
    data = response.json()["data"]

    # Decode based on byte count
    if len(data) == 1:
        value = data[0]
        if signed and value >= 0x80:
            value -= 0x100
    elif len(data) == 2:
        lsb, msb = data[0], data[1]
        value = lsb + (msb << 8)
        if signed and value >= 0x8000:
            value -= 0x10000
    else:
        raise ValueError(f"Unsupported byte count: {len(data)}")

    return value * factor

# Read TPMA temperature (ID 4145, factor 0.1)
tpma_temp = read_telemetry("http://192.168.1.100", uuid, 4145, factor=0.1, signed=True)
print(f"TPMA Temperature: {tpma_temp}°C")

# Read heat pump power (ID 4201)
power = read_telemetry("http://192.168.1.100", uuid, 4201, factor=1.0, signed=False)
print(f"Heat Pump Power: {power}W")
```

#### GET /device/{DEVICE_UUID}/property/{UNIT}/{SUBUNIT}/{PROPERTY}

Read device properties (RMI protocol). Properties are addressed by Unit/Subunit/Property.

```python
def read_property(base_url, device_uuid, unit, subunit, prop, factor=1.0, signed=True):
    """Read property value"""
    response = requests.get(
        f"{base_url}/device/{device_uuid}/property/{unit}/{subunit}/{prop}"
    )
    data = response.json()["data"]

    # Handle string properties
    if all(0 <= byte < 256 for byte in data):
        try:
            return "".join(chr(byte) for byte in data if byte != 0)
        except:
            pass

    # Handle numeric properties
    if len(data) == 1:
        value = data[0]
        if signed and value >= 0x80:
            value -= 0x100
    elif len(data) == 2:
        lsb, msb = data[0], data[1]
        value = lsb + (msb << 8)
        if signed and value >= 0x8000:
            value -= 0x10000
    else:
        return data

    return value * factor

# Read serial number (Unit 1, Subunit 1, Property 4)
serial = read_property("http://192.168.1.100", device_uuid, 1, 1, 4)
print(f"Serial Number: {serial}")

# Read heating comfort temperature (Unit 22, Subunit 1, Property 9, factor 0.1)
comfort_temp = read_property("http://192.168.1.100", device_uuid, 22, 1, 9, factor=0.1)
print(f"Heating Comfort: {comfort_temp}°C")
```

#### PUT /device/{DEVICE_UUID}/method/{UNIT}/{SUBUNIT}/3

Write device properties. The URL ends with `/3` (write command).

```python
def write_property(base_url, device_uuid, unit, subunit, prop, value, factor=1.0, signed=True):
    """Write property value"""
    # Convert value to raw integer
    raw_value = int(round(value / factor))

    # Encode to bytes (2 bytes)
    if signed and raw_value < 0:
        raw_value += 0x10000
    lsb = raw_value & 0xFF
    msb = (raw_value >> 8) & 0xFF

    # Payload: [property_id, lsb, msb]
    payload = {"data": [prop, lsb, msb]}

    response = requests.put(
        f"{base_url}/device/{device_uuid}/method/{unit}/{subunit}/3",
        json=payload
    )
    return response.status_code == 200

# Set heating knee point to 17°C (Unit 22, Subunit 1, Property 4, factor 0.1)
write_property("http://192.168.1.100", device_uuid, 22, 1, 4, 17.0, factor=0.1)

# Set temperature profile to Comfort=0, Power=1, Eco=2 (Unit 22, Subunit 1, Property 29)
write_property("http://192.168.1.100", device_uuid, 22, 1, 29, 0, factor=1.0)
```

#### PUT /system/reset

Restart the ComfoClime device.

```python
def reset_system(base_url):
    """Restart ComfoClime device"""
    response = requests.put(f"{base_url}/system/reset")
    return response.status_code == 200

reset_system("http://192.168.1.100")
```

## Protocol Details

### PDO Protocol (Telemetry)

PDO (Process Data Object) sensors provide real-time sensor values. Based on the [aiocomfoconnect PDO protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md).

#### Common Telemetry IDs

| ID  | Type   | Description                      | Factor | Example               |
| --- | ------ | -------------------------------- | ------ | --------------------- |
| 117 | INT16  | Outdoor air temperature          | 0.1    | `[75, 0]` = 7.5°C     |
| 118 | INT16  | Supply air temperature           | 0.1    | `[210, 0]` = 21.0°C   |
| 119 | UINT16 | Exhaust air flow                 | 1.0    | `[110, 0]` = 110 m³/h |
| 120 | UINT16 | Supply air flow                  | 1.0    | `[105, 0]` = 105 m³/h |
| 209 | INT16  | Running Mean Outdoor Temperature | 0.1    | `[117, 0]` = 11.7°C   |
| 212 | UINT8  | Temperature profile target       | 0.1    | `[238]` = 23.8°C      |
| 227 | UINT8  | Bypass state                     | 1.0    | `[100]` = 100%        |

#### ComfoClime Specific Telemetry

| ID   | Type   | Description                 | Factor | Values                      |
| ---- | ------ | --------------------------- | ------ | --------------------------- |
| 4145 | INT16  | TPMA temperature            | 0.1    | Temperature in °C           |
| 4148 | INT16  | Target temperature          | 0.1    | Temperature in °C           |
| 4149 | UINT8  | Device mode                 | 1.0    | 0=Off, 1=Heating, 2=Cooling |
| 4151 | INT16  | Current comfort temperature | 0.1    | Temperature in °C           |
| 4154 | INT16  | Indoor temperature          | 0.1    | Temperature in °C           |
| 4193 | INT16  | Supply air temperature      | 0.1    | Temperature in °C           |
| 4194 | INT16  | Exhaust temperature         | 0.1    | Temperature in °C           |
| 4195 | INT16  | Supply coil temperature     | 0.1    | Temperature in °C           |
| 4196 | INT16  | Exhaust coil temperature    | 0.1    | Temperature in °C           |
| 4197 | INT16  | Compressor temperature      | 0.1    | Temperature in °C           |
| 4198 | UINT8  | Heat pump power %           | 1.0    | 0-100%                      |
| 4201 | UINT16 | Current power               | 1.0    | Watts                       |

#### PDO Data Types

```python
PDO_TYPES = {
    0: "CN_BOOL",    # 0x00=False, 0x01=True
    1: "CN_UINT8",   # 0-255
    2: "CN_UINT16",  # Little-endian 16-bit
    3: "CN_UINT32",  # Little-endian 32-bit
    5: "CN_INT8",    # Signed 8-bit
    6: "CN_INT16",   # Signed little-endian 16-bit
    8: "CN_INT64",   # Signed little-endian 64-bit
    9: "CN_STRING",  # Null-terminated string
}

def decode_pdo_value(data, pdo_type, factor=1.0):
    """Decode PDO sensor value"""
    if pdo_type == 0:  # CN_BOOL
        return bool(data[0])
    elif pdo_type == 1:  # CN_UINT8
        return data[0] * factor
    elif pdo_type == 2:  # CN_UINT16
        return (data[0] + (data[1] << 8)) * factor
    elif pdo_type == 5:  # CN_INT8
        value = data[0]
        if value >= 0x80:
            value -= 0x100
        return value * factor
    elif pdo_type == 6:  # CN_INT16
        value = data[0] + (data[1] << 8)
        if value >= 0x8000:
            value -= 0x10000
        return value * factor
    elif pdo_type == 9:  # CN_STRING
        return "".join(chr(b) for b in data if b != 0)
    else:
        return data
```

### RMI Protocol (Properties)

RMI (Remote Method Invocation) provides access to device properties. Based on the [aiocomfoconnect RMI protocol](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md).

#### ComfoClime Units

| Unit (Dec) | Unit (Hex) | Subunits | Name        | Description                           |
| ---------- | ---------- | -------- | ----------- | ------------------------------------- |
| 1          | 0x01       | 1        | NODE        | General device info (serial, version) |
| 2          | 0x02       | 1        | COMFOBUS    | Bus communication                     |
| 3          | 0x03       | 1        | ERROROBJECT | Error handling                        |
| 22         | 0x16       | 1        | TEMPCONFIG  | Temperature configuration             |
| 23         | 0x17       | 1        | HEATPUMP    | Heat pump configuration               |

#### NODE Properties (Unit 1)

| Subunit | Property | Access | Type   | Description      | Example         |
| ------- | -------- | ------ | ------ | ---------------- | --------------- |
| 1       | 1        | RW     | UINT8  | Zone             | 1               |
| 1       | 2        | RO     | UINT8  | Product ID       | 20 (ComfoClime) |
| 1       | 3        | RO     | UINT8  | Product Variant  | 1               |
| 1       | 4        | RO     | STRING | Serial Number    | "MBE123123123"  |
| 1       | 5        | RO     | UINT8  | Hardware Version | 1               |
| 1       | 6        | RO     | UINT8  | Firmware Version | Version number  |
| 1       | 20       | RW     | STRING | Device Name      | Custom name     |

#### TEMPCONFIG Properties (Unit 22)

| Subunit | Property | Access | Type   | Factor | Description              | Range                              |
| ------- | -------- | ------ | ------ | ------ | ------------------------ | ---------------------------------- |
| 1       | 2        | RW     | UINT8  | 1      | Automatic season         | 0=Off, 1=On                        |
| 1       | 3        | RW     | UINT8  | 1      | Season select            | 0=Transition, 1=Heating, 2=Cooling |
| 1       | 4        | RW     | UINT16 | 0.1    | Heating curve knee point | 5-15°C                             |
| 1       | 5        | RW     | UINT16 | 0.1    | Cooling curve knee point | 15-25°C                            |
| 1       | 9        | RW     | UINT16 | 0.1    | Heating comfort temp     | 15-25°C                            |
| 1       | 10       | RW     | UINT16 | 0.1    | Cooling comfort temp     | 20-28°C                            |
| 1       | 11       | RW     | UINT16 | 0.1    | Max temp while cooling   | 20-28°C                            |
| 1       | 12       | RW     | UINT16 | 0.1    | Heating delta            | 0-5°C                              |
| 1       | 13       | RW     | UINT16 | 0.1    | Manual target temp       | 18-28°C                            |
| 1       | 29       | RW     | UINT8  | 1      | Temperature profile      | 0=Comfort, 1=Power, 2=Eco          |

#### HEATPUMP Properties (Unit 23)

| Subunit | Property | Access | Type   | Factor | Description        | Range   |
| ------- | -------- | ------ | ------ | ------ | ------------------ | ------- |
| 1       | 3        | RW     | UINT16 | 0.1    | Heat pump max temp | 40-60°C |
| 1       | 4        | RW     | UINT16 | 0.1    | Heat pump min temp | 10-17°C |

#### RMI Error Codes

```python
RMI_ERRORS = {
    11: "Unknown Command",
    12: "Unknown Unit",
    13: "Unknown SubUnit",
    14: "Unknown property",
    15: "Type can not have a range",
    30: "Value given not in Range",
    32: "Property not gettable or settable",
    40: "Internal error",
    41: "Internal error, maybe your command is wrong"
}
```

## Python Examples

### Complete API Client

```python
import requests
from typing import Optional, Union

class ComfoClimeAPI:
    """Complete ComfoClime API client"""

    def __init__(self, ip_address: str):
        self.base_url = f"http://{ip_address}"
        self.uuid: Optional[str] = None

    # Core methods
    def get_uuid(self) -> str:
        """Get and cache device UUID"""
        if not self.uuid:
            response = requests.get(f"{self.base_url}/monitoring/ping")
            response.raise_for_status()
            self.uuid = response.json()["uuid"]
        return self.uuid

    def get_dashboard(self) -> dict:
        """Get dashboard data"""
        uuid = self.get_uuid()
        response = requests.get(f"{self.base_url}/system/{uuid}/dashboard")
        response.raise_for_status()
        return response.json()

    def get_devices(self) -> list:
        """Get connected devices"""
        uuid = self.get_uuid()
        response = requests.get(f"{self.base_url}/system/{uuid}/devices")
        response.raise_for_status()
        return response.json()["devices"]

    # Modern dashboard update method
    def update_dashboard(self, **kwargs) -> dict:
        """Update dashboard settings (modern flexible method).

        Args:
            set_point_temperature: Target temperature (°C)
            fan_speed: Fan speed (0-3)
            season: Season value (0=transition, 1=heating, 2=cooling)
            hpStandby: Heat pump standby state (True=off, False=active)
            schedule: Schedule mode
            temperature_profile: Temperature profile (0=comfort, 1=power, 2=eco)
            season_profile: Season profile (0=comfort, 1=power, 2=eco)
            status: Control mode (0=manual, 1=automatic)
        """
        import datetime
        uuid = self.get_uuid()

        # Build payload with only provided fields
        payload = {}
        if kwargs.get("set_point_temperature") is not None:
            payload["setPointTemperature"] = kwargs["set_point_temperature"]
        if kwargs.get("fan_speed") is not None:
            payload["fanSpeed"] = kwargs["fan_speed"]
        if kwargs.get("season") is not None:
            payload["season"] = kwargs["season"]
        if kwargs.get("schedule") is not None:
            payload["schedule"] = kwargs["schedule"]
        if kwargs.get("temperature_profile") is not None:
            payload["temperatureProfile"] = kwargs["temperature_profile"]
        if kwargs.get("season_profile") is not None:
            payload["seasonProfile"] = kwargs["season_profile"]
        if kwargs.get("status") is not None:
            payload["status"] = kwargs["status"]
        if kwargs.get("hpStandby") is not None:
            payload["hpStandby"] = kwargs["hpStandby"]

        payload["timestamp"] = datetime.datetime.now().isoformat()

        response = requests.put(
            f"{self.base_url}/system/{uuid}/dashboard",
            json=payload,
            headers={"content-type": "application/json; charset=utf-8"}
        )
        response.raise_for_status()
        return response.json()

    def get_thermal_profile(self) -> dict:
        """Get thermal profile settings"""
        uuid = self.get_uuid()
        response = requests.get(f"{self.base_url}/system/{uuid}/thermalprofile")
        response.raise_for_status()
        return response.json()

    def update_thermal_profile(self, updates: dict) -> bool:
        """Update thermal profile settings.

        Args:
            updates: Dict with partial values, e.g.
                    {"heatingThermalProfileSeasonData": {"comfortTemperature": 20.0}}
        """
        uuid = self.get_uuid()

        # Full payload structure with nulls
        full_payload = {
            "season": {
                "status": None,
                "season": None,
                "heatingThresholdTemperature": None,
                "coolingThresholdTemperature": None,
            },
            "temperature": {
                "status": None,
                "manualTemperature": None,
            },
            "temperatureProfile": None,
            "heatingThermalProfileSeasonData": {
                "comfortTemperature": None,
                "kneePointTemperature": None,
                "reductionDeltaTemperature": None,
            },
            "coolingThermalProfileSeasonData": {
                "comfortTemperature": None,
                "kneePointTemperature": None,
                "temperatureLimit": None,
            },
        }

        # Deep update: override specific fields
        for section, values in updates.items():
            if section in full_payload and isinstance(values, dict):
                full_payload[section].update(values)
            else:
                full_payload[section] = values

        response = requests.put(
            f"{self.base_url}/system/{uuid}/thermalprofile",
            json=full_payload
        )
        response.raise_for_status()
        return response.status_code == 200

    # Telemetry
    def read_telemetry(self, device_uuid: str, telemetry_id: int,
                       factor: float = 1.0, signed: bool = True) -> float:
        """Read telemetry value"""
        response = requests.get(
            f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"
        )
        response.raise_for_status()
        data = response.json()["data"]

        if len(data) == 1:
            value = data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif len(data) == 2:
            value = data[0] + (data[1] << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            raise ValueError(f"Unsupported byte count: {len(data)}")

        return value * factor

    # Properties
    def read_property(self, device_uuid: str, unit: int, subunit: int,
                      prop: int, factor: float = 1.0, signed: bool = True) -> Union[str, float]:
        """Read property value"""
        response = requests.get(
            f"{self.base_url}/device/{device_uuid}/property/{unit}/{subunit}/{prop}"
        )
        response.raise_for_status()
        data = response.json()["data"]

        # Try to decode as string
        if len(data) > 2:
            try:
                return "".join(chr(b) for b in data if b != 0)
            except:
                pass

        # Decode as number
        if len(data) == 1:
            value = data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif len(data) == 2:
            value = data[0] + (data[1] << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            return data

        return value * factor

    def write_property(self, device_uuid: str, unit: int, subunit: int,
                       prop: int, value: float, factor: float = 1.0,
                       signed: bool = True) -> bool:
        """Write property value"""
        raw_value = int(round(value / factor))

        if signed and raw_value < 0:
            raw_value += 0x10000

        payload = {
            "data": [prop, raw_value & 0xFF, (raw_value >> 8) & 0xFF]
        }

        response = requests.put(
            f"{self.base_url}/device/{device_uuid}/method/{unit}/{subunit}/3",
            json=payload
        )
        return response.status_code == 200

    # High-level HVAC control methods (Home Assistant integration style)
    def set_hvac_mode_heat(self) -> bool:
        """Set HVAC mode to heating"""
        return self.update_dashboard(season=1, hpStandby=False)

    def set_hvac_mode_cool(self) -> bool:
        """Set HVAC mode to cooling"""
        return self.update_dashboard(season=2, hpStandby=False)

    def set_hvac_mode_fan_only(self) -> bool:
        """Set HVAC mode to fan only (transition season)"""
        return self.update_dashboard(season=0, hpStandby=False)

    def set_hvac_mode_off(self) -> bool:
        """Turn off heat pump (standby mode)"""
        return self.update_dashboard(hpStandby=True)

    def set_manual_temperature(self, temperature: float) -> bool:
        """Set manual target temperature (switches to manual mode)"""
        return self.update_dashboard(
            set_point_temperature=temperature,
            status=0  # 0=manual mode
        )

    def set_preset_comfort(self) -> bool:
        """Set comfort preset (switches to automatic mode)"""
        return self.update_dashboard(temperature_profile=0, status=1)

    def set_preset_power(self) -> bool:
        """Set power preset (switches to automatic mode)"""
        return self.update_dashboard(temperature_profile=1, status=1)

    def set_preset_eco(self) -> bool:
        """Set eco preset (switches to automatic mode)"""
        return self.update_dashboard(temperature_profile=2, status=1)

    def set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (0-3)"""
        return self.update_dashboard(fan_speed=speed)

    def reset_system(self) -> bool:
        """Restart the ComfoClime device"""
        response = requests.put(f"{self.base_url}/system/reset")
        response.raise_for_status()
        return response.status_code == 200

# Usage examples
api = ComfoClimeAPI("192.168.1.100")

# Get basic info
uuid = api.get_uuid()
print(f"Device: {uuid}")

# Read dashboard
dashboard = api.get_dashboard()
print(f"Indoor: {dashboard['indoorTemperature']}°C")
print(f"Fan: {dashboard['fanSpeed']}")

# HVAC control examples
api.set_hvac_mode_heat()              # Switch to heating mode
api.set_manual_temperature(22.5)      # Set manual temperature to 22.5°C
api.set_preset_comfort()              # Use comfort preset
api.set_fan_speed(2)                  # Set fan to medium speed
api.set_hvac_mode_off()               # Turn off heat pump

# Read telemetry
tpma_temp = api.read_telemetry(uuid, 4145, factor=0.1)
print(f"TPMA: {tpma_temp}°C")

# Read/write properties
serial = api.read_property(uuid, 1, 1, 4)
print(f"Serial: {serial}")

api.write_property(uuid, 22, 1, 9, 21.5, factor=0.1)  # Set heating comfort
print("Heating comfort set to 21.5°C")
```

### Async Version (for Home Assistant)

```python
import asyncio
import aiohttp

class AsyncComfoClimeAPI:
    """Async ComfoClime API client for Home Assistant"""

    def __init__(self, ip_address: str):
        self.base_url = f"http://{ip_address}"
        self.uuid: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def get_uuid(self) -> str:
        """Get device UUID"""
        await self._ensure_session()
        if not self.uuid:
            async with self.session.get(f"{self.base_url}/monitoring/ping") as resp:
                data = await resp.json()
                self.uuid = data["uuid"]
        return self.uuid

    async def get_dashboard(self) -> dict:
        """Get dashboard data"""
        await self._ensure_session()
        uuid = await self.get_uuid()
        async with self.session.get(f"{self.base_url}/system/{uuid}/dashboard") as resp:
            return await resp.json()

    async def read_telemetry(self, device_uuid: str, telemetry_id: int,
                             factor: float = 1.0, signed: bool = True) -> float:
        """Read telemetry value"""
        await self._ensure_session()
        url = f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"
        async with self.session.get(url) as resp:
            data = await resp.json()
            raw_data = data["data"]

        if len(raw_data) == 1:
            value = raw_data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif len(raw_data) == 2:
            value = raw_data[0] + (raw_data[1] << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            raise ValueError(f"Unsupported byte count: {len(raw_data)}")

        return value * factor

# Usage
async def main():
    api = AsyncComfoClimeAPI("192.168.1.100")
    try:
        dashboard = await api.get_dashboard()
        print(f"Temperature: {dashboard['indoorTemperature']}°C")

        tpma = await api.read_telemetry(api.uuid, 4145, factor=0.1)
        print(f"TPMA: {tpma}°C")
    finally:
        await api.close()

asyncio.run(main())
```

### Heat Pump Status Decoder

```python
def decode_heat_pump_status(status_code: int) -> dict:
    """Decode heat pump status bitfield with bitwise operations.

    The status code is a bitfield where:
    - Bit 0 (0x01): Device is active/running
    - Bit 1 (0x02): Heating mode flag
    - Bit 2 (0x04): Cooling mode flag
    - Other bits: Various states (defrost, transition, etc.)
    """
    status_names = {
        0: "Off",
        1: "Starting",
        3: "Heating",
        5: "Cooling",
        17: "Idle (Transitional)",
        19: "Heating (Transitional)",
        21: "Cooling (Transitional)",
        67: "Heating",
        75: "Heating (Multi-mode)",
        83: "Heating"
    }

    # Bit interpretation using bitwise operations
    bits = {
        "running": bool(status_code & 0x01),    # Bit 0
        "heating": bool(status_code & 0x02),    # Bit 1
        "cooling": bool(status_code & 0x04),    # Bit 2
        "flag_8": bool(status_code & 0x08),     # Bit 3 (transition/other)
        "flag_16": bool(status_code & 0x10),    # Bit 4
        "flag_32": bool(status_code & 0x20),    # Bit 5
        "flag_64": bool(status_code & 0x40),    # Bit 6 (defrost/other)
        "flag_128": bool(status_code & 0x80),   # Bit 7
    }

    # Determine current action (as used in Home Assistant integration)
    if status_code == 0:
        action = "off"
    elif bits["heating"]:
        action = "heating"
    elif bits["cooling"]:
        action = "cooling"
    elif bits["running"]:
        action = "idle"
    else:
        action = "off"

    return {
        "code": status_code,
        "description": status_names.get(status_code, f"Unknown ({status_code})"),
        "action": action,
        "bits": bits,
        "binary": f"{status_code:08b}"
    }

# Usage
dashboard = api.get_dashboard()
status = decode_heat_pump_status(dashboard["heatPumpStatus"])
print(f"Heat Pump: {status['description']}")
print(f"Action: {status['action']}")
print(f"Binary: {status['binary']}")
print(f"Heating: {status['bits']['heating']}, Cooling: {status['bits']['cooling']}")
```

### Bitwise Heat Pump Status Interpretation

The Home Assistant integration uses **bitwise operations** to accurately interpret heat pump status codes:

```python
def get_hvac_action(heat_pump_status: int) -> str:
    """Determine HVAC action from heat pump status using bitwise operations.

    Heat pump status is a bitfield:
    - Bit 0 (0x01): Device is active/running
    - Bit 1 (0x02): Heating mode flag
    - Bit 2 (0x04): Cooling mode flag

    Status codes interpretation:
    Code | Binary      | Action
    -----|-------------|--------
    0    | 0000 0000  | Off
    1    | 0000 0001  | Idle (starting)
    3    | 0000 0011  | Heating (active + heating flag)
    5    | 0000 0101  | Cooling (active + cooling flag)
    17   | 0001 0001  | Idle (transitional)
    19   | 0001 0011  | Heating (heating + transition)
    21   | 0001 0101  | Cooling (cooling + transition)
    67   | 0100 0011  | Heating
    75   | 0100 1011  | Heating (both bits set, heating priority)
    83   | 0101 0011  | Heating
    """
    if heat_pump_status is None or heat_pump_status == 0:
        return "off"

    # Bitwise check for heating/cooling flags
    is_heating = bool(heat_pump_status & 0x02)  # Check bit 1
    is_cooling = bool(heat_pump_status & 0x04)  # Check bit 2

    # Heating has priority if both bits are set
    if is_heating:
        return "heating"

    if is_cooling:
        return "cooling"

    # Device is active but not heating or cooling
    return "idle"

# Usage
dashboard = api.get_dashboard()
action = get_hvac_action(dashboard["heatPumpStatus"])
print(f"Current action: {action}")
```

## Home Assistant Integration

This API documentation is part of the [ComfoClime Home Assistant Integration](https://github.com/Revilo91/comfoclime). The integration provides:

### Climate Control Entity

A comprehensive climate control entity that unifies all temperature and ventilation control:

**HVAC Modes:**

- **Off**: System standby mode (via `hpStandby=True`)
- **Heat**: Heating mode (sets `season=1` via thermal profile)
- **Cool**: Cooling mode (sets `season=2` via thermal profile)
- **Fan Only**: Ventilation only mode (sets `season=0` - transition)

**Preset Modes:**

- **Manual** (none): Manual temperature control (via `setPointTemperature`)
- **Comfort**: Comfort temperature profile (`temperatureProfile=0`)
- **Boost** (Power): Power saving profile (`temperatureProfile=1`)
- **Eco**: Energy efficient profile (`temperatureProfile=2`)

**Features:**

- Target temperature control for heating (15-25°C) and cooling (20-28°C)
- Current temperature display from indoor sensor
- Fan speed control (0=off, 1=low, 2=medium, 3=high)
- Automatic temperature range adjustment based on season
- Smart season detection and HVAC action display

### Integration Architecture

```
┌─────────────────────────────────────────┐
│   Home Assistant Climate Entity         │
│  ┌─────────────────────────────────┐   │
│  │  HVAC Mode (Heat/Cool/Fan/Off)  │   │
│  │  Preset Mode (Comfort/Eco/...)  │   │
│  │  Target Temperature             │   │
│  │  Fan Mode (Low/Medium/High)     │   │
│  └─────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      ComfoClimeAPI (Python)             │
│  ┌─────────────────────────────────┐   │
│  │  update_dashboard()             │   │
│  │  update_thermal_profile()       │   │
│  │  async_set_hvac_season()        │   │
│  └─────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│    ComfoClime REST API (HTTP)           │
│  • PUT /system/{UUID}/dashboard         │
│  • PUT /system/{UUID}/thermalprofile    │
│  • GET /system/{UUID}/dashboard         │
│  • GET/PUT /device/{UUID}/...           │
└─────────────────────────────────────────┘
```

### Integration-Specific API Usage

The Home Assistant integration uses these patterns:

**Setting HVAC Mode to Heat:**

```python
# Atomically set season and activate device
await api.async_set_hvac_season(hass, season=1, hpStandby=False)
```

**Setting HVAC Mode to Off:**

```python
# Deactivate heat pump via dashboard
await api.async_update_dashboard(hpStandby=True)
```

**Setting Manual Temperature:**

```python
# Switch to manual mode with specific temperature
await api.async_update_dashboard(
    set_point_temperature=22.0,
    status=0  # 0=manual mode
)
```

**Setting Temperature Preset:**

```python
# Switch to automatic mode with comfort preset
await api.async_update_dashboard(
    temperature_profile=0,  # 0=comfort, 1=power, 2=eco
    status=1  # 1=automatic mode
)
```

**Setting Fan Speed:**

```python
# Set fan to medium speed
await api.async_update_dashboard(fan_speed=2)
```

### Entity Organization

The integration creates multiple devices and entities:

**ComfoClime Device:**

- Climate entity (HVAC control)
- Sensors (temperatures, status)
- Numbers (thermal profile settings)
- Selects (profiles, modes)
- Fan entity (ventilation control)

**ComfoAir Q Device:**

- Sensors (telemetry values)
- Numbers (properties)
- Selects (modes)

**ComfoHub Device** (if connected):

- Sensors (telemetry values)

All devices are automatically discovered when the integration connects to the ComfoClime unit.

### Supported Features

- ✅ Climate control entity with HVAC modes (heat/cool/fan_only/off)
- ✅ Preset modes (comfort/power/eco/manual)
- ✅ Fan speed control (0-3)
- ✅ Target temperature setting
- ✅ Reading dashboard data (sensors)
- ✅ Reading and writing thermal profile (numbers, selects)
- ✅ Reading telemetry values of all connected devices (sensors)
- ✅ Reading and writing property values (numbers, service calls)
- ✅ Device organization (ComfoClime, ComfoAir Q, ComfoHub)
- ✅ Configuration via config flow
- ✅ Service calls (reset system, write properties)
- ✅ Localization (English, German)

## Additional Resources

- **Home Assistant Integration**: [comfoclime](https://github.com/Revilo91/comfoclime)
- **Original API Documentation**: [ComfoClimeAPI.md](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)
- **PDO Protocol**: [PROTOCOL-PDO.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-PDO.md)
- **RMI Protocol**: [PROTOCOL-RMI.md](https://github.com/michaelarnauts/aiocomfoconnect/blob/master/docs/PROTOCOL-RMI.md)

## License

MIT
