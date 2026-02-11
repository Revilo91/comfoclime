"""ComfoClime Fan Platform.

This module provides the Home Assistant fan entity for ComfoClime
integration. The fan entity controls the ventilation fan speed
independently of the climate entity.

The fan entity supports:
    - On/Off control
    - Speed control with 3 discrete levels (low, medium, high)
    - Percentage-based speed control (0%, 33%, 66%, 100%)

The fan speed directly controls the ComfoClime device's ventilation
fan, which is also accessible through the climate entity's fan_mode
attribute.

Example:
    >>> # In Home Assistant
    >>> fan.turn_on(entity_id="fan.comfoclime_fan_speed")
    >>> fan.set_percentage(entity_id="fan.comfoclime_fan_speed", percentage=66)

Note:
    The fan entity and climate entity share the same underlying fan
    speed control. Changing the fan speed in one will be reflected
    in the other after the next coordinator update.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from pydantic import BaseModel

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pydantic import BaseModel

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import ComfoClimeDashboardCoordinator

from . import DOMAIN
from .constants import FanSpeed
from .entity_helper import (
    get_device_display_name,
    get_device_model_type,
    get_device_uuid,
    get_device_version,
)

_LOGGER = logging.getLogger(__name__)


class ComfoClimeFan(CoordinatorEntity, FanEntity):
    """ComfoClime Fan entity for ventilation fan speed control.

    Provides control over the ComfoClime ventilation fan speed with
    3 discrete speed levels (low/medium/high) plus off. The fan speed
    is also controlled by the climate entity's fan_mode attribute.

    Attributes:
        is_on: Whether the fan is on (speed > 0)
        percentage: Current fan speed as percentage (0%, 33%, 66%, 100%)
        speed_count: Number of discrete speed levels (3)

    Example:
        >>> # Set fan to medium speed (66%)
        >>> await fan.async_set_percentage(66)
        >>> # Turn off fan
        >>> await fan.async_set_percentage(0)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeDashboardCoordinator,
        api: ComfoClimeAPI,
        device: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
        """Initialize the ComfoClime fan entity.

        Args:
            hass: Home Assistant instance
            coordinator: Dashboard data coordinator
            api: ComfoClime API instance
            device: Device info dictionary
            entry: Config entry for this integration
        """
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._device = device
        self._entry = entry
        self._current_speed = FanSpeed.OFF

        self._attr_has_entity_name = True
        self._attr_translation_key = "fan_speed"
        self._attr_unique_id = f"{entry.entry_id}_fan_speed"
        self._attr_config_entry_id = entry.entry_id

        # Setze percentage-Modus mit diskreten Stufen
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_speed_count = 3
        self._attr_percentage_step = 100 // (self._attr_speed_count)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, get_device_uuid(self._device))},
            name=get_device_display_name(self._device),
            manufacturer="Zehnder",
            model=get_device_model_type(self._device),
            sw_version=get_device_version(self._device),
        )

    @property
    def is_on(self) -> bool:
        return self._current_speed > FanSpeed.OFF

    @property
    def percentage(self) -> int | None:
        return self._current_speed.to_percentage()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed by percentage.

        Converts percentage to discrete speed level (0-3) and updates
        the device. The speed levels are:
            - 0%: Off (speed 0)
            - 33%: Low (speed 1)
            - 66%: Medium (speed 2)
            - 100%: High (speed 3)

        Args:
            percentage: Fan speed percentage (0-100)

        Raises:
            aiohttp.ClientError: If API call fails
            asyncio.TimeoutError: If API call times out
        """
        fan_speed = FanSpeed.from_percentage(percentage)
        try:
            await self._api.async_update_dashboard(
                fan_speed=fan_speed,
            )
            self._current_speed = fan_speed
            self.async_write_ha_state()

            # Schedule background refresh without blocking
            async def safe_refresh() -> None:
                """Safely refresh coordinator with error handling."""
                try:
                    await self.coordinator.async_request_refresh()
                except Exception:
                    _LOGGER.exception("Background refresh failed after fan speed update")

            self._hass.async_create_task(safe_refresh())
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.exception("Error setting fan speed")
            raise HomeAssistantError(f"Failed to set fan speed: {err}") from err

    def _handle_coordinator_update(self) -> None:
        try:
            data = self.coordinator.data
            if isinstance(data, BaseModel):
                speed = getattr(data, "fan_speed", 0)
            else:
                speed = data.get("fanSpeed", 0)
            speed_int = int(speed)
            if speed_int in FanSpeed._value2member_map_:
                self._current_speed = FanSpeed(speed_int)
            else:
                self._current_speed = FanSpeed.OFF
        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.warning("Error fetching fan speed from dashboard: %s", e)
            self._current_speed = FanSpeed.OFF
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up ComfoClime fan entity from a config entry.

    Creates the fan entity for controlling the ComfoClime ventilation
    fan speed. The fan entity provides percentage-based speed control
    with 3 discrete levels.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration
        async_add_entities: Callback to add entities

    Note:
        Only one fan entity is created per integration instance.
    """
    try:
        data = hass.data[DOMAIN][entry.entry_id]
        api = data["api"]
        main_device = data["main_device"]
        coordinator = data["coordinator"]
        if not main_device:
            _LOGGER.warning("No main device with modelTypeId 20 found")
            return

        # Note: Coordinator first refresh is already done in __init__.py
        # We don't need to await it here to avoid blocking fan setup
        fan_entity = ComfoClimeFan(hass, coordinator, api, main_device, entry)
        async_add_entities([fan_entity], True)

    except KeyError:
        _LOGGER.exception("Error during fan entity setup")
