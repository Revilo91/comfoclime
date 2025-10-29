# Climate Sensor Attributes

## Overview

The ComfoClime Climate sensor now exposes all interface data from the ComfoClime API as attributes. This allows you to access any API value directly from the Climate entity in Home Assistant automations and templates.

## Attribute Structure

The Climate entity (`climate.comfoclime`) provides three main attribute groups:

### 1. `dashboard`
Complete raw data from the `/system/{UUID}/dashboard` API endpoint.

**Available fields:**
- `indoorTemperature` - Indoor temperature (°C)
- `outdoorTemperature` - Outdoor temperature (°C)
- `exhaustAirFlow` - Exhaust air flow (m³/h)
- `supplyAirFlow` - Supply air flow (m³/h)
- `fanSpeed` - Current fan speed (0-3: auto, low, medium, high)
- `temperatureProfile` - Temperature profile (0: comfort, 1: power, 2: eco)
- `seasonProfile` - Season profile setting
- `season` - Current season (0: transitional, 1: heating, 2: cooling)
- `schedule` - Schedule status
- `status` - Overall system status
- `heatPumpStatus` - Heat pump status (0: off, 1: starting, 3: heating, 5: cooling)
- `hpStandby` - Heat pump standby state (true/false)
- `freeCoolingEnabled` - Free cooling enabled (true/false)
- `setPointTemperature` - Manual set point temperature (°C)
- And all other fields returned by the dashboard API

### 2. `thermal_profile`
Complete raw data from the `/system/{UUID}/thermalprofile` API endpoint.

**Available sections:**
- `season` - Season configuration
  - `status` - Automatic season mode (0: manual, 1: automatic)
  - `season` - Current season (0: transitional, 1: heating, 2: cooling)
  - `heatingThresholdTemperature` - Threshold for heating season
  - `coolingThresholdTemperature` - Threshold for cooling season
  
- `temperature` - Temperature configuration
  - `status` - Automatic temperature mode (0: manual, 1: automatic)
  - `manualTemperature` - Manual temperature setting
  
- `temperatureProfile` - Active temperature profile (0: comfort, 1: power, 2: eco)

- `heatingThermalProfileSeasonData` - Heating season settings
  - `comfortTemperature` - Comfort temperature for heating
  - `kneePointTemperature` - Knee point temperature
  - `reductionDeltaTemperature` - Temperature reduction delta
  
- `coolingThermalProfileSeasonData` - Cooling season settings
  - `comfortTemperature` - Comfort temperature for cooling
  - `kneePointTemperature` - Knee point temperature
  - `temperatureLimit` - Maximum temperature limit

### 3. `calculated`
Convenience values derived from the raw data for easier access.

**Available values:**
- `season_season` - Current season value
- `season_status` - Season mode (automatic/manual)
- `temperature_status` - Temperature mode status
- `temperature_profile` - Active temperature profile
- `hvac_mode` - Current HVAC mode (as string)
- `preset_mode` - Current preset mode
- `temperature_mode` - "automatic" or "manual"

## Usage Examples

### In Templates

Access dashboard data:
```yaml
{{ state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] }}
{{ state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] }}
{{ state_attr('climate.comfoclime', 'dashboard')['freeCoolingEnabled'] }}
```

Access thermal profile data:
```yaml
{{ state_attr('climate.comfoclime', 'thermal_profile')['heatingThermalProfileSeasonData']['comfortTemperature'] }}
{{ state_attr('climate.comfoclime', 'thermal_profile')['season']['status'] }}
```

Access calculated values:
```yaml
{{ state_attr('climate.comfoclime', 'calculated')['hvac_mode'] }}
{{ state_attr('climate.comfoclime', 'calculated')['temperature_mode'] }}
```

### In Automations

```yaml
automation:
  - alias: "Low Outdoor Temperature Alert"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] < 5 }}
    action:
      - service: notify.mobile_app
        data:
          message: "Outdoor temperature is below 5°C!"

  - alias: "Heat Pump Status Monitor"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] }}
    action:
      - service: persistent_notification.create
        data:
          title: "Heat Pump Status Changed"
          message: >
            Heat Pump Status: {{ state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] }}
```

### As Template Sensors

```yaml
template:
  - sensor:
      - name: "ComfoClime Outdoor Temperature"
        unit_of_measurement: "°C"
        device_class: temperature
        state: >
          {{ state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] }}
      
      - name: "ComfoClime Air Flow"
        unit_of_measurement: "m³/h"
        state: >
          {{ state_attr('climate.comfoclime', 'dashboard')['supplyAirFlow'] }}
      
      - name: "ComfoClime Season"
        state: >
          {% set season = state_attr('climate.comfoclime', 'dashboard')['season'] %}
          {% set seasons = {0: 'Transitional', 1: 'Heating', 2: 'Cooling'} %}
          {{ seasons.get(season, 'Unknown') }}
```

## Benefits

1. **Complete API Access**: All data from the ComfoClime device is accessible
2. **No Extra Entities Needed**: All data available through one Climate entity
3. **Flexible Automations**: Create any automation based on any API value
4. **Easy Debugging**: See all raw API values for troubleshooting
5. **Backward Compatible**: Existing automations continue to work

## See Also

- `examples/climate_attributes_usage.py` - Comprehensive usage examples
- `test_climate_attributes.py` - Test coverage
- [ComfoClime API Documentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)

## Testing

Run the test to verify the attribute structure:
```bash
python3 test_climate_attributes.py
```

View usage examples:
```bash
python3 examples/climate_attributes_usage.py
```
