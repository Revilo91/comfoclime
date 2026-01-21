import logging

import aiohttp
import asyncio
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .access_tracker import AccessTracker
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    TELEMETRY_SENSORS,
    THERMALPROFILE_SENSORS,
)
from .entity_helper import is_entity_category_enabled, is_entity_enabled

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
    coordinator: ComfoClimeDashboardCoordinator = data["coordinator"]
    tlcoordinator: ComfoClimeTelemetryCoordinator = data["tlcoordinator"]
    propcoordinator: ComfoClimePropertyCoordinator = data["propcoordinator"]
    definitioncoordinator: ComfoClimeDefinitionCoordinator = data[
        "definitioncoordinator"
    ]

    # Note: Coordinator first refresh is already done in __init__.py
    # We don't need to await it here to avoid blocking sensor setup
    devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    main_device = hass.data[DOMAIN][entry.entry_id]["main_device"]

    # Dashboard-Sensoren
    if is_entity_category_enabled(entry.options, "sensors", "dashboard"):
        for sensor_def in DASHBOARD_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "dashboard", sensor_def):
                sensors.append(
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
                )

    # ThermalProfile-Sensoren
    thermalprofile_coordinator: ComfoClimeThermalprofileCoordinator = data[
        "tpcoordinator"
    ]
    if is_entity_category_enabled(entry.options, "sensors", "thermalprofile"):
        for sensor_def in THERMALPROFILE_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "thermalprofile", sensor_def):
                sensors.append(
                    ComfoClimeSensor(
                        hass=hass,
                        coordinator=thermalprofile_coordinator,
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
                )

    # Monitoring-Sensoren (uptime, etc.)
    monitoring_coordinator: ComfoClimeMonitoringCoordinator = data.get(
        "monitoringcoordinator"
    )
    if monitoring_coordinator and is_entity_category_enabled(
        entry.options, "sensors", "monitoring"
    ):
        for sensor_def in MONITORING_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "monitoring", sensor_def):
                sensors.append(
                    ComfoClimeSensor(
                        hass=hass,
                        coordinator=monitoring_coordinator,
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
                )

    # Feste Telemetrie-Sensoren für das ComfoClime-Gerät (from TELEMETRY_SENSORS)
    for sensor_def in TELEMETRY_SENSORS:
        device_uuid = api.uuid or (main_device.get("uuid") if main_device else None)
        if device_uuid:
            await tlcoordinator.register_telemetry(
                device_uuid=device_uuid,
                telemetry_id=str(sensor_def["id"]),
                faktor=sensor_def.get("faktor", 1.0),
                signed=sensor_def.get("signed", True),
                byte_count=sensor_def.get("byte_count"),
            )
            sensors.append(
                ComfoClimeTelemetrySensor(
                    hass=hass,
                    coordinator=tlcoordinator,
                    telemetry_id=sensor_def["id"],
                    name=sensor_def["name"],
                    translation_key=sensor_def.get("translation_key", False),
                    unit=sensor_def.get("unit"),
                    faktor=sensor_def.get("faktor", 1.0),
                    byte_count=sensor_def.get("byte_count"),
                    device_class=sensor_def.get("device_class"),
                    state_class=sensor_def.get("state_class"),
                    entity_category=sensor_def.get("entity_category"),
                    override_device_uuid=device_uuid,
                    entry=entry,
                )
            )

    # Verbundene Geräte abrufen
    try:
        devices = hass.data[DOMAIN][entry.entry_id]["devices"]
    except KeyError as e:
        _LOGGER.warning("Could not load connected devices: %s", e)
        devices = []

    for device in devices:
        model_id = device.get("modelTypeId")
        dev_uuid = device.get("uuid")
        if dev_uuid == "NULL":
            continue

        sensor_defs = CONNECTED_DEVICE_SENSORS.get(model_id)
        if sensor_defs and is_entity_category_enabled(entry.options, "sensors", "connected_telemetry"):
            for sensor_def in sensor_defs:
                # Check if this individual sensor is enabled
                if not is_entity_enabled(entry.options, "sensors", "connected_telemetry", sensor_def):
                    continue
                
                # Always create entities, but diagnostic ones are disabled by default
                # unless enable_diagnostics is True
                is_diagnose = sensor_def.get("diagnose", False)
                enabled_default = not is_diagnose or entry.options.get(
                    "enable_diagnostics", False
                )
                
                # Register telemetry with coordinator for batched fetching
                await tlcoordinator.register_telemetry(
                    device_uuid=dev_uuid,
                    telemetry_id=str(sensor_def["telemetry_id"]),
                    faktor=sensor_def.get("faktor", 1.0),
                    signed=sensor_def.get("signed", True),
                    byte_count=sensor_def.get("byte_count"),
                )
                sensors.append(
                    ComfoClimeTelemetrySensor(
                        hass=hass,
                        coordinator=tlcoordinator,
                        telemetry_id=sensor_def["telemetry_id"],
                        name=sensor_def["name"],
                        translation_key=sensor_def.get("translation_key", False),
                        unit=sensor_def.get("unit"),
                        faktor=sensor_def.get("faktor", 1.0),
                        byte_count=sensor_def.get("byte_count"),
                        device_class=sensor_def.get("device_class"),
                        device=device,
                        state_class=sensor_def.get("state_class"),
                        override_device_uuid=dev_uuid,
                        entry=entry,
                        entity_registry_enabled_default=enabled_default,
                    )
                )

        property_defs = CONNECTED_DEVICE_PROPERTIES.get(model_id)
        if property_defs and is_entity_category_enabled(entry.options, "sensors", "connected_properties"):
            for prop_def in property_defs:
                # Check if this individual property sensor is enabled
                if not is_entity_enabled(entry.options, "sensors", "connected_properties", prop_def):
                    continue
                
                # Register property with coordinator for batched fetching
                await propcoordinator.register_property(
                    device_uuid=dev_uuid,
                    property_path=prop_def["path"],
                    faktor=prop_def.get("faktor", 1.0),
                    signed=prop_def.get("signed", True),
                    byte_count=prop_def.get("byte_count"),
                )
                sensors.append(
                    ComfoClimePropertySensor(
                        hass=hass,
                        coordinator=propcoordinator,
                        path=prop_def["path"],
                        name=prop_def["name"],
                        translation_key=prop_def.get("translation_key", False),
                        unit=prop_def.get("unit"),
                        faktor=prop_def.get("faktor", 1.0),
                        byte_count=prop_def.get("byte_count"),
                        mapping_key=prop_def.get("mapping_key", ""),
                        device_class=prop_def.get("device_class"),
                        state_class=prop_def.get("state_class"),
                        entity_category=prop_def.get("entity_category"),
                        device=device,
                        override_device_uuid=dev_uuid,
                        entry=entry,
                    )
                )

        # Definition-based sensors (from /device/{UUID}/definition endpoint)
        definition_defs = CONNECTED_DEVICE_DEFINITION_SENSORS.get(model_id)
        if definition_defs and is_entity_category_enabled(entry.options, "sensors", "connected_definition"):
            for def_sensor_def in definition_defs:
                # Check if this individual definition sensor is enabled
                if not is_entity_enabled(entry.options, "sensors", "connected_definition", def_sensor_def):
                    continue
                
                sensors.append(
                    ComfoClimeDefinitionSensor(
                        hass=hass,
                        coordinator=definitioncoordinator,
                        key=def_sensor_def["key"],
                        name=def_sensor_def["name"],
                        translation_key=def_sensor_def.get("translation_key", False),
                        unit=def_sensor_def.get("unit"),
                        device_class=def_sensor_def.get("device_class"),
                        state_class=def_sensor_def.get("state_class"),
                        entity_category=def_sensor_def.get("entity_category"),
                        device=device,
                        override_device_uuid=dev_uuid,
                        entry=entry,
                    )
                )

    # Access tracking sensors for monitoring API access patterns
    access_tracker: AccessTracker = data["access_tracker"]
    if is_entity_category_enabled(entry.options, "sensors", "access_tracking"):
        for sensor_def in ACCESS_TRACKING_SENSORS:
            # Check if this individual access tracking sensor is enabled
            if not is_entity_enabled(entry.options, "sensors", "access_tracking", sensor_def):
                continue
            
            sensors.append(
                ComfoClimeAccessTrackingSensor(
                    hass=hass,
                    access_tracker=access_tracker,
                    coordinator_name=sensor_def.get("coordinator"),
                    metric=sensor_def["metric"],
                    name=sensor_def["name"],
                    translation_key=sensor_def.get("translation_key", False),
                    state_class=sensor_def.get("state_class"),
                    entity_category=sensor_def.get("entity_category"),
                    device=main_device,
                    entry=entry,
                )
            )

    # Add entities immediately without waiting for data
    # Coordinators will fetch data on their regular update interval
    # This prevents timeout issues during setup with many devices
    async_add_entities(sensors, True)
    
    # Schedule background refresh of coordinators after entities are added
    # This avoids blocking the setup process
    async def _refresh_coordinators():
        """Background task to refresh coordinators after entities are added."""
        try:
            await tlcoordinator.async_config_entry_first_refresh()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            _LOGGER.debug("Telemetry data could not be loaded: %s", e)
        
        try:
            await propcoordinator.async_config_entry_first_refresh()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            _LOGGER.debug("Property data could not be loaded: %s", e)
    
    # Run coordinator refresh in background
    hass.async_create_task(_refresh_coordinators())


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
        self._attr_device_class = (
            SensorDeviceClass(device_class) if device_class else None
        )
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = (
            EntityCategory(entity_category) if entity_category else None
        )
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        # Determine if this is a thermal profile sensor based on coordinator type
        is_thermal_profile = isinstance(
            coordinator, ComfoClimeThermalprofileCoordinator
        )
        prefix = "thermalprofile" if is_thermal_profile else "dashboard"
        self._attr_unique_id = (
            f"{entry.entry_id}_{prefix}_{sensor_type.replace('.', '_')}"
        )
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
        return {"raw_value": self._raw_value}

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

            # raw_value wurde ermittelt
            self._raw_value = raw_value

            # Wenn es eine definierte Übersetzung gibt, wende sie an
            if self._type in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._type].get(raw_value, raw_value)
            else:
                self._state = raw_value

        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.warning("Error updating sensor values: %s", e)
            self._state = None

        self.async_write_ha_state()


class ComfoClimeTelemetrySensor(
    CoordinatorEntity[ComfoClimeTelemetryCoordinator], SensorEntity
):
    """Sensor for telemetry data using coordinator for batched fetching."""

    def __init__(
        self,
        hass,
        coordinator: ComfoClimeTelemetryCoordinator,
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
        entity_registry_enabled_default=True,
    ):
        super().__init__(coordinator)
        self._hass = hass
        self._id = str(telemetry_id)
        self._name = name
        self._faktor = faktor
        self._byte_count = byte_count
        self._signed = signed
        self._state = None
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = (
            SensorDeviceClass(device_class) if device_class else None
        )
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = (
            EntityCategory(entity_category) if entity_category else None
        )
        self._device = device
        self._override_uuid = override_device_uuid
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_telemetry_{telemetry_id}"
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default
        if not translation_key:
            self._attr_name = name
        else:
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
            name=self._device.get("displayName", "ComfoClime Device"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_telemetry_value(self._override_uuid, self._id)
            self._state = value
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug(
                "Error updating telemetry %s", self._id, exc_info=True
            )
            self._state = None
        self.async_write_ha_state()


class ComfoClimePropertySensor(
    CoordinatorEntity[ComfoClimePropertyCoordinator], SensorEntity
):
    """Sensor for property data using coordinator for batched fetching."""

    def __init__(
        self,
        hass,
        coordinator: ComfoClimePropertyCoordinator,
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
        super().__init__(coordinator)
        self._hass = hass
        self._path = path
        self._name = name
        self._faktor = faktor
        self._byte_count = byte_count
        self._signed = signed
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = (
            SensorDeviceClass(device_class) if device_class else None
        )
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = (
            EntityCategory(entity_category) if entity_category else None
        )
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_property_value(self._override_uuid, self._path)
            if self._mapping_key and self._mapping_key in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._mapping_key].get(value, value)
            else:
                self._state = value
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Error fetching property %s", self._path, exc_info=True)
            self._state = None
        self.async_write_ha_state()


class ComfoClimeDefinitionSensor(
    CoordinatorEntity[ComfoClimeDefinitionCoordinator], SensorEntity
):
    """Sensor for definition data using coordinator for batched fetching."""

    def __init__(
        self,
        hass,
        coordinator: ComfoClimeDefinitionCoordinator,
        key: str,
        name: str,
        translation_key: str,
        *,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        entity_category: str | None = None,
        device: dict | None = None,
        override_device_uuid: str | None = None,
        entry: ConfigEntry,
    ):
        super().__init__(coordinator)
        self._hass = hass
        self._key = key
        self._name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = (
            SensorDeviceClass(device_class) if device_class else None
        )
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = (
            EntityCategory(entity_category) if entity_category else None
        )
        self._device = device
        self._override_uuid = override_device_uuid
        self._state = None
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = (
            f"{entry.entry_id}_definition_{override_device_uuid}_{key}"
        )
        if not translation_key:
            self._attr_name = name
        else:
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            definition_data = self.coordinator.get_definition_data(self._override_uuid)
            if definition_data:
                self._state = definition_data.get(self._key)
            else:
                self._state = None
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug(
                "Error retrieving definition %s", self._key, exc_info=True
            )
            self._state = None
        self.async_write_ha_state()


class ComfoClimeAccessTrackingSensor(SensorEntity):
    """Sensor for tracking API access patterns per coordinator.

    These sensors expose the number of API accesses per minute and per hour
    for each coordinator, helping users monitor and optimize API access patterns.
    """

    def __init__(
        self,
        hass,
        access_tracker: AccessTracker,
        coordinator_name: str | None,
        metric: str,
        name: str,
        translation_key: str,
        *,
        state_class: str | None = None,
        entity_category: str | None = None,
        device: dict | None = None,
        entry: ConfigEntry,
    ):
        """Initialize the access tracking sensor.

        Args:
            hass: Home Assistant instance.
            access_tracker: The AccessTracker instance to get data from.
            coordinator_name: Name of the coordinator to track, or None for totals.
            metric: The metric type (per_minute, per_hour, total_per_minute, total_per_hour).
            name: Human-readable name for the sensor.
            translation_key: Translation key for localization.
            state_class: Sensor state class.
            entity_category: Entity category (e.g., diagnostic).
            device: Device information dict.
            entry: Config entry.
        """
        self._hass = hass
        self._access_tracker = access_tracker
        self._coordinator_name = coordinator_name
        self._metric = metric
        self._name = name
        self._state = 0
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = (
            EntityCategory(entity_category) if entity_category else None
        )
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id

        # Build unique_id based on coordinator and metric
        if coordinator_name:
            self._attr_unique_id = (
                f"{entry.entry_id}_access_{coordinator_name.lower()}_{metric}"
            )
        else:
            self._attr_unique_id = f"{entry.entry_id}_access_{metric}"

        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

        # These sensors don't have a native unit (they count accesses)
        self._attr_native_unit_of_measurement = None

    @property
    def native_value(self):
        """Return the current value of the sensor."""
        return self._state

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this sensor."""
        if not self._device:
            return None

        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    @property
    def should_poll(self) -> bool:
        """Return True as we need to poll to get updated access counts."""
        return True

    async def async_update(self) -> None:
        """Update the sensor state from the access tracker."""
        try:
            if self._metric == "per_minute":
                self._state = self._access_tracker.get_accesses_per_minute(
                    self._coordinator_name
                )
            elif self._metric == "per_hour":
                self._state = self._access_tracker.get_accesses_per_hour(
                    self._coordinator_name
                )
            elif self._metric == "total_per_minute":
                self._state = self._access_tracker.get_total_accesses_per_minute()
            elif self._metric == "total_per_hour":
                self._state = self._access_tracker.get_total_accesses_per_hour()
            else:
                self._state = 0
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug(
                "Error updating access tracking sensor %s", self._name, exc_info=True
            )
            self._state = 0

    @property
    def extra_state_attributes(self):
        """Return additional attributes with detailed access information."""
        if self._coordinator_name:
            return {
                "coordinator": self._coordinator_name,
                "metric": self._metric,
                "total_accesses": self._access_tracker.get_total_accesses(
                    self._coordinator_name
                ),
            }
        return {
            "metric": self._metric,
            "summary": self._access_tracker.get_summary(),
        }
