# Entity Selection Feature

## Overview

This feature allows users to selectively enable/disable entity categories in the ComfoClime Home Assistant integration through the configuration flow. This is useful for reducing API load on the ComfoClime device by disabling entity categories that are not needed.

## How It Works

### Configuration Flow Changes

The options flow has been restructured into a multi-step menu:

1. **Main Menu** (`async_step_init`): Users can choose between:
   - General Settings
   - Entity Selection

2. **General Settings** (`async_step_general`): Contains all the existing timeout, polling, and API configuration options

3. **Entity Selection** (`async_step_entities`): New step that allows users to select which entity categories to enable

### Available Entity Categories

Users can enable/disable the following entity categories:

#### Sensors
- **Dashboard Sensors**: Main device dashboard sensors (indoor/outdoor temperature, fan speed, etc.)
- **Thermal Profile Sensors**: Thermal profile related sensors (season status, comfort temperatures, etc.)
- **Connected Device Telemetry Sensors**: Telemetry data from connected devices (ComfoAirQ, etc.)
- **Connected Device Property Sensors**: Property sensors from connected devices
- **Connected Device Definition Sensors**: Definition-based sensors from connected devices
- **Access Tracking Sensors**: Diagnostic sensors for monitoring API access patterns

#### Controls
- **Switches**: All switch entities (season detection, temperature control, heatpump on/off)
- **Thermal Profile Number Controls**: Number entities for thermal profile settings
- **Connected Device Number Properties**: Number properties from connected devices
- **Thermal Profile Select Controls**: Select entities for thermal profile
- **Connected Device Select Properties**: Select properties from connected devices

### Default Behavior

- **New Installations**: All entity categories except Access Tracking Sensors are enabled by default
- **Existing Installations**: If `enabled_entities` is not set in options, all categories are enabled (backward compatibility)
- **After Configuration**: Only selected categories will be loaded on Home Assistant restart

## Implementation Details

### Files Changed

1. **entity_helper.py** (NEW): 
   - Helper functions to collect and organize entity definitions
   - `get_all_entity_categories()`: Returns all entity definitions organized by type
   - `get_entity_selection_options()`: Returns user-friendly options for the selector
   - `get_default_enabled_entities()`: Returns default set of enabled categories
   - `is_entity_category_enabled()`: Checks if a category is enabled in options

2. **config_flow.py**: 
   - Restructured `ComfoClimeOptionsFlow` to use multi-step menu
   - Added `async_step_entities()` for entity selection
   - Moved existing options to `async_step_general()`

3. **sensor.py, switch.py, number.py, select.py**:
   - Added checks using `is_entity_category_enabled()` before creating entities
   - Entities are only created if their category is enabled in options

4. **Translations** (en.json, de.json):
   - Added translations for new menu and entity selection options
   - Added German translations for all new UI elements

### Entity Filtering Logic

The filtering is applied during entity setup:

```python
if is_entity_category_enabled(entry.options, "sensors", "dashboard"):
    # Create dashboard sensors
```

If a category is not enabled:
- Entities are not created
- No API calls are made for that category's data
- Coordinators still run but with fewer entities to update

### API Load Reduction

By disabling entity categories, users can reduce:
- Number of API requests during each coordinator update cycle
- Data fetching from the ComfoClime device
- Processing overhead in Home Assistant

This is particularly useful for:
- Users with slower networks
- Users who only need basic monitoring
- Users experiencing rate limiting issues

## Usage Instructions

### For Users

1. Go to **Settings** → **Devices & Services** → **ComfoClime**
2. Click the **Configure** button on your ComfoClime integration
3. Select **Entity Selection** from the menu
4. Check/uncheck the entity categories you want to enable/disable
5. Click **Submit**
6. **Restart Home Assistant** for changes to take effect

### For Developers

To add a new entity category:

1. Add the definitions to the appropriate file in `entities/`
2. Update `entity_helper.py`:
   - Add the category to `get_all_entity_categories()`
   - Add selection option to `get_entity_selection_options()`
   - Add to defaults in `get_default_enabled_entities()` if appropriate
3. Update the entity setup file (sensor.py, etc.):
   - Wrap entity creation with `is_entity_category_enabled()` check
4. Update translations (en.json, de.json):
   - Add translations for the new category

## Testing

Tests have been added in:
- `tests/test_entity_helper.py`: Tests for helper functions
- `tests/test_config_flow.py`: Tests for updated options flow

## Migration Notes

### Backward Compatibility

The implementation is fully backward compatible:
- Existing installations without `enabled_entities` in options will have all entities enabled
- No data loss or configuration reset
- Users can continue using the integration without configuring entity selection

### Breaking Changes

None. This is a purely additive feature.

## Future Enhancements

Possible future improvements:
- Per-device entity control
- Individual entity enable/disable (not just by category)
- Dynamic reloading without Home Assistant restart
- Entity count display in UI
- Recommended presets (e.g., "Minimal", "Standard", "Complete")
