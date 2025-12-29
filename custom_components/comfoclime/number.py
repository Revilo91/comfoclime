import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import (
    ComfoClimePropertyCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    main_device = data["main_device"]
    devices = data["devices"]
    tpcoordinator = data["tpcoordinator"]
    propcoordinator: ComfoClimePropertyCoordinator = data["propcoordinator"]

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
            _LOGGER.debug(f"Skipping device with NULL uuid (model_id: {model_id})")
            continue

        number_properties = CONNECTED_DEVICE_NUMBER_PROPERTIES.get(model_id, [])
        _LOGGER.debug(
            f"Found {len(number_properties)} number properties for model_id {model_id}"
        )

        for number_def in number_properties:
            _LOGGER.debug(f"Creating number entity for property: {number_def}")
            # Register property with coordinator for batched fetching
            propcoordinator.register_property(
                device_uuid=dev_uuid,
                property_path=number_def["property"],
                faktor=number_def.get("faktor", 1.0),
                signed=number_def.get("signed", True),
                byte_count=number_def.get("byte_count"),
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

    _LOGGER.debug(f"Adding {len(entities)} number entities to Home Assistant")
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
        if (
            self._key_path[0] == "temperature"
            and self._key_path[1] == "manualTemperature"
        ):
            try:
                coordinator_data = self.coordinator.data
                automatic_temperature_status = coordinator_data.get(
                    "temperature", {}
                ).get("status")

                # Only available if automatic mode is disabled (status = 0)
                return automatic_temperature_status == 0
            except Exception as e:
                _LOGGER.debug(
                    f"Could not check automatic temperature status for availability: {e}"
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
        except Exception:
            _LOGGER.exception("Fehler beim Update")
            self._value = None  # besser als Absturz
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float):
        # Check if this is a manual temperature setting
        if (
            self._key_path[0] == "temperature"
            and self._key_path[1] == "manualTemperature"
        ):
            # Check if automatic comfort temperature is enabled
            try:
                coordinator_data = self.coordinator.data
                automatic_temperature_status = coordinator_data.get(
                    "temperature", {}
                ).get("status")

                if automatic_temperature_status == 1:
                    _LOGGER.warning(
                        "Cannot set manual temperature: automatic comfort temperature is enabled"
                    )
                    # Don't proceed with setting the temperature
                    return
            except Exception as e:
                _LOGGER.warning(f"Could not check automatic temperature status: {e}")
                # Proceed anyway if we can't determine the status

        # Mapping aller NUMBER_ENTITIES Keys zu thermal_profile Parametern
        # Basierend auf dem thermalprofile JSON Schema
        param_mapping = {
            # season nested fields
            "season.season": "season_value",
            "season.status": "season_status",
            "season.heatingThresholdTemperature": "heating_threshold_temperature",
            "season.coolingThresholdTemperature": "cooling_threshold_temperature",
            # temperature nested fields
            "temperature.status": "temperature_status",
            "temperature.manualTemperature": "manual_temperature",
            # heating profile fields
            "heatingThermalProfileSeasonData.comfortTemperature": "heating_comfort_temperature",
            "heatingThermalProfileSeasonData.kneePointTemperature": "heating_knee_point_temperature",
            "heatingThermalProfileSeasonData.reductionDeltaTemperature": "heating_reduction_delta_temperature",
            # cooling profile fields
            "coolingThermalProfileSeasonData.comfortTemperature": "cooling_comfort_temperature",
            "coolingThermalProfileSeasonData.kneePointTemperature": "cooling_knee_point_temperature",
            "coolingThermalProfileSeasonData.temperatureLimit": "cooling_temperature_limit",
        }

        key_str = ".".join(self._key_path)
        if key_str not in param_mapping:
            _LOGGER.warning(f"Unbekannter number key: {key_str}")
            return

        param_name = param_mapping[key_str]
        try:
            await self._api.async_update_thermal_profile(**{param_name: value})
            self._value = value
            await self.coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception(f"Fehler beim Setzen von {self._name}")


class ComfoClimePropertyNumber(
    CoordinatorEntity[ComfoClimePropertyCoordinator], NumberEntity
):
    """Number entity for property values using coordinator for batched fetching."""

    def __init__(
        self,
        hass,
        coordinator: ComfoClimePropertyCoordinator,
        api,
        config,
        device,
        entry,
    ):
        super().__init__(coordinator)
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
        self._byte_count = config.get("byte_count", 2)
        self._signed = config.get("signed", True)  # Default to signed values

        _LOGGER.debug(
            f"ComfoClimePropertyNumber initialized: path={self._property_path}, "
            f"device={device.get('uuid')}, unique_id={self._attr_unique_id}"
        )

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_property_value(
                self._device["uuid"], self._property_path
            )
            _LOGGER.debug(
                f"Property {self._property_path} updated from coordinator: {value}"
            )
            self._value = value
        except Exception as e:
            _LOGGER.debug(
                f"Fehler beim Abrufen von Property {self._property_path}: {e}"
            )
            self._value = None
        self.async_write_ha_state()

    async def async_set_native_value(self, value):
        try:
            await self._api.async_set_property_for_device(
                device_uuid=self._device["uuid"],
                property_path=self._property_path,
                value=value,
                byte_count=self._byte_count,
                faktor=self._faktor,
            )
            self._value = value
            # Trigger coordinator refresh to update all entities
            await self.coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception(
                f"Fehler beim Schreiben von Property {self._property_path}"
            )
