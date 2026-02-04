"""Switch platform for ComfoClime integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .entities.switch_definitions import SWITCHES
from .entity_helper import is_entity_category_enabled, is_entity_enabled

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import (
        ComfoClimeDashboardCoordinator,
        ComfoClimeThermalprofileCoordinator,
    )

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    tpcoordinator = data["tpcoordinator"]
    dbcoordinator = data["coordinator"]
    main_device = data["main_device"]

    # Note: Coordinator first refresh is already done in __init__.py
    # We don't need to await it here to avoid blocking switch setup
    switches = []

    # Create switches from definitions only if enabled
    if is_entity_category_enabled(entry.options, "switches", "all"):
        for s in SWITCHES:
            # Check if this individual switch is enabled
            if not is_entity_enabled(entry.options, "switches", "all", s):
                continue

            # Determine which coordinator to use based on endpoint
            coordinator = tpcoordinator if s.endpoint == "thermal_profile" else dbcoordinator

            switches.append(
                ComfoClimeSwitch(
                    hass,
                    coordinator,
                    api,
                    s.key,
                    s.translation_key,
                    s.name,
                    invert=s.invert,
                    endpoint=s.endpoint,
                    device=main_device,
                    entry=entry,
                )
            )

    async_add_entities(switches, True)


class ComfoClimeSwitch(CoordinatorEntity, SwitchEntity):
    """Unified switch entity for ComfoClime integration.

    Supports switches from both thermal profile and dashboard endpoints.
    Can optionally invert the state logic.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeDashboardCoordinator | ComfoClimeThermalprofileCoordinator,
        api: ComfoClimeAPI,
        key: str,
        translation_key: str,
        name: str,
        invert: bool = False,
        endpoint: str = "thermal_profile",
        device: dict[str, Any] | None = None,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the switch entity.

        Args:
            hass: Home Assistant instance
            coordinator: Data coordinator (ThermalProfile or Dashboard)
            api: ComfoClime API instance
            key: Switch configuration key
            translation_key: i18n translation key
            name: Display name
            invert: If True, invert the state logic (e.g., for hpstandby)
            endpoint: Either 'thermal_profile' or 'dashboard'
            device: Device information
            entry: Config entry
        """
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._key = key
        self._invert = invert
        self._endpoint = endpoint
        self._name = name
        self._state = False
        self._device = device
        self._entry = entry

        self._attr_config_entry_id = entry.entry_id
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_switch_{key}"

        # Parse key path for nested access
        self._key_path = key.split(".")

    @property
    def is_on(self):
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    def _handle_coordinator_update(self) -> None:
        """Update the state from coordinator data."""
        data = self.coordinator.data
        try:
            # Navigate through nested keys
            val = data
            for key in self._key_path:
                val = val.get(key)

            # Apply logic based on endpoint
            if self._endpoint == "thermal_profile":
                self._state = val == 1
            else:  # dashboard
                # For dashboard, apply invert logic if needed
                if isinstance(val, bool):
                    self._state = not val if self._invert else val
                else:
                    self._state = (val != 1) if self._invert else (val == 1)
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Error updating switch %s", self._name, exc_info=True)
            self._state = None
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._invert:
            await self._async_set_status(0)
        else:
            await self._async_set_status(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._invert:
            await self._async_set_status(1)
        else:
            await self._async_set_status(0)

    async def _async_set_status(self, value: int) -> None:
        """Set the switch status.

        Args:
            value: Integer value (0 or 1)
        """
        try:
            if self._endpoint == "thermal_profile":
                await self._set_thermal_profile_status(value)
            else:  # dashboard
                await self._set_dashboard_status(value)
        except (TimeoutError, aiohttp.ClientError):
            _LOGGER.exception("Error setting switch %s", self._name)
            raise HomeAssistantError(f"Error setting {self._name}") from None

    async def _set_thermal_profile_status(self, value: int) -> None:
        """Set thermal profile switch status via API."""
        # Mapping aller SWITCHES Keys zu thermal_profile Parametern
        param_mapping = {
            "season.status": "season_status",
            "temperature.status": "temperature_status",
        }

        key_str = ".".join(self._key_path)
        if key_str not in param_mapping:
            _LOGGER.warning("Unknown switch key: %s", key_str)
            return

        param_name = param_mapping[key_str]
        _LOGGER.debug("Setting %s: value=%s", self._name, value)
        await self._api.async_update_thermal_profile(**{param_name: value})
        self._state = value == 1
        await self.coordinator.async_request_refresh()

    async def _set_dashboard_status(self, value: int) -> None:
        """Set dashboard switch status via API."""
        _LOGGER.debug("Setting %s: %s=%s", self._name, self._key, value)
        await self._api.async_update_dashboard(**{self._key: value})
        # Update state based on inverted logic
        if self._invert:
            self._state = value == 0
        else:
            self._state = value == 1
        await self.coordinator.async_request_refresh()
