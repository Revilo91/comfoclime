"""Base entity mixin for all ComfoClime entities.

Provides shared functionality to eliminate code duplication across
sensor, switch, number, select, fan, and climate entity modules.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from pydantic import BaseModel

from . import DOMAIN
from .entity_helper import (
    get_device_display_name,
    get_device_model_type,
    get_device_uuid,
    get_device_version,
)

if TYPE_CHECKING:
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from .models import DeviceConfig

_LOGGER = logging.getLogger(__name__)


class ComfoClimeBaseEntity:
    """Mixin providing common functionality for all ComfoClime entities.

    Subclasses must set ``_device`` (DeviceConfig or None) before
    ``device_info`` is accessed.  Typical usage::

        class MyEntity(ComfoClimeBaseEntity, CoordinatorEntity, SensorEntity):
            ...
    """

    _device: DeviceConfig | None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case for Pydantic attribute access."""
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()

    # ------------------------------------------------------------------
    # Device info (shared across all entity types)
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for the entity registry."""
        if not self._device:
            return None

        dev_id = get_device_uuid(self._device)
        if not dev_id or dev_id == "NULL":
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=get_device_display_name(self._device),
            manufacturer="Zehnder",
            model=get_device_model_type(self._device),
            sw_version=get_device_version(self._device),
        )

    # ------------------------------------------------------------------
    # Nested value extraction from Pydantic / dict data
    # ------------------------------------------------------------------

    def _extract_nested_value(self, data: Any, key_path: list[str]) -> Any:
        """Navigate nested Pydantic models / dicts using a dot-split key path.

        Args:
            data: Root data object (Pydantic BaseModel or dict).
            key_path: List of keys to traverse, e.g. ["season", "status"].

        Returns:
            The resolved value, or ``None`` if any step fails.
        """
        val = data
        for key in key_path:
            if val is None:
                return None
            if isinstance(val, BaseModel):
                snake_key = self._camel_to_snake(key)
                val = getattr(val, snake_key, None)
            elif isinstance(val, dict):
                val = val.get(key)
            else:
                return None
        return val

    # ------------------------------------------------------------------
    # Safe coordinator refresh
    # ------------------------------------------------------------------

    async def _safe_refresh(self, coordinator: DataUpdateCoordinator, name: str = "") -> None:
        """Refresh a coordinator, swallowing exceptions to avoid entity crashes."""
        try:
            await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Background refresh failed for %s", name)
