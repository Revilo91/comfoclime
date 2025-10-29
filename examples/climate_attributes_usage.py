#!/usr/bin/env python3
"""
Integration test example for Climate entity attributes.

This shows how users can access all interface data through the Climate entity
in Home Assistant automations and templates.
"""

def print_usage_examples():
    """Print examples of how to use the Climate entity attributes."""
    
    print("="*80)
    print("ComfoClime Climate Entity - Attribute Access Examples")
    print("="*80)
    
    print("\n1. ACCESSING DASHBOARD DATA")
    print("-" * 80)
    print("All raw dashboard data from /system/{UUID}/dashboard is available under")
    print("the 'dashboard' attribute.\n")
    
    print("Example template sensors:")
    print("""
# Get outdoor temperature from dashboard
{% set outdoor_temp = state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] %}
{{ outdoor_temp }}°C

# Get exhaust air flow
{% set exhaust = state_attr('climate.comfoclime', 'dashboard')['exhaustAirFlow'] %}
{{ exhaust }} m³/h

# Get heat pump status
{% set hp_status = state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] %}
Heat Pump Status: {{ hp_status }}

# Check if free cooling is enabled
{% set free_cooling = state_attr('climate.comfoclime', 'dashboard')['freeCoolingEnabled'] %}
Free Cooling: {{ 'Yes' if free_cooling else 'No' }}
""")
    
    print("\n2. ACCESSING THERMAL PROFILE DATA")
    print("-" * 80)
    print("All thermal profile data from /system/{UUID}/thermalprofile is available")
    print("under the 'thermal_profile' attribute.\n")
    
    print("Example template sensors:")
    print("""
# Get heating comfort temperature
{% set heating = state_attr('climate.comfoclime', 'thermal_profile')['heatingThermalProfileSeasonData'] %}
{{ heating['comfortTemperature'] }}°C

# Get cooling comfort temperature
{% set cooling = state_attr('climate.comfoclime', 'thermal_profile')['coolingThermalProfileSeasonData'] %}
{{ cooling['comfortTemperature'] }}°C

# Get season status (automatic/manual)
{% set season = state_attr('climate.comfoclime', 'thermal_profile')['season'] %}
Season Mode: {{ 'Automatic' if season['status'] == 1 else 'Manual' }}
Current Season: {{ ['Transitional', 'Heating', 'Cooling'][season['season']] }}

# Get temperature mode
{% set temp = state_attr('climate.comfoclime', 'thermal_profile')['temperature'] %}
Temperature Mode: {{ 'Automatic' if temp['status'] == 1 else 'Manual' }}
Manual Temperature: {{ temp['manualTemperature'] }}°C
""")
    
    print("\n3. ACCESSING CALCULATED VALUES")
    print("-" * 80)
    print("Convenience values calculated from the raw data are available under")
    print("the 'calculated' attribute.\n")
    
    print("Example template sensors:")
    print("""
# Get current HVAC mode
{% set calc = state_attr('climate.comfoclime', 'calculated') %}
HVAC Mode: {{ calc['hvac_mode'] }}
Preset Mode: {{ calc['preset_mode'] }}
Temperature Mode: {{ calc['temperature_mode'] }}

# Get season information
Season: {{ calc['season_season'] }}
Season Status: {{ calc['season_status'] }}
""")
    
    print("\n4. AUTOMATION EXAMPLES")
    print("-" * 80)
    print("Use the attributes in Home Assistant automations:\n")
    
    print("""
# Example 1: Notify when heat pump status changes
automation:
  - alias: "ComfoClime Heat Pump Status Changed"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] }}
    action:
      - service: notify.mobile_app
        data:
          message: >
            Heat Pump Status: {{ state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] }}

# Example 2: Alert if outdoor temperature is below threshold
automation:
  - alias: "ComfoClime Low Outdoor Temperature"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] < 5 }}
    action:
      - service: notify.mobile_app
        data:
          message: "Outdoor temperature is below 5°C!"

# Example 3: Monitor air flow
automation:
  - alias: "ComfoClime Low Air Flow Warning"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('climate.comfoclime', 'dashboard')['supplyAirFlow'] < 300 }}
    action:
      - service: persistent_notification.create
        data:
          title: "Low Air Flow"
          message: "Supply air flow is below 300 m³/h"
""")
    
    print("\n5. TEMPLATE SENSOR EXAMPLES")
    print("-" * 80)
    print("Create template sensors from the attributes:\n")
    
    print("""
# configuration.yaml
template:
  - sensor:
      - name: "ComfoClime Outdoor Temperature"
        unit_of_measurement: "°C"
        state: >
          {{ state_attr('climate.comfoclime', 'dashboard')['outdoorTemperature'] }}
        device_class: temperature
      
      - name: "ComfoClime Exhaust Air Flow"
        unit_of_measurement: "m³/h"
        state: >
          {{ state_attr('climate.comfoclime', 'dashboard')['exhaustAirFlow'] }}
      
      - name: "ComfoClime Supply Air Flow"
        unit_of_measurement: "m³/h"
        state: >
          {{ state_attr('climate.comfoclime', 'dashboard')['supplyAirFlow'] }}
      
      - name: "ComfoClime Heat Pump Status"
        state: >
          {% set status = state_attr('climate.comfoclime', 'dashboard')['heatPumpStatus'] %}
          {# Heat pump status codes: 0=Off, 1=Starting, 3=Heating, 5=Cooling #}
          {# See https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md #}
          {% set statuses = {0: 'Off', 1: 'Starting', 3: 'Heating', 5: 'Cooling'} %}
          {{ statuses.get(status, 'Unknown') }}
      
      - name: "ComfoClime Season"
        state: >
          {% set season = state_attr('climate.comfoclime', 'dashboard')['season'] %}
          {# Season codes: 0=Transitional, 1=Heating, 2=Cooling #}
          {% set seasons = {0: 'Transitional', 1: 'Heating', 2: 'Cooling'} %}
          {{ seasons.get(season, 'Unknown') }}
      
      - name: "ComfoClime Heating Comfort Temperature"
        unit_of_measurement: "°C"
        state: >
          {{ state_attr('climate.comfoclime', 'thermal_profile')['heatingThermalProfileSeasonData']['comfortTemperature'] }}
        device_class: temperature
      
      - name: "ComfoClime Cooling Comfort Temperature"
        unit_of_measurement: "°C"
        state: >
          {{ state_attr('climate.comfoclime', 'thermal_profile')['coolingThermalProfileSeasonData']['comfortTemperature'] }}
        device_class: temperature
""")
    
    print("\n" + "="*80)
    print("All interface data is now accessible through the Climate entity attributes!")
    print("="*80)


if __name__ == "__main__":
    print_usage_examples()
