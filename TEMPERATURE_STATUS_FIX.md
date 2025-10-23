# Temperature Status Switch Fix

## Problem Description

The `async_set_temperature` function in `climate.py` was not checking the state of the `switch.comfoclime_24_automatische_komforttemperatur` (Automatic Comfort Temperature switch). This led to incorrect temperature setting behavior.

Additionally, the implementation was not using the correct API endpoint according to the ComfoClime API documentation.

## Root Cause

According to the ComfoClime API specification, there are two temperature control modes:

1. **Automatic Mode** (`temperature.status = 1`): 
   - System uses `comfortTemperature` values for heating and cooling seasons
   - Dashboard API returns `temperatureProfile` and `seasonProfile` fields
   - Temperature is set via thermalprofile API

2. **Manual Mode** (`temperature.status = 0`): 
   - System uses **`setPointTemperature`** from dashboard API
   - Dashboard API returns `setPointTemperature` field (NOT `temperatureProfile`)
   - Temperature should be set via **dashboard API**, not thermalprofile API

The previous implementation did not properly respect this distinction and was using the thermalprofile API's `manualTemperature` field instead of the dashboard API's `setPointTemperature` field.

## Solution

### Changes to `target_temperature` Property

The property now correctly checks `temperature.status` and uses the appropriate field:

```python
if self._get_temperature_status() == 0:
    # Manual mode: use setPointTemperature from dashboard
    if self.coordinator.data:
        set_point = self.coordinator.data.get("setPointTemperature")
        if set_point is not None:
            return set_point
    # Fallback to manualTemperature from thermal profile
    return temp_data.get("manualTemperature")

# Automatic mode: use comfortTemperature based on season
if season == 1:  # heating
    return heating_data.get("comfortTemperature")
elif season == 2:  # cooling
    return cooling_data.get("comfortTemperature")
```

### Changes to `async_set_temperature` Method

The method now uses the correct API endpoint based on the switch state:

```python
temp_status = self._get_temperature_status()

if temp_status == 0:
    # Manual mode: set setPointTemperature via dashboard API
    await self._set_setpoint_temperature(temperature)
else:
    # Automatic mode: set comfortTemperature via thermalprofile API
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

### New Helper Method: `_set_setpoint_temperature`

Added a new method to set the temperature via the dashboard API:

```python
async def _set_setpoint_temperature(self, temperature: float) -> None:
    """Set setPointTemperature via dashboard API.
    
    According to API documentation, setPointTemperature is set via the dashboard
    PUT endpoint in manual mode.
    """
```

This method uses the `/system/$UUID$/dashboard` PUT endpoint as specified in the API documentation.

### Additional Refactoring

Added new helper method for better code organization:

- **`_get_season_status()`**: Returns the current season.status value (0=manual, 1=automatic)

Updated properties to use helper methods consistently:
- `hvac_mode` now uses `_get_season_status()` instead of direct access
- `hvac_action` now uses `_get_season_status()` instead of direct access

## Behavior After Fix

### Switch ON (Automatic Mode - temperature.status=1)
- `target_temperature` returns: `comfortTemperature` for current season
- `async_set_temperature`: Updates `comfortTemperature` via **thermalprofile API**
- Dashboard shows: `temperatureProfile` and `seasonProfile` fields (no `setPointTemperature`)

### Switch OFF (Manual Mode - temperature.status=0)
- `target_temperature` returns: `setPointTemperature` from dashboard
- `async_set_temperature`: Updates `setPointTemperature` via **dashboard API**
- Dashboard shows: `setPointTemperature` field (no `temperatureProfile`)

## API Compliance

This fix properly implements the ComfoClime API specification as documented at:
https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md

Key points from the documentation:
- **Manual Mode**: `setPointTemperature` field is only returned when temperature selection is in manual mode
- **Automatic Mode**: `seasonProfile` and `temperatureProfile` fields are only returned when in auto mode
- The fields are **mutually exclusive** - only one set appears based on the mode

## Testing Recommendations

1. **Test with switch ON (Automatic Mode)**:
   - Set HVAC mode to HEAT
   - Adjust temperature via climate entity
   - Verify: `heatingThermalProfileSeasonData.comfortTemperature` is updated in thermalprofile
   - Verify: Dashboard shows `temperatureProfile` (not `setPointTemperature`)
   - Switch to COOL mode
   - Adjust temperature again
   - Verify: `coolingThermalProfileSeasonData.comfortTemperature` is updated

2. **Test with switch OFF (Manual Mode)**:
   - Turn off the Automatic Comfort Temperature switch
   - Set any HVAC mode (HEAT, COOL, FAN_ONLY)
   - Adjust temperature via climate entity
   - Verify: `setPointTemperature` is updated in dashboard API
   - Verify: Dashboard shows `setPointTemperature` (not `temperatureProfile`)
   - Verify: Climate entity displays the setpoint temperature

3. **Test Mode Switching**:
   - With switch ON, set temperature to 22°C in HEAT mode
   - Turn switch OFF
   - Verify: Temperature display changes to setPointTemperature from dashboard
   - Set temperature to 20°C
   - Turn switch back ON
   - Verify: Temperature display changes back to comfortTemperature

## API Mapping Reference

### Dashboard API (`/system/$UUID$/dashboard`)

**In Manual Mode** (temperature.status=0):
```json
{
  "indoorTemperature": 21.5,
  "setPointTemperature": 20.0,  // ← This field is present
  "season": 1,
  "fanSpeed": 2,
  // temperatureProfile NOT present
  // seasonProfile NOT present
}
```

**In Automatic Mode** (temperature.status=1):
```json
{
  "indoorTemperature": 21.5,
  "temperatureProfile": 0,  // ← These fields are present
  "seasonProfile": 0,
  "season": 2,
  "fanSpeed": 2,
  // setPointTemperature NOT present
}
```

### Thermalprofile API (`/system/$UUID$/thermalprofile`)

```json
{
  "temperature": {
    "status": 0,          // 0=manual, 1=automatic
    "manualTemperature": 20.0  // Fallback value
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
  - ON (1): Automatic mode, use `comfortTemperature` (thermalprofile API)
  - OFF (0): Manual mode, use `setPointTemperature` (dashboard API)

## Related Files

- `custom_components/comfoclime/climate.py`: Main climate entity implementation
- `custom_components/comfoclime/entities/switch_definitions.py`: Switch entity definitions
- `custom_components/comfoclime/comfoclime_api.py`: API communication layer
- `custom_components/comfoclime/coordinator.py`: Data coordinators

## Compatibility

This fix is backward compatible and follows the official ComfoClime API specification. It correctly uses:
- Dashboard API for `setPointTemperature` in manual mode
- Thermalprofile API for `comfortTemperature` in automatic mode
