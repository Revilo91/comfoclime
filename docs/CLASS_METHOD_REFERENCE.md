# ComfoClime - Vollständige Klassen & Methoden Referenz
Dieses Dokument listet alle Klassen und deren Methoden mit Signaturen auf.
**Generiert:** 2026-02-05
**Gesamtanzahl:** 48 Klassen, 197 Methoden

---

## comfoclime.access_tracker

**Dateipfad:** `custom_components/comfoclime/access_tracker.py`

### Klasse: `AccessTracker`

**Beschreibung:**
```
Tracks API access patterns for all coordinators.

Provides per-minute and per-hour access counts for each coordinator,
allowing users to monitor and optimize API access patterns.

Attributes:
    coordinators: Dictionary mapping coordinator names to their stats.
```

**Methoden:** 11

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self | None | 91 |
| `_cleanup_old_entries` | sync | self, stats, current_time | <ast.Constant object at 0x7f59efba3290> | 115 |
| `_get_current_time` | sync | self | float | 95 |
| `get_accesses_per_hour` | sync | self, coordinator_name | int | 144 |
| `get_accesses_per_minute` | sync | self, coordinator_name | int | 125 |
| `get_all_coordinator_names` | sync | self | <ast.Subscript object at 0x7f59ef943ad0> | 175 |
| `get_summary` | sync | self | dict | 199 |
| `get_total_accesses` | sync | self, coordinator_name | int | 162 |
| `get_total_accesses_per_hour` | sync | self | int | 191 |
| `get_total_accesses_per_minute` | sync | self | int | 183 |
| `record_access` | sync | self, coordinator_name | <ast.Constant object at 0x7f59efba31d0> | 99 |

#### Methoden-Details

##### `__init__(self)`

```
Initialize the access tracker.
```

**Typ:** sync

**Zeile:** 91

##### `_cleanup_old_entries(self, stats, current_time)`

```
Remove entries older than the hour window.

Args:
    stats: The coordinator stats to clean up.
    current_time: Current monotonic time.
```

**Typ:** sync

**Zeile:** 115

##### `_get_current_time(self)`

```
Get current monotonic time for rate limiting.
```

**Typ:** sync

**Zeile:** 95

##### `get_accesses_per_hour(self, coordinator_name)`

```
Get the number of accesses in the last hour for a coordinator.

Args:
    coordinator_name: Name of the coordinator.

Returns:
    Number of accesses in the last hour.
```

**Typ:** sync

**Zeile:** 144

##### `get_accesses_per_minute(self, coordinator_name)`

```
Get the number of accesses in the last minute for a coordinator.

Args:
    coordinator_name: Name of the coordinator.

Returns:
    Number of accesses in the last minute.
```

**Typ:** sync

**Zeile:** 125

##### `get_all_coordinator_names(self)`

```
Get all registered coordinator names.

Returns:
    List of coordinator names.
```

**Typ:** sync

**Zeile:** 175

##### `get_summary(self)`

```
Get a summary of all coordinator access statistics.

Returns:
    Dictionary with coordinator statistics.
```

**Typ:** sync

**Zeile:** 199

##### `get_total_accesses(self, coordinator_name)`

```
Get the total number of accesses for a coordinator since startup.

Args:
    coordinator_name: Name of the coordinator.

Returns:
    Total number of accesses.
```

**Typ:** sync

**Zeile:** 162

##### `get_total_accesses_per_hour(self)`

```
Get total accesses per hour across all coordinators.

Returns:
    Total accesses in the last hour.
```

**Typ:** sync

**Zeile:** 191

##### `get_total_accesses_per_minute(self)`

```
Get total accesses per minute across all coordinators.

Returns:
    Total accesses in the last minute.
```

**Typ:** sync

**Zeile:** 183

##### `record_access(self, coordinator_name)`

```
Record an API access for a coordinator.

Args:
    coordinator_name: Name of the coordinator making the access.
```

**Typ:** sync

**Zeile:** 99


---

### Klasse: `CoordinatorStats`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Statistics for a single coordinator's API accesses.

Tracks access timestamps, counts, and timing for monitoring
API usage patterns.

Attributes:
    access_timestamps: FIFO queue of access timestamps (monotonic time).
    total_count: Total number of accesses since creation.
    last_access_time: Timestamp of most recent access.

Example:
    >>> stats = CoordinatorStats()
    >>> stats.record_access(time.monotonic())
    >>> stats.total_count
    1
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `cleanup_old_entries` | sync | self, cutoff | int | 61 |
| `record_access` | sync | self, timestamp | <ast.Constant object at 0x7f59efb1fe10> | 51 |

#### Methoden-Details

##### `cleanup_old_entries(self, cutoff)`

```
Remove entries older than cutoff.

Args:
    cutoff: Timestamp threshold; entries before this are removed.

Returns:
    Number of entries removed.
```

**Typ:** sync

**Zeile:** 61

##### `record_access(self, timestamp)`

```
Record a new API access.

Args:
    timestamp: Monotonic timestamp of the access.
```

**Typ:** sync

**Zeile:** 51


---

## comfoclime.climate

**Dateipfad:** `custom_components/comfoclime/climate.py`

### Klasse: `ComfoClimeClimate`

**Erbt von:** `CoordinatorEntity, ClimateEntity`

**Beschreibung:**
```
ComfoClime Climate entity for HVAC control.

Provides climate control for the ComfoClime ventilation and heat pump
system. Supports temperature control, HVAC modes (heating/cooling/fan),
preset modes (comfort/power/eco/manual), fan speed control, and
special scenario modes (cooking/party/away/boost).

The entity monitors two coordinators:
    - DashboardCoordinator: Real-time temperature, fan, and season data
    - ThermalprofileCoordinator: Thermal profile and preset settings

Attributes:
    hvac_mode: Current HVAC mode (off/fan_only/heat/cool)
    current_temperature: Current indoor temperature in °C
    target_temperature: Target temperature in °C
    preset_mode: Current preset mode
    fan_mode: Current fan speed mode
    hvac_action: Current HVAC action (idle/heating/cooling/fan)

Example:
    >>> # Set heating mode with comfort preset at 22°C
    >>> await climate.async_set_hvac_mode(HVACMode.HEAT)
    >>> await climate.async_set_preset_mode(PRESET_COMFORT)
    >>> await climate.async_set_temperature(temperature=22.0)
```

**Methoden:** 25

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, dashboard_coordinator, thermalprofile_coordinator, ... (+3) | <ast.Constant object at 0x7f59efb1ff10> | 196 |
| `_async_refresh_coordinators` | async | self, blocking | <ast.Constant object at 0x7f59efbdd950> | 443 |
| `_get_current_season` | sync | self | Season | 431 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efa74050> | 257 |
| `async_added_to_hass` | async | self | <ast.Constant object at 0x7f59efa77f50> | 248 |
| `async_set_fan_mode` | async | self, fan_mode | <ast.Constant object at 0x7f59efa8e090> | 635 |
| `async_set_hvac_mode` | async | self, hvac_mode | <ast.Constant object at 0x7f59efac7950> | 528 |
| `async_set_preset_mode` | async | self, preset_mode | <ast.Constant object at 0x7f59efa13610> | 572 |
| `async_set_scenario_mode` | async | self, scenario_mode, duration, ... (+1) | <ast.Constant object at 0x7f59efa7cc10> | 668 |
| `async_set_temperature` | async | self | <ast.Constant object at 0x7f59efb37590> | 478 |
| `async_turn_off` | async | self | <ast.Constant object at 0x7f59efae1ad0> | 790 |
| `async_turn_on` | async | self | <ast.Constant object at 0x7f59ef949110> | 812 |
| `async_update_dashboard` | async | self | <ast.Constant object at 0x7f59efb36d50> | 515 |
| `available` | sync | self | bool | 270 |
| `current_temperature` | sync | self | <ast.BinOp object at 0x7f59efabe490> | 290 |
| `device_info` | sync | self | DeviceInfo | 279 |
| `extra_state_attributes` | sync | self | <ast.Subscript object at 0x7f59ef942150> | 755 |
| `fan_mode` | sync | self | <ast.BinOp object at 0x7f59efbc1b10> | 411 |
| `fan_modes` | sync | self | <ast.BinOp object at 0x7f59efa03b50> | 427 |
| `hvac_action` | sync | self | <ast.Subscript object at 0x7f59efb239d0> | 346 |
| `hvac_mode` | sync | self | HVACMode | 320 |
| `max_temp` | sync | self | float | 315 |
| `min_temp` | sync | self | float | 310 |
| `preset_mode` | sync | self | <ast.BinOp object at 0x7f59efbc1590> | 386 |
| `target_temperature` | sync | self | <ast.BinOp object at 0x7f59efbc67d0> | 297 |

#### Methoden-Details

##### `__init__(self, dashboard_coordinator, thermalprofile_coordinator, api, device, entry)`

```
Initialize the ComfoClime climate entity.

Args:
    dashboard_coordinator: Coordinator for dashboard data
    thermalprofile_coordinator: Coordinator for thermal profile data
    api: ComfoClime API instance
    device: Device info dictionary
    entry: Config entry for this integration
```

**Typ:** sync

**Zeile:** 196

##### `_async_refresh_coordinators(self, blocking)`

```
Refresh both dashboard and thermal profile coordinators.

Args:
    blocking: If True (default), waits for coordinators to complete refresh.
             If False, schedules non-blocking refresh in background.

When blocking=True (default for "set then fetch" pattern):
- Waits for both coordinators to complete refresh
- Ensures UI shows actual device state after setting values
- Prevents stale state display

When blocking=False:
- Schedules non-blocking refresh for both coordinators
- Prevents UI from becoming unresponsive
- Updates happen in background
```

**Typ:** async

**Zeile:** 443

##### `_get_current_season(self)`

```
Get the current season value from dashboard.

Returns:
    Season enum (TRANSITIONAL, HEATING, or COOLING)
```

**Typ:** sync

**Zeile:** 431

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 257

##### `async_added_to_hass(self)`

```
When entity is added to hass, register listeners for both coordinators.
```

**Typ:** async

**Zeile:** 248

##### `async_set_fan_mode(self, fan_mode)`

```
Set fan mode by updating fan speed via dashboard API.

Maps fan mode strings to fanSpeed values:
- off: 0
- low: 1
- medium: 2
- high: 3
```

**Typ:** async

**Zeile:** 635

##### `async_set_hvac_mode(self, hvac_mode)`

```
Set new HVAC mode by updating season via thermal profile API.

The HVAC mode is determined by the season field in the thermal profile:
- OFF: Sets hpStandby=True via dashboard (device off)
- FAN_ONLY: Sets season=0 (transition) via thermal profile, hpStandby=False
- HEAT: Sets season=1 (heating) via thermal profile, hpStandby=False
- COOL: Sets season=2 (cooling) via thermal profile, hpStandby=False
```

**Typ:** async

**Zeile:** 528

##### `async_set_preset_mode(self, preset_mode)`

```
Set preset mode via dashboard API.

Setting PRESET_MANUAL (none) switches to manual temperature control mode.
Setting other presets (comfort/boost/eco) activates automatic mode with
both seasonProfile and temperatureProfile set to the selected preset value.

Args:
    preset_mode: The preset mode to activate
```

**Typ:** async

**Zeile:** 572

##### `async_set_scenario_mode(self, scenario_mode, duration, start_delay)`

```
Set scenario mode via dashboard API.

Activates a special operating mode (scenario) on the ComfoClime device.

Supported scenarios:
- cooking: High ventilation for cooking (default: 30 min)
- party: High ventilation for parties (default: 30 min)
- away: Reduced mode for vacation (default: 24 hours)
- boost: Maximum power boost (default: 30 min)

Args:
    scenario_mode: The scenario mode to activate (cooking, party, away, boost)
    duration: Optional duration in minutes. If not provided, uses default.
    start_delay: Optional start delay as datetime string (YYYY-MM-DD HH:MM:SS)
```

**Typ:** async

**Zeile:** 668

##### `async_set_temperature(self)`

```
Set new target temperature via dashboard API in manual mode.

Setting a manual temperature activates manual mode (status=0) and replaces
the preset profiles (seasonProfile, temperatureProfile) with setPointTemperature.
```

**Typ:** async

**Zeile:** 478

##### `async_turn_off(self)`

```
Turn the climate device off.

Sets hpStandby=True via dashboard API to turn off the heat pump.
This is equivalent to setting HVAC mode to OFF.
```

**Typ:** async

**Zeile:** 790

##### `async_turn_on(self)`

```
Turn the climate device on.

Sets hpStandby=False via dashboard API to turn on the heat pump.
The season remains unchanged.
```

**Typ:** async

**Zeile:** 812

##### `async_update_dashboard(self)`

```
Update dashboard settings via API.

Wrapper method that delegates to the API's async_update_dashboard method.
This ensures all dashboard updates go through the centralized API method.

Args:
    **kwargs: Dashboard fields to update (set_point_temperature, fan_speed,
             season, hpStandby, schedule, temperature_profile,
             season_profile, status)
```

**Typ:** async

**Zeile:** 515

##### `available(self)`

```
Return True if entity is available.

Climate entity depends on both dashboard and thermal profile coordinators,
so we check both for successful updates.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 270

##### `current_temperature(self)`

```
Return current temperature from dashboard data.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 290

##### `device_info(self)`

```
Return device information.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 279

##### `extra_state_attributes(self)`

```
Return dashboard data as extra state attributes.

Exposes all available data from the ComfoClime Dashboard API interface:
- Dashboard data from /system/{UUID}/dashboard
- Scenario time left (remaining duration of active scenario in seconds)
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 755

##### `fan_mode(self)`

```
Return current fan mode from dashboard data.

Maps fanSpeed from dashboard (0-3) to fan mode strings:
- 0: off
- 1: low
- 2: medium
- 3: high
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 411

##### `fan_modes(self)`

```
Return the list of available fan modes.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 427

##### `hvac_action(self)`

```
Return current HVAC action based on dashboard heatPumpStatus.

Heat pump status codes (from API documentation):

Bit-Mapping:
Bit         | 7    | 6          | 5    | 4          | 3              | 2       | 1       | 0
------------|------|------------|------|------------|----------------|---------|---------|-----
Value (dec) | 128  | 64         | 32   | 16         | 8              | 4       | 2       | 1
Value (hex) | 0x80 | 0x40       | 0x20 | 0x10       | 0x08           | 0x04    | 0x02    | 0x01
Meaning     | IDLE | DEFROSTING | IDLE | DRYING (?) | PREHEATING (?) | COOLING | HEATING | IDLE

Reference: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 346

##### `hvac_mode(self)`

```
Return current HVAC mode from dashboard data.

Maps the season field from dashboard to HVAC mode:
- season 0 (transition) → FAN_ONLY
- season 1 (heating) → HEAT
- season 2 (cooling) → COOL
- season None or unknown → OFF (default fallback)
- hpStandby true + season None → OFF (device powered off)
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 320

##### `max_temp(self)`

```
Return maximum temperature as per system requirements.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 315

##### `min_temp(self)`

```
Return minimum temperature as per system requirements.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 310

##### `preset_mode(self)`

```
Return current preset mode from dashboard data.

Returns PRESET_MANUAL (none) if in manual mode (status=0 or setPointTemperature is set).
Returns preset name (comfort/boost/eco) if in automatic mode (status=1).
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 386

##### `target_temperature(self)`

```
Return target temperature for display.

Uses manualTemperature from thermal profile as the display value.
This represents the last set temperature.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 297


---

## comfoclime.comfoclime_api

**Dateipfad:** `custom_components/comfoclime/comfoclime_api.py`

### Klasse: `ComfoClimeAPI`

**Beschreibung:**
```
Async client for ComfoClime device API.

Provides methods for reading and writing device data with automatic
rate limiting, caching, retry logic, and session management.

Attributes:
    base_url: Base URL of the ComfoClime device
    hass: Home Assistant instance (optional)
    uuid: Device UUID (fetched automatically)
    read_timeout: Timeout for read operations in seconds
    write_timeout: Timeout for write operations in seconds
    max_retries: Maximum number of retries for failed requests
```

**Methoden:** 24

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, base_url, hass, ... (+7) | <ast.Constant object at 0x7f59efa13010> | 111 |
| `_async_get_uuid_internal` | async | self, response_data | None | 210 |
| `_async_update_thermal_profile` | async | self | dict | 789 |
| `_convert_dict_to_kwargs_and_update` | async | self, updates | <ast.Subscript object at 0x7f59efb21e50> | 880 |
| `_get_session` | async | self | aiohttp.ClientSession | 175 |
| `_read_property_for_device_raw` | async | self, response_data, device_uuid, ... (+1) | <ast.BinOp object at 0x7f59efac48d0> | 609 |
| `_read_telemetry_raw` | async | self, response_data, device_uuid, ... (+1) | None | 405 |
| `_set_property_internal` | async | self, device_uuid, x, ... (+3) | None | 974 |
| `_update_thermal_profile` | async | self | dict | 673 |
| `_wait_for_rate_limit` | async | self, is_write | <ast.Constant object at 0x7f59efa13c10> | 159 |
| `async_get_connected_devices` | async | self, response_data | None | 336 |
| `async_get_dashboard_data` | async | self, response_data | None | 294 |
| `async_get_device_definition` | async | self, response_data, device_uuid | None | 388 |
| `async_get_monitoring_ping` | async | self, response_data | None | 250 |
| `async_get_thermal_profile` | async | self, response_data | None | 637 |
| `async_get_uuid` | async | self | <ast.BinOp object at 0x7f59efaaf110> | 229 |
| `async_read_property_for_device` | async | self, device_uuid, property_path, ... (+3) | <ast.BinOp object at 0x7f59efaa1c50> | 509 |
| `async_read_telemetry_for_device` | async | self, device_uuid, telemetry_id, ... (+3) | <ast.BinOp object at 0x7f59efacfd50> | 427 |
| `async_reset_system` | async | self | None | 1070 |
| `async_set_hvac_season` | async | self, season, hpStandby | <ast.Constant object at 0x7f59efbc6790> | 944 |
| `async_set_property_for_device` | async | self, device_uuid, property_path, ... (+1) | <ast.Subscript object at 0x7f59efa76690> | 1002 |
| `async_update_dashboard` | async | self, set_point_temperature, fan_speed, ... (+9) | dict | 719 |
| `async_update_thermal_profile` | async | self, updates | <ast.Subscript object at 0x7f59efbc0fd0> | 833 |
| `close` | async | self | <ast.Constant object at 0x7f59efaafc50> | 193 |

#### Methoden-Details

##### `__init__(self, base_url, hass, read_timeout, write_timeout, cache_ttl, max_retries, min_request_interval, write_cooldown, request_debounce)`

```
Initialize ComfoClime API client.

Args:
    base_url: Base URL of the ComfoClime device (e.g., "http://192.168.1.100")
    hass: Optional Home Assistant instance for integration
    read_timeout: Timeout for read operations (GET) in seconds
    write_timeout: Timeout for write operations (PUT) in seconds
    cache_ttl: Cache time-to-live in seconds for telemetry/property reads
    max_retries: Maximum number of retries for transient failures
    min_request_interval: Minimum interval between requests in seconds
    write_cooldown: Cooldown period after write operations in seconds
    request_debounce: Debounce time for rapid requests in seconds
```

**Typ:** sync

**Zeile:** 111

##### `_async_get_uuid_internal(self, response_data)`

```
Internal method to get device UUID from monitoring endpoint.

Uses skip_lock=True because it's called from within other api_get
decorated methods where the lock is already held.

Args:
    response_data: JSON response from /monitoring/ping endpoint

Returns:
    Device UUID string or None if not found.

Note:
    The @api_get decorator handles rate limiting, session management,
    and HTTP request execution.
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 210

##### `_async_update_thermal_profile(self)`

```
Internal decorated method for thermal profile updates.

This method is decorated with @api_put which handles:
- UUID retrieval
- Rate limiting
- Retry with exponential backoff
- Error handling

Only called from async_update_thermal_profile wrapper to avoid duplication.

Supported kwargs:
    - season_status, season_value, heating_threshold_temperature, cooling_threshold_temperature
    - temperature_status, manual_temperature
    - temperature_profile
    - heating_comfort_temperature, heating_knee_point_temperature, heating_reduction_delta_temperature
    - cooling_comfort_temperature, cooling_knee_point_temperature, cooling_temperature_limit

Returns:
    Payload dict for the decorator to process.
```

**Decorators:** `api_put`

**Typ:** async

**Zeile:** 789

##### `_convert_dict_to_kwargs_and_update(self, updates)`

```
Convert legacy dict-based thermal profile updates to kwargs format.

Internal method that translates nested dict structure to modern
kwargs format for calling _async_update_thermal_profile.

Args:
    updates: Nested dict structure with thermal profile updates

Returns:
    Response from _async_update_thermal_profile.
```

**Typ:** async

**Zeile:** 880

##### `_get_session(self)`

```
Get or create aiohttp session.

Returns an existing session if available, or creates a new one.
The session is reused across all API calls for connection pooling.

Returns:
    Active aiohttp ClientSession instance.

Note:
    Timeouts are set per-request, not on the session level,
    to allow different timeouts for read vs write operations.
```

**Typ:** async

**Zeile:** 175

##### `_read_property_for_device_raw(self, response_data, device_uuid, property_path)`

```
Read raw property data from device.

The @api_get decorator handles:
- Request locking
- Rate limiting
- Session management
- Error handling (returns None on error)

Args:
    device_uuid: UUID of the device
    property_path: Property path (e.g., "29/1/10")

Returns:
    List of bytes or None on error
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 609

##### `_read_telemetry_raw(self, response_data, device_uuid, telemetry_id)`

```
Read raw telemetry data from device.

The @api_get decorator handles:
- Request locking
- Rate limiting
- Session management
- Error handling (returns None on error)

Args:
    device_uuid: UUID of the device
    telemetry_id: Telemetry ID to read

Returns:
    List of bytes or None on error
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 405

##### `_set_property_internal(self, device_uuid, x, y, z, data)`

```
Internal method to build property write payload.

The @api_put decorator handles:
- Request locking
- Rate limiting (write mode)
- Session management
- Retry with exponential backoff
- Error handling

Args:
    device_uuid: UUID of the device
    x, y: URL path parameters from property_path
    z: First data byte (property ID)
    data: Additional data bytes (value)

Returns:
    Payload dict for the decorator to process
```

**Decorators:** `api_put`

**Typ:** async

**Zeile:** 974

##### `_update_thermal_profile(self)`

```
Update thermal profile settings via API.

Modern method for thermal profile updates. Only fields that are provided
will be included in the update payload.

The @api_put decorator handles:
- UUID retrieval
- Rate limiting
- Retry with exponential backoff
- Error handling

Supported kwargs:
    - season_status, season_value, heating_threshold_temperature, cooling_threshold_temperature
    - temperature_status, manual_temperature
    - temperature_profile
    - heating_comfort_temperature, heating_knee_point_temperature, heating_reduction_delta_temperature
    - cooling_comfort_temperature, cooling_knee_point_temperature, cooling_temperature_limit

Returns:
    Payload dict for the decorator to process.
```

**Decorators:** `api_put`

**Typ:** async

**Zeile:** 673

##### `_wait_for_rate_limit(self, is_write)`

```
Wait if necessary to respect rate limits.

This method enforces minimum request intervals and write cooldowns
to prevent overloading the device's API.

Args:
    is_write: True for write operations, False for read operations.
        Write operations have longer cooldown periods.
```

**Typ:** async

**Zeile:** 159

##### `async_get_connected_devices(self, response_data)`

```
Fetch list of connected devices from the system.

Returns information about all devices connected to the ComfoClime
system, including heat pumps, sensors, and other peripherals.

Args:
    response_data: Extracted 'devices' array from response

Returns:
    List of DeviceConfig Pydantic models, each validated and containing:
        - uuid (str): Device UUID
        - model_type_id (int): Device model type/ID
        - display_name (str): Human-readable device name
        - version (str): Firmware version (optional)

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> devices = await api.async_get_connected_devices()
    >>> for device in devices:
    ...     print(f"{device.display_name}: {device.model_type_id}")

Note:
    The @api_get decorator extracts 'devices' key from response
    and returns [] if not found. Invalid device entries are skipped.
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 336

##### `async_get_dashboard_data(self, response_data)`

```
Fetch current dashboard data from the device.

Returns real-time status including temperatures, fan speed,
operating mode, and system state. All temperature values are
automatically fixed for signed integer handling.

Args:
    response_data: JSON response from /system/{uuid}/dashboard endpoint

Returns:
    Dictionary containing:
        - indoorTemperature (float): Current indoor temperature in °C
        - outdoorTemperature (float): Current outdoor temperature in °C
        - setPointTemperature (float): Target temperature in °C
        - fanSpeed (int): Current fan speed level (0-3)
        - season (int): Season mode (0=transition, 1=heating, 2=cooling)
        - hpStandby (bool): Heat pump standby state
        - temperatureProfile (int): Active temperature profile (0-2)
        - status (int): Control mode (0=manual, 1=automatic)

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> data = await api.async_get_dashboard_data()
    >>> if data['season'] == 1:
    ...     print(f"Heating mode: {data['indoorTemperature']}°C")

Note:
    The @api_get decorator handles request locking, rate limiting,
    UUID retrieval, session management, and temperature value fixing.
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 294

##### `async_get_device_definition(self, response_data, device_uuid)`

```
Get device definition data.

Args:
    device_uuid: UUID of the device

Returns:
    Dictionary containing device definition data

The @api_get decorator handles:
- Request locking
- Rate limiting
- Session management
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 388

##### `async_get_monitoring_ping(self, response_data)`

```
Get monitoring/ping data including device uptime.

Returns comprehensive monitoring information including UUID,
uptime, and timestamp.

Args:
    response_data: JSON response from /monitoring/ping endpoint

Returns:
    Dictionary containing:
        - uuid (str): Device UUID
        - up_time_seconds (int): Device uptime in seconds
        - timestamp (int): Current timestamp

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> data = await api.async_get_monitoring_ping()
    >>> hours = data['up_time_seconds'] / 3600
    >>> print(f"Device has been running for {hours:.1f} hours")

Note:
    The @api_get decorator handles request locking, rate limiting,
    and session management automatically.
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 250

##### `async_get_thermal_profile(self, response_data)`

```
Fetch thermal profile configuration from the device.

Returns heating and cooling parameters including temperature profiles,
season settings, and control modes. All temperature values are
automatically fixed for signed integer handling.

Args:
    response_data: JSON response from /system/{uuid}/thermalprofile endpoint

Returns:
    Dictionary containing thermal profile data:
        - season: Season configuration (status, season value, thresholds)
        - temperature: Temperature control settings (status, manual temp)
        - temperatureProfile: Active profile (0=comfort, 1=power, 2=eco)
        - heatingThermalProfileSeasonData: Heating parameters
        - coolingThermalProfileSeasonData: Cooling parameters
        Returns {} on error.

Raises:
    aiohttp.ClientError: If connection to device fails (returns {}).
    asyncio.TimeoutError: If request times out (returns {}).

Example:
    >>> profile = await api.async_get_thermal_profile()
    >>> if profile['season']['season'] == 1:
    ...     comfort = profile['heatingThermalProfileSeasonData']['comfortTemperature']
    ...     print(f"Heating comfort temperature: {comfort}°C")

Note:
    The @api_get decorator returns {} on any error to prevent
    integration failures.
```

**Decorators:** `api_get`

**Typ:** async

**Zeile:** 637

##### `async_get_uuid(self)`

```
Get device UUID with lock protection.

Public method to fetch the system UUID from the device.
The UUID is cached after the first call.

Returns:
    Device UUID string or None if not available.

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> uuid = await api.async_get_uuid()
    >>> print(f"Device UUID: {uuid}")
```

**Typ:** async

**Zeile:** 229

##### `async_read_property_for_device(self, device_uuid, property_path, faktor, signed, byte_count)`

```
Read property data for a device with automatic caching.

Fetches property data from a device. Results are cached for CACHE_TTL
seconds to reduce API load. Supports numeric properties (1-2 bytes)
and string properties (3+ bytes).

Args:
    device_uuid: UUID of the device
    property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
    faktor: Scaling factor for numeric values (default: 1.0)
    signed: If True, interpret numeric values as signed (default: True)
    byte_count: Number of bytes (1-2 for numeric, 3+ for string)

Returns:
    PropertyReading model with validated data and scaled_value property,
    or None if failed.

Raises:
    ValueError: If byte_count is invalid or data size mismatch.
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> # Read numeric property
    >>> reading = await api.async_read_property_for_device(
    ...     device_uuid="abc123",
    ...     property_path="29/1/10",
    ...     byte_count=2,
    ...     faktor=0.1
    ... )
    >>> if reading:
    ...     print(f"Value: {reading.scaled_value}")
```

**Typ:** async

**Zeile:** 509

##### `async_read_telemetry_for_device(self, device_uuid, telemetry_id, faktor, signed, byte_count)`

```
Read telemetry data for a device with automatic caching.

Fetches telemetry data from a specific device sensor. Results are
cached for CACHE_TTL seconds to reduce API load. Supports scaling
and signed/unsigned interpretation.

Args:
    device_uuid: UUID of the device
    telemetry_id: Telemetry sensor ID to read
    faktor: Scaling factor to multiply the raw value by (default: 1.0)
    signed: If True, interpret as signed integer (default: True)
    byte_count: Number of bytes to read (1 or 2, auto-detected if None)

Returns:
    TelemetryReading model with validated data and scaled_value property,
    or None if read failed.

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> # Read temperature sensor (2 bytes, signed, factor 0.1)
    >>> reading = await api.async_read_telemetry_for_device(
    ...     device_uuid="abc123",
    ...     telemetry_id="100",
    ...     faktor=0.1,
    ...     signed=True,
    ...     byte_count=2
    ... )
    >>> if reading:
    ...     print(f"Temperature: {reading.scaled_value}°C")
```

**Typ:** async

**Zeile:** 427

##### `async_reset_system(self)`

```
Trigger a system restart of the ComfoClime device.

Sends a reset command to reboot the device. The device will
be unavailable for a short time during the restart process.

Returns:
    Response from device API.

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> await api.async_reset_system()
    >>> # Wait for device to restart
    >>> await asyncio.sleep(10)

Note:
    The @api_put decorator handles request locking, rate limiting,
    session management, and retry with exponential backoff.
```

**Decorators:** `api_put`

**Typ:** async

**Zeile:** 1070

##### `async_set_hvac_season(self, season, hpStandby)`

```
Set HVAC season and heat pump standby state atomically.

Updates both the season (via thermal profile) and hpStandby state
(via dashboard) in a single atomic operation. The decorators handle
all locking internally.

Args:
    season: Season value (0=transition, 1=heating, 2=cooling)
    hpStandby: Heat pump standby state (False=active, True=standby/off)

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> # Activate heating mode
    >>> await api.async_set_hvac_season(season=1, hpStandby=False)
    >>> # Put system in standby
    >>> await api.async_set_hvac_season(season=0, hpStandby=True)
```

**Typ:** async

**Zeile:** 944

##### `async_set_property_for_device(self, device_uuid, property_path, value)`

```
Set property value for a device.

Writes a property value to a device. The decorator handles all
locking, rate limiting, and retry logic. After successful write,
the cache for this device is invalidated.

Args:
    device_uuid: UUID of the device
    property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
    value: Value to set (will be scaled by faktor)
    byte_count: Number of bytes (1 or 2)
    signed: If True, encode as signed integer (default: True)
    faktor: Scaling factor to divide value by before encoding (default: 1.0)

Returns:
    Response from device API.

Raises:
    ValueError: If byte_count is not 1 or 2.
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> # Set property to 22.5°C (factor 0.1, so raw value = 225)
    >>> await api.async_set_property_for_device(
    ...     device_uuid="abc123",
    ...     property_path="29/1/10",
    ...     value=22.5,
    ...     byte_count=2,
    ...     signed=True,
    ...     faktor=0.1
    ... )
```

**Typ:** async

**Zeile:** 1002

##### `async_update_dashboard(self, set_point_temperature, fan_speed, season, hpStandby, schedule, temperature_profile, season_profile, status, scenario, scenario_time_left, scenario_start_delay)`

```
Update dashboard settings via API.

Modern method for dashboard updates. Only fields that are provided
(not None) will be included in the update payload.

The @api_put decorator handles:
- UUID retrieval
- Rate limiting
- Timestamp addition (is_dashboard=True)
- Retry with exponential backoff
- Error handling

Args:
    set_point_temperature: Target temperature (°C) - activates manual mode
    fan_speed: Fan speed (0-3)
    season: Season value (0=transition, 1=heating, 2=cooling)
    hpStandby: Heat pump standby state (True=standby/off, False=active)
    schedule: Schedule mode
    temperature_profile: Temperature profile/preset (0=comfort, 1=boost, 2=eco)
    season_profile: Season profile/preset (0=comfort, 1=boost, 2=eco)
    status: Temperature control mode (0=manual, 1=automatic)
    scenario: Scenario mode (4=Kochen, 5=Party, 7=Urlaub, 8=Boost)
    scenario_time_left: Duration for scenario in seconds (e.g., 1800 for 30min)
    scenario_start_delay: Start delay for scenario in seconds (optional)

Returns:
    Payload dict for the decorator to process.
```

**Decorators:** `api_put`

**Typ:** async

**Zeile:** 719

##### `async_update_thermal_profile(self, updates)`

```
Update thermal profile settings on the device.

Provides backward compatibility with legacy dict-based calls while
supporting modern kwargs-based calls. Only specified fields are updated.

Supports two calling styles:
    1. Legacy dict-based: await api.async_update_thermal_profile({"season": {"season": 1}})
    2. Modern kwargs-based: await api.async_update_thermal_profile(season_value=1)

Args:
    updates: Optional dict with nested thermal profile structure (legacy style)
    **kwargs: Modern kwargs style parameters:
        - season_status (int): Season control mode
        - season_value (int): Season (0=transition, 1=heating, 2=cooling)
        - heating_threshold_temperature (float): Temperature threshold for heating
        - cooling_threshold_temperature (float): Temperature threshold for cooling
        - temperature_status (int): Temperature control mode (0=manual, 1=automatic)
        - manual_temperature (float): Manual temperature setpoint
        - temperature_profile (int): Profile (0=comfort, 1=power, 2=eco)
        - heating_comfort_temperature (float): Heating comfort temperature
        - heating_knee_point_temperature (float): Heating knee point
        - heating_reduction_delta_temperature (float): Heating reduction delta
        - cooling_comfort_temperature (float): Cooling comfort temperature
        - cooling_knee_point_temperature (float): Cooling knee point
        - cooling_temperature_limit (float): Cooling temperature limit

Returns:
    Response from device API.

Raises:
    aiohttp.ClientError: If connection to device fails.
    asyncio.TimeoutError: If request times out.

Example:
    >>> # Modern style - set season to heating
    >>> await api.async_update_thermal_profile(season_value=1)
    >>> # Modern style - set heating comfort temperature
    >>> await api.async_update_thermal_profile(heating_comfort_temperature=22.0)
    >>> # Legacy style
    >>> await api.async_update_thermal_profile({"season": {"season": 1}})
```

**Typ:** async

**Zeile:** 833

##### `close(self)`

```
Close the aiohttp session.

This should be called when the API client is no longer needed
to properly clean up network resources.

Example:
    >>> api = ComfoClimeAPI("http://192.168.1.100")
    >>> try:
    ...     await api.async_get_dashboard_data()
    ... finally:
    ...     await api.close()
```

**Typ:** async

**Zeile:** 193


---

## comfoclime.config_flow

**Dateipfad:** `custom_components/comfoclime/config_flow.py`

### Klasse: `ComfoClimeConfigFlow`

**Erbt von:** `ConfigFlow`

**Beschreibung:**
```
Handle a config flow for ComfoClime integration.

Validates device connection by attempting to fetch the UUID from
the monitoring/ping endpoint. If successful, creates a config entry.
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `async_get_options_flow` | sync | cls, entry | None | 161 |
| `async_step_user` | async | self, user_input | None | 95 |

#### Methoden-Details

##### `async_get_options_flow(cls, entry)`

**Decorators:** `classmethod`

**Typ:** sync

**Zeile:** 161

##### `async_step_user(self, user_input)`

```
Handle the initial step where user provides device hostname.

Validates that the device is reachable and responds with a valid
UUID. If validation succeeds, creates the config entry.

Args:
    user_input: Dictionary with 'host' key containing hostname or IP

Returns:
    FlowResult: Either shows form or creates entry
```

**Typ:** async

**Zeile:** 95


---

### Klasse: `ComfoClimeOptionsFlow`

**Erbt von:** `OptionsFlow`

**Beschreibung:**
```
Handle options flow for ComfoClime integration.

Provides a multi-step wizard for configuring integration options including:
    - Performance settings (polling intervals, timeouts)
    - Entity categories (sensors, switches, numbers, selects)
    - Individual entity enable/disable

Changes are tracked in _pending_changes and only saved when the user
completes the flow or explicitly saves.
```

**Methoden:** 23

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, entry | <ast.Constant object at 0x7f59efabbf90> | 177 |
| `_get_current_value` | sync | self, key, default | Any | 188 |
| `_update_pending` | sync | self, data | <ast.Constant object at 0x7f59efaaf990> | 202 |
| `async_step_entities` | async | self, user_input | FlowResult | 230 |
| `async_step_entities_menu` | async | self, user_input | FlowResult | 630 |
| `async_step_entities_numbers` | async | self, user_input | FlowResult | 1054 |
| `async_step_entities_selects` | async | self, user_input | FlowResult | 1104 |
| `async_step_entities_sensors` | async | self, user_input | FlowResult | 614 |
| `async_step_entities_sensors_access_tracking` | async | self, user_input | FlowResult | 954 |
| `async_step_entities_sensors_connected_definition` | async | self, user_input | FlowResult | 900 |
| `async_step_entities_sensors_connected_properties` | async | self, user_input | FlowResult | 846 |
| `async_step_entities_sensors_connected_telemetry` | async | self, user_input | FlowResult | 792 |
| `async_step_entities_sensors_dashboard` | async | self, user_input | FlowResult | 643 |
| `async_step_entities_sensors_monitoring` | async | self, user_input | FlowResult | 743 |
| `async_step_entities_sensors_thermalprofile` | async | self, user_input | FlowResult | 693 |
| `async_step_entities_switches` | async | self, user_input | FlowResult | 1004 |
| `async_step_general` | async | self, user_input | FlowResult | 451 |
| `async_step_general_diagnostics` | async | self, user_input | FlowResult | 464 |
| `async_step_general_polling` | async | self, user_input | FlowResult | 520 |
| `async_step_general_rate_limiting` | async | self, user_input | FlowResult | 563 |
| `async_step_general_timeouts` | async | self, user_input | FlowResult | 483 |
| `async_step_init` | async | self, user_input | FlowResult | 219 |
| `async_step_save_and_exit` | async | self, user_input | FlowResult | 211 |

#### Methoden-Details

##### `__init__(self, entry)`

```
Initialize the options flow.

Args:
    entry: Config entry being configured
```

**Typ:** sync

**Zeile:** 177

##### `_get_current_value(self, key, default)`

```
Get current value from pending changes first, then from saved options.

Args:
    key: Option key to retrieve
    default: Default value if not found

Returns:
    Current value for the option
```

**Typ:** sync

**Zeile:** 188

##### `_update_pending(self, data)`

```
Update pending changes without saving.

Args:
    data: Dictionary of changes to merge into pending changes
```

**Typ:** sync

**Zeile:** 202

##### `async_step_entities(self, user_input)`

```
Handle all entity selection in one page with multiple selectors.
```

**Typ:** async

**Zeile:** 230

##### `async_step_entities_menu(self, user_input)`

```
Show submenu for entity categories (sensors, switches, numbers, selects).
```

**Typ:** async

**Zeile:** 630

##### `async_step_entities_numbers(self, user_input)`

```
Handle number entity selection.
```

**Typ:** async

**Zeile:** 1054

##### `async_step_entities_selects(self, user_input)`

```
Handle select entity selection.
```

**Typ:** async

**Zeile:** 1104

##### `async_step_entities_sensors(self, user_input)`

```
Show menu to select which sensor category to configure.
```

**Typ:** async

**Zeile:** 614

##### `async_step_entities_sensors_access_tracking(self, user_input)`

```
Handle access tracking sensor entity selection.
```

**Typ:** async

**Zeile:** 954

##### `async_step_entities_sensors_connected_definition(self, user_input)`

```
Handle connected device definition sensor entity selection.
```

**Typ:** async

**Zeile:** 900

##### `async_step_entities_sensors_connected_properties(self, user_input)`

```
Handle connected device properties sensor entity selection.
```

**Typ:** async

**Zeile:** 846

##### `async_step_entities_sensors_connected_telemetry(self, user_input)`

```
Handle connected device telemetry sensor entity selection.
```

**Typ:** async

**Zeile:** 792

##### `async_step_entities_sensors_dashboard(self, user_input)`

```
Handle dashboard sensor entity selection.
```

**Typ:** async

**Zeile:** 643

##### `async_step_entities_sensors_monitoring(self, user_input)`

```
Handle monitoring sensor entity selection.
```

**Typ:** async

**Zeile:** 743

##### `async_step_entities_sensors_thermalprofile(self, user_input)`

```
Handle thermal profile sensor entity selection.
```

**Typ:** async

**Zeile:** 693

##### `async_step_entities_switches(self, user_input)`

```
Handle switch entity selection.
```

**Typ:** async

**Zeile:** 1004

##### `async_step_general(self, user_input)`

```
Handle general configuration options - show menu.
```

**Typ:** async

**Zeile:** 451

##### `async_step_general_diagnostics(self, user_input)`

```
Handle diagnostic configuration options.
```

**Typ:** async

**Zeile:** 464

##### `async_step_general_polling(self, user_input)`

```
Handle polling and caching configuration options.
```

**Typ:** async

**Zeile:** 520

##### `async_step_general_rate_limiting(self, user_input)`

```
Handle rate limiting configuration options.
```

**Typ:** async

**Zeile:** 563

##### `async_step_general_timeouts(self, user_input)`

```
Handle timeout configuration options.
```

**Typ:** async

**Zeile:** 483

##### `async_step_init(self, user_input)`

```
Handle options flow - show menu.
```

**Typ:** async

**Zeile:** 219

##### `async_step_save_and_exit(self, user_input)`

```
Save all pending changes and exit.
```

**Typ:** async

**Zeile:** 211


---

## comfoclime.constants

**Dateipfad:** `custom_components/comfoclime/constants.py`

### Klasse: `APIDefaults`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Default values for API configuration.

Immutable configuration values for API timeouts, caching, and rate limiting.
These values can be overridden when instantiating ComfoClimeAPI.

Note: frozen=True provides immutability at the instance level. Final type hints
are not needed with Pydantic as the frozen configuration prevents reassignment.
```


---

### Klasse: `FanSpeed`

**Erbt von:** `IntEnum`

**Beschreibung:**
```
Discrete fan speed levels.

Fan speed levels supported by ComfoClime:
- OFF: Fan disabled
- LOW: Low fan speed
- MEDIUM: Medium fan speed
- HIGH: High fan speed
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `from_percentage` | sync | cls, percentage | FanSpeed | 123 |
| `to_percentage` | sync | self | int | 112 |

#### Methoden-Details

##### `from_percentage(cls, percentage)`

```
Convert percentage to fan speed level.

Args:
    percentage: Fan speed as percentage (0-100).

Returns:
    Corresponding FanSpeed level.
```

**Decorators:** `classmethod`

**Typ:** sync

**Zeile:** 123

##### `to_percentage(self)`

```
Convert fan speed to percentage (0-100).

Returns:
    Fan speed as percentage (0, 33, 66, 100).
```

**Typ:** sync

**Zeile:** 112


---

### Klasse: `ScenarioMode`

**Erbt von:** `IntEnum`

**Beschreibung:**
```
Scenario modes supported by ComfoClime.

These modes temporarily override normal operation for specific use cases.
Each mode has a default duration and can be activated via climate presets
or the set_scenario_mode service.
```

**Methoden:** 3

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `default_duration_minutes` | sync | self | int | 24 |
| `from_preset_name` | sync | cls, name | <ast.BinOp object at 0x7f59efa09a90> | 54 |
| `preset_name` | sync | self | str | 39 |

#### Methoden-Details

##### `default_duration_minutes(self)`

```
Get default duration in minutes for this scenario.

Returns:
    Default duration in minutes for the scenario mode.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 24

##### `from_preset_name(cls, name)`

```
Get ScenarioMode from preset name.

Args:
    name: Home Assistant preset name.

Returns:
    ScenarioMode instance or None if not found.
```

**Decorators:** `classmethod`

**Typ:** sync

**Zeile:** 54

##### `preset_name(self)`

```
Get Home Assistant preset name for this scenario.

Returns:
    Home Assistant preset name string.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 39


---

### Klasse: `Season`

**Erbt von:** `IntEnum`

**Beschreibung:**
```
Season modes for heating/cooling control.

Determines the operating mode of the heat pump:
- TRANSITIONAL: Fan only, no heating or cooling
- HEATING: Heating mode active
- COOLING: Cooling mode active
```


---

### Klasse: `TemperatureProfile`

**Erbt von:** `IntEnum`

**Beschreibung:**
```
Temperature profile presets.

Predefined temperature profiles for automatic mode:
- COMFORT: Comfort temperature settings
- POWER: Power/Boost temperature settings
- ECO: Energy-saving temperature settings
```


---

## comfoclime.coordinator

**Dateipfad:** `custom_components/comfoclime/coordinator.py`

### Klasse: `ComfoClimeDashboardCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for fetching real-time dashboard data from ComfoClime device.

Polls the device at regular intervals to fetch current operating status
including temperatures, fan speed, season mode, and system state.
This data is used by climate, fan, and sensor entities.

Attributes:
    api: ComfoClimeAPI instance for device communication

Example:
    >>> coordinator = ComfoClimeDashboardCoordinator(
    ...     hass=hass,
    ...     api=api,
    ...     polling_interval=60
    ... )
    >>> await coordinator.async_config_entry_first_refresh()
    >>> temp = coordinator.data['indoorTemperature']
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+3) | None | 75 |
| `_async_update_data` | async | self | DashboardData | 101 |

#### Methoden-Details

##### `__init__(self, hass, api, polling_interval, access_tracker, config_entry)`

```
Initialize the dashboard data coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 75

##### `_async_update_data(self)`

```
Fetch dashboard data from the API.

Returns:
    DashboardData model containing validated dashboard data with fields:
        - indoor_temperature: Indoor temperature in °C
        - outdoor_temperature: Outdoor temperature in °C
        - set_point_temperature: Target temperature in °C (manual mode)
        - exhaust_air_flow: Exhaust air flow in m³/h
        - supply_air_flow: Supply air flow in m³/h
        - fan_speed: Fan speed level (0-3)
        - season: Season mode (0=transition, 1=heating, 2=cooling)
        - status: Control mode (0=manual, 1=automatic)
        - and more (see DashboardData model)

Raises:
    UpdateFailed: If API call fails or times out.
```

**Typ:** async

**Zeile:** 101


---

### Klasse: `ComfoClimeDefinitionCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for fetching device definition data.

Fetches definition data for connected devices, particularly useful
for ComfoAirQ devices (modelTypeId=1) which provide detailed sensor
and control point definitions. ComfoClime devices provide less useful
definition data and are skipped.

Attributes:
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices

Example:
    >>> coordinator = ComfoClimeDefinitionCoordinator(hass, api, devices)
    >>> await coordinator.async_config_entry_first_refresh()
    >>> definition = coordinator.get_definition_data("abc123")
```

**Methoden:** 3

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+4) | <ast.Constant object at 0x7f59efb2e890> | 636 |
| `_async_update_data` | async | self | <ast.Subscript object at 0x7f59efab9210> | 665 |
| `get_definition_data` | sync | self, device_uuid | <ast.BinOp object at 0x7f59efaba550> | 705 |

#### Methoden-Details

##### `__init__(self, hass, api, devices, polling_interval, access_tracker, config_entry)`

```
Initialize the device definition coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 636

##### `_async_update_data(self)`

```
Fetch definition data for ComfoAirQ devices.

Only fetches definitions for ComfoAirQ devices (modelTypeId=1)
as ComfoClime devices provide minimal useful definition data.
Failed reads are logged but don't fail the entire update.

Returns:
    Dictionary mapping device_uuid to definition data.
    Values are None if read failed or device skipped.
```

**Typ:** async

**Zeile:** 665

##### `get_definition_data(self, device_uuid)`

```
Get cached definition data for a device.

Retrieves definition data that was fetched during the last
coordinator update. Returns None if the device doesn't exist,
wasn't fetched, or if the read failed.

Args:
    device_uuid: UUID of the device

Returns:
    Dictionary containing device definition data, or None if not found.

Example:
    >>> definition = coordinator.get_definition_data("abc123")
    >>> if definition:
    ...     print(f"Device has {len(definition.get('sensors', []))} sensors")
```

**Typ:** sync

**Zeile:** 705


---

### Klasse: `ComfoClimeMonitoringCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for fetching device monitoring and health data.

Polls the monitoring endpoint to fetch device uptime, UUID, and
health status. This data is used by sensor entities to track
device availability and performance.

Attributes:
    api: ComfoClimeAPI instance for device communication

Example:
    >>> coordinator = ComfoClimeMonitoringCoordinator(hass, api)
    >>> await coordinator.async_config_entry_first_refresh()
    >>> uptime = coordinator.data['up_time_seconds']
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+3) | <ast.Constant object at 0x7f59efaa0e10> | 146 |
| `_async_update_data` | async | self | <ast.Subscript object at 0x7f59efaa11d0> | 172 |

#### Methoden-Details

##### `__init__(self, hass, api, polling_interval, access_tracker, config_entry)`

```
Initialize the monitoring data coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 146

##### `_async_update_data(self)`

```
Fetch monitoring data from the API.

Returns:
    Dictionary containing monitoring data with keys:
        - uuid: Device UUID string
        - up_time_seconds: Device uptime in seconds
        - timestamp: Current timestamp

Raises:
    UpdateFailed: If API call fails or times out.
```

**Typ:** async

**Zeile:** 172


---

### Klasse: `ComfoClimePropertyCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for batching property requests from all devices.

Instead of each sensor/number/select making individual API calls,
this coordinator collects all property requests and fetches them
in a single batched update cycle. This significantly reduces API
load on the Airduino board.

Entities register their property needs using register_property(), and
the coordinator fetches all values during each update. Entities then
retrieve their values using get_property_value().

Attributes:
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices

Example:
    >>> coordinator = ComfoClimePropertyCoordinator(hass, api, devices)
    >>> # Register a property
    >>> await coordinator.register_property(
    ...     device_uuid="abc123",
    ...     property_path="29/1/10",
    ...     faktor=0.1,
    ...     byte_count=2
    ... )
    >>> await coordinator.async_config_entry_first_refresh()
    >>> # Retrieve value
    >>> value = coordinator.get_property_value("abc123", "29/1/10")
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+4) | <ast.Constant object at 0x7f59efacc250> | 470 |
| `_async_update_data` | async | self | <ast.Subscript object at 0x7f59efb1c3d0> | 544 |
| `get_property_value` | sync | self, device_uuid, property_path | Any | 592 |
| `register_property` | async | self, device_uuid, property_path, ... (+3) | <ast.Constant object at 0x7f59efae2b10> | 503 |

#### Methoden-Details

##### `__init__(self, hass, api, devices, polling_interval, access_tracker, config_entry)`

```
Initialize the property data coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 470

##### `_async_update_data(self)`

```
Fetch all registered property data in a batched manner.

Iterates through all registered properties and fetches their
values from the API. Failed reads are logged but don't fail
the entire update.

Returns:
    Nested dictionary: {device_uuid: {property_path: value}}
    Values are None if read failed.
```

**Typ:** async

**Zeile:** 544

##### `get_property_value(self, device_uuid, property_path)`

```
Get a cached property value from the last update.

Retrieves a property value that was fetched during the last
coordinator update. Returns None if the value doesn't exist or
if the read failed.

Args:
    device_uuid: UUID of the device
    property_path: Property path (e.g., "29/1/10")

Returns:
    The cached property value (float or string), or None if not found/failed.

Example:
    >>> value = coordinator.get_property_value("abc123", "29/1/10")
    >>> if value is not None:
    ...     print(f"Property value: {value}")
```

**Typ:** sync

**Zeile:** 592

##### `register_property(self, device_uuid, property_path, faktor, signed, byte_count)`

```
Register a property to be fetched during updates.

Entities should call this during their initialization to register
their property needs. The coordinator will then fetch this value
during each update cycle.

Args:
    device_uuid: UUID of the device to read from
    property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
    faktor: Scaling factor to multiply numeric values by (default: 1.0)
    signed: If True, interpret numeric values as signed (default: True)
    byte_count: Number of bytes (1-2 for numeric, 3+ for string)

Example:
    >>> await coordinator.register_property(
    ...     device_uuid="abc123",
    ...     property_path="29/1/10",
    ...     faktor=0.1,
    ...     signed=True,
    ...     byte_count=2
    ... )
```

**Typ:** async

**Zeile:** 503


---

### Klasse: `ComfoClimeTelemetryCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for batching telemetry requests from all devices.

Instead of each sensor making individual API calls, this coordinator
collects all telemetry requests and fetches them in a single batched
update cycle. This significantly reduces API load on the Airduino board.

Sensors register their telemetry needs using register_telemetry(), and
the coordinator fetches all values during each update. Sensors then
retrieve their values using get_telemetry_value().

Attributes:
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices

Example:
    >>> coordinator = ComfoClimeTelemetryCoordinator(hass, api, devices)
    >>> # Register a sensor
    >>> await coordinator.register_telemetry(
    ...     device_uuid="abc123",
    ...     telemetry_id="100",
    ...     faktor=0.1,
    ...     signed=True,
    ...     byte_count=2
    ... )
    >>> await coordinator.async_config_entry_first_refresh()
    >>> # Retrieve value
    >>> value = coordinator.get_telemetry_value("abc123", "100")
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+4) | <ast.Constant object at 0x7f59efbc48d0> | 292 |
| `_async_update_data` | async | self | <ast.Subscript object at 0x7f59efae9a10> | 366 |
| `get_telemetry_value` | sync | self, device_uuid, telemetry_id | Any | 414 |
| `register_telemetry` | async | self, device_uuid, telemetry_id, ... (+3) | <ast.Constant object at 0x7f59efbce9d0> | 325 |

#### Methoden-Details

##### `__init__(self, hass, api, devices, polling_interval, access_tracker, config_entry)`

```
Initialize the telemetry data coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    devices: List of connected devices
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 292

##### `_async_update_data(self)`

```
Fetch all registered telemetry data in a batched manner.

Iterates through all registered telemetry sensors and fetches
their values from the API. Failed reads are logged but don't
fail the entire update.

Returns:
    Nested dictionary: {device_uuid: {telemetry_id: value}}
    Values are None if read failed.
```

**Typ:** async

**Zeile:** 366

##### `get_telemetry_value(self, device_uuid, telemetry_id)`

```
Get a cached telemetry value from the last update.

Retrieves a telemetry value that was fetched during the last
coordinator update. Returns None if the value doesn't exist or
if the read failed.

Args:
    device_uuid: UUID of the device
    telemetry_id: Telemetry sensor ID (string or int)

Returns:
    The cached telemetry value, or None if not found/failed.

Example:
    >>> temp = coordinator.get_telemetry_value("abc123", "100")
    >>> if temp is not None:
    ...     print(f"Temperature: {temp}°C")
```

**Typ:** sync

**Zeile:** 414

##### `register_telemetry(self, device_uuid, telemetry_id, faktor, signed, byte_count)`

```
Register a telemetry sensor to be fetched during updates.

Sensors should call this during their initialization to register
their telemetry needs. The coordinator will then fetch this value
during each update cycle.

Args:
    device_uuid: UUID of the device to read from
    telemetry_id: Telemetry sensor ID to fetch
    faktor: Scaling factor to multiply the raw value by (default: 1.0)
    signed: If True, interpret as signed integer (default: True)
    byte_count: Number of bytes to read (1 or 2, auto-detected if None)

Example:
    >>> await coordinator.register_telemetry(
    ...     device_uuid="abc123",
    ...     telemetry_id="100",
    ...     faktor=0.1,  # Temperature in 0.1°C units
    ...     signed=True,
    ...     byte_count=2
    ... )
```

**Typ:** async

**Zeile:** 325


---

### Klasse: `ComfoClimeThermalprofileCoordinator`

**Erbt von:** `DataUpdateCoordinator`

**Beschreibung:**
```
Coordinator for fetching thermal profile configuration data.

Polls the device to fetch heating and cooling parameters, season settings,
temperature profiles, and control modes. This data is used by climate
entities and sensor entities for temperature control.

Attributes:
    api: ComfoClimeAPI instance for device communication

Example:
    >>> coordinator = ComfoClimeThermalprofileCoordinator(hass, api)
    >>> await coordinator.async_config_entry_first_refresh()
    >>> season = coordinator.data['season']['season']
```

**Methoden:** 2

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, api, ... (+3) | <ast.Constant object at 0x7f59efb20a50> | 212 |
| `_async_update_data` | async | self | <ast.Subscript object at 0x7f59efbc6290> | 238 |

#### Methoden-Details

##### `__init__(self, hass, api, polling_interval, access_tracker, config_entry)`

```
Initialize the thermal profile data coordinator.

Args:
    hass: Home Assistant instance
    api: ComfoClimeAPI instance for device communication
    polling_interval: Update interval in seconds (default: 60)
    access_tracker: Optional access tracker for monitoring API calls
```

**Typ:** sync

**Zeile:** 212

##### `_async_update_data(self)`

```
Fetch thermal profile data from the API.

Returns:
    Dictionary containing thermal profile data with keys:
        - season: Season configuration
        - temperature: Temperature control settings
        - temperatureProfile: Active profile
        - heatingThermalProfileSeasonData: Heating parameters
        - coolingThermalProfileSeasonData: Cooling parameters

Raises:
    UpdateFailed: If API call fails or times out.
```

**Typ:** async

**Zeile:** 238


---

## comfoclime.entities.number_definitions

**Dateipfad:** `custom_components/comfoclime/entities/number_definitions.py`

### Klasse: `NumberDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a number entity.

Attributes:
    key: Unique identifier for the number in API responses.
    name: Display name for the number control.
    translation_key: Key for i18n translations.
    min: Minimum value.
    max: Maximum value.
    step: Step increment.
    unit: Optional unit of measurement.
```


---

### Klasse: `PropertyNumberDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a property-based number entity.

Attributes:
    property: Property path in format "X/Y/Z".
    name: Display name for the number control.
    translation_key: Key for i18n translations.
    min: Minimum value.
    max: Maximum value.
    step: Step increment.
    unit: Optional unit of measurement.
    faktor: Multiplication factor for the raw value.
    byte_count: Number of bytes to read/write.
```


---

## comfoclime.entities.select_definitions

**Dateipfad:** `custom_components/comfoclime/entities/select_definitions.py`

### Klasse: `PropertySelectDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a property-based select entity.

Attributes:
    path: Property path in format "X/Y/Z".
    name: Display name for the select control.
    translation_key: Key for i18n translations.
    options: Dictionary mapping numeric values to string options.
```


---

### Klasse: `SelectDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a select entity.

Attributes:
    key: Unique identifier for the select in API responses.
    name: Display name for the select control.
    translation_key: Key for i18n translations.
    options: Dictionary mapping numeric values to string options.
```


---

## comfoclime.entities.sensor_definitions

**Dateipfad:** `custom_components/comfoclime/entities/sensor_definitions.py`

### Klasse: `AccessTrackingSensorDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition for access tracking sensors.

Attributes:
    coordinator: Name of the coordinator to track (None for total).
    metric: Metric type (per_minute, per_hour, total_per_minute, total_per_hour).
    name: Display name for the sensor (fallback if translation missing).
    translation_key: Key for i18n translations.
    state_class: Home Assistant state class.
    entity_category: Entity category (None, diagnostic, config).
    unit: Unit of measurement (e.g., "°C", "m³/h").
    device_class: Home Assistant device class.
    icon: MDI icon name.
    suggested_display_precision: Decimal places for display.
```


---

### Klasse: `PropertySensorDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition for property-based sensors.

Attributes:
    path: Property path in format "X/Y/Z".
    name: Display name for the sensor (fallback if translation missing).
    translation_key: Key for i18n translations.
    faktor: Multiplication factor for the raw value.
    signed: Whether the value is signed.
    byte_count: Number of bytes to read from property.
    unit: Unit of measurement (e.g., "°C", "m³/h").
    device_class: Home Assistant device class.
    state_class: Home Assistant state class.
    entity_category: Entity category (None, diagnostic, config).
    icon: MDI icon name.
    suggested_display_precision: Decimal places for display.
```


---

### Klasse: `SensorCategory`

**Erbt von:** `Enum`

**Beschreibung:**
```
Categories of sensors in the integration.
```


---

### Klasse: `SensorDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a sensor entity.

Attributes:
    key: Unique identifier for the sensor in API responses or dict key.
    translation_key: Key for i18n translations.
    name: Display name for the sensor (fallback if translation missing).
    unit: Unit of measurement (e.g., "°C", "m³/h").
    device_class: Home Assistant device class.
    state_class: Home Assistant state class.
    entity_category: Entity category (None, diagnostic, config).
    icon: MDI icon name.
    suggested_display_precision: Decimal places for display.
```


---

### Klasse: `TelemetrySensorDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition for telemetry-based sensors.

Attributes:
    telemetry_id: ID for telemetry endpoint.
    name: Display name for the sensor (fallback if translation missing).
    translation_key: Key for i18n translations.
    faktor: Multiplication factor for the raw value.
    signed: Whether the value is signed.
    byte_count: Number of bytes to read from telemetry.
    unit: Unit of measurement (e.g., "°C", "m³/h").
    device_class: Home Assistant device class.
    state_class: Home Assistant state class.
    entity_category: Entity category (None, diagnostic, config).
    icon: MDI icon name.
    suggested_display_precision: Decimal places for display.
    diagnose: Whether this is a diagnostic sensor (experimental/unknown).
```


---

## comfoclime.entities.switch_definitions

**Dateipfad:** `custom_components/comfoclime/entities/switch_definitions.py`

### Klasse: `SwitchDefinition`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Definition of a switch entity.

Attributes:
    key: Unique identifier for the switch in API responses or dict key.
    name: Display name for the switch (fallback if translation missing).
    translation_key: Key for i18n translations.
    endpoint: Either "thermal_profile" or "dashboard".
    invert: If True, invert the state logic (e.g., for hpstandby).
```


---

## comfoclime.exceptions

**Dateipfad:** `custom_components/comfoclime/exceptions.py`

### Klasse: `ComfoClimeAPIError`

**Erbt von:** `ComfoClimeError`

**Beschreibung:**
```
Raised when API returns an error.
```


---

### Klasse: `ComfoClimeConnectionError`

**Erbt von:** `ComfoClimeError`

**Beschreibung:**
```
Raised when connection to ComfoClime device fails.
```


---

### Klasse: `ComfoClimeError`

**Erbt von:** `Exception`

**Beschreibung:**
```
Base exception for ComfoClime.
```


---

### Klasse: `ComfoClimeTimeoutError`

**Erbt von:** `ComfoClimeError`

**Beschreibung:**
```
Raised when request times out.
```


---

### Klasse: `ComfoClimeValidationError`

**Erbt von:** `ComfoClimeError`

**Beschreibung:**
```
Raised when input validation fails.
```


---

## comfoclime.fan

**Dateipfad:** `custom_components/comfoclime/fan.py`

### Klasse: `ComfoClimeFan`

**Erbt von:** `CoordinatorEntity, FanEntity`

**Beschreibung:**
```
ComfoClime Fan entity for ventilation fan speed control.

Provides control over the ComfoClime ventilation fan speed with
3 discrete speed levels (low/medium/high) plus off. The fan speed
is also controlled by the climate entity's fan_mode attribute.

Attributes:
    is_on: Whether the fan is on (speed > 0)
    percentage: Current fan speed as percentage (0%, 33%, 66%, 100%)
    speed_count: Number of discrete speed levels (3)

Example:
    >>> # Set fan to medium speed (66%)
    >>> await fan.async_set_percentage(66)
    >>> # Turn off fan
    >>> await fan.async_set_percentage(0)
```

**Methoden:** 6

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+3) | <ast.Constant object at 0x7f59efb1a1d0> | 71 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efb04bd0> | 161 |
| `async_set_percentage` | async | self, percentage | <ast.Constant object at 0x7f59efb2e5d0> | 123 |
| `device_info` | sync | self | DeviceInfo | 106 |
| `is_on` | sync | self | bool | 116 |
| `percentage` | sync | self | <ast.BinOp object at 0x7f59efb1ff50> | 120 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, device, entry)`

```
Initialize the ComfoClime fan entity.

Args:
    hass: Home Assistant instance
    coordinator: Dashboard data coordinator
    api: ComfoClime API instance
    device: Device info dictionary
    entry: Config entry for this integration
```

**Typ:** sync

**Zeile:** 71

##### `_handle_coordinator_update(self)`

**Typ:** sync

**Zeile:** 161

##### `async_set_percentage(self, percentage)`

```
Set the fan speed by percentage.

Converts percentage to discrete speed level (0-3) and updates
the device. The speed levels are:
    - 0%: Off (speed 0)
    - 33%: Low (speed 1)
    - 66%: Medium (speed 2)
    - 100%: High (speed 3)

Args:
    percentage: Fan speed percentage (0-100)

Raises:
    aiohttp.ClientError: If API call fails
    asyncio.TimeoutError: If API call times out
```

**Typ:** async

**Zeile:** 123

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 106

##### `is_on(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 116

##### `percentage(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 120


---

## comfoclime.models

**Dateipfad:** `custom_components/comfoclime/models.py`

### Klasse: `DashboardData`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Dashboard data from ComfoClime device.

Contains key operational data from the device dashboard endpoint.
Not frozen to allow for mutable updates from coordinator.
All fields are optional as the API response varies between AUTO and MANUAL mode.

Attributes:
    indoor_temperature: Current indoor temperature in °C
    outdoor_temperature: Current outdoor temperature in °C
    set_point_temperature: Target temperature in °C (manual mode only)
    exhaust_air_flow: Exhaust air flow in m³/h
    supply_air_flow: Supply air flow in m³/h
    fan_speed: Current fan speed level (0-3)
    season_profile: Season profile (0=comfort, 1=boost, 2=eco)
    temperature_profile: Temperature profile (0=comfort, 1=boost, 2=eco)
    season: Season mode (0=transition, 1=heating, 2=cooling)
    schedule: Schedule mode status
    status: Control mode (0=manual, 1=automatic)
    heat_pump_status: Heat pump operating status code
    hp_standby: Heat pump standby state (True=standby/off, False=active)
    free_cooling_enabled: Free cooling status
    caq_free_cooling_available: ComfoAirQ free cooling availability
    scenario: Active scenario mode (4=cooking, 5=party, 7=away, 8=boost, None=none)
    scenario_time_left: Remaining time in seconds for active scenario

Example:
    >>> # Parse from API response
    >>> data = DashboardData(
    ...     indoor_temperature=22.5,
    ...     outdoor_temperature=18.0,
    ...     fan_speed=2,
    ...     season=1,
    ...     status=1
    ... )
    >>> data.indoor_temperature
    22.5
    >>> data.is_heating_mode
    True
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `is_auto_mode` | sync | self | bool | 410 |
| `is_cooling_mode` | sync | self | bool | 400 |
| `is_heating_mode` | sync | self | bool | 395 |
| `is_manual_mode` | sync | self | bool | 405 |

#### Methoden-Details

##### `is_auto_mode(self)`

```
Check if system is in automatic temperature control mode.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 410

##### `is_cooling_mode(self)`

```
Check if system is in cooling mode.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 400

##### `is_heating_mode(self)`

```
Check if system is in heating mode.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 395

##### `is_manual_mode(self)`

```
Check if system is in manual temperature control mode.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 405


---

### Klasse: `DeviceConfig`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
Configuration for a connected device.

Immutable Pydantic model representing device configuration from API responses.

Attributes:
    uuid: Device unique identifier.
    model_type_id: Model type identifier (numeric).
    display_name: Human-readable device name.
    version: Optional firmware version.

Example:
    >>> config = DeviceConfig(
    ...     uuid="abc123",
    ...     model_type_id=1,
    ...     display_name="Heat Pump"
    ... )
    >>> config.uuid
    'abc123'
```


---

### Klasse: `PropertyReading`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
A property reading from a device.

Similar to TelemetryReading but for property-based data access.

Attributes:
    device_uuid: UUID of the device.
    path: Property path (e.g., "29/1/10").
    raw_value: Raw integer value from device.
    faktor: Multiplicative scaling factor.
    signed: Whether the value is signed.
    byte_count: Number of bytes (1 or 2).

Example:
    >>> prop = PropertyReading(
    ...     device_uuid="abc123",
    ...     path="29/1/10",
    ...     raw_value=123,
    ...     faktor=1.0
    ... )
    >>> prop.scaled_value
    123.0
```

**Methoden:** 1

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `scaled_value` | sync | self | float | 248 |

#### Methoden-Details

##### `scaled_value(self)`

```
Calculate the scaled value.

Applies signed interpretation and scaling factor.
Uses the bytes_to_signed_int utility function for proper conversion.

Returns:
    The scaled property value.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 248


---

### Klasse: `TelemetryReading`

**Erbt von:** `BaseModel`

**Beschreibung:**
```
A single telemetry reading from a device.

Represents a telemetry value with its metadata for scaling and interpretation.

Attributes:
    device_uuid: UUID of the device providing the reading.
    telemetry_id: Telemetry identifier (path or ID).
    raw_value: Raw integer value from device.
    faktor: Multiplicative scaling factor (must be > 0).
    signed: Whether the value should be interpreted as signed.
    byte_count: Number of bytes in the value (1 or 2).

Example:
    >>> reading = TelemetryReading(
    ...     device_uuid="abc123",
    ...     telemetry_id="10",
    ...     raw_value=250,
    ...     faktor=0.1
    ... )
    >>> reading.scaled_value
    25.0
```

**Methoden:** 1

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `scaled_value` | sync | self | float | 198 |

#### Methoden-Details

##### `scaled_value(self)`

```
Calculate the scaled value.

Applies signed interpretation (if needed) and scaling factor.
Uses the bytes_to_signed_int utility function for proper conversion.

Returns:
    The scaled telemetry value.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 198


---

## comfoclime.number

**Dateipfad:** `custom_components/comfoclime/number.py`

### Klasse: `ComfoClimePropertyNumber`

**Erbt von:** `CoordinatorEntity, NumberEntity`

**Beschreibung:**
```
Number entity for property values using coordinator for batched fetching.
```

**Methoden:** 6

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+4) | <ast.Constant object at 0x7f59efac4950> | 258 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efaccbd0> | 317 |
| `async_set_native_value` | async | self, value | <ast.Constant object at 0x7f59efb04750> | 328 |
| `device_info` | sync | self | None | 305 |
| `name` | sync | self | None | 297 |
| `native_value` | sync | self | None | 301 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, config, device, entry)`

**Typ:** sync

**Zeile:** 258

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 317

##### `async_set_native_value(self, value)`

**Typ:** async

**Zeile:** 328

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 305

##### `name(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 297

##### `native_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 301


---

### Klasse: `ComfoClimeTemperatureNumber`

**Erbt von:** `CoordinatorEntity, NumberEntity`

**Methoden:** 10

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+4) | <ast.Constant object at 0x7f59efb23990> | 99 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efb35dd0> | 191 |
| `async_set_native_value` | async | self, value | <ast.Constant object at 0x7f59efbda710> | 203 |
| `available` | sync | self | None | 125 |
| `device_info` | sync | self | DeviceInfo | 175 |
| `native_max_value` | sync | self | None | 167 |
| `native_min_value` | sync | self | None | 163 |
| `native_step` | sync | self | None | 171 |
| `native_unit_of_measurement` | sync | self | None | 159 |
| `native_value` | sync | self | None | 155 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, conf, device, entry)`

**Typ:** sync

**Zeile:** 99

##### `_handle_coordinator_update(self)`

**Typ:** sync

**Zeile:** 191

##### `async_set_native_value(self, value)`

**Typ:** async

**Zeile:** 203

##### `available(self)`

```
Return True if entity is available.

First checks if coordinator update was successful, then applies
business logic for manual temperature entities.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 125

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 175

##### `native_max_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 167

##### `native_min_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 163

##### `native_step(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 171

##### `native_unit_of_measurement(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 159

##### `native_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 155


---

## comfoclime.rate_limiter_cache

**Dateipfad:** `custom_components/comfoclime/rate_limiter_cache.py`

### Klasse: `RateLimiterCache`

**Beschreibung:**
```
Manages rate limiting and caching for API requests.

This class provides:
- Rate limiting to prevent overwhelming the API
- Write priority mechanism to ensure writes always succeed before reads
- Write cooldown to ensure reads after writes are stable
- Request debouncing to prevent rapid successive calls
- TTL-based caching for telemetry and property reads

Attributes:
    min_request_interval: Minimum seconds between any requests
    write_cooldown: Seconds to wait after write before allowing reads
    request_debounce: Debounce time for rapid successive requests
    cache_ttl: Cache time-to-live in seconds (0 = disabled)
```

**Methoden:** 16

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, min_request_interval, write_cooldown, ... (+2) | None | 44 |
| `_get_current_time` | sync | self | float | 81 |
| `_is_cache_valid` | sync | self, timestamp | bool | 230 |
| `clear_all_caches` | sync | self | <ast.Constant object at 0x7f59efb37d90> | 327 |
| `debounced_request` | async | self, key, coro_factory, ... (+1) | None | 177 |
| `get_cache_key` | sync | device_uuid, data_id | str | 218 |
| `get_property_from_cache` | sync | self, cache_key | None | 278 |
| `get_telemetry_from_cache` | sync | self, cache_key | None | 247 |
| `has_pending_writes` | sync | self | bool | 106 |
| `invalidate_cache_for_device` | sync | self, device_uuid | <ast.Constant object at 0x7f59efb36f90> | 309 |
| `set_property_cache` | sync | self, cache_key, value | <ast.Constant object at 0x7f59efb34950> | 296 |
| `set_telemetry_cache` | sync | self, cache_key, value | <ast.Constant object at 0x7f59efb2e210> | 265 |
| `signal_write_complete` | sync | self | <ast.Constant object at 0x7f59efb196d0> | 98 |
| `signal_write_pending` | sync | self | <ast.Constant object at 0x7f59efb1a590> | 89 |
| `wait_for_rate_limit` | async | self, is_write | <ast.Constant object at 0x7f59efb07950> | 134 |
| `yield_to_writes` | async | self, max_wait | <ast.Constant object at 0x7f59efb0bad0> | 114 |

#### Methoden-Details

##### `__init__(self, min_request_interval, write_cooldown, request_debounce, cache_ttl)`

```
Initialize the RateLimiterCache.

Args:
    min_request_interval: Minimum seconds between any requests
    write_cooldown: Seconds to wait after write before allowing reads
    request_debounce: Debounce time for rapid successive requests
    cache_ttl: Cache time-to-live in seconds (0 = disabled)
```

**Typ:** sync

**Zeile:** 44

##### `_get_current_time(self)`

```
Get current monotonic time for rate limiting.
```

**Typ:** sync

**Zeile:** 81

##### `_is_cache_valid(self, timestamp)`

```
Check if a cached value is still valid.

Args:
    timestamp: Timestamp when the value was cached

Returns:
    True if cache is still valid, False otherwise
```

**Typ:** sync

**Zeile:** 230

##### `clear_all_caches(self)`

```
Clear all cached values.
```

**Typ:** sync

**Zeile:** 327

##### `debounced_request(self, key, coro_factory, debounce_time)`

```
Execute a request with debouncing to prevent rapid successive calls.

If the same request (identified by key) is called again within debounce_time,
the previous pending request is cancelled and a new one is scheduled.

Args:
    key: Unique identifier for this request type
    coro_factory: Callable that returns the coroutine to execute
    debounce_time: Time to wait before executing (allows cancellation)

Returns:
    Result of the request
```

**Typ:** async

**Zeile:** 177

##### `get_cache_key(device_uuid, data_id)`

```
Generate a cache key from device UUID and data ID.

Args:
    device_uuid: UUID of the device
    data_id: Telemetry ID or property path

Returns:
    Cache key string
```

**Decorators:** `staticmethod`

**Typ:** sync

**Zeile:** 218

##### `get_property_from_cache(self, cache_key)`

```
Get a property value from cache if it's still valid.

Args:
    cache_key: Cache key (use get_cache_key to generate)

Returns:
    Cached value or None if not found/expired
```

**Typ:** sync

**Zeile:** 278

##### `get_telemetry_from_cache(self, cache_key)`

```
Get a telemetry value from cache if it's still valid.

Args:
    cache_key: Cache key (use get_cache_key to generate)

Returns:
    Cached value or None if not found/expired
```

**Typ:** sync

**Zeile:** 247

##### `has_pending_writes(self)`

```
Check if there are pending write operations.

Returns:
    True if there are write operations waiting to be processed.
```

**Typ:** sync

**Zeile:** 106

##### `invalidate_cache_for_device(self, device_uuid)`

```
Invalidate all cache entries for a specific device.

Args:
    device_uuid: UUID of the device
```

**Typ:** sync

**Zeile:** 309

##### `set_property_cache(self, cache_key, value)`

```
Store a property value in cache with current timestamp.

Args:
    cache_key: Cache key (use get_cache_key to generate)
    value: Value to cache
```

**Typ:** sync

**Zeile:** 296

##### `set_telemetry_cache(self, cache_key, value)`

```
Store a telemetry value in cache with current timestamp.

Args:
    cache_key: Cache key (use get_cache_key to generate)
    value: Value to cache
```

**Typ:** sync

**Zeile:** 265

##### `signal_write_complete(self)`

```
Signal that a write operation has completed.

This should be called after a write operation is done.
```

**Typ:** sync

**Zeile:** 98

##### `signal_write_pending(self)`

```
Signal that a write operation is pending.

This should be called before acquiring the lock for a write operation.
Read operations will check this flag and yield priority to writes.
```

**Typ:** sync

**Zeile:** 89

##### `wait_for_rate_limit(self, is_write)`

```
Wait if necessary to respect rate limits.

For write operations: Only applies minimum request interval.
For read operations: Also waits for write cooldown period.

Write operations have priority - they skip write cooldown checks.

Args:
    is_write: True if this is a write operation (will set cooldown after)
```

**Typ:** async

**Zeile:** 134

##### `yield_to_writes(self, max_wait)`

```
Yield to pending write operations.

Read operations call this to allow pending writes to proceed first.
This ensures writes always have priority over reads.

Args:
    max_wait: Maximum time to wait for writes in seconds (default: 0.5)
```

**Typ:** async

**Zeile:** 114


---

## comfoclime.select

**Dateipfad:** `custom_components/comfoclime/select.py`

### Klasse: `ComfoClimePropertySelect`

**Erbt von:** `CoordinatorEntity, SelectEntity`

**Beschreibung:**
```
Select entity for property values using coordinator for batched fetching.
```

**Methoden:** 6

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+4) | <ast.Constant object at 0x7f59efae0790> | 203 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efae8d50> | 249 |
| `async_select_option` | async | self, option | <ast.Constant object at 0x7f59efaeb910> | 258 |
| `current_option` | sync | self | None | 232 |
| `device_info` | sync | self | DeviceInfo | 236 |
| `options` | sync | self | None | 228 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, conf, device, entry)`

**Typ:** sync

**Zeile:** 203

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 249

##### `async_select_option(self, option)`

```
Select an option via the API.
```

**Typ:** async

**Zeile:** 258

##### `current_option(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 232

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 236

##### `options(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 228


---

### Klasse: `ComfoClimeSelect`

**Erbt von:** `CoordinatorEntity, SelectEntity`

**Methoden:** 6

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+4) | <ast.Constant object at 0x7f59efb05610> | 97 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efb1de90> | 143 |
| `async_select_option` | async | self, option | None | 154 |
| `current_option` | sync | self | None | 127 |
| `device_info` | sync | self | DeviceInfo | 131 |
| `options` | sync | self | None | 123 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, conf, device, entry)`

**Typ:** sync

**Zeile:** 97

##### `_handle_coordinator_update(self)`

**Typ:** sync

**Zeile:** 143

##### `async_select_option(self, option)`

**Typ:** async

**Zeile:** 154

##### `current_option(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 127

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 131

##### `options(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 123


---

## comfoclime.sensor

**Dateipfad:** `custom_components/comfoclime/sensor.py`

### Klasse: `ComfoClimeAccessTrackingSensor`

**Erbt von:** `SensorEntity`

**Beschreibung:**
```
Sensor for tracking API access patterns per coordinator.

These sensors expose the number of API accesses per minute and per hour
for each coordinator, helping users monitor and optimize API access patterns.
```

**Methoden:** 6

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, access_tracker, ... (+4) | <ast.Constant object at 0x7f59efaae4d0> | 748 |
| `async_update` | async | self | <ast.Constant object at 0x7f59efac4250> | 827 |
| `device_info` | sync | self | DeviceInfo | 809 |
| `extra_state_attributes` | sync | self | None | 845 |
| `native_value` | sync | self | None | 804 |
| `should_poll` | sync | self | bool | 823 |

#### Methoden-Details

##### `__init__(self, hass, access_tracker, coordinator_name, metric, name, translation_key)`

```
Initialize the access tracking sensor.

Args:
    hass: Home Assistant instance.
    access_tracker: The AccessTracker instance to get data from.
    coordinator_name: Name of the coordinator to track, or None for totals.
    metric: The metric type (per_minute, per_hour, total_per_minute, total_per_hour).
    name: Human-readable name for the sensor.
    translation_key: Translation key for localization.
    state_class: Sensor state class.
    entity_category: Entity category (e.g., diagnostic).
    device: Device information dict.
    entry: Config entry.
```

**Typ:** sync

**Zeile:** 748

##### `async_update(self)`

```
Update the sensor state from the access tracker.
```

**Typ:** async

**Zeile:** 827

##### `device_info(self)`

```
Return device info for this sensor.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 809

##### `extra_state_attributes(self)`

```
Return additional attributes with detailed access information.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 845

##### `native_value(self)`

```
Return the current value of the sensor.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 804

##### `should_poll(self)`

```
Return True as we need to poll to get updated access counts.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 823


---

### Klasse: `ComfoClimeDefinitionSensor`

**Erbt von:** `CoordinatorEntity, SensorEntity`

**Beschreibung:**
```
Sensor for definition data using coordinator for batched fetching.
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+3) | <ast.Constant object at 0x7f59efa98e10> | 675 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efaa0f50> | 727 |
| `device_info` | sync | self | DeviceInfo | 715 |
| `native_value` | sync | self | None | 711 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, key, name, translation_key)`

**Typ:** sync

**Zeile:** 675

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 727

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 715

##### `native_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 711


---

### Klasse: `ComfoClimePropertySensor`

**Erbt von:** `CoordinatorEntity, SensorEntity`

**Beschreibung:**
```
Sensor for property data using coordinator for batched fetching.
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+3) | <ast.Constant object at 0x7f59efa76f90> | 598 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efa83710> | 658 |
| `device_info` | sync | self | DeviceInfo | 646 |
| `native_value` | sync | self | None | 642 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, path, name, translation_key)`

**Typ:** sync

**Zeile:** 598

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 658

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 646

##### `native_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 642


---

### Klasse: `ComfoClimeSensor`

**Erbt von:** `CoordinatorEntity, SensorEntity`

**Methoden:** 5

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+10) | <ast.Constant object at 0x7f59efa31c90> | 403 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efa1e010> | 471 |
| `device_info` | sync | self | DeviceInfo | 459 |
| `extra_state_attributes` | sync | self | None | 454 |
| `state` | sync | self | None | 450 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, sensor_type, name, translation_key, unit, device_class, state_class, entity_category, device, entry)`

**Typ:** sync

**Zeile:** 403

##### `_handle_coordinator_update(self)`

**Typ:** sync

**Zeile:** 471

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 459

##### `extra_state_attributes(self)`

```
Gibt zusätzliche Attribute zurück.
```

**Decorators:** `property`

**Typ:** sync

**Zeile:** 454

##### `state(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 450


---

### Klasse: `ComfoClimeTelemetrySensor`

**Erbt von:** `CoordinatorEntity, SensorEntity`

**Beschreibung:**
```
Sensor for telemetry data using coordinator for batched fetching.
```

**Methoden:** 4

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+14) | <ast.Constant object at 0x7f59efa60ad0> | 523 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efa68750> | 584 |
| `device_info` | sync | self | DeviceInfo | 571 |
| `native_value` | sync | self | None | 567 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, telemetry_id, name, translation_key, unit, faktor, signed, byte_count, device_class, state_class, entity_category, device, override_device_uuid, entry, entity_registry_enabled_default)`

**Typ:** sync

**Zeile:** 523

##### `_handle_coordinator_update(self)`

```
Handle updated data from the coordinator.
```

**Decorators:** `callback`

**Typ:** sync

**Zeile:** 584

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 571

##### `native_value(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 567


---

## comfoclime.switch

**Dateipfad:** `custom_components/comfoclime/switch.py`

### Klasse: `ComfoClimeSwitch`

**Erbt von:** `CoordinatorEntity, SwitchEntity`

**Beschreibung:**
```
Unified switch entity for ComfoClime integration.

Supports switches from both thermal profile and dashboard endpoints.
Can optionally invert the state logic.
```

**Methoden:** 9

| Methode | Typ | Args | Return | Zeile |
|---------|-----|------|--------|-------|
| `__init__` | sync | self, hass, coordinator, ... (+8) | <ast.Constant object at 0x7f59efb1c950> | 78 |
| `_async_set_status` | async | self, value | <ast.Constant object at 0x7f59efb09010> | 178 |
| `_handle_coordinator_update` | sync | self | <ast.Constant object at 0x7f59efb05090> | 141 |
| `_set_dashboard_status` | async | self, value | <ast.Constant object at 0x7f59efb1b210> | 212 |
| `_set_thermal_profile_status` | async | self, value | <ast.Constant object at 0x7f59efb19450> | 193 |
| `async_turn_off` | async | self | <ast.Constant object at 0x7f59efb07a50> | 171 |
| `async_turn_on` | async | self | <ast.Constant object at 0x7f59efb05f50> | 164 |
| `device_info` | sync | self | DeviceInfo | 129 |
| `is_on` | sync | self | None | 125 |

#### Methoden-Details

##### `__init__(self, hass, coordinator, api, key, translation_key, name, invert, endpoint, device, entry)`

```
Initialize the switch entity.

Args:
    hass: Home Assistant instance
    coordinator: Data coordinator (ThermalProfile or Dashboard)
    api: ComfoClime API instance
    key: Switch configuration key
    translation_key: i18n translation key
    name: Display name
    invert: If True, invert the state logic (e.g., for hpstandby)
    endpoint: Either 'thermal_profile' or 'dashboard'
    device: Device information
    entry: Config entry
```

**Typ:** sync

**Zeile:** 78

##### `_async_set_status(self, value)`

```
Set the switch status.

Args:
    value: Integer value (0 or 1)
```

**Typ:** async

**Zeile:** 178

##### `_handle_coordinator_update(self)`

```
Update the state from coordinator data.
```

**Typ:** sync

**Zeile:** 141

##### `_set_dashboard_status(self, value)`

```
Set dashboard switch status via API.
```

**Typ:** async

**Zeile:** 212

##### `_set_thermal_profile_status(self, value)`

```
Set thermal profile switch status via API.
```

**Typ:** async

**Zeile:** 193

##### `async_turn_off(self)`

```
Turn the switch off.
```

**Typ:** async

**Zeile:** 171

##### `async_turn_on(self)`

```
Turn the switch on.
```

**Typ:** async

**Zeile:** 164

##### `device_info(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 129

##### `is_on(self)`

**Decorators:** `property`

**Typ:** sync

**Zeile:** 125


---

