"""Helper module for managing entity definitions and selections."""

import logging
from typing import Dict, List, Set

from .entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    THERMALPROFILE_SENSORS,
)
from .entities.switch_definitions import SWITCHES
from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)
from .entities.select_definitions import PROPERTY_SELECT_ENTITIES, SELECT_ENTITIES

_LOGGER = logging.getLogger(__name__)


def get_all_entity_categories() -> Dict[str, Dict[str, List]]:
    """Get all entity definitions organized by category.
    
    Returns:
        Dict with structure:
        {
            "sensors": {
                "dashboard": [...],
                "thermalprofile": [...],
                "connected_device_telemetry": {...},
                "connected_device_properties": {...},
                "connected_device_definition": {...},
                "access_tracking": [...]
            },
            "switches": [...],
            "numbers": {
                "thermal_profile": [...],
                "connected_device_properties": {...}
            },
            "selects": {
                "thermal_profile": [...],
                "connected_device_properties": {...}
            }
        }
    """
    return {
        "sensors": {
            "dashboard": DASHBOARD_SENSORS,
            "thermalprofile": THERMALPROFILE_SENSORS,
            "monitoring": MONITORING_SENSORS,
            "connected_device_telemetry": CONNECTED_DEVICE_SENSORS,
            "connected_device_properties": CONNECTED_DEVICE_PROPERTIES,
            "connected_device_definition": CONNECTED_DEVICE_DEFINITION_SENSORS,
            "access_tracking": ACCESS_TRACKING_SENSORS,
        },
        "switches": SWITCHES,
        "numbers": {
            "thermal_profile": NUMBER_ENTITIES,
            "connected_device_properties": CONNECTED_DEVICE_NUMBER_PROPERTIES,
        },
        "selects": {
            "thermal_profile": SELECT_ENTITIES,
            "connected_device_properties": PROPERTY_SELECT_ENTITIES,
        },
    }


def _make_sensor_id(category: str, subcategory: str, sensor_def: dict) -> str:
    """Create a unique ID for a sensor.
    
    Args:
        category: Main category (sensors, switches, numbers, selects)
        subcategory: Subcategory (dashboard, thermalprofile, etc.)
        sensor_def: Sensor definition dict
        
    Returns:
        Unique sensor ID string
    """
    # Get identifier from sensor definition
    # Different sensor types use different keys for identification
    if "key" in sensor_def:
        identifier = sensor_def["key"].replace(".", "_")
    elif "telemetry_id" in sensor_def:
        identifier = f"telem_{sensor_def['telemetry_id']}"
    elif "path" in sensor_def:
        identifier = f"prop_{sensor_def['path'].replace('/', '_')}"
    elif "property" in sensor_def:
        identifier = f"prop_{sensor_def['property'].replace('/', '_')}"
    elif "metric" in sensor_def:
        coord = sensor_def.get("coordinator")
        if coord is None:
            coord = "total"
        else:
            coord = coord.lower()
        identifier = f"{coord}_{sensor_def['metric']}"
    else:
        # Fallback to name-based ID
        identifier = sensor_def.get("name", "unknown").lower().replace(" ", "_")
    
    return f"{category}_{subcategory}_{identifier}"


def get_individual_entity_options() -> List[Dict[str, str]]:
    """Get list of individual entities for user selection in config flow.
    
    Returns:
        List of dicts with 'value' and 'label' keys for multi-select UI,
        grouped by category for better organization
    """
    options = []
    
    # Dashboard sensors
    for sensor_def in DASHBOARD_SENSORS:
        sensor_id = _make_sensor_id("sensors", "dashboard", sensor_def)
        label = f"📊 Dashboard: {sensor_def['name']}"
        options.append({"value": sensor_id, "label": label})
    
    # Thermal profile sensors
    for sensor_def in THERMALPROFILE_SENSORS:
        sensor_id = _make_sensor_id("sensors", "thermalprofile", sensor_def)
        label = f"🌡️ Thermal: {sensor_def['name']}"
        options.append({"value": sensor_id, "label": label})
    
    # Monitoring sensors
    for sensor_def in MONITORING_SENSORS:
        sensor_id = _make_sensor_id("sensors", "monitoring", sensor_def)
        label = f"⏱️ Monitoring: {sensor_def['name']}"
        options.append({"value": sensor_id, "label": label})
    
    # Connected device telemetry sensors (modelTypeId-based)
    # Note: These are model-specific, so we'll create entries for known models
    for model_id, sensor_list in CONNECTED_DEVICE_SENSORS.items():
        for sensor_def in sensor_list:
            sensor_id = _make_sensor_id("sensors", "connected_telemetry", sensor_def)
            label = f"📡 Device {model_id}: {sensor_def['name']}"
            options.append({"value": sensor_id, "label": label})
    
    # Connected device properties
    for model_id, prop_list in CONNECTED_DEVICE_PROPERTIES.items():
        for prop_def in prop_list:
            sensor_id = _make_sensor_id("sensors", "connected_properties", prop_def)
            label = f"🔧 Device {model_id} Property: {prop_def['name']}"
            options.append({"value": sensor_id, "label": label})
    
    # Connected device definition sensors
    for model_id, def_list in CONNECTED_DEVICE_DEFINITION_SENSORS.items():
        for def_sensor in def_list:
            sensor_id = _make_sensor_id("sensors", "connected_definition", def_sensor)
            label = f"📋 Device {model_id} Definition: {def_sensor['name']}"
            options.append({"value": sensor_id, "label": label})
    
    # Access tracking sensors
    for sensor_def in ACCESS_TRACKING_SENSORS:
        sensor_id = _make_sensor_id("sensors", "access_tracking", sensor_def)
        label = f"🔍 Tracking: {sensor_def['name']}"
        options.append({"value": sensor_id, "label": label})
    
    # Switches
    for switch_def in SWITCHES:
        switch_id = _make_sensor_id("switches", "all", switch_def)
        label = f"🔌 Switch: {switch_def['name']}"
        options.append({"value": switch_id, "label": label})
    
    # Number entities
    for number_def in NUMBER_ENTITIES:
        number_id = _make_sensor_id("numbers", "thermal_profile", number_def)
        label = f"🔢 Number: {number_def['name']}"
        options.append({"value": number_id, "label": label})
    
    # Connected device number properties
    for model_id, number_list in CONNECTED_DEVICE_NUMBER_PROPERTIES.items():
        for number_def in number_list:
            number_id = _make_sensor_id("numbers", "connected_properties", number_def)
            label = f"🔢 Device {model_id} Number: {number_def['name']}"
            options.append({"value": number_id, "label": label})
    
    # Select entities
    for select_def in SELECT_ENTITIES:
        select_id = _make_sensor_id("selects", "thermal_profile", select_def)
        label = f"📝 Select: {select_def['name']}"
        options.append({"value": select_id, "label": label})
    
    # Connected device select properties
    for model_id, select_list in PROPERTY_SELECT_ENTITIES.items():
        for select_def in select_list:
            select_id = _make_sensor_id("selects", "connected_properties", select_def)
            label = f"📝 Device {model_id} Select: {select_def['name']}"
            options.append({"value": select_id, "label": label})
    
    return options


def get_entity_selection_options() -> List[Dict[str, str]]:
    """Get list of entity categories for user selection in config flow.
    
    Returns:
        List of dicts with 'value' and 'label' keys for multi-select UI
    """
    return [
        # Sensors
        {"value": "sensors_dashboard", "label": "Dashboard Sensors"},
        {"value": "sensors_thermalprofile", "label": "Thermal Profile Sensors"},
        {"value": "sensors_monitoring", "label": "Monitoring Sensors"},
        {"value": "sensors_connected_device_telemetry", "label": "Connected Device Telemetry Sensors"},
        {"value": "sensors_connected_device_properties", "label": "Connected Device Property Sensors"},
        {"value": "sensors_connected_device_definition", "label": "Connected Device Definition Sensors"},
        {"value": "sensors_access_tracking", "label": "Access Tracking Sensors"},
        # Switches
        {"value": "switches", "label": "Switches"},
        # Numbers
        {"value": "numbers_thermal_profile", "label": "Thermal Profile Number Controls"},
        {"value": "numbers_connected_device_properties", "label": "Connected Device Number Properties"},
        # Selects
        {"value": "selects_thermal_profile", "label": "Thermal Profile Select Controls"},
        {"value": "selects_connected_device_properties", "label": "Connected Device Select Properties"},
    ]


def get_default_enabled_entities() -> Set[str]:
    """Get default set of enabled entity categories.
    
    Returns:
        Set of entity category keys that should be enabled by default
    """
    # By default, enable everything except diagnostic sensors
    return {
        "sensors_dashboard",
        "sensors_thermalprofile",
        "sensors_monitoring",
        "sensors_connected_device_telemetry",
        "sensors_connected_device_properties",
        "sensors_connected_device_definition",
        # Note: sensors_access_tracking is diagnostic and disabled by default
        "switches",
        "numbers_thermal_profile",
        "numbers_connected_device_properties",
        "selects_thermal_profile",
        "selects_connected_device_properties",
    }


def get_default_enabled_individual_entities() -> Set[str]:
    """Get default set of enabled individual entities.
    
    Returns:
        Set of individual entity IDs that should be enabled by default.
        This includes all entities except diagnostic ones.
    """
    enabled = set()
    
    # Dashboard sensors - all by default
    for sensor_def in DASHBOARD_SENSORS:
        enabled.add(_make_sensor_id("sensors", "dashboard", sensor_def))
    
    # Thermal profile sensors - all by default
    for sensor_def in THERMALPROFILE_SENSORS:
        enabled.add(_make_sensor_id("sensors", "thermalprofile", sensor_def))
    
    # Monitoring sensors - all by default
    for sensor_def in MONITORING_SENSORS:
        enabled.add(_make_sensor_id("sensors", "monitoring", sensor_def))
    
    # Connected device telemetry - all non-diagnostic by default
    for model_id, sensor_list in CONNECTED_DEVICE_SENSORS.items():
        for sensor_def in sensor_list:
            if not sensor_def.get("diagnose", False):
                enabled.add(_make_sensor_id("sensors", "connected_telemetry", sensor_def))
    
    # Connected device properties - all by default
    for model_id, prop_list in CONNECTED_DEVICE_PROPERTIES.items():
        for prop_def in prop_list:
            enabled.add(_make_sensor_id("sensors", "connected_properties", prop_def))
    
    # Connected device definition sensors - all by default
    for model_id, def_list in CONNECTED_DEVICE_DEFINITION_SENSORS.items():
        for def_sensor in def_list:
            enabled.add(_make_sensor_id("sensors", "connected_definition", def_sensor))
    
    # Access tracking sensors - NONE by default (diagnostic)
    # (intentionally not added)
    
    # Switches - all by default
    for switch_def in SWITCHES:
        enabled.add(_make_sensor_id("switches", "all", switch_def))
    
    # Number entities - all by default
    for number_def in NUMBER_ENTITIES:
        enabled.add(_make_sensor_id("numbers", "thermal_profile", number_def))
    
    for model_id, number_list in CONNECTED_DEVICE_NUMBER_PROPERTIES.items():
        for number_def in number_list:
            enabled.add(_make_sensor_id("numbers", "connected_properties", number_def))
    
    # Select entities - all by default
    for select_def in SELECT_ENTITIES:
        enabled.add(_make_sensor_id("selects", "thermal_profile", select_def))
    
    for model_id, select_list in PROPERTY_SELECT_ENTITIES.items():
        for select_def in select_list:
            enabled.add(_make_sensor_id("selects", "connected_properties", select_def))
    
    return enabled


def is_entity_enabled(
    options: dict, 
    category: str, 
    subcategory: str, 
    entity_def: dict
) -> bool:
    """Check if an individual entity is enabled in options.
    
    Args:
        options: Config entry options dict
        category: Main category (sensors, switches, numbers, selects)
        subcategory: Subcategory (dashboard, thermalprofile, etc.)
        entity_def: Entity definition dict
    
    Returns:
        True if enabled, False otherwise
    """
    enabled_entities = options.get("enabled_entities", None)
    
    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        return True
    
    # Build the individual entity ID
    entity_id = _make_sensor_id(category, subcategory, entity_def)
    
    # Check if this specific entity is enabled
    if entity_id in enabled_entities:
        return True
    
    # Fall back to category-level check for backward compatibility
    # If the category is enabled but no individual entities are selected,
    # enable all entities in that category
    if subcategory:
        category_key = f"{category}_{subcategory}"
    else:
        category_key = category
    
    if category_key in enabled_entities:
        # Category is enabled - check if any individual entities from this category are in the selection
        # If not, it means we're using old-style category selection, so enable all
        any_individual_in_category = any(
            e.startswith(f"{category}_{subcategory}_") 
            for e in enabled_entities
        )
        if not any_individual_in_category:
            # Old-style category selection - enable all in category
            return True
    
    return False


def is_entity_category_enabled(
    options: dict, category: str, subcategory: str = None
) -> bool:
    """Check if an entity category is enabled in options.
    
    This function is kept for backward compatibility and for checking
    if we should even attempt to load entities from a category.
    
    Args:
        options: Config entry options dict
        category: Main category (sensors, switches, numbers, selects)
        subcategory: Optional subcategory (dashboard, thermalprofile, etc.)
    
    Returns:
        True if enabled, False otherwise
    """
    enabled_entities = options.get("enabled_entities", None)
    
    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        return True
    
    # Build the key to check
    if subcategory:
        key = f"{category}_{subcategory}"
    else:
        key = category
    
    # Check if category itself is enabled
    if key in enabled_entities:
        return True
    
    # Check if any individual entities from this category are enabled
    # This handles the case where user selected individual entities
    prefix = f"{category}_{subcategory}_" if subcategory else f"{category}_"
    return any(e.startswith(prefix) for e in enabled_entities)
