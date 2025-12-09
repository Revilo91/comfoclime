import asyncio
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entities.sensor_definitions import (
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    TELEMETRY_SENSORS,
    THERMALPROFILE_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


VALUE_MAPPINGS = {
    "temperatureProfile": {0: "comfort", 1: "power", 2: "eco"},
    "season": {0: "transitional", 1: "heating", 2: "cooling"},
    "humidityMode": {0: "off", 1: "autoonly", 2: "on"},
    "hpStandby": {False: "false", True: "true"},
    "freeCoolingEnabled": {False: "false", True: "true"},
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]

    sensors = []
    coordinator = data["coordinator"]
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.warning(f"Dashboard-Daten konnten nicht geladen werden: {e}")

    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    main_device = hass.data[DOMAIN][entry.entry_id]["main_device"]
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
            entity_category=sensor_def.get("entity_category"),
            device=main_device,
            entry=entry,
        )
        for sensor_def in DASHBOARD_SENSORS
    ]
    sensors.extend(sensor_list)
    # ThermalProfile-Sensoren
    tp_coordinator = data["tpcoordinator"]
    sensor_list = [
        ComfoClimeSensor(
            hass=hass,
            coordinator=tp_coordinator,
            api=api,
            sensor_type=sensor_def["key"],
            name=sensor_def["name"],
            translation_key=sensor_def["translation_key"],
            unit=sensor_def.get("unit"),
            device_class=sensor_def.get("device_class"),
            state_class=sensor_def.get("state_class"),
            entity_category=sensor_def.get("entity_category"),
            device=main_device,
            entry=entry,
        )
        for sensor_def in THERMALPROFILE_SENSORS
    ]
    sensors.extend(sensor_list)

    # Feste Telemetrie-Sensoren für das ComfoClime-Gerät
    sensors.extend(
        ComfoClimeTelemetrySensor(
            hass=hass,
            api=api,
            telemetry_id=sensor_def["id"],
            name=sensor_def["name"],
            translation_key=sensor_def.get("translation_key", False),
            unit=sensor_def.get("unit"),
            faktor=sensor_def.get("faktor", 1.0),
            signed=sensor_def.get("signed", True),
            byte_count=sensor_def.get("byte_count"),
            device_class=sensor_def.get("device_class"),
            state_class=sensor_def.get("state_class"),
            entity_category=sensor_def.get("entity_category"),
            entry=entry,
        )
        for sensor_def in TELEMETRY_SENSORS
    )

    # Verbundene Geräte abrufen
    try:
        devices = hass.data[DOMAIN][entry.entry_id]["devices"]
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
                            translation_key=sensor_def.get("translation_key", False),
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
                translation_key=prop_def.get("translation_key", False),
                unit=prop_def.get("unit"),
                faktor=prop_def.get("faktor", 1.0),
                signed=prop_def.get("signed", True),
                byte_count=prop_def.get("byte_count"),
                mapping_key=prop_def.get("mapping_key", ""),
                device_class=prop_def.get("device_class"),
                state_class=prop_def.get("state_class"),
                entity_category=prop_def.get("entity_category"),
                device=device,
                override_device_uuid=dev_uuid,
                entry=entry,
            )
            for prop_def in property_defs
        )
    async_add_entities(sensors, True)


class ComfoClimeSensor(CoordinatorEntity[ComfoClimeDashboardCoordinator], SensorEntity):
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
        entity_category=None,
        device=None,
        entry=None,
    ):
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._type = sensor_type
        self._name = name
        self._state = None
        self._raw_state = None
        self._raw_value = None
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        # Determine if this is a thermal profile sensor based on coordinator type
        is_thermal_profile = isinstance(coordinator, ComfoClimeThermalprofileCoordinator)
        prefix = "thermalprofile" if is_thermal_profile else "dashboard"
        self._attr_unique_id = f"{entry.entry_id}_{prefix}_{sensor_type.replace('.', '_')}"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        """Gibt zusätzliche Attribute zurück."""
        return {
            "raw_value": self._raw_value
        }

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
        try:
            data = self.coordinator.data

            # raw_value wurde ermittelt
            self._raw_value = data

            # Handle nested keys (e.g., "season.status" or "heatingThermalProfileSeasonData.comfortTemperature")
            if "." in self._type:
                keys = self._type.split(".")
                raw_value = data
                for key in keys:
                    if isinstance(raw_value, dict) and key in raw_value:
                        raw_value = raw_value[key]
                    else:
                        raw_value = None
                        break
            else:
                raw_value = data.get(self._type)

            # Wenn es eine definierte Übersetzung gibt, wende sie an
            if self._type in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._type].get(raw_value, raw_value)
            else:
                self._state = raw_value

        except Exception as e:
            _LOGGER.warning(f"Fehler beim Aktualisieren der Sensorwerte: {e}")
            self._state = None

        self.async_write_ha_state()


class ComfoClimeTelemetrySensor(SensorEntity):
    """Sensor for telemetry data with optimized update throttling."""
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
        state_class=None,
        entity_category=None,
        device=None,
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
        self._attr_device_class = SensorDeviceClass(device_class) if device_class else None
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = EntityCategory(entity_category) if entity_category else None
        self._device = device
        self._override_uuid = override_device_uuid
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_telemetry_{telemetry_id}"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True
        # Throttle to 60 seconds to avoid excessive API calls
        self._last_update = None

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
        """Update with throttling to prevent excessive API calls."""
        current_time = asyncio.get_event_loop().time()

        # Only update once per 60 seconds per sensor
        if self._last_update is not None and (current_time - self._last_update) < 60:
            return

        try:
            self._state = await self._api.async_read_telemetry_for_device(
                device_uuid=self._override_uuid or self._api.uuid,
                telemetry_id=self._id,
                faktor=self._faktor,
                signed=self._signed,
                byte_count=self._byte_count,
            )
            self._last_update = current_time
        except Exception:
            _LOGGER.exception("Fehler beim Aktualisieren von Telemetrie %s", self._id)


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
        entity_category: str | None = None,
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
        self._attr_device_class = SensorDeviceClass(device_class) if device_class else None
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = EntityCategory(entity_category) if entity_category else None
        self._mapping_key = mapping_key
        self._device = device
        self._override_uuid = override_device_uuid
        self._state = None
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_property_{path.replace('/', '_')}"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True
        # Throttle to 60 seconds to avoid excessive API calls
        self._last_update = None

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
        """Update with throttling to prevent excessive API calls."""
        current_time = asyncio.get_event_loop().time()

        # Only update once per 60 seconds per sensor
        if self._last_update is not None and (current_time - self._last_update) < 60:
            return

        try:
            value = await asyncio.wait_for(
                self._api.async_read_property_for_device(
                    device_uuid=self._override_uuid or self._api.uuid,
                    property_path=self._path,
                    faktor=self._faktor,
                    signed=self._signed,
                    byte_count=self._byte_count,
                ),
                timeout=5.0
            )
            if self._mapping_key and self._mapping_key in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._mapping_key].get(value, value)
            else:
                self._state = value
            self._last_update = current_time
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout beim Abrufen von Property %s", self._path)
            self._state = None
        except Exception:
            _LOGGER.debug("Fehler beim Abrufen von Property %s", self._path, exc_info=True)
            self._state = None
