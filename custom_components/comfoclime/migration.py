"""One-time migration from options-based entity selection to the entity registry.

Config entries at version 1 stored, per category, the list of entities that
should be created. Version 2 creates everything and lets the entity registry
decide what is visible, so those lists have to be translated into registry
state exactly once.

The translation has to be exact: a sloppy match would silently disable an
entity the user wanted. So instead of pattern-matching unique IDs, this module
rebuilds the mapping from the same entity definitions both schemes were derived
from - legacy option ID on one side, registry unique ID on the other.

This is deliberately throwaway code. Once entries created by 1.x are gone it
can be deleted along with ``LEGACY_ENTITY_OPTION_KEYS``.
"""

from __future__ import annotations

import logging

from .entities.number_definitions import CONNECTED_DEVICE_NUMBER_PROPERTIES, NUMBER_ENTITIES
from .entities.select_definitions import PROPERTY_SELECT_ENTITIES, SELECT_ENTITIES
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

# Which option key held the selection for each group of entities. The first
# name that exists in the stored options wins; the later ones are aliases used
# by even older releases.
_OPTION_KEYS: dict[str, tuple[str, ...]] = {
    "dashboard": ("enabled_dashboard",),
    "thermalprofile": ("enabled_thermalprofile",),
    "monitoring": ("enabled_monitoring",),
    "connected_telemetry": ("enabled_connected_device_telemetry", "enabled_connected_telemetry"),
    "connected_properties": ("enabled_connected_device_properties", "enabled_connected_properties"),
    "connected_definition": ("enabled_connected_device_definition", "enabled_connected_definition"),
    "access_tracking": ("enabled_access_tracking",),
    "switches": ("enabled_switches",),
    "numbers": ("enabled_numbers",),
    "selects": ("enabled_selects",),
}


def _flat(per_model: dict) -> list:
    """Flatten a {model_id: [definitions]} mapping into a plain list."""
    return [definition for definitions in per_model.values() for definition in definitions]


def build_option_id_map(entry_id: str) -> dict[str, tuple[str, str]]:
    """Map each legacy option ID to ``(group, unique_id_or_suffix)``.

    The second element is a full unique ID except for definition sensors,
    whose unique ID embeds a device UUID that is not known here; those are
    returned as a ``*``-suffixed prefix and matched accordingly.
    """
    mapping: dict[str, tuple[str, str]] = {}

    def add(group: str, option_id: str, unique_id: str) -> None:
        mapping[option_id] = (group, unique_id)

    for definitions, subcategory in (
        (DASHBOARD_SENSORS, "dashboard"),
        (THERMALPROFILE_SENSORS, "thermalprofile"),
        (MONITORING_SENSORS, "monitoring"),
    ):
        for definition in definitions:
            flat_key = definition.key.replace(".", "_")
            add(subcategory, f"sensors_{subcategory}_{flat_key}", f"{entry_id}_{subcategory}_{flat_key}")

    for definition in _flat(CONNECTED_DEVICE_SENSORS):
        telemetry_id = definition.telemetry_id
        add(
            "connected_telemetry",
            f"sensors_connected_telemetry_telem_{telemetry_id}",
            f"{entry_id}_telemetry_{telemetry_id}",
        )

    for definition in _flat(CONNECTED_DEVICE_PROPERTIES):
        flat_path = definition.path.replace("/", "_")
        add(
            "connected_properties",
            f"sensors_connected_properties_prop_{flat_path}",
            f"{entry_id}_property_{flat_path}",
        )

    for definition in _flat(CONNECTED_DEVICE_DEFINITION_SENSORS):
        # unique_id is "{entry_id}_definition_{device_uuid}_{key}"; the UUID is
        # unknown here, so match on the surrounding parts instead.
        add(
            "connected_definition",
            f"sensors_connected_definition_{definition.key}",
            f"{entry_id}_definition_*_{definition.key}",
        )

    for definition in ACCESS_TRACKING_SENSORS:
        coordinator = (definition.coordinator or "total").lower()
        add(
            "access_tracking",
            f"sensors_access_tracking_{coordinator}_{definition.metric}",
            f"{entry_id}_access_{coordinator}_{definition.metric}"
            if definition.coordinator
            else f"{entry_id}_access_{definition.metric}",
        )

    for definition in SWITCHES:
        add(
            "switches",
            f"switches_all_{definition.key.replace('.', '_')}",
            f"{entry_id}_switch_{definition.key}",
        )

    for definition in NUMBER_ENTITIES:
        add(
            "numbers",
            f"numbers_thermal_profile_{definition.key.replace('.', '_')}",
            f"{entry_id}_{definition.key}",
        )

    for definition in _flat(CONNECTED_DEVICE_NUMBER_PROPERTIES):
        flat_path = definition.property.replace("/", "_")
        add(
            "numbers",
            f"numbers_connected_properties_prop_{flat_path}",
            f"{entry_id}_property_number_{flat_path}",
        )

    for definition in SELECT_ENTITIES:
        add(
            "selects",
            f"selects_thermal_profile_{definition.key.replace('.', '_')}",
            f"{entry_id}_select_{definition.key}",
        )

    for definition in _flat(PROPERTY_SELECT_ENTITIES):
        flat_path = definition.path.replace("/", "_")
        add(
            "selects",
            f"selects_connected_properties_prop_{flat_path}",
            f"{entry_id}_select_{flat_path}",
        )

    return mapping


def unique_ids_to_disable(options: dict, entry_id: str) -> set[str]:
    """Return unique IDs (or wildcard patterns) the user had switched off.

    Only groups the user actually configured are considered. A group whose
    option key is missing was never touched, so nothing in it is disabled.
    """
    mapping = build_option_id_map(entry_id)

    configured_groups: dict[str, set[str]] = {}
    for group, keys in _OPTION_KEYS.items():
        for key in keys:
            value = options.get(key)
            if isinstance(value, list):
                configured_groups[group] = set(value)
                break

    to_disable = {
        unique_id
        for option_id, (group, unique_id) in mapping.items()
        if group in configured_groups and option_id not in configured_groups[group]
    }

    # The two core entities were plain booleans rather than list entries.
    if options.get("enabled_climate") is False:
        to_disable.add(f"{entry_id}_climate")
    if options.get("enabled_fan") is False:
        to_disable.add(f"{entry_id}_fan_speed")

    return to_disable


def matches(unique_id: str, patterns: set[str]) -> bool:
    """Test a registry unique ID against exact IDs and ``*`` wildcard patterns."""
    if unique_id in patterns:
        return True
    for pattern in patterns:
        if "*" not in pattern:
            continue
        prefix, _, suffix = pattern.partition("*")
        if unique_id.startswith(prefix) and unique_id.endswith(suffix):
            return True
    return False
