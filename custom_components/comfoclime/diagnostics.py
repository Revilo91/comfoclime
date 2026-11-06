"""Diagnostics support for ComfoClime (downloadable from the device page)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from pydantic import BaseModel

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .runtime_data import ComfoClimeConfigEntry

# Keys whose values must never end up in a public issue report.
TO_REDACT = {
    # Local IP/hostname of the unit: reveals the user's home network layout.
    "host",
    # Config entry title is "ComfoClime @ {host}", i.e. it contains the host.
    "title",
    # The entry's unique_id is the device UUID (= serial number of the unit).
    "unique_id",
    # Device UUIDs are the hardware serial numbers and uniquely identify the unit.
    "uuid",
    "device_uuid",
    # Serial numbers can additionally show up in the free-form device definition
    # and ping payloads (these models accept extra fields).
    "serial",
    "serialNumber",
    "serial_number",
}

# Device UUIDs also appear as *dict keys* in the coordinator data, which
# async_redact_data does not touch. They are replaced by stable aliases so the
# data of different devices stays distinguishable without leaking the serial.
DEVICE_ALIAS_PREFIX = "device_"


def _to_jsonable(value: Any) -> Any:
    """Convert Pydantic models (also nested in dicts/lists) into JSON-safe data."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, timedelta):
        return value.total_seconds()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _rekey(value: Any, aliases: dict[str, str]) -> Any:
    """Replace device UUIDs used as dict keys by their alias, recursively."""
    if isinstance(value, dict):
        return {aliases.get(key, key): _rekey(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_rekey(item, aliases) for item in value]
    return value


def _device_uuid(device: Any) -> str | None:
    """Return a device's UUID from a Pydantic model or an API dict."""
    uuid = device.get("uuid") if isinstance(device, Mapping) else getattr(device, "uuid", None)
    return uuid or None


def _build_aliases(entry: ComfoClimeConfigEntry) -> dict[str, str]:
    """Map every known device UUID to a stable ``device_N`` alias."""
    runtime = entry.runtime_data
    uuids: list[str] = [u for u in (_device_uuid(d) for d in runtime.devices) if u]
    for extra in (entry.unique_id, getattr(runtime.api, "uuid", None)):
        if isinstance(extra, str) and extra and extra not in uuids:
            uuids.append(extra)
    return {uuid: f"{DEVICE_ALIAS_PREFIX}{index}" for index, uuid in enumerate(uuids, start=1)}


def _coordinator_info(coordinator: Any, aliases: dict[str, str], registry: Any = None) -> dict[str, Any]:
    """Describe one coordinator: state, interval, data and (optionally) its registry."""
    interval = coordinator.update_interval
    info: dict[str, Any] = {
        "last_update_success": coordinator.last_update_success,
        "update_interval": interval.total_seconds() if interval is not None else None,
        "data": _rekey(async_redact_data(_to_jsonable(coordinator.data), TO_REDACT), aliases)
        if coordinator.data is not None
        else None,
    }
    if registry is not None:
        info["registered_count"] = sum(len(items) for items in registry.values())
        info["registered"] = _rekey(_to_jsonable(registry), aliases)
    return info


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ComfoClimeConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry, with sensitive data redacted."""
    runtime = entry.runtime_data
    aliases = _build_aliases(entry)

    devices = []
    for device in runtime.devices:
        dumped = async_redact_data(_to_jsonable(device), TO_REDACT)
        dumped["alias"] = aliases.get(_device_uuid(device) or "")
        devices.append(dumped)

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "devices": devices,
        "coordinators": {
            "dashboard": _coordinator_info(runtime.coordinator, aliases),
            "thermalprofile": _coordinator_info(runtime.tpcoordinator, aliases),
            "monitoring": _coordinator_info(runtime.monitoringcoordinator, aliases),
            "telemetry": _coordinator_info(runtime.tlcoordinator, aliases, runtime.tlcoordinator._telemetry_registry),
            "property": _coordinator_info(runtime.propcoordinator, aliases, runtime.propcoordinator._property_registry),
            "definition": _coordinator_info(runtime.definitioncoordinator, aliases),
        },
    }
