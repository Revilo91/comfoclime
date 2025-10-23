import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI
from .coordinator import ComfoClimeThermalprofileCoordinator
from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")
    await api.async_get_uuid(hass)
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    main_device = hass.data[DOMAIN][entry.entry_id]["main_device"]

    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    tpcoordinator = data["tpcoordinator"]
    try:
        await tpcoordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.warning(f"Thermalprofile-Daten konnten nicht geladen werden: {e}")

    entities = [
        ComfoClimeTemperatureNumber(
            hass, tpcoordinator, api, conf, device=main_device, entry=entry
        )
        for conf in NUMBER_ENTITIES
    ]

    for device in devices:
        model_id = device.get("modelTypeId")
        dev_uuid = device.get("uuid")
        if dev_uuid == "NULL":
            continue
        for number_def in CONNECTED_DEVICE_NUMBER_PROPERTIES.get(model_id, []):
            entities.extend(
                [
                    ComfoClimePropertyNumber(
                        hass=hass,
                        api=api,
                        config=number_def,
                        device=device,
                        entry=entry,
                    )
                ]
            )

    async_add_entities(entities, True)


class ComfoClimeTemperatureNumber(
    CoordinatorEntity[ComfoClimeThermalprofileCoordinator], NumberEntity
):
    def __init__(self, hass, coordinator, api, conf, device=None, entry=None):
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._conf = conf
        self._key_path = conf["key"].split(".")
        self._name = conf["name"]
        self._value = None
        self._device = device
        self._entry = entry
        self._attr_mode = (
            NumberMode.SLIDER if conf.get("mode", "box") == "slider" else NumberMode.BOX
        )
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{conf['key']}"
        # self._attr_name = conf["name"]
        self._attr_translation_key = conf["translation_key"]
        self._attr_has_entity_name = True

    def _get_automatic_temperature_status(self):
        """Helper method to get the automatic temperature status from coordinator data.

        Returns:
            int or None: 1 if automatic mode is ON, 0 if OFF, None if unable to determine
        """
        try:
            coordinator_data = self.coordinator.data
            return coordinator_data.get("temperature", {}).get("status")
        except Exception as e:
            _LOGGER.debug(f"Could not check automatic temperature status: {e}")
            return None

    @property
    def available(self):
        """Return True if entity is available based on automatic temperature mode.

        - Manual temperature: only available when automatic mode is OFF (status = 0)
        - Heating/Cooling comfort temperatures: only available when automatic mode is ON (status = 1)
        - Other entities: always available
        """
        automatic_status = self._get_automatic_temperature_status()

        # If we can't determine status, make entity available to avoid breaking functionality
        if automatic_status is None:
            return True

        # Manual temperature is only available when automatic mode is disabled
        if self._key_path[0] == "temperature" and self._key_path[1] == "manualTemperature":
            return automatic_status == 0

        # Heating/Cooling comfort temperatures are only available when automatic mode is enabled
        is_heating_cooling_comfort = (
            self._key_path[0] in ["heatingThermalProfileSeasonData", "coolingThermalProfileSeasonData"] and
            self._key_path[1] == "comfortTemperature"
        )
        if is_heating_cooling_comfort:
            return automatic_status == 1

        # All other temperature entities are always available
        return True

    @property
    def native_value(self):
        return self._value

    @property
    def native_unit_of_measurement(self):
        return "°C"

    @property
    def native_min_value(self):
        return self._conf["min"]

    @property
    def native_max_value(self):
        return self._conf["max"]

    @property
    def native_step(self):
        return self._conf["step"]

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

        dev_id = self._device.get("uuid")
        if not dev_id or dev_id == "NULL":
            return None  # <-- Verhindert fehlerhafte Registrierung

        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    def _handle_coordinator_update(self):
        try:
            data = self.coordinator.data
            val = data
            for k in self._key_path:
                val = val.get(k)
            self._value = val
        except Exception as e:
            _LOGGER.warning(f"[{self.name}] Fehler beim Update: {e}")
            self._value = None  # besser als Absturz
        self.async_write_ha_state()

    def set_native_value(self, value: float):
        """Set the temperature value after checking automatic mode constraints."""
        automatic_status = self._get_automatic_temperature_status()

        # Validate manual temperature can only be set when automatic mode is OFF
        if self._key_path[0] == "temperature" and self._key_path[1] == "manualTemperature":
            if automatic_status == 1:
                _LOGGER.warning(
                    "Cannot set manual temperature: automatic comfort temperature is enabled. "
                    "Please disable the automatic comfort temperature switch first."
                )
                return

        # Validate heating/cooling comfort temperatures can only be set when automatic mode is ON
        is_heating_cooling_comfort = (
            self._key_path[0] in ["heatingThermalProfileSeasonData", "coolingThermalProfileSeasonData"] and
            self._key_path[1] == "comfortTemperature"
        )
        if is_heating_cooling_comfort:
            if automatic_status == 0:
                _LOGGER.warning(
                    f"Cannot set {self._name}: automatic comfort temperature is disabled. "
                    "Please enable the automatic comfort temperature switch first."
                )
                return

        section = self._key_path[0]
        key = self._key_path[1]
        update = {section: {key: value}}

        try:
            self._api.update_thermal_profile(update)
            self._value = value
            self._hass.add_job(self.coordinator.async_request_refresh)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von {self._name}: {e}")


class ComfoClimePropertyNumber(NumberEntity):
    def __init__(self, hass, api, config, device, entry):
        self._hass = hass
        self._api = api
        self._config = config
        self._device = device
        self._entry = entry
        self._value = None

        self._property_path = config["property"]
        self._attr_translation_key = config.get("translation_key")
        self._attr_unique_id = (
            f"{entry.entry_id}_property_number_{self._property_path.replace('/', '_')}"
        )
        self._attr_config_entry_id = entry.entry_id
        self._attr_has_entity_name = True
        self._attr_mode = (
            NumberMode.SLIDER
            if config.get("mode", "box") == "slider"
            else NumberMode.BOX
        )
        self._attr_native_min_value = config.get("min", 0)
        self._attr_native_max_value = config.get("max", 100)
        self._attr_native_step = config.get("step", 1)
        self._attr_native_unit_of_measurement = config.get("unit")
        self._faktor = config.get("faktor", 1.0)
        self._signed = config.get("signed", True)
        self._byte_count = config.get("byte_count", 2)

    @property
    def name(self):
        return self._config.get("name", "Property Number")

    @property
    def native_value(self):
        return self._value

    @property
    def device_info(self):
        if not self._device:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version"),
        )

    async def async_update(self):
        try:
            value = await self._api.async_read_property_for_device(
                self._hass,
                self._device["uuid"],
                self._property_path,
                faktor=self._faktor,
                signed=self._signed,
                byte_count=self._byte_count,
            )
            self._value = value
        except Exception as e:
            _LOGGER.error(
                f"Fehler beim Abrufen von Property {self._property_path}: {e}"
            )
            self._value = None

    async def async_set_native_value(self, value):
        try:
            await self._api.async_set_property_for_device(
                self._hass,
                self._device["uuid"],
                self._property_path,
                value,
                byte_count=self._byte_count,
                faktor=self._faktor,
                signed=self._signed,
            )
            self._value = value
        except Exception as e:
            _LOGGER.error(
                f"Fehler beim Schreiben von Property {self._property_path}: {e}"
            )
