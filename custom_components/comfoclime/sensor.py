import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)

DASHBOARD_SENSORS = [
    {
        "key": "indoorTemperature",
        "name": "Indoor Temperature",
        "translation_key": "indoor_temperature",
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    {
        "key": "outdoorTemperature",
        "name": "Outdoor Temperature",
        "translation_key": "outdoor_temperature",
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    {
        "key": "exhaustAirFlow",
        "name": "Exhaust Air Flow",
        "translation_key": "exhaust_air_flow",
        "unit": "m³/h",
        "state_class": "measurement",
        "device_class": "volume_flow_rate",
    },
    {
        "key": "supplyAirFlow",
        "name": "Supply Air Flow",
        "translation_key": "supply_air_flow",
        "unit": "m³/h",
        "state_class": "measurement",
        "device_class": "volume_flow_rate",
    },
    {
        "key": "fanSpeed",
        "name": "Fan Speed",
        "translation_key": "fan_speed",
    },
    {
        "key": "season",
        "name": "Season",
        "translation_key": "season",
    },
    {
        "key": "temperatureProfile",
        "name": "Temperature Profile",
        "translation_key": "temperature_profile",
    },
    {
        "key": "heatPumpStatus",
        "name": "Heat Pump Status",
        "translation_key": "heat_pump_status",
    },
]

VALUE_MAPPINGS = {
    "temperatureProfile": {0: "Comfort", 1: "Power", 2: "Eco"},
    "season": {0: "Transitional", 1: "Heating", 2: "Cooling"},
    "heatPumpStatus": {0: "Off", 1: "Heating", 2: "Cooling"},
    "humidityMode": {0: "Off", 1: "AutoOnly", 2: "On"},
}

TELEMETRY_SENSORS = []

CONNECTED_DEVICE_SENSORS = {
    20: [
        {
            "telemetry_id": 4193,
            "name": "Supply Air Temperature",
            "translation_key": "supply_air_temperature",
            "unit": "°C",
            "faktor": 0.1,
            "signed": True,
            "byte_count": 2,
            "device_class": "temperature",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 4145,
            "name": "TPMA Temperature",
            "translation_key": "tpma_temperature",
            "unit": "°C",
            "faktor": 0.1,
            "signed": True,
            "byte_count": 2,
            "device_class": "temperature",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 4151,
            "name": "Current Comfort Temperature",
            "translation_key": "current_comfort_temperature",
            "unit": "°C",
            "faktor": 0.1,
            "signed": True,
            "byte_count": 2,
            "device_class": "temperature",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 4201,
            "name": "Power Heatpump",
            "translation_key": "power_heatpump",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
        },
    ],
    1: [
        {
            "telemetry_id": 128,
            "name": "Power Ventilation",
            "translation_key": "power_ventilation",
            "unit": "W",
            "device_class": "power",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 227,
            "name": "Bypass State",
            "translation_key": "bypass_state",
            "unit": "%",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 117,
            "name": "Exhaust Fan Duty",
            "translation_key": "exhaust_fan_duty",
            "unit": "%",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 118,
            "name": "Supply Fan Duty",
            "translation_key": "supply_fan_duty",
            "unit": "%",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 121,
            "name": "Exhaust Fan Speed",
            "translation_key": "exhaust_fan_speed",
            "unit": "rpm",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 122,
            "name": "Supply Fan Speed",
            "translation_key": "supply_fan_speed",
            "unit": "rpm",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 129,
            "name": "Energy YTD",
            "translation_key": "energy_ytd",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
        },
        {
            "telemetry_id": 130,
            "name": "Energy Total",
            "translation_key": "energy_total",
            "unit": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
        },
    ],
}

CONNECTED_DEVICE_PROPERTIES = {
    1: [
        {
            "path": "30/1/18",  # X/Y/Z
            "name": "Ventilation Disbalance",
            "translation_key": "ventilation_disbalance",
            "unit": "%",
            "faktor": 0.1,
            "signed": True,
            "byte_count": 2,
        },
        {
            "path": "29/1/6",  # X/Y/Z
            "name": "Humidity Comfort Control",
            "translation_key": "humidity_comfort_control",
            "signed": False,
            "byte_count": 1,
            "mapping_key": "humidityMode",
        },
        {
            "path": "29/1/7",  # X/Y/Z
            "name": "Humidity Protection",
            "translation_key": "humidity_protection",
            "signed": False,
            "byte_count": 1,
            "mapping_key": "humidityMode",
        },
    ],
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
    try:
        await api.async_get_dashboard_data(hass)
    except Exception as e:
        _LOGGER.warning(f"Dashboard-Daten konnten nicht geladen werden: {e}")

    devices = await api.async_get_connected_devices(hass)

    # Hauptgerät (modelTypeId 20)
    main_device = next((d for d in devices if d.get("modelTypeId") == 20), None)
    # Dashboard-Sensoren
    sensors.extend(
        ComfoClimeSensor(
            hass=hass,
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
    )

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

        sensors.extend(
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
            for sensor_def in sensor_defs
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


class ComfoClimeSensor(SensorEntity):
    def __init__(
        self,
        hass,
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
        _LOGGER.debug(
            f"{self._attr_unique_id} translation_key: {self._attr_translation_key}, device_info: {self.device_info}"
        )

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
            data = await self._api.async_get_dashboard_data(self._hass)

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
        _LOGGER.debug(f"Translation-Key für Sensor: {self._attr_translation_key}")

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
        _LOGGER.debug(f"Translation-Key für Sensor: {self._attr_translation_key}")

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
