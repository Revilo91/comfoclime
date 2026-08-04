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
