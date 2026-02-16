from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .comfoclime_api import ComfoClimeAPI
    from .coordinator import (
        ComfoClimePropertyCoordinator,
        ComfoClimeThermalprofileCoordinator,
    )

from . import DOMAIN
from .entities.select_definitions import (
    PROPERTY_SELECT_ENTITIES,
    SELECT_ENTITIES,
    PropertySelectDefinition,
    SelectDefinition,
)
from .entity_base import ComfoClimeBaseEntity
from .entity_helper import (
    get_device_model_type_id,
    get_device_uuid,
    is_entity_category_enabled,
    is_entity_enabled,
)
from .models import DeviceConfig, PropertyWriteRequest

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    main_device = data["main_device"]
    devices = data["devices"]
    tpcoordinator = data["tpcoordinator"]
    propcoordinator: ComfoClimePropertyCoordinator = data["propcoordinator"]

    # Note: Coordinator first refresh is already done in __init__.py
    # We don't need to await it here to avoid blocking select setup
    entities = []

    if is_entity_category_enabled(entry.options, "selects", "thermal_profile"):
        for conf in SELECT_ENTITIES:
            if is_entity_enabled(entry.options, "selects", "thermal_profile", conf):
                entities.append(ComfoClimeSelect(hass, tpcoordinator, api, conf, device=main_device, entry=entry))

    # Verbundene Geräte abrufen
    try:
        devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    except KeyError as e:
        _LOGGER.warning("Could not load connected devices: %s", e)
        devices = []

    if is_entity_category_enabled(entry.options, "selects", "connected_properties"):
        for device in devices:
            model_id = get_device_model_type_id(device)
            dev_uuid = get_device_uuid(device)
            if dev_uuid == "NULL":
                continue

            select_defs = PROPERTY_SELECT_ENTITIES.get(model_id)
            if not select_defs:
                continue

            for select_def in select_defs:
                # Check if this individual select property is enabled
                if not is_entity_enabled(entry.options, "selects", "connected_properties", select_def):
                    continue

                # Register property with coordinator for batched fetching
                await propcoordinator.register_property(
                    device_uuid=dev_uuid,
                    property_path=select_def.path,
                    faktor=1.0,
                    signed=False,
                    byte_count=1,
                )
                entities.append(
                    ComfoClimePropertySelect(
                        hass=hass,
                        coordinator=propcoordinator,
                        api=api,
                        conf=select_def,
                        device=device,
                        entry=entry,
                    )
                )
    async_add_entities(entities, True)


class ComfoClimeSelect(ComfoClimeBaseEntity, CoordinatorEntity, SelectEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeThermalprofileCoordinator,
        api: ComfoClimeAPI,
        conf: SelectDefinition,
        device: DeviceConfig | None = None,
        entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._key = conf.key
        self._name = conf.name
        self._key_path = self._key.split(".")
        self._options_map = conf.options
        self._options_reverse = {v: k for k, v in self._options_map.items()}
        self._current = None
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_select_{conf.key}"
        self._attr_translation_key = conf.translation_key
        self._attr_has_entity_name = True

    @property
    def options(self):
        return list(self._options_map.values())

    @property
    def current_option(self):
        return self._current

    def _handle_coordinator_update(self) -> None:
        try:
            data = self.coordinator.data
            val = self._extract_nested_value(data, self._key_path)
            self._current = self._options_map.get(val)
        except (AttributeError, TypeError, ValueError):
            _LOGGER.debug("Error loading select %s", self._name, exc_info=True)
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        value = self._options_reverse.get(option)
        if value is None:
            return

        try:
            _LOGGER.debug("Setting %s: %s (value=%s)", self._name, option, value)

            param_mapping = {
                "temperatureProfile": "temperature_profile",
                "season.season": "season_value",
                "season.status": "season_status",
                "season.heatingThresholdTemperature": "heating_threshold_temperature",
                "season.coolingThresholdTemperature": "cooling_threshold_temperature",
                "temperature.status": "temperature_status",
                "temperature.manualTemperature": "manual_temperature",
            }

            if self._key not in param_mapping:
                _LOGGER.warning("Unknown select key: %s", self._key)
                return

            param_name = param_mapping[self._key]
            await self._api.async_update_thermal_profile(**{param_name: value})

            self._current = option
            self._hass.async_create_task(self._safe_refresh(self.coordinator, "select"))
        except (TimeoutError, aiohttp.ClientError):
            _LOGGER.exception("Error setting select %s", self._name)
            raise HomeAssistantError(f"Error setting {self._name}") from None


class ComfoClimePropertySelect(ComfoClimeBaseEntity, CoordinatorEntity, SelectEntity):
    """Select entity for property values using coordinator for batched fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimePropertyCoordinator,
        api: ComfoClimeAPI,
        conf: PropertySelectDefinition,
        device: DeviceConfig | None = None,
        entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._name = conf.name
        self._options_map = conf.options
        self._options_reverse = {v: k for k, v in self._options_map.items()}
        self._current = None
        self._device = device
        self._entry = entry
        self._path = conf.path
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_select_{conf.path.replace('/', '_')}"
        self._attr_translation_key = conf.translation_key
        self._attr_has_entity_name = True

    @property
    def options(self):
        return list(self._options_map.values())

    @property
    def current_option(self):
        return self._current

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            val = self.coordinator.get_property_value(get_device_uuid(self._device), self._path)
            self._current = self._options_map.get(val)
        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.debug("Error loading %s: %s", self._name, e)
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Select an option via the API."""
        value = self._options_reverse.get(option)
        if value is None:
            return

        try:
            request = PropertyWriteRequest(
                device_uuid=get_device_uuid(self._device),
                path=self._path,
                value=value,
                byte_count=1,
                faktor=1.0,
            )
            await self._api.async_set_property_for_device(request=request)
            self._current = option
            # Trigger coordinator refresh to update all entities
            await self.coordinator.async_request_refresh()
        except (TimeoutError, aiohttp.ClientError):
            _LOGGER.exception("Error setting select %s", self._name)
            raise HomeAssistantError(f"Error setting {self._name}") from None
