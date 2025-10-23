# Temperature Status Switch Fix

## Problem Description

The `async_set_temperature` function in `climate.py` was not checking the state of the `switch.comfoclime_24_automatische_komforttemperatur` (Automatic Comfort Temperature switch). This led to incorrect temperature setting behavior.

## Root Cause

According to the ComfoClime API specification, there are two temperature control modes:

1. **Automatic Mode** (`temperature.status = 1`): System uses `comfortTemperature` values for heating and cooling seasons
2. **Manual Mode** (`temperature.status = 0`): System uses `manualTemperature` value regardless of season

The previous implementation did not properly respect this distinction.

## Solution

### Changes to `target_temperature` Property

The property now correctly checks `temperature.status`:

```python
if self._get_temperature_status() == 0:
    # Manual mode: always use manualTemperature
    return temp_data.get("manualTemperature")

# Automatic mode: use comfortTemperature based on season
if season == 1:  # heating
    return heating_data.get("comfortTemperature")
elif season == 2:  # cooling
    return cooling_data.get("comfortTemperature")
```

### Changes to `async_set_temperature` Method

The method now checks the switch state before updating temperatures:

```python
temp_status = self._get_temperature_status()

if temp_status == 0:
    # Manual mode: update manualTemperature only
    updates = {
        "temperature": {
            "manualTemperature": temperature
        }
    }
else:
    # Automatic mode: update appropriate comfortTemperature based on season
    if season == 1:  # heating
        updates = {
            "heatingThermalProfileSeasonData": {
                "comfortTemperature": temperature
            }
        }
    elif season == 2:  # cooling
        updates = {
            "coolingThermalProfileSeasonData": {
                "comfortTemperature": temperature
            }
        }
```

### Code Refactoring

Added helper methods for better code organization:

1. **`_get_temperature_status()`**: Returns the current temperature.status value (0=manual, 1=automatic)
2. **`_get_current_season()`**: Returns the current season value (0=transitional, 1=heating, 2=cooling)

These methods:
- Reduce code duplication
- Improve readability
- Make the code easier to maintain
- Provide a single source of truth for these values

### Enhanced Debugging

Added new attributes to `extra_state_attributes` for debugging:

```python
"current_mappings": {
    "temperature_status": temp_data.get("status"),
    "temperature_mode": "automatic" if self._get_temperature_status() == 1 else "manual",
    ...
}

"api_mappings": {
    "temperature_modes": {
        "automatic": "temperature.status=1 (uses comfortTemperature)",
        "manual": "temperature.status=0 (uses manualTemperature)"
    },
    ...
}
```

## Behavior After Fix

### Switch ON (Automatic Mode - temperature.status=1)
- `target_temperature` returns: `comfortTemperature` for current season
- `async_set_temperature`: Updates `comfortTemperature` for current season (heating or cooling)
- Display: Shows the comfort temperature for the active season

### Switch OFF (Manual Mode - temperature.status=0)
- `target_temperature` returns: `manualTemperature`
- `async_set_temperature`: Updates `manualTemperature` only, regardless of HVAC mode
- Display: Shows the manual temperature

## Testing Recommendations

1. **Test with switch ON (Automatic Mode)**:
   - Set HVAC mode to HEAT
   - Adjust temperature via climate entity
   - Verify: `heatingThermalProfileSeasonData.comfortTemperature` is updated
   - Switch to COOL mode
   - Adjust temperature again
   - Verify: `coolingThermalProfileSeasonData.comfortTemperature` is updated

2. **Test with switch OFF (Manual Mode)**:
   - Turn off the Automatic Comfort Temperature switch
   - Set any HVAC mode (HEAT, COOL, FAN_ONLY)
   - Adjust temperature via climate entity
   - Verify: Only `temperature.manualTemperature` is updated
   - Verify: Climate entity displays the manual temperature

3. **Test Mode Switching**:
   - With switch ON, set temperature to 22°C in HEAT mode
   - Turn switch OFF
   - Verify: Temperature display changes to manualTemperature
   - Set temperature to 20°C
   - Turn switch back ON
   - Verify: Temperature display changes back to comfortTemperature

## API Mapping Reference

### Temperature Fields in Thermal Profile

```json
{
  "temperature": {
    "status": 0,          // 0=manual, 1=automatic
    "manualTemperature": 20.0
  },
  "heatingThermalProfileSeasonData": {
    "comfortTemperature": 21.0
  },
  "coolingThermalProfileSeasonData": {
    "comfortTemperature": 24.0
  }
}
```

### Switch Entity

- **Entity**: `switch.comfoclime_XX_automatic_comfort_temperature`
- **API Path**: `temperature.status`
- **Values**: 
  - ON (1): Automatic mode, use comfortTemperature
  - OFF (0): Manual mode, use manualTemperature

## Related Files

- `custom_components/comfoclime/climate.py`: Main climate entity implementation
- `custom_components/comfoclime/entities/switch_definitions.py`: Switch entity definitions
- `custom_components/comfoclime/comfoclime_api.py`: API communication layer
- `custom_components/comfoclime/coordinator.py`: Data coordinators

## Compatibility

This fix is backward compatible and does not change any API endpoints or data structures. It only corrects the logic to properly respect the existing `temperature.status` field.
