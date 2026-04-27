# ComfoClime Entity Strategy & Categorization

This document defines the entity categorization strategy for the ComfoClime Home Assistant integration, ensuring optimal user experience by properly classifying entities according to Home Assistant best practices.

## Entity Categories Overview

Home Assistant defines three entity categories:

| Category | `entity_category` | `entity_registry_enabled_default` | Purpose | UI Location |
|----------|------------------|-----------------------------------|---------|-------------|
| **Standard** | `None` | `True` | Core functionality entities that users interact with regularly | Main device card |
| **Configuration** | `"config"` | `False` (disabled by default) | Settings and configuration options | Configuration section |
| **Diagnostic** | `"diagnostic"` | `False` (disabled by default) | System status, debug info, telemetry | Diagnostic section |

## ComfoClime Entity Categories

### Standard Entities (Enabled by Default)

These entities are **always visible** and represent the core functionality of the ComfoClime system.

#### Climate
- `climate.comfoclime` - Climate control entity (main interface)

#### Fan
- `fan.fan_speed` - Fan speed control

#### Sensors (Standard)
- `sensor.indoor_temperature` - Indoor temperature
- `sensor.outdoor_temperature` - Outdoor temperature
- `sensor.set_point_temperature` - Target/set point temperature
- `sensor.exhaust_air_flow` - Exhaust air flow rate
- `sensor.supply_air_flow` - Supply air flow rate
- `sensor.fan_speed` - Current fan speed level
- `sensor.temperature_profile_status` - Active temperature profile
- `sensor.season` - Current season (heating/cooling/transitional)
- `sensor.heat_pump_status` - Heat pump operational status

#### Numbers (Standard)
- `number.heating_comfort_temperature` - Heating comfort temperature setpoint
- `number.cooling_comfort_temperature` - Cooling comfort temperature setpoint
- `number.manual_comfort_temperature` - Manual comfort temperature

#### Switches (Standard)
- `switch.automatic_season_detection` - Enable/disable automatic season switching
- `switch.automatic_comfort_temperature` - Enable/disable automatic comfort temp
- `switch.heatpump_onoff` - Heat pump on/off control

#### Selects (Standard)
- `select.temperature_profile` - Temperature profile selector (Comfort/Eco/Power)
- `select.season_mode` - Season mode selector

---

### Configuration Entities (Disabled by Default)

These entities are **disabled by default** but can be enabled for advanced configuration. They appear in the Configuration section of the device page.

#### Numbers (Configuration)
- `number.heating_knee_point` - Heating curve knee point
- `number.heating_reduction_delta` - Heating reduction delta temperature
- `number.heating_threshold` - Heating threshold temperature
- `number.cooling_knee_point` - Cooling curve knee point
- `number.cooling_threshold` - Cooling threshold temperature
- `number.cooling_temperature_limit` - Cooling temperature limit
- `number.rmot_heating_threshold` - Ventilation heating threshold (RMOT)
- `number.rmot_cooling_threshold` - Ventilation cooling threshold (RMOT)
- `number.heatpump_min_temp` - Heat pump minimum cooling temperature
- `number.heatpump_max_temp` - Heat pump maximum heating temperature

#### Selects (Configuration)
- `select.humidity_comfort_control` - Humidity control mode
- `select.humidity_protection` - Humidity protection mode

---

### Diagnostic Entities (Disabled by Default)

These entities are **disabled by default** and provide detailed system information for troubleshooting and monitoring. They appear in the Diagnostic section.

#### Sensors (Diagnostic - Dashboard)
- `sensor.season_profile` - Internal season profile value
- `sensor.schedule_status` - Active schedule name
- `sensor.dashboard_status` - Raw dashboard status field
- `sensor.device_power_status` - Device power/standby status
- `sensor.free_cooling_status` - Free cooling enabled/disabled
- `sensor.caq_free_cooling_available` - ComfoAirQ free cooling availability

#### Sensors (Diagnostic - Monitoring)
- `sensor.uptime` - Device uptime in seconds

#### Sensors (Diagnostic - Thermal Profile)
- `sensor.cooling_knee_point_temperature` - Cooling knee point value
- `sensor.cooling_threshold_temperature` - Cooling threshold value
- `sensor.heating_knee_point_temperature` - Heating knee point value
- `sensor.heating_reduction_delta_temperature` - Heating reduction delta value
- `sensor.heating_threshold_temperature` - Heating threshold value
- `sensor.thermal_manual_temperature` - Thermal manual temperature setting
- `sensor.thermal_season_mode` - Thermal season mode value
- `sensor.thermal_season_status` - Thermal season status
- `sensor.thermal_temperature_profile` - Thermal temperature profile setting
- `sensor.thermal_temperature_status` - Thermal temperature status

#### Sensors (Diagnostic - Telemetry)
All telemetry sensors for connected devices (ComfoClime, ComfoAir) are **diagnostic** by default:

**ComfoClime Telemetry (modelTypeId=20):**
- `sensor.tpma_temperature` - Mean outdoor temperature (TPMA)
- `sensor.comfo_clime_status` - ComfoClime operating mode
- `sensor.current_comfort_temperature` - Current comfort temperature
- `sensor.supply_air_temperature` - Supply air temperature
- `sensor.comfoclime_exhaust_temperature` - Exhaust temperature
- `sensor.supply_coil_temperature` - Supply coil (gas) temperature
- `sensor.exhaust_coil_temperature` - Exhaust coil (gas) temperature
- `sensor.compressor_temperature` - Compressor temperature
- `sensor.powerfactor_heatpump` - Heat pump power factor (%)
- `sensor.power_heatpump` - Heat pump power consumption (W)
- `sensor.high_pressure` - High pressure / hot side (kPa)
- `sensor.expansion_valve` - Expansion valve position (%)
- `sensor.low_pressure` - Low pressure / cold side (kPa)
- `sensor.four_way_valve_position` - Four-way valve position
- Unknown/experimental telemetry values (4198, 4204, 4206, 4208)

**ComfoAir Telemetry (modelTypeId=1):**
- `sensor.exhaust_fan_duty` - Exhaust fan duty cycle (%)
- `sensor.supply_fan_duty` - Supply fan duty cycle (%)
- `sensor.exhaust_fan_speed` - Exhaust fan speed (rpm)
- `sensor.supply_fan_speed` - Supply fan speed (rpm)
- `sensor.power_ventilation` - Ventilation power consumption (W)
- `sensor.energy_ytd` - Ventilation energy year-to-date (kWh)
- `sensor.energy_total` - Total ventilation energy (kWh)
- `sensor.bypass_state` - Bypass valve state (%)
- `sensor.temp_rmot` - Mean outdoor temperature for ventilation (RMOT)
- `sensor.extract_temperature` - Extract air temperature
- `sensor.exhaust_temperature` - Exhaust air temperature
- `sensor.supply_temperature` - Supply air temperature
- `sensor.extract_humidity` - Extract air humidity (%)
- `sensor.exhaust_humidity` - Exhaust air humidity (%)
- `sensor.outdoor_humidity` - Outdoor air humidity (%)
- `sensor.supply_humidity` - Supply air humidity (%)
- `sensor.ventilation_disbalance` - Ventilation imbalance

#### Sensors (Diagnostic - Access Tracking)
All access tracking sensors are **always diagnostic**:
- `sensor.dashboard_accesses_per_minute` - Dashboard API calls per minute
- `sensor.dashboard_accesses_per_hour` - Dashboard API calls per hour
- `sensor.thermalprofile_accesses_per_minute` - Thermal profile API calls per minute
- `sensor.thermalprofile_accesses_per_hour` - Thermal profile API calls per hour
- `sensor.telemetry_accesses_per_minute` - Telemetry API calls per minute
- `sensor.telemetry_accesses_per_hour` - Telemetry API calls per hour
- `sensor.property_accesses_per_minute` - Property API calls per minute
- `sensor.property_accesses_per_hour` - Property API calls per hour
- `sensor.definition_accesses_per_minute` - Definition API calls per minute
- `sensor.definition_accesses_per_hour` - Definition API calls per hour
- `sensor.monitoring_accesses_per_minute` - Monitoring API calls per minute
- `sensor.monitoring_accesses_per_hour` - Monitoring API calls per hour
- `sensor.total_api_accesses_per_minute` - Total API calls per minute
- `sensor.total_api_accesses_per_hour` - Total API calls per hour

---

## Implementation Guidelines

### For Developers

When adding new entities to the integration:

1. **Determine the entity category:**
   - Is it core functionality? → Standard (no `entity_category`, `entity_registry_enabled_default=True`)
   - Is it a configuration option? → Configuration (`entity_category="config"`, `entity_registry_enabled_default=False`)
   - Is it diagnostic/telemetry? → Diagnostic (`entity_category="diagnostic"`, `entity_registry_enabled_default=False`)

2. **Set the correct attributes in entity definition:**
   ```python
   SensorDefinition(
       key="my_sensor",
       name="My Sensor",
       translation_key="my_sensor",
       entity_category="diagnostic",  # or "config" or None for standard
       # ... other attributes
   )
   ```

3. **Handle in sensor creation:**
   ```python
   # In sensor.py async_setup_entry
   entity_registry_enabled_default = sensor_def.entity_category is None

   ComfoClimeSensor(
       # ... other params
       entity_category=sensor_def.entity_category,
       entity_registry_enabled_default=entity_registry_enabled_default,
   )
   ```

### For Users

**To enable disabled entities:**

1. Go to Settings → Devices & Services → ComfoClime
2. Click on your ComfoClime device
3. Scroll to "Configuration" or "Diagnostic" sections
4. Click on the disabled entity you want to enable
5. Click the gear icon → Enable entity

**Entity count expectations:**

- **Standard entities (always visible)**: ~20-30 entities
- **Configuration entities (optional)**: ~10-15 entities
- **Diagnostic entities (optional)**: ~60-80 entities

By default, users will see approximately **25 entities** that represent the core functionality of their ComfoClime system. Advanced users can enable diagnostic sensors for detailed monitoring and troubleshooting.

---

## Migration Notes

### From v2.0.x to v3.0.0

The v3.0.0 release implements proper entity categorization. Existing installations will:

1. **Retain all previously enabled entities** - No entities will be automatically disabled
2. **New entities will follow the new strategy** - Configuration and diagnostic entities disabled by default
3. **Users can manually disable diagnostic entities** if desired to reduce entity count

No action required from users during upgrade.

---

## Rationale

This categorization strategy is based on:

1. **Home Assistant Entity Guidelines**: Following official best practices for entity categorization
2. **User Experience**: Reducing clutter in the main UI while preserving access to advanced features
3. **API Load Optimization**: Diagnostic telemetry sensors can be disabled to reduce API load on the device
4. **Progressive Disclosure**: Users see essential features first, with advanced options available when needed

---

## References

- [Home Assistant Entity Categories](https://developers.home-assistant.io/docs/core/entity/#entity-categories)
- [Home Assistant Entity Registry](https://developers.home-assistant.io/docs/entity_registry_disabled_by/)
- [ComfoClime API Documentation](./ComfoClimeAPI.md)
- [Entity Definitions Summary](./ENTITY_DEFINITIONS_SUMMARY.md)
