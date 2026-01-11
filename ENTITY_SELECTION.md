# Entity Selection Feature

## Overview

This feature allows users to selectively enable/disable **individual entities** in the ComfoClime Home Assistant integration through the configuration flow. This provides fine-grained control over which sensors, switches, numbers, and selects are loaded, reducing API load and clutter.

## How It Works

### Configuration Flow Changes

The options flow has been restructured into a multi-step menu:

1. **Main Menu** (`async_step_init`): Users can choose between:
   - General Settings
   - Entity Selection

2. **General Settings** (`async_step_general`): Contains all the existing timeout, polling, and API configuration options

3. **Entity Selection** (`async_step_entities`): Allows users to select which **individual entities** to enable

### Individual Entity Selection

**NEW in v2.1:** Users can now select individual entities, not just categories. Each entity is presented with:
- An emoji icon indicating its type (📊 Dashboard, 🌡️ Thermal, 📡 Device, 🔌 Switch, etc.)
- The entity category
- The entity name

Examples:
- `📊 Dashboard: Indoor Temperature`
- `🌡️ Thermal: Heating Comfort Temperature`
- `📡 Device 1: Supply Air Temperature`
- `🔌 Switch: Automatic Season Detection`

### Available Entities

The selector presents all available entities grouped by type:

#### Sensors
- **Dashboard Sensors** (📊): Indoor/outdoor temperature, fan speed, heat pump status, etc.
- **Thermal Profile Sensors** (🌡️): Season mode, comfort temperatures, thresholds, etc.
- **Connected Device Telemetry** (📡): Device-specific telemetry (supply air temp, fan speeds, power, etc.)
- **Connected Device Properties** (🔧): Device properties (ventilation disbalance, etc.)
- **Connected Device Definition** (📋): Definition-based sensors from connected devices
- **Access Tracking Sensors** (🔍): Diagnostic sensors for monitoring API access patterns

#### Controls
- **Switches** (🔌): Season detection, temperature control, heatpump on/off
- **Number Controls** (🔢): Thermal profile settings, device-specific numbers
- **Select Controls** (📝): Temperature profile, season mode, humidity settings

### Default Behavior

- **New Installations**: All entities except diagnostic sensors (access tracking, device diagnostic sensors) are enabled by default
- **Existing Installations**: If `enabled_entities` is not set in options, all entities are enabled (backward compatibility)
- **After Configuration**: Only selected entities will be loaded on Home Assistant restart

### Backward Compatibility

The implementation maintains full backward compatibility with the old category-based selection:

1. **No Selection**: If `enabled_entities` is not set (old installations), all entities are enabled
2. **Old Category Selection**: If only category keys are present (e.g., `sensors_dashboard`), all entities in that category are enabled
3. **New Individual Selection**: If individual entity IDs are present, only those specific entities are enabled
4. **Mixed Selection**: The system intelligently detects whether you're using old category-based or new individual-based selection

## Implementation Details

### Files Changed

1. **entity_helper.py**: 
   - `_make_sensor_id()`: Creates unique IDs for each entity (format: `category_subcategory_identifier`)
   - `get_individual_entity_options()`: Returns all individual entities with user-friendly labels
   - `get_default_enabled_individual_entities()`: Returns default set of enabled individual entities
   - `is_entity_enabled()`: Checks if an individual entity is enabled (with backward compatibility)
   - `is_entity_category_enabled()`: Updated to support both category and individual checks

2. **config_flow.py**: 
   - Updated `async_step_entities()` to use individual entity selection
   - Uses `get_individual_entity_options()` for the selector
   - Defaults to `get_default_enabled_individual_entities()` for new configurations

3. **sensor.py, switch.py, number.py, select.py**:
   - Added `is_entity_enabled()` checks before creating each entity
   - Entities are only created if individually enabled or if using old category-based selection
   - Maintains backward compatibility with category-level checks

4. **Translations** (en.json, de.json):
   - No changes needed - emoji prefixes make entities self-documenting
   - Existing translations continue to work

### Entity ID Format

Individual entity IDs follow this pattern:
```
{category}_{subcategory}_{identifier}
```

Examples:
- `sensors_dashboard_indoorTemperature` - Dashboard sensor with key "indoorTemperature"
- `sensors_connected_telemetry_telem_4193` - Telemetry sensor with ID 4193
- `sensors_connected_properties_prop_30_1_18` - Property sensor at path 30/1/18
- `switches_all_season_status` - Switch with key "season.status"
- `numbers_thermal_profile_heatingThermalProfileSeasonData_comfortTemperature` - Number entity

The identifier is derived from:
- `key` field (dots replaced with underscores)
- `telemetry_id` field (prefixed with "telem_")
- `path` or `property` field (slashes replaced with underscores, prefixed with "prop_")
- `coordinator` + `metric` for access tracking sensors
- `name` field as fallback (spaces replaced with underscores)

### Entity Filtering Logic

The filtering is applied during entity setup:

```python
if is_entity_category_enabled(entry.options, "sensors", "dashboard"):
    for sensor_def in DASHBOARD_SENSORS:
        if is_entity_enabled(entry.options, "sensors", "dashboard", sensor_def):
            # Create sensor
```

The `is_entity_enabled()` function:
1. Checks if the specific entity ID is in `enabled_entities`
2. Falls back to category-level check if using old-style selection
3. Returns `True` if `enabled_entities` is `None` (backward compatibility)

### API Load Reduction

By disabling individual entities, users can reduce:
- Number of API requests during each coordinator update cycle
- Data fetching from the ComfoClime device
- Processing overhead in Home Assistant
- Entity registry clutter

This is particularly useful for:
- Users who only need basic monitoring
- Users experiencing rate limiting issues
- Users who want to disable diagnostic/unknown sensors
- Multi-device installations where not all sensors are needed

## Usage Instructions

### For Users

1. Go to **Settings** → **Devices & Services** → **ComfoClime**
2. Click the **Configure** button on your ComfoClime integration
3. Select **Entity Selection** from the menu
4. Select/deselect the individual entities you want to enable/disable
   - Use the search/filter box to find specific entities
   - Entities are grouped with emoji prefixes for easy identification
5. Click **Submit**
6. **Restart Home Assistant** for changes to take effect

### Tips for Selection

- **Start with defaults**: All non-diagnostic entities are enabled by default
- **Use diagnostic entities**: Access tracking sensors help identify API usage patterns
- **Disable unknown sensors**: Connected devices may have "Unknown" sensors that you can disable
- **Keep essential sensors**: Don't disable temperature or fan speed sensors if you use automations
- **Device-specific**: Sensors are labeled by device model ID (e.g., "Device 1" for ComfoAirQ)

### For Developers

To add a new entity:

1. Add the definition to the appropriate file in `entities/` (sensor_definitions.py, switch_definitions.py, etc.)
2. The entity will automatically appear in the selection list with `get_individual_entity_options()`
3. Default enablement is controlled by `get_default_enabled_individual_entities()`
4. No additional wiring needed - the system automatically generates IDs and checks enablement

## Testing

Tests validate:
- Entity ID generation for all entity types
- Backward compatibility with old category-based selection
- Individual entity selection
- Mixed selection scenarios
- Default enablement logic

## Migration Notes

### Upgrading from v2.0.x (Category-based)

When upgrading from a version with category-based selection:

1. **Automatic Migration**: Your existing category selections will continue to work
2. **Gradual Migration**: You can switch to individual selection at any time through the config flow
3. **No Data Loss**: All entities remain available; configuration is not reset

### Behavior After Upgrade

- **If you had category selections**: Those categories will continue to enable all their entities
- **To switch to individual selection**: Go to config flow and manually select individual entities
- **Mixed selection**: The system automatically detects and handles mixed old/new selections

### Breaking Changes

None. This is a fully backward-compatible enhancement.

### What Changed in v2.1

**Before (v2.0.x):**
- Could only enable/disable entire categories
- Example: "Dashboard Sensors" enabled all 14 dashboard sensors

**After (v2.1):**
- Can enable/disable individual entities
- Example: Enable only "Indoor Temperature" and "Outdoor Temperature" from dashboard
- Old category-based selections still work

## Future Enhancements

Possible future improvements:
- Per-device entity control (enable/disable entities per connected device)
- Dynamic reloading without Home Assistant restart
- Entity count display in UI
- Recommended presets (e.g., "Minimal", "Standard", "Complete")
- Bulk selection helpers (e.g., "Select all temperatures", "Select all diagnostic")

## Technical Details

### Performance Considerations

- **Minimal Overhead**: Entity checking happens only during setup, not during runtime
- **Coordinator Optimization**: Disabled entities don't register with coordinators, reducing API calls
- **Memory Usage**: Fewer entities = lower memory footprint
- **Startup Time**: Slightly faster startup with fewer entities to initialize

### Debug Logging

Enable debug logging to see which entities are being created:

```yaml
logger:
  default: info
  logs:
    custom_components.comfoclime: debug
```

Look for log messages like:
- "Creating number entity for property: ..."
- "Found X number properties for model_id Y"
- "Skipping device with NULL uuid"

These help diagnose entity selection issues.
