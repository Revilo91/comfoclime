# Debug Logging Guide

This document explains the debug logging added to help trace configuration and data flow issues in the ComfoClime Home Assistant integration.

## Overview

Debug logging has been added to all critical steps of the integration's data flow:
1. Configuration loading
2. API initialization
3. Coordinator setup and data fetching
4. Entity creation and state updates
5. Entity enable/disable decisions

## How to Enable Debug Logging

Add the following to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.comfoclime: debug
```

After adding this, restart Home Assistant and check the logs at **Settings > System > Logs** or in the `home-assistant.log` file.

## What Gets Logged

### 1. Configuration Loading (`__init__.py`)

When the integration is set up, it logs:
- Host being configured
- All configuration options with their values (timeouts, polling intervals, cache TTL, etc.)

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime] Setting up ComfoClime integration for host: 192.168.1.100
DEBUG (MainThread) [custom_components.comfoclime] Configuration loaded: read_timeout=10, write_timeout=30, polling_interval=60, cache_ttl=30, max_retries=3, min_request_interval=0.1, write_cooldown=2.0, request_debounce=0.3
```

### 2. API and Device Discovery

- When the API instance is created
- Number of connected devices found

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime] ComfoClimeAPI instance created with base_url: http://192.168.1.100
DEBUG (MainThread) [custom_components.comfoclime] Connected devices retrieved: 2 devices found
```

### 3. Coordinator Creation and Initialization

- Creation of each coordinator (Dashboard, Thermalprofile, Monitoring, Definition, Telemetry, Property)
- Results of first refresh for all coordinators

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime] Created ComfoClimeDashboardCoordinator with polling_interval=60
DEBUG (MainThread) [custom_components.comfoclime] Created ComfoClimeThermalprofileCoordinator with polling_interval=60
DEBUG (MainThread) [custom_components.comfoclime] Created ComfoClimeMonitoringCoordinator with polling_interval=60
DEBUG (MainThread) [custom_components.comfoclime] Starting parallel first refresh of all coordinators
DEBUG (MainThread) [custom_components.comfoclime] Coordinator first refresh completed. Results: ['Success', 'Success', 'Success', 'Success']
```

### 4. Monitoring Data Fetching (`coordinator.py`)

The MonitoringCoordinator logs:
- When it starts fetching data
- The complete response data from the API

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime.coordinator] MonitoringCoordinator: Fetching monitoring data from API
DEBUG (MainThread) [custom_components.comfoclime.coordinator] MonitoringCoordinator: Received data: {'uuid': 'MBE123456789', 'uptime': 123456, 'timestamp': '2024-01-15T10:30:00Z'}
```

**This is the key log to check if uptime data is being received from the device!**

### 5. API GET Responses (`api_decorators.py`)

All API GET requests log their responses:
- The URL being called
- The complete JSON response data

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime.api_decorators] API GET http://192.168.1.100/monitoring/ping returned data: {'uuid': 'MBE123456789', 'uptime': 123456, 'timestamp': '2024-01-15T10:30:00Z'}
```

### 6. Entity Category Enable/Disable Checks (`entity_helper.py`)

For each entity category and individual entity, logs whether it's enabled:
- Which category is being checked
- The entity ID being evaluated
- The decision (enabled/disabled) and why

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime.entity_helper] Checking if entity category is enabled (category=sensors, subcategory=monitoring)
DEBUG (MainThread) [custom_components.comfoclime.entity_helper] Category check: enabled_monitoring has 1 enabled entities, returning True
DEBUG (MainThread) [custom_components.comfoclime.entity_helper] Checking if entity 'sensors_monitoring_uptime' is enabled (category=sensors, subcategory=monitoring)
DEBUG (MainThread) [custom_components.comfoclime.entity_helper] Entity 'sensors_monitoring_uptime': checked in enabled_monitoring list, result=True
```

### 7. Sensor Entity Creation (`sensor.py`)

Logs:
- Whether monitoring sensors will be created
- Each monitoring sensor being evaluated
- Confirmation when a sensor is created
- Total number of sensors added

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime.sensor] Setting up monitoring sensors. Coordinator available: True, Category enabled: True
DEBUG (MainThread) [custom_components.comfoclime.sensor] Monitoring sensor 'Uptime' (key=uptime): enabled=True
DEBUG (MainThread) [custom_components.comfoclime.sensor] Created monitoring sensor: Uptime
DEBUG (MainThread) [custom_components.comfoclime.sensor] Adding 15 sensor entities to Home Assistant
```

### 8. Sensor State Updates (`sensor.py`)

When coordinator data is updated, each sensor logs:
- The sensor name and type
- Available data keys in the coordinator
- The raw value retrieved
- The final state value

**Example log output:**
```
DEBUG (MainThread) [custom_components.comfoclime.sensor] Sensor 'Uptime' (type=uptime) handling coordinator update. Data keys: ['uuid', 'uptime', 'timestamp']
DEBUG (MainThread) [custom_components.comfoclime.sensor] Sensor 'Uptime' (type=uptime): raw_value=123456
DEBUG (MainThread) [custom_components.comfoclime.sensor] Sensor 'Uptime' (type=uptime): state set to 123456
```

**This is where you can see if the sensor is receiving the data correctly!**

## Troubleshooting Common Issues

### Uptime Sensor Not Showing Data

Check the logs for these key indicators:

1. **Is monitoring data being received?**
   ```
   MonitoringCoordinator: Received data: {'uuid': '...', 'uptime': ..., ...}
   ```
   - If you see `'uptime': <number>` in the data, the API is working correctly.
   - If you don't see this log, the monitoring coordinator may not be polling.

2. **Is the monitoring sensor category enabled?**
   ```
   Setting up monitoring sensors. Coordinator available: True, Category enabled: True
   ```
   - If `Category enabled: False`, go to integration options and enable monitoring sensors.

3. **Is the uptime sensor being created?**
   ```
   Monitoring sensor 'Uptime' (key=uptime): enabled=True
   Created monitoring sensor: Uptime
   ```
   - If you see `enabled=False`, the sensor is disabled in options.
   - Go to integration options and enable the uptime sensor specifically.

4. **Is the sensor receiving coordinator updates?**
   ```
   Sensor 'Uptime' (type=uptime) handling coordinator update. Data keys: ['uuid', 'uptime', 'timestamp']
   Sensor 'Uptime' (type=uptime): raw_value=123456
   ```
   - If you see these logs, the sensor is working correctly.
   - If you don't see coordinator updates, the coordinator may have failed to initialize.

### Config Flow Options Not Being Applied

Check:
1. Configuration values logged at startup match what you set in options
2. Coordinators are created with the correct polling_interval
3. First refresh results show all "Success"

If you see errors in the first refresh results, that coordinator failed to initialize properly.

## Support

If you encounter issues:
1. Enable debug logging as described above
2. Restart Home Assistant
3. Wait for at least one polling cycle (default: 60 seconds)
4. Copy the relevant log sections
5. Report the issue with logs included

The debug logs should help identify exactly where in the data flow the problem occurs.
