# HVAC Action Implementation Update

## Overview

This document describes the update to the `hvac_action` property in the ComfoClime climate entity to use dashboard data as requested in the GitHub issue.

## Problem Statement

The previous implementation of `hvac_action` calculated the HVAC action based on:
- Fan speed (to determine if system is active)
- Season data from thermal profile
- Temperature differences between current and target temperatures

This approach was complex and didn't accurately reflect the actual heat pump status.

## Solution

The implementation has been updated to use the `heatPumpStatus` field directly from the dashboard data, as recommended in the issue and the ComfoClime API documentation.

## Changes Made

### 1. Updated `hvac_action` Property

The property now:
- Reads `heatPumpStatus` directly from `self.coordinator.data` (dashboard coordinator)
- Maps the status codes to Home Assistant's `HVACAction` enum values
- Returns appropriate actions based on the API documentation

### 2. Heat Pump Status Code Mapping

According to the [ComfoClime API documentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes):

| heatPumpStatus | Meaning | Mapped to HVACAction |
|----------------|---------|---------------------|
| 0 | Heat pump is off | `OFF` |
| 1 | Starting up | `IDLE` |
| 3 | Actively heating | `HEATING` |
| 5 | Actively cooling | `COOLING` |
| 17, 19, 21, 67, 75, 83, etc. | Transitional states (defrost, anti-freeze, etc.) | `IDLE` |

### 3. Removed Code

- Removed `_is_system_active()` helper method (no longer needed)
- Removed complex temperature-based logic
- Removed season-based action determination

### 4. Enhanced Debugging

Added to `extra_state_attributes`:
- `heat_pump_status`: Current heat pump status code
- `hp_standby`: Device power status (off or on)

## Benefits

1. **Accuracy**: The HVAC action now accurately reflects what the heat pump is actually doing
2. **Simplicity**: Much simpler implementation that's easier to understand and maintain
3. **API Compliance**: Follows the ComfoClime API documentation exactly
4. **Real-time**: Shows the actual current state rather than calculated approximations

## Testing

A comprehensive test suite (`test_hvac_action.py`) has been created that verifies:
- All documented heat pump status codes map correctly
- Edge cases (None, missing data) are handled properly
- All test cases pass ✅

## Coordinator Usage

The implementation uses the existing `ComfoClimeDashboardCoordinator` which:
- Is already initialized in `__init__.py`
- Updates every 30 seconds
- Fetches data from `/system/{UUID}/dashboard` endpoint

No new coordinator needed to be created as mentioned in the issue.

## Security Summary

- ✅ Code review completed with no issues
- ✅ CodeQL security scan completed with 0 alerts
- ✅ No security vulnerabilities introduced

## References

- [Issue: Anpassen der hvac_action](https://github.com/Revilo91/comfoclime/issues/XX)
- [ComfoClime API Documentation](https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md)
- [Home Assistant Climate Entity Documentation](https://developers.home-assistant.io/docs/core/entity/climate/#hvac-action)
