"""Helper module for managing entity definitions and selections."""

import logging

from .models import DeviceConfig
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

_LOGGER = logging.getLogger(__name__)

# Map known modelTypeId values to friendly names for UI grouping
MODEL_TYPE_NAMES = {
    20: "ComfoClime",
    1: "ComfoAirQ",
}


def get_device_uuid(device: DeviceConfig) -> str | None:
    """Get device UUID from Pydantic DeviceConfig model.

    Args:
        device: DeviceConfig instance

    Returns:
        Device UUID string or None if not found
    """
    return device.uuid


def get_device_model_type_id(device: DeviceConfig) -> int | None:
    """Get device model type ID from Pydantic DeviceConfig model.

    Args:
        device: DeviceConfig instance

    Returns:
        Model type ID integer or None if not found
    """
    return device.model_type_id


def get_device_display_name(device: DeviceConfig, default: str = "ComfoClime") -> str:
    """Get device display name from Pydantic DeviceConfig model.

    Args:
        device: DeviceConfig instance
        default: Default name if not found

    Returns:
        Device display name string
    """
    return device.display_name or default


def get_device_version(device: DeviceConfig) -> str | None:
    """Get device version from Pydantic DeviceConfig model.

    Args:
        device: DeviceConfig instance

    Returns:
        Device version string or None if not found
    """
    return device.version


def get_device_model_type(device: DeviceConfig) -> str | None:
    """Get device model type string from Pydantic DeviceConfig model.

    Returns a friendly name based on model_type_id.

    Args:
        device: DeviceConfig instance

    Returns:
        Device model type string or None if not found
    """
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
    """Create a unique ID for a sensor.

    Args:
        category: Main category (sensors, switches, numbers, selects)
        subcategory: Subcategory (dashboard, thermalprofile, etc.)
        sensor_def: Sensor definition model instance

    Returns:
        Unique sensor ID string
    """
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
    """Format simple entities (without per-model grouping) to option dicts.

    Args:
        entity_list: List of entity definition model instances
        category: Entity category (sensors, switches, etc.)
        subcategory: Entity subcategory (dashboard, thermal_profile, etc.)
        emoji: Emoji to prefix the label with
        prefix: Optional prefix for the label (e.g., "Thermal • ")

    Returns:
        List of {value, label} dicts
    """
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
    """Format entities grouped per connected device model to option dicts.

    Args:
        entity_dict: Dictionary mapping model_id to list of entity definition model instances
        category: Entity category (sensors, numbers, selects, etc.)
        subcategory: Entity subcategory
        emoji: Emoji to prefix the label with
        fallback_name: Fallback name pattern if 'name' attribute is missing

    Returns:
        List of {value, label} dicts
    """
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


def _get_sensor_options() -> list[dict]:
    """Get all sensor entity options (dashboard, thermal, telemetry, properties, etc.)."""
    options = []
    options.extend(_get_dashboard_sensors())
    options.extend(_get_thermalprofile_sensors())
    options.extend(_get_monitoring_sensors())
    options.extend(_get_connected_device_telemetry_sensors())
    options.extend(_get_connected_device_properties_sensors())
    options.extend(_get_connected_device_definition_sensors())
    options.extend(_get_access_tracking_sensors())
    return options


def _get_dashboard_sensors() -> list[dict]:
    """Get all dashboard sensor entity options."""
    return _format_simple_entities(DASHBOARD_SENSORS, "sensors", "dashboard", "📊")


def _get_thermalprofile_sensors() -> list[dict]:
    """Get all thermal profile sensor entity options."""
    return _format_simple_entities(THERMALPROFILE_SENSORS, "sensors", "thermalprofile", "🌡️")


def _get_monitoring_sensors() -> list[dict]:
    """Get all monitoring sensor entity options."""
    return _format_simple_entities(MONITORING_SENSORS, "sensors", "monitoring", "⏱️")


def _get_connected_device_telemetry_sensors() -> list[dict]:
    """Get all connected device telemetry sensor entity options."""
    return _format_per_model_entities(
        CONNECTED_DEVICE_SENSORS,
        "sensors",
        "connected_telemetry",
        "📡",
        fallback_name="telemetry_{telemetry_id}",
    )


def _get_connected_device_properties_sensors() -> list[dict]:
    """Get all connected device properties sensor entity options."""
    return _format_per_model_entities(
        CONNECTED_DEVICE_PROPERTIES,
        "sensors",
        "connected_properties",
        "🔧",
        fallback_name="prop_{path}",
    )


def _get_connected_device_definition_sensors() -> list[dict]:
    """Get all connected device definition sensor entity options."""
    return _format_per_model_entities(CONNECTED_DEVICE_DEFINITION_SENSORS, "sensors", "connected_definition", "📋")


def _get_access_tracking_sensors() -> list[dict]:
    """Get all access tracking sensor entity options."""
    return _format_simple_entities(ACCESS_TRACKING_SENSORS, "sensors", "access_tracking", "🔍")


def _get_switch_options() -> list[dict]:
    """Get all switch entity options."""
    return _format_simple_entities(SWITCHES, "switches", "all", "🔌")


def _get_number_options() -> list[dict]:
    """Get all number entity options (thermal profile and connected device properties)."""
    options = []
    # Thermal profile numbers
    options.extend(_format_simple_entities(NUMBER_ENTITIES, "numbers", "thermal_profile", "🔢", prefix="Thermal • "))

    # Connected device number properties - per model
    options.extend(
        _format_per_model_entities(
            CONNECTED_DEVICE_NUMBER_PROPERTIES,
            "numbers",
            "connected_properties",
            "🔢",
            fallback_name="number_{property}",
        )
    )
    return options


def _get_select_options() -> list[dict]:
    """Get all select entity options (thermal profile and connected device properties)."""
    options = []
    # Thermal profile selects
    options.extend(_format_simple_entities(SELECT_ENTITIES, "selects", "thermal_profile", "📝", prefix="Thermal • "))

    # Connected device select properties - per model
    options.extend(
        _format_per_model_entities(
            PROPERTY_SELECT_ENTITIES,
            "selects",
            "connected_properties",
            "📝",
            fallback_name="select_{property}",
        )
    )
    return options


def get_sensors() -> list[dict]:
    """Get all sensor entity options."""
    return _get_sensor_options()


def get_dashboard_sensors() -> list[dict]:
    """Get all dashboard sensor entity options."""
    return _get_dashboard_sensors()


def get_thermalprofile_sensors() -> list[dict]:
    """Get all thermal profile sensor entity options."""
    return _get_thermalprofile_sensors()


def get_monitoring_sensors() -> list[dict]:
    """Get all monitoring sensor entity options."""
    return _get_monitoring_sensors()


def get_connected_device_telemetry_sensors() -> list[dict]:
    """Get all connected device telemetry sensor entity options."""
    return _get_connected_device_telemetry_sensors()


def get_connected_device_properties_sensors() -> list[dict]:
    """Get all connected device properties sensor entity options."""
    return _get_connected_device_properties_sensors()


def get_connected_device_definition_sensors() -> list[dict]:
    """Get all connected device definition sensor entity options."""
    return _get_connected_device_definition_sensors()


def get_access_tracking_sensors() -> list[dict]:
    """Get all access tracking sensor entity options."""
    return _get_access_tracking_sensors()


def get_switches() -> list[dict]:
    """Get all switch entity options."""
    return _get_switch_options()


def get_numbers() -> list[dict]:
    """Get all number entity options."""
    return _get_number_options()


def get_selects() -> list[dict]:
    """Get all select entity options."""
    return _get_select_options()


def get_individual_entity_options() -> list[dict]:
    """Get list of individual entities for user selection in config flow.

    Returns a FLAT list of {value, label} dicts (NOT optgroups).
    Grouping is handled through label prefixes and visual separation.

    Returns:
        List of {value, label} dicts for SelectSelector options
    """
    options = []

    _LOGGER.debug("🔍 get_individual_entity_options() called - start building flat options")

    options.extend(_get_sensor_options())
    options.extend(_get_switch_options())
    options.extend(_get_number_options())
    options.extend(_get_select_options())

    _LOGGER.debug(f"✅ get_individual_entity_options() finished - created {len(options)} total options")

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
    for _model_id, sensor_list in CONNECTED_DEVICE_SENSORS.items():
        for sensor_def in sensor_list:
            if not getattr(sensor_def, "diagnose", False):
                enabled.add(_make_sensor_id("sensors", "connected_telemetry", sensor_def))

    # Connected device properties - all by default
    for _model_id, prop_list in CONNECTED_DEVICE_PROPERTIES.items():
        for prop_def in prop_list:
            enabled.add(_make_sensor_id("sensors", "connected_properties", prop_def))

    # Connected device definition sensors - all by default
    for _model_id, def_list in CONNECTED_DEVICE_DEFINITION_SENSORS.items():
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

    for _model_id, number_list in CONNECTED_DEVICE_NUMBER_PROPERTIES.items():
        for number_def in number_list:
            enabled.add(_make_sensor_id("numbers", "connected_properties", number_def))

    # Select entities - all by default
    for select_def in SELECT_ENTITIES:
        enabled.add(_make_sensor_id("selects", "thermal_profile", select_def))

    for _model_id, select_list in PROPERTY_SELECT_ENTITIES.items():
        for select_def in select_list:
            enabled.add(_make_sensor_id("selects", "connected_properties", select_def))

    return enabled


def is_entity_enabled(options: dict, category: str, subcategory: str, entity_def: object) -> bool:
    """Check if an individual entity is enabled in options.

    Args:
        options: Config entry options dict
        category: Main category (sensors, switches, numbers, selects)
        subcategory: Subcategory (dashboard, thermalprofile, etc.)
        entity_def: Entity definition model instance

    Returns:
        True if enabled, False otherwise
    """
    # Build the individual entity ID
    entity_id = _make_sensor_id(category, subcategory, entity_def)

    _LOGGER.debug(
        "Checking if entity '%s' is enabled (category=%s, subcategory=%s)",
        entity_id,
        category,
        subcategory,
    )

    # Check new config flow format first (enabled_dashboard, enabled_thermalprofile, etc.)
    if subcategory:
        specific_key = f"enabled_{subcategory}"
        if specific_key in options:
            enabled_list = options.get(specific_key, [])
            # If list is empty, nothing is enabled
            if not enabled_list:
                _LOGGER.debug(
                    "Entity '%s': %s list is empty, returning False",
                    entity_id,
                    specific_key,
                )
                return False
            # Check if this entity is in the enabled list
            result = entity_id in enabled_list
            _LOGGER.debug(
                "Entity '%s': checked in %s list, result=%s",
                entity_id,
                specific_key,
                result,
            )
            return result

    # Check for enabled_switches, enabled_numbers, enabled_selects (no subcategory)
    if not subcategory:
        specific_key = f"enabled_{category}"
        if specific_key in options:
            enabled_list = options.get(specific_key, [])
            if not enabled_list:
                _LOGGER.debug(
                    "Entity '%s': %s list is empty, returning False",
                    entity_id,
                    specific_key,
                )
                return False
            result = entity_id in enabled_list
            _LOGGER.debug(
                "Entity '%s': checked in %s list, result=%s",
                entity_id,
                specific_key,
                result,
            )
            return result

    # Check old format (enabled_entities)
    enabled_entities = options.get("enabled_entities")

    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        _LOGGER.debug("Entity '%s': no enabled_entities key, enabling by default", entity_id)
        return True

    # Check if this specific entity is enabled
    if entity_id in enabled_entities:
        _LOGGER.debug("Entity '%s': found in enabled_entities list", entity_id)
        return True

    # Fall back to category-level check for backward compatibility
    # If the category is enabled but no individual entities are selected,
    # enable all entities in that category
    category_key = f"{category}_{subcategory}" if subcategory else category

    if category_key in enabled_entities:
        # Category is enabled - check if any individual entities from this category are in the selection
        # If not, it means we're using old-style category selection, so enable all
        any_individual_in_category = any(e.startswith(f"{category}_{subcategory}_") for e in enabled_entities)
        if not any_individual_in_category:
            # Old-style category selection - enable all in category
            _LOGGER.debug(
                "Entity '%s': category '%s' enabled with no individual selections, enabling all",
                entity_id,
                category_key,
            )
            return True

    _LOGGER.debug("Entity '%s': not enabled, returning False", entity_id)
    return False


def is_entity_category_enabled(options: dict, category: str, subcategory: str | None = None) -> bool:
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
    _LOGGER.debug(
        "Checking if entity category is enabled (category=%s, subcategory=%s)",
        category,
        subcategory,
    )

    # Check new config flow format first (enabled_dashboard, enabled_thermalprofile, etc.)
    if subcategory:
        specific_key = f"enabled_{subcategory}"
        if specific_key in options:
            # If the key exists, check if it has any values
            enabled_list = options.get(specific_key, [])
            result = len(enabled_list) > 0
            _LOGGER.debug(
                "Category check: %s has %d enabled entities, returning %s",
                specific_key,
                len(enabled_list),
                result,
            )
            return result

    # Check for enabled_switches, enabled_numbers, enabled_selects (no subcategory)
    if not subcategory:
        specific_key = f"enabled_{category}"
        if specific_key in options:
            enabled_list = options.get(specific_key, [])
            result = len(enabled_list) > 0
            _LOGGER.debug(
                "Category check: %s has %d enabled entities, returning %s",
                specific_key,
                len(enabled_list),
                result,
            )
            return result

    # Check old format (enabled_entities)
    enabled_entities = options.get("enabled_entities")

    # If no selection has been made yet, enable everything by default
    if enabled_entities is None:
        _LOGGER.debug("Category check: no enabled_entities key, enabling by default")
        return True

    # Build the key to check
    key = f"{category}_{subcategory}" if subcategory else category

    # Check if category itself is enabled
    if key in enabled_entities:
        _LOGGER.debug("Category check: '%s' found in enabled_entities", key)
        return True

    # Check if any individual entities from this category are enabled
    # This handles the case where user selected individual entities
    prefix = f"{category}_{subcategory}_" if subcategory else f"{category}_"
    return any(e.startswith(prefix) for e in enabled_entities)
