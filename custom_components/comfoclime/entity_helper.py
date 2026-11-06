"""Helpers for reading device metadata off the ComfoNet bus.

Devices come back from the API either as Pydantic models (``DeviceConfig``)
or, in older code paths and tests, as raw dicts using the API's camelCase
keys. The accessors here normalise both shapes so entity modules do not
have to care which one they were handed.

Note:
    This module used to also own the entity-selection machinery for the
    options flow (``is_entity_enabled`` and friends). Enabling and disabling
    individual entities is now handled by Home Assistant's entity registry,
    so that code is gone. Platform modules create every entity they know
    about and express defaults through ``entity_registry_enabled_default``.
"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

# Map known modelTypeId values to friendly names.
MODEL_TYPE_NAMES = {
    1: "ComfoAirQ",
    20: "ComfoClime",
    222: "ComfoHub",
}


def _friendly_model_name(model_id) -> str:
    """Return a human-friendly model name for a model_id, safe for strings/ints."""
    if model_id is None:
        return "Unknown Model"
    try:
        mid = int(model_id)
    except ValueError, TypeError:
        return f"Model {model_id}"
    return MODEL_TYPE_NAMES.get(mid, f"Model {mid}")


def get_device_uuid(device: dict | object) -> str | None:
    """Return the device UUID from either a dict or a Pydantic model."""
    if hasattr(device, "uuid"):
        return device.uuid
    if isinstance(device, dict):
        return device.get("uuid")
    return None


# Unique IDs of entities that belong to a device on the ComfoNet bus. They embed
# the device UUID because the bus can carry several devices of the same model
# (e.g. two ComfoAir Q), whose telemetry IDs and property paths are identical.
# Defined once here so the platforms and the 2.2 registry migration agree.


def _flat_path(path: str) -> str:
    """Turn a property path ``X/Y/Z`` into the ``X_Y_Z`` form used in unique IDs."""
    return path.replace("/", "_")


def telemetry_unique_id(entry_id: str, device_uuid: str, telemetry_id: str | int) -> str:
    """Return the unique ID of a bus device's telemetry sensor."""
    return f"{entry_id}_telemetry_{device_uuid}_{telemetry_id}"


def property_sensor_unique_id(entry_id: str, device_uuid: str, path: str) -> str:
    """Return the unique ID of a bus device's property sensor."""
    return f"{entry_id}_property_{device_uuid}_{_flat_path(path)}"


def property_number_unique_id(entry_id: str, device_uuid: str, path: str) -> str:
    """Return the unique ID of a bus device's property number."""
    return f"{entry_id}_property_number_{device_uuid}_{_flat_path(path)}"


def property_select_unique_id(entry_id: str, device_uuid: str, path: str) -> str:
    """Return the unique ID of a bus device's property select."""
    return f"{entry_id}_select_{device_uuid}_{_flat_path(path)}"


def get_device_info_fields(device: dict | object) -> dict[str, str | None]:
    """Return the descriptive DeviceInfo fields shared by entities and setup.

    Used both for the entity ``DeviceInfo`` and for registering the main device
    up front, so the two can never drift apart.
    """
    return {
        "name": get_device_display_name(device),
        "manufacturer": "Zehnder",
        "model": get_device_model_type(device),
        "sw_version": get_device_version(device),
    }


def get_device_model_type_id(device: dict | object) -> int | None:
    """Return the modelTypeId from either a dict or a Pydantic model."""
    if hasattr(device, "model_type_id"):
        return device.model_type_id
    if isinstance(device, dict):
        return device.get("modelTypeId")
    return None


def get_device_display_name(device: dict | object, default: str = "ComfoClime") -> str:
    """Return the device display name from either a dict or a Pydantic model."""
    if hasattr(device, "display_name"):
        return device.display_name or default
    if isinstance(device, dict):
        return device.get("displayName", default)
    return default


def get_device_version(device: dict | object) -> str | None:
    """Return the device firmware version from either a dict or a Pydantic model."""
    if hasattr(device, "version"):
        return device.version
    if isinstance(device, dict):
        return device.get("version")
    return None


def get_device_model_type(device: dict | object) -> str | None:
    """Return the device model type string.

    Dicts carry the vendor's ``@modelType`` field verbatim. Pydantic models
    do not, so a friendly name is derived from the modelTypeId instead.
    """
    if isinstance(device, dict):
        return device.get("@modelType")
    if hasattr(device, "model_type_id"):
        return _friendly_model_name(device.model_type_id)
    return None
