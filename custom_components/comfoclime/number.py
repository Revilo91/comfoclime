from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
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
from .constants import ENTITY_TO_API_PARAM_MAPPING
from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
    NumberDefinition,
    PropertyNumberDefinition,
)
from .entity_helper import (
    get_device_display_name,
    get_device_model_type,
    get_device_model_type_id,
    get_device_uuid,
    get_device_version,
    is_entity_category_enabled,
    is_entity_enabled,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    main_device = data["main_device"]
    devices = data["devices"]
    tpcoordinator = data["tpcoordinator"]
    propcoordinator: ComfoClimePropertyCoordinator = data["propcoordinator"]

    # Note: Coordinator first refresh is already done in __init__.py
    # We don't need to await it here to avoid blocking number setup
    entities = []

    if is_entity_category_enabled(entry.options, "numbers", "thermal_profile"):
        for conf in NUMBER_ENTITIES:
            if is_entity_enabled(entry.options, "numbers", "thermal_profile", conf):
                entities.append(
                    ComfoClimeTemperatureNumber(hass, tpcoordinator, api, conf, device=main_device, entry=entry)
                )

    if is_entity_category_enabled(entry.options, "numbers", "connected_properties"):
        for device in devices:
            model_id = get_device_model_type_id(device)
            dev_uuid = get_device_uuid(device)
            if dev_uuid == "NULL":
                _LOGGER.debug("Skipping device with NULL uuid (model_id: %s)", model_id)
                continue

            number_properties = CONNECTED_DEVICE_NUMBER_PROPERTIES.get(model_id, [])
            _LOGGER.debug(
                "Found %s number properties for model_id %s",
                len(number_properties),
                model_id,
            )

            for number_def in number_properties:
                # Check if this individual number property is enabled
                if not is_entity_enabled(entry.options, "numbers", "connected_properties", number_def):
                    continue

                _LOGGER.debug("Creating number entity for property: %s", number_def)
                # Register property with coordinator for batched fetching
                await propcoordinator.register_property(
                    device_uuid=dev_uuid,
                    property_path=number_def.property,
                    faktor=number_def.faktor,
                    signed=False,
                    byte_count=number_def.byte_count,
                )
                entities.append(
                    ComfoClimePropertyNumber(
                        hass=hass,
                        coordinator=propcoordinator,
                        api=api,
                        config=number_def,
                        device=device,
                        entry=entry,
                    )
                )

    _LOGGER.debug("Adding %s number entities to Home Assistant", len(entities))
    async_add_entities(entities, True)


class ComfoClimeTemperatureNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeThermalprofileCoordinator,
        api: ComfoClimeAPI,
        conf: NumberDefinition,
        device: dict[str, Any] | None = None,
        entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._conf = conf
        self._key_path = conf.key.split(".")
        self._name = conf.name
        self._value = None
        self._device = device
        self._entry = entry
        self._attr_mode = NumberMode.BOX
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{conf.key}"
        # self._attr_name = conf.name
        self._attr_translation_key = conf.translation_key
        self._attr_has_entity_name = True

    @property
    def available(self):
        """Return True if entity is available.

        First checks if coordinator update was successful, then applies
        business logic for manual temperature entities.
        """
        # First check if coordinator update was successful
        if not super().available:
            return False

        # For manual temperature setting, check if automatic mode is disabled
        if self._key_path[0] == "temperature" and self._key_path[1] == "manualTemperature":
            try:
                coordinator_data = self.coordinator.data
                automatic_temperature_status = coordinator_data.get("temperature", {}).get("status")

                # Only available if automatic mode is disabled (status = 0)
                return automatic_temperature_status == 0
            except (KeyError, TypeError, ValueError) as e:
                _LOGGER.debug(
                    "Could not check automatic temperature status for availability: %s",
                    e,
                )
                # Return True if we can't determine the status to avoid breaking functionality
                return True

        # For all other temperature entities, use default availability
        return True

    @property
    def native_value(self):
        return self._value

    @property
    def native_unit_of_measurement(self):
        return "°C"

    @property
    def native_min_value(self):
        return self._conf.min

    @property
    def native_max_value(self):
        return self._conf.max

    @property
    def native_step(self):
        return self._conf.step

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

        dev_id = get_device_uuid(self._device)
        if not dev_id or dev_id == "NULL":
            return None  # <-- Verhindert fehlerhafte Registrierung

        return DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=get_device_display_name(self._device),
            manufacturer="Zehnder",
            model=get_device_model_type(self._device),
            sw_version=get_device_version(self._device),
        )

    def _handle_coordinator_update(self) -> None:
        try:
            data = self.coordinator.data
            val = data
            for k in self._key_path:
                val = val.get(k)
            self._value = val
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Error updating number entity %s", self._name, exc_info=True)
            self._value = None  # besser als Absturz
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        # Check if this is a manual temperature setting
        if self._key_path[0] == "temperature" and self._key_path[1] == "manualTemperature":
            # Check if automatic comfort temperature is enabled
            try:
                coordinator_data = self.coordinator.data
                automatic_temperature_status = coordinator_data.get("temperature", {}).get("status")

                if automatic_temperature_status == 1:
                    _LOGGER.warning("Cannot set manual temperature: automatic comfort temperature is enabled")
                    # Don't proceed with setting the temperature
                    return
            except (KeyError, TypeError, ValueError) as e:
                _LOGGER.warning("Could not check automatic temperature status: %s", e)
                # Proceed anyway if we can't determine the status

        key_str = ".".join(self._key_path)
        if key_str not in ENTITY_TO_API_PARAM_MAPPING:
            _LOGGER.warning("Unknown number key: %s", key_str)
            return

        param_name = ENTITY_TO_API_PARAM_MAPPING[key_str]
        try:
            await self._api.async_update_thermal_profile(**{param_name: value})
            self._value = value
            await self.coordinator.async_request_refresh()
        except (TimeoutError, aiohttp.ClientError):
            _LOGGER.exception("Error setting number entity %s", self._name)
            raise HomeAssistantError(f"Error setting {self._name}") from None


class ComfoClimePropertyNumber(CoordinatorEntity, NumberEntity):
    """Number entity for property values using coordinator for batched fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimePropertyCoordinator,
        api: ComfoClimeAPI,
        config: PropertyNumberDefinition,
        device: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._config = config
        self._device = device
        self._entry = entry
        self._value = None

        self._property_path = config.property
        self._attr_translation_key = config.translation_key
        self._attr_unique_id = f"{entry.entry_id}_property_number_{self._property_path.replace('/', '_')}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_has_entity_name = True
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = config.min
        self._attr_native_max_value = config.max
        self._attr_native_step = config.step
        self._attr_native_unit_of_measurement = config.unit
        self._faktor = config.faktor
        self._byte_count = config.byte_count
        self._signed = False  # PropertyNumberDefinition always uses unsigned

        _LOGGER.debug(
            "ComfoClimePropertyNumber initialized: path=%s, device=%s, unique_id=%s",
            self._property_path,
            get_device_uuid(device),
            self._attr_unique_id,
        )

    @property
    def name(self):
        return self._config.name

    @property
    def native_value(self):
        return self._value

    @property
    def device_info(self):
        if not self._device:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, get_device_uuid(self._device))},
            name=get_device_display_name(self._device),
            manufacturer="Zehnder",
            model=get_device_model_type(self._device),
            sw_version=get_device_version(self._device),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_property_value(get_device_uuid(self._device), self._property_path)
            _LOGGER.debug("Property %s updated from coordinator: %s", self._property_path, value)
            self._value = value
        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.debug("Error fetching property %s: %s", self._property_path, e)
            self._value = None
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self._api.async_set_property_for_device(
                device_uuid=get_device_uuid(self._device),
                property_path=self._property_path,
                value=value,
                byte_count=self._byte_count,
                faktor=self._faktor,
            )
            self._value = value
            # Trigger coordinator refresh to update all entities
            await self.coordinator.async_request_refresh()
        except (TimeoutError, aiohttp.ClientError):
            _LOGGER.exception("Error writing property %s", self._property_path)
            raise HomeAssistantError(f"Error writing property {self._property_path}") from None
