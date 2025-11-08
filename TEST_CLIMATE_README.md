# ComfoClime Climate Integration Test

## Overview

This integration test (`test_climate_integration.py`) directly controls a real ComfoClime device to verify that all climate control operations work correctly. **This test does NOT use mocks** - it interacts with the actual device API.

## ⚠️ Important Warning

**This test will temporarily change settings on your ComfoClime device!**

The test will:
- Change HVAC modes (heat, cool, fan only, off)
- Change preset modes (comfort, boost, eco, manual)
- Change temperature settings
- Change fan speeds

**However**, the test automatically restores the original state at the end.

## Requirements

1. **Hardware**: A ComfoClime device connected to your network
2. **Network**: The device must be reachable from the machine running the test
3. **Python**: Python 3.10 or higher
4. **Dependencies**: `requests` library (usually already installed)

## Installation

No installation needed - the test script is standalone and uses the existing `comfoclime_api.py` module.

## Usage

### Method 1: Environment Variable

```bash
# Set the device IP address
export COMFOCLIME_IP="192.168.1.100"

# Run the test
python3 test_climate_integration.py
```

### Method 2: Command Line Argument

```bash
python3 test_climate_integration.py 192.168.1.100
```

### Method 3: Command Line Option

```bash
python3 test_climate_integration.py --ip 192.168.1.100
```

### Help

```bash
python3 test_climate_integration.py --help
```

## What the Test Does

The test performs the following operations in sequence:

### 1. Connection & State Capture
- Connects to the ComfoClime device
- Reads and saves the current state (to restore later)
- Displays the original state

### 2. HVAC Mode Tests
- Tests switching to **HEAT** mode (season=1, hpStandby=False)
- Tests switching to **COOL** mode (season=2, hpStandby=False)
- Tests switching to **FAN_ONLY** mode (season=0, hpStandby=False)
- Tests switching to **OFF** mode (hpStandby=True)

### 3. Preset Mode Tests
- Tests **COMFORT** preset (profile=0, status=1)
- Tests **BOOST** preset (profile=1, status=1)
- Tests **ECO** preset (profile=2, status=1)
- Tests **MANUAL** mode (status=0)

### 4. Temperature Tests
- Tests setting temperature to 21.0°C
- Tests setting temperature to 22.5°C

### 5. Fan Mode Tests
- Tests **LOW** fan speed (speed=1)
- Tests **MEDIUM** fan speed (speed=2)
- Tests **HIGH** fan speed (speed=3)
- Tests **OFF** fan speed (speed=0)

### 6. State Restoration
- Restores all original settings
- Displays the final state

### 7. Results Summary
- Shows which tests passed/failed
- Displays success rate

## Example Output

```
============================================================
ComfoClime Climate Integration Test
============================================================
Device IP: 192.168.1.100
Test Start: 2025-11-08 16:30:00
============================================================

2025-11-08 16:30:00 - __main__ - INFO - Connecting to ComfoClime device at 192.168.1.100...
2025-11-08 16:30:01 - __main__ - INFO - Connected successfully! Device UUID: abc123...

============================================================
Original State (will be restored)
============================================================
Indoor Temperature:    22.3°C
Target Temperature:    21.5°C
Set Point Temperature: 21.5°C
Season:                1 (Heating)
HP Standby:            False
Fan Speed:             2 (Medium)
Status:                0 (Manual)
Temperature Profile:   None
Season Profile:        None
Heat Pump Status:      3
============================================================

************************************************************
Testing: Set HVAC Mode: HEAT
************************************************************
2025-11-08 16:30:04 - __main__ - INFO - Setting HVAC mode to heat - setting season=1 and hpStandby=False
2025-11-08 16:30:04 - __main__ - INFO - Waiting 3.0s for device to process update...
2025-11-08 16:30:07 - __main__ - INFO - Verification: season=1, hpStandby=False (expected: season=1, hpStandby=False)
2025-11-08 16:30:07 - __main__ - INFO - ✅ Set HVAC Mode: HEAT - SUCCESS

...

============================================================
TEST RESULTS SUMMARY
============================================================
✅ PASS - Set HVAC Mode: HEAT
✅ PASS - Set HVAC Mode: COOL
✅ PASS - Set HVAC Mode: FAN_ONLY
✅ PASS - Set HVAC Mode: OFF
✅ PASS - Set Preset Mode: COMFORT
✅ PASS - Set Preset Mode: BOOST
✅ PASS - Set Preset Mode: ECO
✅ PASS - Set Preset Mode: MANUAL
✅ PASS - Set Temperature: 21.0°C
✅ PASS - Set Temperature: 22.5°C
✅ PASS - Set Fan Mode: LOW
✅ PASS - Set Fan Mode: MEDIUM
✅ PASS - Set Fan Mode: HIGH
✅ PASS - Set Fan Mode: OFF

------------------------------------------------------------
Total Tests:  14
Passed:       14
Failed:       0
Success Rate: 100.0%
============================================================
```

## Test Logic

The test uses the same logic as the actual `climate.py` component:

### HVAC Mode Control
- **OFF**: Sets `hpStandby=True` via dashboard API
- **HEAT/COOL/FAN_ONLY**: Uses `async_set_hvac_season()` to atomically set both `season` (via thermal profile) and `hpStandby=False` (via dashboard)

### Preset Mode Control
- **MANUAL** (none): Sets `status=0` via dashboard API
- **COMFORT/BOOST/ECO**: Sets `temperatureProfile`, `seasonProfile`, and `status=1` via dashboard API

### Temperature Control
- Sets `setPointTemperature` and `status=0` (manual mode) via dashboard API

### Fan Mode Control
- Sets `fanSpeed` (0-3) via dashboard API

## Verification

After each operation, the test:
1. Waits 3 seconds for the device to process the change
2. Reads the current state from the device
3. Compares the actual values with expected values
4. Reports success or failure

## Troubleshooting

### Connection Failed
```
ERROR: Failed to connect to ComfoClime device
```
**Solution**: Check that:
- The IP address is correct
- The device is powered on and connected to the network
- There is no firewall blocking the connection
- The device API is accessible (try `curl http://YOUR_IP/monitoring/ping`)

### Test Failed
If a specific test fails:
1. Check the device logs if available
2. Verify the device is responding (not frozen)
3. Try running the test again
4. Check if manual control via the ComfoClime app works

### State Not Restored
If the test crashes before restoring state:
- The device will remain in the last test state
- Manually restore settings via the ComfoClime app
- Or re-run the test with proper IP - it will capture current state and restore after

## Integration with Home Assistant

This test validates that the climate control logic matches what the actual Home Assistant integration (`custom_components/comfoclime/climate.py`) does. If this test passes, the integration should work correctly.

The test can be run:
- **Before deployment**: To verify the device and API work as expected
- **After changes**: To verify changes to `climate.py` or `comfoclime_api.py` don't break functionality
- **For debugging**: To isolate issues with the ComfoClime device vs. Home Assistant integration

## Technical Details

### API Methods Used
- `async_get_uuid()` - Get device UUID
- `async_get_dashboard_data()` - Read dashboard state
- `async_get_thermal_profile()` - Read thermal profile state
- `async_update_dashboard()` - Update dashboard settings
- `async_set_hvac_season()` - Atomically update season and standby
- `async_update_thermal_profile()` - Update thermal profile settings

### State Management
The test uses a `ClimateState` dataclass to track:
- Indoor temperature
- Target temperature
- Season (0=transition, 1=heating, 2=cooling)
- HP standby state
- Fan speed (0-3)
- Status (0=manual, 1=automatic)
- Temperature profile
- Season profile
- Set point temperature
- Heat pump status

### Thread Safety
The test uses the `_request_lock` in `ComfoClimeAPI` to ensure thread-safe API access, just like the Home Assistant integration.

## License

This test is part of the comfoclime Home Assistant integration and uses the same license.
