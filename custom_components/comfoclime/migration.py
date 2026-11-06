"""One-time config entry migrations that rewrite entity registry state.

Version 1 -> 2: config entries at version 1 stored, per category, the list of
entities that should be created. Version 2 creates everything and lets the
entity registry decide what is visible, so those lists have to be translated
into registry state exactly once.

The translation has to be exact: a sloppy match would silently disable an
entity the user wanted. So instead of pattern-matching unique IDs, this module
rebuilds the mapping from the same entity definitions both schemes were derived
from - legacy option ID on one side, registry unique ID on the other.

This is deliberately throwaway code. Once entries created by 1.x are gone it
can be deleted along with ``LEGACY_ENTITY_OPTION_KEYS``.

Version 2.1 -> 2.2: unique IDs of entities that belong to a bus device gained
the device UUID (see ``entity_helper``), so two devices of the same model no
longer collide. Here pattern matching *is* safe, because the four legacy
shapes are fixed and anchored; the UUID comes from the device the registry
entry is already attached to.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr, entity_registry as er

from .constants import DOMAIN
from .entities.number_definitions import CONNECTED_DEVICE_NUMBER_PROPERTIES, NUMBER_ENTITIES
from .entities.select_definitions import PROPERTY_SELECT_ENTITIES, SELECT_ENTITIES
from .entities.sensor_definitions import (
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    THERMALPROFILE_SENSORS,
)
from .entities.switch_definitions import SWITCHES
from .entity_helper import (
    property_number_unique_id,
    property_select_unique_id,
    property_sensor_unique_id,
    telemetry_unique_id,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

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


# --- 2.1 -> 2.2: device UUID in bus-device unique IDs --------------------------

# Property paths were flattened from ``X/Y/Z`` to ``X_Y_Z``.
_LEGACY_PATH = r"(\d+)_(\d+)_(\d+)"


def _path_from(match: re.Match[str]) -> str:
    """Rebuild ``X/Y/Z`` from a match of ``_LEGACY_PATH``."""
    return "/".join(match.groups())


def legacy_bus_id_rewriter(entry_id: str, entity_domain: str, unique_id: str) -> Callable[[str], str] | None:
    """Recognise a pre-2.2 bus-device unique ID.

    Returns a function mapping the owning device's UUID to the new unique ID,
    or ``None`` if ``unique_id`` is not one of the four legacy shapes. The
    platform is checked too, so a sensor ID can never be rewritten into a
    select ID. Key-based selects (``<entry>_select_temperatureProfile``) and
    already migrated IDs (which contain the UUID) do not match, which is what
    makes the migration idempotent.
    """
    prefix = re.escape(entry_id)
    rules: tuple[tuple[str, str, Callable[[str, re.Match[str]], str]], ...] = (
        (
            "sensor",
            rf"{prefix}_telemetry_(\d+)",
            lambda uuid, m: telemetry_unique_id(entry_id, uuid, m[1]),
        ),
        (
            "sensor",
            rf"{prefix}_property_{_LEGACY_PATH}",
            lambda uuid, m: property_sensor_unique_id(entry_id, uuid, _path_from(m)),
        ),
        (
            "number",
            rf"{prefix}_property_number_{_LEGACY_PATH}",
            lambda uuid, m: property_number_unique_id(entry_id, uuid, _path_from(m)),
        ),
        (
            "select",
            rf"{prefix}_select_{_LEGACY_PATH}",
            lambda uuid, m: property_select_unique_id(entry_id, uuid, _path_from(m)),
        ),
    )
    for domain, pattern, build in rules:
        if domain == entity_domain and (match := re.fullmatch(pattern, unique_id)):
            return lambda device_uuid, build=build, match=match: build(device_uuid, match)
    return None


def comfoclime_device_uuid(device_registry: dr.DeviceRegistry, device_id: str | None) -> str | None:
    """Return the ComfoClime UUID of a registry device, or ``None`` if unknown.

    Entities register their device with exactly one ``(DOMAIN, uuid)``
    identifier. Anything else (no device, no such identifier, several of them)
    is ambiguous, and guessing would attach the entity to the wrong device.
    """
    device = device_registry.async_get(device_id) if device_id else None
    if device is None:
        return None
    uuids = [value for domain, value in device.identifiers if domain == DOMAIN]
    return uuids[0] if len(uuids) == 1 else None


async def async_migrate_bus_device_unique_ids(hass: HomeAssistant, entry_id: str) -> int:
    """Add the device UUID to legacy bus-device unique IDs of one config entry.

    Registry entries are renamed in place, so entity ID, history, name and
    area survive. Entries that cannot be migrated safely are left unchanged
    and logged; this never raises, because a failed migration would keep the
    whole integration from loading.

    Returns:
        Number of migrated registry entries.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    migrated = 0

    def _migrate(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
        nonlocal migrated
        rewrite = legacy_bus_id_rewriter(entry_id, reg_entry.domain, reg_entry.unique_id)
        if rewrite is None:
            return None

        device_uuid = comfoclime_device_uuid(device_registry, reg_entry.device_id)
        if device_uuid is None:
            _LOGGER.warning(
                "Not migrating unique ID %s of %s: it is not attached to a ComfoClime device, "
                "so its device UUID is unknown. A new entity will be created for it",
                reg_entry.unique_id,
                reg_entry.entity_id,
            )
            return None

        new_unique_id = rewrite(device_uuid)
        if existing := entity_registry.async_get_entity_id(reg_entry.domain, reg_entry.platform, new_unique_id):
            _LOGGER.warning(
                "Not migrating unique ID %s of %s: %s already uses %s",
                reg_entry.unique_id,
                reg_entry.entity_id,
                existing,
                new_unique_id,
            )
            return None

        _LOGGER.debug("Migrating unique ID of %s: %s -> %s", reg_entry.entity_id, reg_entry.unique_id, new_unique_id)
        migrated += 1
        return {"new_unique_id": new_unique_id}

    await er.async_migrate_entries(hass, entry_id, _migrate)
    if migrated:
        _LOGGER.info("Added the device UUID to the unique IDs of %s bus-device entities", migrated)
    return migrated
