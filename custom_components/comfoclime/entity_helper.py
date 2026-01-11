"""Helper module for managing entity definitions and selections."""

import logging
from typing import Dict, List, Set

from .entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
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


def get_entity_selection_options() -> List[Dict[str, str]]:
    """Get list of entity categories for user selection in config flow.
    
    Returns:
        List of dicts with 'value' and 'label' keys for multi-select UI
    """
    return [
        # Sensors
        {"value": "sensors_dashboard", "label": "Dashboard Sensors"},
        {"value": "sensors_thermalprofile", "label": "Thermal Profile Sensors"},
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


def is_entity_category_enabled(
    options: dict, category: str, subcategory: str = None
) -> bool:
    """Check if an entity category is enabled in options.
    
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
    
    return key in enabled_entities
