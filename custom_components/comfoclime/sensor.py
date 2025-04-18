import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI
from .entities.sensor_definitions import (
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    TELEMETRY_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


VALUE_MAPPINGS = {
    "temperatureProfile": {0: "Comfort", 1: "Power", 2: "Eco"},
    "season": {0: "Transitional", 1: "Heating", 2: "Cooling"},
    "heatPumpStatus": {0: "Off", 1: "Heating", 2: "Cooling"},
    "humidityMode": {0: "Off", 1: "AutoOnly", 2: "On"},
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")

    sensors = []

    # UUID abrufen
    try:
        await api.async_get_uuid(hass)
    except Exception as e:
        _LOGGER.error(f"Fehler beim Abrufen der UUID: {e}")
        return

    # Dashboard-Daten abrufen (optional beim Start)
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]
    coordinator = data["coordinator"]
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.warning(f"Dashboard-Daten konnten nicht geladen werden: {e}")

    devices = await api.async_get_connected_devices(hass)

    # Hauptgerät (modelTypeId 20)
    main_device = next((d for d in devices if d.get("modelTypeId") == 20), None)
    # Dashboard-Sensoren
    sensor_list = [
        ComfoClimeSensor(
            hass=hass,
            coordinator=coordinator,
            api=api,
            sensor_type=sensor_def["key"],
            name=sensor_def["name"],
            translation_key=sensor_def["translation_key"],
            unit=sensor_def.get("unit"),
            device_class=sensor_def.get("device_class"),
            state_class=sensor_def.get("state_class"),
            device=main_device,
            entry=entry,
        )
        for sensor_def in DASHBOARD_SENSORS
    ]
    sensors.extend(sensor_list)

    # Feste Telemetrie-Sensoren für das ComfoClime-Gerät
    sensors.extend(
        ComfoClimeTelemetrySensor(
            hass=hass,
            api=api,
            telemetry_id=sensor_def["id"],
            name=sensor_def["name"],
            translation_key=sensor_def["translation_key"],
            unit=sensor_def.get("unit"),
            faktor=sensor_def.get("faktor", 1.0),
            signed=sensor_def.get("signed", True),
            byte_count=sensor_def.get("byte_count"),
            device_class=sensor_def.get("device_class"),
            state_class=sensor_def.get("state_class"),
            entry=entry,
        )
        for sensor_def in TELEMETRY_SENSORS
    )

    # Verbundene Geräte abrufen
    try:
        devices = await api.async_get_connected_devices(hass)
    except Exception as e:
        _LOGGER.warning(f"Verbundene Geräte konnten nicht geladen werden: {e}")
        devices = []

    for device in devices:
        model_id = device.get("modelTypeId")
        dev_uuid = device.get("uuid")
        if dev_uuid == "NULL":
            continue

        sensor_defs = CONNECTED_DEVICE_SENSORS.get(model_id)
        if not sensor_defs:
            continue

        for sensor_def in sensor_defs:
            if not sensor_def.get("diagnose", False) or entry.options.get(
                "enable_diagnostics", False
            ):
                sensors.extend(
                    [
                        ComfoClimeTelemetrySensor(
                            hass=hass,
                            api=api,
                            telemetry_id=sensor_def["telemetry_id"],
                            name=sensor_def["name"],
                            translation_key=sensor_def["translation_key"],
                            unit=sensor_def.get("unit"),
                            faktor=sensor_def.get("faktor", 1.0),
                            signed=sensor_def.get("signed", True),
                            byte_count=sensor_def.get("byte_count"),
                            device_class=sensor_def.get("device_class"),
                            device=device,
                            state_class=sensor_def.get("state_class"),
                            override_device_uuid=dev_uuid,
                            entry=entry,
                        )
                    ]
                )

        property_defs = CONNECTED_DEVICE_PROPERTIES.get(model_id)
        if not property_defs:
            continue

        sensors.extend(
            ComfoClimePropertySensor(
                hass=hass,
                api=api,
                path=prop_def["path"],
                name=prop_def["name"],
                translation_key=prop_def["translation_key"],
                unit=prop_def.get("unit"),
                faktor=prop_def.get("faktor", 1.0),
                signed=prop_def.get("signed", True),
                byte_count=prop_def.get("byte_count"),
                mapping_key=prop_def.get("mapping_key", ""),
                device=device,
                override_device_uuid=dev_uuid,
                entry=entry,
            )
            for prop_def in property_defs
        )
    async_add_entities(sensors, True)


class ComfoClimeSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        hass,
        coordinator,
        api,
        sensor_type,
        name,
        translation_key,
        unit=None,
        device_class=None,
        state_class=None,
        device=None,
        entry=None,
    ):
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._type = sensor_type
        self._name = name
        self._state = None
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_dashboard_{sensor_type}"
        # self._attr_name = name
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def state(self):
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

    async def async_update(self):
        try:
            data = self.coordinator.data

            raw_value = data.get(self._type)

            # Wenn es eine definierte Übersetzung gibt, wende sie an
            if self._type in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._type].get(raw_value, raw_value)
            else:
                self._state = raw_value

        except Exception as e:
            _LOGGER.warning(f"Fehler beim Aktualisieren der Sensorwerte: {e}")
            self._state = None


class ComfoClimeTelemetrySensor(SensorEntity):
    def __init__(
        self,
        hass,
        api,
        telemetry_id,
        name,
        translation_key,
        unit,
        faktor=1.0,
        signed=True,
        byte_count=None,
        device_class=None,
        device=None,
        state_class=None,
        override_device_uuid=None,
        entry=None,
    ):
        self._hass = hass
        self._api = api
        self._id = telemetry_id
        self._name = name
        self._faktor = faktor
        self._signed = signed
        self._byte_count = byte_count
        self._state = None
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._device = device
        self._override_uuid = override_device_uuid
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_telemetry_{telemetry_id}"
        # self._attr_name = name
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def state(self):
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime Device"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    async def async_update(self):
        try:
            self._state = await self._api.async_read_telemetry_for_device(
                self._hass,
                self._override_uuid or self._api.uuid,
                self._id,
                self._faktor,
                self._signed,
                self._byte_count,
            )
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren von Telemetrie {self._id}: {e}")
            self._state = None


class ComfoClimePropertySensor(SensorEntity):
    def __init__(
        self,
        hass,
        api,
        path: str,
        name: str,
        translation_key: str,
        *,
        unit: str | None = None,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        mapping_key: str | None = None,
        device: dict | None = None,
        override_device_uuid: str | None = None,
        entry: ConfigEntry,
    ):
        self._hass = hass
        self._api = api
        self._path = path
        self._name = name
        self._faktor = faktor
        self._signed = signed
        self._byte_count = byte_count
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._mapping_key = mapping_key
        self._device = device
        self._override_uuid = override_device_uuid
        self._state = None
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_property_{path.replace('/', '_')}"
        # self._attr_name = name
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def native_value(self):
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
            sw_version=self._device.get("version"),
        )

    async def async_update(self):
        try:
            value = await self._api.async_read_property_for_device(
                self._hass,
                self._override_uuid or self._api.uuid,
                self._path,
                self._faktor,
                self._signed,
                self._byte_count,
            )
            if self._mapping_key and self._mapping_key in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._mapping_key].get(value, value)
            else:
                self._state = value
        except Exception as e:
            _LOGGER.error(f"Fehler beim Abrufen von Property {self._path}: {e}")
            self._state = None
