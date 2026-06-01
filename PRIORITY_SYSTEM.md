# Priority-Based Sensor Polling System

## Overview

The ComfoClime integration implements a priority-based polling system to optimize API communication with the ComfoClime/ComfoAirQ devices. This system allows for dynamic configuration of polling intervals based on sensor importance, reducing device communication load and preventing communication breakdowns during extended operation.

## Priority Levels

Each sensor is assigned one of four priority levels that determine its polling frequency:

### HIGH Priority
**Default Interval: 5-15 seconds**

Critical real-time data that requires frequent updates for proper system operation and user monitoring.

**Examples:**
- Indoor/Outdoor/Supply Air Temperatures
- Fan Speed and Status
- Heat Pump Status
- Device Operating Mode
- Active Scenario Mode and Time Remaining
- Power Consumption (real-time)

### MEDIUM Priority
**Default Interval: 30-60 seconds**

Important monitoring data that changes regularly but doesn't require real-time precision.

**Examples:**
- Air Flow Rates (Exhaust/Supply)
- Temperature Profile Settings
- Season Mode
- Humidity Levels
- Pressure Readings (High/Low)
- Free Cooling Status

### LOW Priority
**Default Interval: 120-300 seconds**

Configuration data and slowly changing metrics that don't need frequent polling.

**Examples:**
- Season Profile Settings
- Thermal Configuration Temperatures
- Schedule Status
- Energy Totals (cumulative)
- Filter Days Remaining
- Heat Pump Configuration Parameters (min/max temps, hysteresis)

### VERY_LOW Priority
**Default Interval: 600+ seconds**

Rarely changing data, primarily diagnostic and statistical information.

**Examples:**
- Device Uptime
- API Access Statistics (per minute/hour counters)
- Version Information

## Sensor Category Priority Assignments

### Dashboard Sensors (17 total)
- **HIGH (8)**: indoorTemperature, outdoorTemperature, setPointTemperature, fanSpeed, status, heatPumpStatus, scenarioTimeLeft, scenario
- **MEDIUM (7)**: exhaustAirFlow, supplyAirFlow, temperatureProfile, season, hpStandby, freeCoolingEnabled, caqFreeCoolingAvailable
- **LOW (2)**: seasonProfile, schedule

### Thermal Profile Sensors (13 total)
- **MEDIUM (2)**: season.season, temperature.manualTemperature
- **LOW (11)**: All configuration temperatures and thresholds

### Monitoring Sensors (1 total)
- **VERY_LOW (1)**: up_time_seconds

### Connected Device Telemetry Sensors
#### ComfoClime (Model 20 - 18 total)
- **HIGH (11)**: All temperature sensors (supply, TPMA, comfort, indoor, exhaust, coils, compressor), device_mode, power_heatpump
- **MEDIUM (2)**: powerfactor_heatpump, pressures
- **LOW (5)**: All diagnostic sensors (expansion valve, 4-way valve, HP diagnostics)

#### ComfoAirQ (Model 1 - 16 total)
- **HIGH (9)**: All temperature sensors, fan duty/speed, power_ventilation
- **MEDIUM (5)**: Humidity sensors (4), bypass_state, RMOT temperature
- **LOW (2)**: energy_ytd, energy_total, filter_days_remaining

### Connected Device Property Sensors
- **LOW (8)**: All heat pump configuration parameters (temperature limits, hysteresis, max power)

### Connected Device Definition Sensors (5 total)
- **HIGH (5)**: All temperature sensors (ComfoAirQ definition endpoint)

### Access Tracking Sensors (14 total)
- **VERY_LOW (14)**: All API access counters

## Implementation Status

### ✅ Completed
1. **Priority Field Addition**
   - Added `SensorPriority` enum to `base_definitions.py`
   - Added `priority` field to `EntityDefinitionBase` (default: MEDIUM)
   - All sensor definitions updated with appropriate priorities
   - All existing tests pass

### 🔄 In Progress
2. **Documentation**
   - This priority system documentation

### ⏳ Remaining Tasks
3. **Coordinator Priority Implementation**
   - Modify coordinators to accept priority-based update intervals
   - Implement separate coordinator instances or dynamic intervals based on sensor priorities

4. **Config Flow Integration**
   - Add UI options to configure polling intervals per priority level
   - Add preset modes (Conservative/Balanced/Aggressive)
   - Store priority interval configuration in entry options

5. **Testing**
   - Add tests for priority field validation
   - Add tests for coordinator priority-based polling
   - Add tests for config flow priority options

6. **Documentation Updates**
   - Update README with priority system explanation
   - Add migration guide for existing installations

## Benefits

1. **Reduced Device Load**: Less frequent polling of low-priority data reduces overall API requests
2. **Improved Reliability**: Lower communication frequency prevents device overload and connection drops
3. **Customizable**: Users can adjust intervals per priority level based on their needs
4. **Better Battery Life**: For devices with battery backup, reduced polling extends battery runtime
5. **Network Optimization**: Less network traffic in IoT environments

## Configuration Example (Future)

```yaml
# Example future configuration in Home Assistant UI
priority_intervals:
  high: 10        # Poll HIGH priority sensors every 10 seconds
  medium: 60      # Poll MEDIUM priority sensors every 60 seconds
  low: 300        # Poll LOW priority sensors every 5 minutes
  very_low: 600   # Poll VERY_LOW priority sensors every 10 minutes
```

## Sensor Visibility

All sensors defined in the `*_definitions.py` files are registered with Home Assistant and should be visible, subject to:

1. **Entity Enablement**: Sensors can be individually enabled/disabled through the config flow options
2. **Category Enablement**: Entire categories can be enabled/disabled (dashboard, thermalprofile, etc.)
3. **Diagnostic Entities**: Entities with `entity_category="diagnostic"` are registered but may be hidden by default in the HA UI (can be shown via UI settings)

### Ensuring Sensor Visibility

If a sensor is not visible in Home Assistant:

1. Check if the entity category is enabled in integration options
2. For diagnostic entities (like `caqFreeCoolingAvailable`), ensure diagnostic entities are shown in HA UI
3. Verify the sensor is enabled in the individual entity options
4. Check integration logs for any errors during sensor setup

### Example: caqFreeCoolingAvailable Sensor

```python
SensorDefinition(
    key="caqFreeCoolingAvailable",
    name="ComfoAirQ Free Cooling Available",
    translation_key="caq_free_cooling_available",
    entity_category="diagnostic",  # Diagnostic category - may be hidden by default in UI
    priority=SensorPriority.MEDIUM,  # Polled every ~60 seconds (when implemented)
)
```

This sensor is:
- ✅ Properly defined in DASHBOARD_SENSORS
- ✅ Mapped to DashboardData model field (`caq_free_cooling_available`)
- ✅ Assigned MEDIUM priority for reasonable update frequency
- ⚠️ Marked as `diagnostic` - may be hidden in HA UI by default (user can enable via UI settings)

## Related Files

- `custom_components/comfoclime/entities/base_definitions.py` - SensorPriority enum
- `custom_components/comfoclime/entities/sensor_definitions.py` - Sensor priority assignments
- `custom_components/comfoclime/coordinator.py` - Coordinator implementation (to be updated)
- `custom_components/comfoclime/config_flow.py` - Config flow UI (to be updated)

## References

- Inspired by [marstek_venus_modbus](https://github.com/viperrnmc/marstek_venus_modbus) integration
- Home Assistant Coordinator documentation: https://developers.home-assistant.io/docs/integration_fetching_data
