from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import ComfoClimeDashboardCoordinator

from . import DOMAIN
from .constants import FanSpeed

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ComfoClimeFan(CoordinatorEntity[ComfoClimeDashboardCoordinator], FanEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeDashboardCoordinator,
        api: ComfoClimeAPI,
        device: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
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
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version"),
        )

    @property
    def is_on(self) -> bool:
        return self._current_speed > FanSpeed.OFF

    @property
    def percentage(self) -> int | None:
        return self._current_speed.to_percentage()

    async def async_set_percentage(self, percentage: int) -> None:
        fan_speed = FanSpeed.from_percentage(percentage)
        try:
            await self._api.async_update_dashboard(
                fan_speed=fan_speed,
            )
            self._current_speed = fan_speed
            self.async_write_ha_state()
            self._hass.add_job(self.coordinator.async_request_refresh)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            _LOGGER.exception("Error setting fan speed")

    def _handle_coordinator_update(self) -> None:
        try:
            data = self.coordinator.data
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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
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
