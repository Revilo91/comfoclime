"""Helper module for managing entity definitions and selections."""

import logging

from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)
from .entities.select_definitions import (
    PROPERTY_SELECT_ENTITIES,
    SELECT_ENTITIES,
)
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
from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)

# Map known modelTypeId values to friendly names for UI grouping
MODEL_TYPE_NAMES = {
    20: "ComfoClime",
    1: "ComfoAirQ",
}


def get_device_uuid(device: DeviceConfig) -> str | None:
    """Get device UUID."""
    return device.uuid


def get_device_model_type_id(device: DeviceConfig) -> int | None:
    """Get device model type ID."""
    return device.model_type_id


def get_device_display_name(device: DeviceConfig, default: str = "ComfoClime") -> str:
    """Get device display name."""
    return device.display_name or default


def get_device_version(device: DeviceConfig) -> str | None:
    """Get device version."""
    return device.version


def get_device_model_type(device: DeviceConfig) -> str | None:
    """Get device model type as friendly name string."""
    return _friendly_model_name(device.model_type_id)


def _friendly_model_name(model_id) -> str:
    """Return a human-friendly model name for a model_id, safe for strings/ints.

    If the model_id exists in MODEL_TYPE_NAMES, return that. Otherwise return
    a fallback 'Model {model_id}'.
    """
    if model_id is None:
        return "Unknown Model"
    try:
        mid = int(model_id)
    except (ValueError, TypeError):
        return f"Model {model_id}"
    return MODEL_TYPE_NAMES.get(mid, f"Model {mid}")


def get_all_entity_categories() -> dict[str, dict[str, list]]:
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


def _make_sensor_id(category: str, subcategory: str, sensor_def: object) -> str:
    """Create a unique ID for a sensor from its definition."""
    # Get identifier from sensor definition based on available attributes
    if hasattr(sensor_def, "key") and sensor_def.key:
        identifier = sensor_def.key.replace(".", "_")
    elif hasattr(sensor_def, "telemetry_id") and sensor_def.telemetry_id:
        identifier = f"telem_{sensor_def.telemetry_id}"
    elif hasattr(sensor_def, "path") and sensor_def.path:
        identifier = f"prop_{sensor_def.path.replace('/', '_')}"
    elif hasattr(sensor_def, "property") and sensor_def.property:
        identifier = f"prop_{sensor_def.property.replace('/', '_')}"
    elif hasattr(sensor_def, "metric") and sensor_def.metric:
        coord = (getattr(sensor_def, "coordinator", None) or "total").lower()
        identifier = f"{coord}_{sensor_def.metric}"
    else:
        # Fallback to name-based ID
        identifier = (getattr(sensor_def, "name", "unknown") or "unknown").lower().replace(" ", "_")

    return f"{category}_{subcategory}_{identifier}"


def _format_simple_entities(
    entity_list: list[object],
    category: str,
    subcategory: str,
    emoji: str,
    prefix: str = "",
) -> list[dict]:
    """Format entities to {value, label} option dicts for config flow."""
    options = []
    for entity_def in entity_list:
        try:
            entity_id = _make_sensor_id(category, subcategory, entity_def)
            label = getattr(entity_def, "name", "unknown")
            full_label = f"{emoji} {prefix}{label}" if prefix else f"{emoji} {label}"
            options.append({"value": entity_id, "label": full_label})
        except (KeyError, AttributeError):
            _LOGGER.exception("❌ Error processing %s_%s entity %s", category, subcategory, entity_def)
    return options


def _format_per_model_entities(
    entity_dict: dict,
    category: str,
    subcategory: str,
    emoji: str,
    fallback_name: str = "",
) -> list[dict]:
    """Format per-model entities to {value, label} option dicts for config flow."""
    options = []
    for model_id, entity_list in entity_dict.items():
        model_name = _friendly_model_name(model_id)
        for entity_def in entity_list:
            try:
                entity_id = _make_sensor_id(category, subcategory, entity_def)
                label = getattr(entity_def, "name", None)
                if not label and fallback_name:
                    label = fallback_name
                if not label:
                    label = "unknown"
                options.append({"value": entity_id, "label": f"{emoji} {model_name} • {label}"})
            except (KeyError, AttributeError):
                _LOGGER.exception(
                    "❌ Error processing %s_%s for model %s",
                    category,
                    subcategory,
                    model_id,
                )
    return options


def get_individual_entity_options() -> list[dict]:
    """Get list of individual entities for user selection in config flow.

    Returns a FLAT list of {value, label} dicts (NOT optgroups).
    Grouping is handled through label prefixes and visual separation.
    """
    options = []

    # Sensors
    options.extend(_format_simple_entities(DASHBOARD_SENSORS, "sensors", "dashboard", "📊"))
    options.extend(_format_simple_entities(THERMALPROFILE_SENSORS, "sensors", "thermalprofile", "🌡️"))
    options.extend(_format_simple_entities(MONITORING_SENSORS, "sensors", "monitoring", "⏱️"))
    options.extend(
        _format_per_model_entities(
            CONNECTED_DEVICE_SENSORS, "sensors", "connected_telemetry", "📡",
            fallback_name="telemetry_{telemetry_id}",
        )
    )
    options.extend(
        _format_per_model_entities(
            CONNECTED_DEVICE_PROPERTIES, "sensors", "connected_properties", "🔧",
            fallback_name="prop_{path}",
        )
    )
    options.extend(
        _format_per_model_entities(CONNECTED_DEVICE_DEFINITION_SENSORS, "sensors", "connected_definition", "📋")
    )
    options.extend(_format_simple_entities(ACCESS_TRACKING_SENSORS, "sensors", "access_tracking", "🔍"))

    # Switches
    options.extend(_format_simple_entities(SWITCHES, "switches", "all", "🔌"))

    # Numbers
    options.extend(_format_simple_entities(NUMBER_ENTITIES, "numbers", "thermal_profile", "🔢", prefix="Thermal • "))
    options.extend(
        _format_per_model_entities(
            CONNECTED_DEVICE_NUMBER_PROPERTIES, "numbers", "connected_properties", "🔢",
            fallback_name="number_{property}",
        )
    )

    # Selects
    options.extend(_format_simple_entities(SELECT_ENTITIES, "selects", "thermal_profile", "📝", prefix="Thermal • "))
    options.extend(
        _format_per_model_entities(
            PROPERTY_SELECT_ENTITIES, "selects", "connected_properties", "📝",
            fallback_name="select_{property}",
        )
    )

    return options


def get_entity_selection_options() -> list[dict[str, str]]:
    """Get list of entity categories for user selection in config flow.

    Returns:
        List of dicts with 'value' and 'label' keys for multi-select UI
    """
    return [
        # Sensors
        {"value": "sensors_dashboard", "label": "Dashboard Sensors"},
        {"value": "sensors_thermalprofile", "label": "Thermal Profile Sensors"},
        {"value": "sensors_monitoring", "label": "Monitoring Sensors"},
        {
            "value": "sensors_connected_device_telemetry",
            "label": "Connected Device Telemetry Sensors",
        },
        {
            "value": "sensors_connected_device_properties",
            "label": "Connected Device Property Sensors",
        },
        {
            "value": "sensors_connected_device_definition",
            "label": "Connected Device Definition Sensors",
        },
        {"value": "sensors_access_tracking", "label": "Access Tracking Sensors"},
        # Switches
        {"value": "switches", "label": "Switches"},
        # Numbers
        {
            "value": "numbers_thermal_profile",
            "label": "Thermal Profile Number Controls",
        },
        {
            "value": "numbers_connected_device_properties",
            "label": "Connected Device Number Properties",
        },
        # Selects
        {
            "value": "selects_thermal_profile",
            "label": "Thermal Profile Select Controls",
        },
        {
            "value": "selects_connected_device_properties",
            "label": "Connected Device Select Properties",
        },
    ]


def get_default_enabled_entities() -> set[str]:
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


def get_default_enabled_individual_entities() -> set[str]:
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
    for sensor_list in CONNECTED_DEVICE_SENSORS.values():
        for sensor_def in sensor_list:
            if not getattr(sensor_def, "diagnose", False):
                enabled.add(_make_sensor_id("sensors", "connected_telemetry", sensor_def))

    # Connected device properties - all by default
    for prop_list in CONNECTED_DEVICE_PROPERTIES.values():
        for prop_def in prop_list:
            enabled.add(_make_sensor_id("sensors", "connected_properties", prop_def))

    # Connected device definition sensors - all by default
    for def_list in CONNECTED_DEVICE_DEFINITION_SENSORS.values():
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

    for number_list in CONNECTED_DEVICE_NUMBER_PROPERTIES.values():
        for number_def in number_list:
            enabled.add(_make_sensor_id("numbers", "connected_properties", number_def))

    # Select entities - all by default
    for select_def in SELECT_ENTITIES:
        enabled.add(_make_sensor_id("selects", "thermal_profile", select_def))

    for select_list in PROPERTY_SELECT_ENTITIES.values():
        for select_def in select_list:
            enabled.add(_make_sensor_id("selects", "connected_properties", select_def))

    return enabled


def is_entity_enabled(options: dict, category: str, subcategory: str, entity_def: object) -> bool:
    """Check if an individual entity is enabled in options."""
    entity_id = _make_sensor_id(category, subcategory, entity_def)

    # Check new config flow format (enabled_dashboard, enabled_thermalprofile, etc.)
    if subcategory:
        specific_key = f"enabled_{subcategory}"
        if specific_key in options:
            enabled_list = options.get(specific_key, [])
            return bool(enabled_list) and entity_id in enabled_list

    # Check for enabled_switches, enabled_numbers, enabled_selects (no subcategory)
    if not subcategory:
        specific_key = f"enabled_{category}"
        if specific_key in options:
            enabled_list = options.get(specific_key, [])
            return bool(enabled_list) and entity_id in enabled_list

    # Check old format (enabled_entities)
    enabled_entities = options.get("enabled_entities")

    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        return True

    if entity_id in enabled_entities:
        return True

    # Fall back to category-level check for backward compatibility
    category_key = f"{category}_{subcategory}" if subcategory else category

    if category_key in enabled_entities:
        any_individual_in_category = any(e.startswith(f"{category}_{subcategory}_") for e in enabled_entities)
        if not any_individual_in_category:
            return True

    return False


def is_entity_category_enabled(options: dict, category: str, subcategory: str | None = None) -> bool:
    """Check if an entity category is enabled in options."""
    # Check new config flow format (enabled_dashboard, enabled_thermalprofile, etc.)
    if subcategory:
        specific_key = f"enabled_{subcategory}"
        if specific_key in options:
            return len(options.get(specific_key, [])) > 0

    # Check for enabled_switches, enabled_numbers, enabled_selects (no subcategory)
    if not subcategory:
        specific_key = f"enabled_{category}"
        if specific_key in options:
            return len(options.get(specific_key, [])) > 0

    # Check old format (enabled_entities)
    enabled_entities = options.get("enabled_entities")

    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        return True

    key = f"{category}_{subcategory}" if subcategory else category

    if key in enabled_entities:
        return True

    # Check if any individual entities from this category are enabled
    prefix = f"{category}_{subcategory}_" if subcategory else f"{category}_"
    return any(e.startswith(prefix) for e in enabled_entities)
