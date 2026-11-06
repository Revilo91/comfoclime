"""ComfoClime Sensor Platform.

This module provides Home Assistant sensor entities for ComfoClime
integration. Sensors display various device data including temperatures,
telemetry values, properties, and system status.

The sensor platform supports multiple sensor types:
    - Dashboard Sensors: Real-time data (temperature, fan speed, etc.)
    - Thermalprofile Sensors: Thermal profile settings
    - Monitoring Sensors: Device uptime and health
    - Telemetry Sensors: Device-specific telemetry data
    - Property Sensors: Device-specific property values
    - Definition Sensors: Device definition data

Every sensor this integration knows about is created. Which of them are
visible is Home Assistant's business, not ours: standard sensors start
enabled, config and diagnostic ones start disabled, and the user flips
individual entities in the entity registry. Telemetry and property sensors
register with their batching coordinator only once they are actually added
to Home Assistant, so a disabled sensor costs no API requests at all.

Example:
    >>> # Dashboard sensor values
    >>> indoor_temp = hass.states.get("sensor.comfoclime_indoor_temperature").state
    >>> # Telemetry sensor for connected device
    >>> device_temp = hass.states.get("sensor.device_temperature").state

Note:
    Sensors use multiple coordinators depending on their data source:
    - Dashboard, Monitoring, Thermalprofile coordinators for system data
    - Telemetry and Property coordinators for batched device data
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pydantic import BaseModel

from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entities.base_definitions import enabled_by_default, entity_category_for
from .entities.sensor_definitions import (
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    THERMALPROFILE_SENSORS,
)
from .entity_base import ComfoClimeBaseEntity
from .entity_helper import (
    get_device_model_type_id,
    get_device_uuid,
)
from .models import uptime_to_boot_time

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .comfoclime_api import ComfoClimeAPI
    from .models import DeviceConfig
    from .runtime_data import ComfoClimeConfigEntry

_LOGGER = logging.getLogger(__name__)


VALUE_MAPPINGS = {
    "temperatureProfile": {0: "comfort", 1: "power", 2: "eco"},
    "season": {0: "transitional", 1: "heating", 2: "cooling"},
    "humidityMode": {0: "off", 1: "autoonly", 2: "on"},
    "hpStandby": {False: "false", True: "true"},
    "freeCoolingEnabled": {False: "false", True: "true"},
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ComfoClimeConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up ComfoClime sensor entities from a config entry.

    Creates every sensor supported for the devices found on the bus:
        - Dashboard: System temperatures, fan speed, season, etc.
        - Thermalprofile: Thermal profile settings
        - Monitoring: Device uptime and health
        - Telemetry: Device-specific telemetry data (batched)
        - Property: Device-specific property values (batched)
        - Definition: Device definition data

    Nothing is filtered here. Definitions carry an entity category, and
    anything categorised as config or diagnostic is registered disabled so
    the user can enable exactly what they want per entity.

    Args:
        hass: Home Assistant instance
        entry: Config entry for this integration
        async_add_entities: Callback to add entities
    """
    data = entry.runtime_data
    api = data.api

    sensors: list[SensorEntity] = []
    coordinator: ComfoClimeDashboardCoordinator = data.coordinator
    thermalprofile_coordinator: ComfoClimeThermalprofileCoordinator = data.tpcoordinator
    monitoring_coordinator: ComfoClimeMonitoringCoordinator | None = data.monitoringcoordinator
    tlcoordinator: ComfoClimeTelemetryCoordinator = data.tlcoordinator
    propcoordinator: ComfoClimePropertyCoordinator = data.propcoordinator
    definitioncoordinator: ComfoClimeDefinitionCoordinator = data.definitioncoordinator

    devices = data.devices or []
    main_device = data.main_device

    # Sensors served straight off a whole-response coordinator.
    system_sources: list[tuple[Any, list]] = [
        (coordinator, DASHBOARD_SENSORS),
        (thermalprofile_coordinator, THERMALPROFILE_SENSORS),
    ]
    if monitoring_coordinator is not None:
        system_sources.append((monitoring_coordinator, MONITORING_SENSORS))

    for source_coordinator, sensor_defs in system_sources:
        for sensor_def in sensor_defs:
            sensors.append(
                ComfoClimeSensor(
                    hass=hass,
                    coordinator=source_coordinator,
                    api=api,
                    sensor_type=sensor_def.key,
                    name=sensor_def.name,
                    translation_key=sensor_def.translation_key,
                    unit=sensor_def.unit,
                    device_class=sensor_def.device_class,
                    state_class=sensor_def.state_class,
                    entity_category=entity_category_for(sensor_def),
                    device=main_device,
                    entry=entry,
                    entity_registry_enabled_default=enabled_by_default(sensor_def),
                )
            )

    for device in devices:
        model_id = get_device_model_type_id(device)
        dev_uuid = get_device_uuid(device)
        if not dev_uuid or dev_uuid == "NULL":
            continue

        for sensor_def in CONNECTED_DEVICE_SENSORS.get(model_id, []):
            sensors.append(
                ComfoClimeTelemetrySensor(
                    hass=hass,
                    coordinator=tlcoordinator,
                    telemetry_id=sensor_def.telemetry_id,
                    name=sensor_def.name,
                    translation_key=sensor_def.translation_key,
                    unit=sensor_def.unit,
                    faktor=sensor_def.faktor,
                    signed=sensor_def.signed,
                    byte_count=sensor_def.byte_count,
                    device_class=sensor_def.device_class,
                    device=device,
                    state_class=sensor_def.state_class,
                    entity_category=entity_category_for(sensor_def),
                    override_device_uuid=dev_uuid,
                    entry=entry,
                    entity_registry_enabled_default=enabled_by_default(sensor_def),
                )
            )

        for prop_def in CONNECTED_DEVICE_PROPERTIES.get(model_id, []):
            sensors.append(
                ComfoClimePropertySensor(
                    hass=hass,
                    coordinator=propcoordinator,
                    path=prop_def.path,
                    name=prop_def.name,
                    translation_key=prop_def.translation_key,
                    unit=prop_def.unit,
                    faktor=prop_def.faktor,
                    signed=prop_def.signed,
                    byte_count=prop_def.byte_count,
                    mapping_key="",
                    device_class=prop_def.device_class,
                    state_class=prop_def.state_class,
                    entity_category=entity_category_for(prop_def),
                    device=device,
                    override_device_uuid=dev_uuid,
                    entry=entry,
                    entity_registry_enabled_default=enabled_by_default(prop_def),
                )
            )

        for def_sensor_def in CONNECTED_DEVICE_DEFINITION_SENSORS.get(model_id, []):
            sensors.append(
                ComfoClimeDefinitionSensor(
                    hass=hass,
                    coordinator=definitioncoordinator,
                    key=def_sensor_def.key,
                    name=def_sensor_def.name,
                    translation_key=def_sensor_def.translation_key,
                    unit=def_sensor_def.unit,
                    device_class=def_sensor_def.device_class,
                    state_class=def_sensor_def.state_class,
                    entity_category=entity_category_for(def_sensor_def),
                    device=device,
                    override_device_uuid=dev_uuid,
                    entry=entry,
                    entity_registry_enabled_default=enabled_by_default(def_sensor_def),
                )
            )

    # Entities that are enabled register their telemetry/property needs in
    # async_added_to_hass and then ask for a (debounced) coordinator refresh,
    # so there is nothing to prefetch here.
    _LOGGER.debug("Adding %s sensor entities to Home Assistant", len(sensors))
    async_add_entities(sensors, True)


class ComfoClimeSensor(ComfoClimeBaseEntity, CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeDashboardCoordinator
        | ComfoClimeThermalprofileCoordinator
        | ComfoClimeMonitoringCoordinator,
        api: ComfoClimeAPI,
        sensor_type: str,
        name: str,
        translation_key: str | bool,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        entity_category: str | None = None,
        device: DeviceConfig | None = None,
        entry: ConfigEntry | None = None,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._type = sensor_type
        self._name = name
        self._state = None
        self._raw_state = None
        self._raw_value = None
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = SensorDeviceClass(device_class) if device_class else None
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = EntityCategory(entity_category) if entity_category else None
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        # Determine data source based on coordinator type
        if isinstance(coordinator, ComfoClimeThermalprofileCoordinator):
            data_source = "thermalprofile"
        elif isinstance(coordinator, ComfoClimeMonitoringCoordinator):
            data_source = "monitoring"
        else:
            data_source = "dashboard"
        self._data_source = data_source
        self._attr_unique_id = f"{entry.entry_id}_{data_source}_{sensor_type.replace('.', '_')}"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        return self._state

    def _handle_coordinator_update(self) -> None:
        try:
            data = self.coordinator.data

            # Handle nested keys (e.g., "season.status")
            if "." in self._type:
                keys = self._type.split(".")
                raw_value = self._extract_nested_value(data, keys)
            else:
                # Direct attribute access
                if isinstance(data, BaseModel):
                    snake_case_key = self._camel_to_snake(self._type)
                    raw_value = getattr(data, snake_case_key, None)
                elif isinstance(data, dict):
                    raw_value = data.get(self._type)
                else:
                    raw_value = None

            self._raw_value = raw_value

            # Die Geräte-API liefert Sekunden seit dem Start, Home Assistant
            # erwartet für diese Device-Class den Zeitpunkt des letzten Neustarts
            # als aware datetime (siehe models.uptime_to_boot_time).
            if self._attr_device_class is SensorDeviceClass.UPTIME:
                timestamp = data.get("timestamp") if isinstance(data, dict) else getattr(data, "timestamp", None)
                self._state = uptime_to_boot_time(raw_value, timestamp)
            # Wenn es eine definierte Übersetzung gibt, wende sie an
            elif self._type in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._type].get(raw_value, raw_value)
            else:
                self._state = raw_value

        except (KeyError, TypeError, ValueError) as e:
            _LOGGER.warning("Error updating sensor '%s' values: %s", self._name, e)
            self._state = None

        self.async_write_ha_state()


class ComfoClimeTelemetrySensor(ComfoClimeBaseEntity, CoordinatorEntity, SensorEntity):
    """Sensor for telemetry data using coordinator for batched fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeTelemetryCoordinator,
        telemetry_id: str | int,
        name: str,
        translation_key: str | bool,
        unit: str | None,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        entity_category: str | None = None,
        device: DeviceConfig | None = None,
        override_device_uuid: str | None = None,
        entry: ConfigEntry | None = None,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._id = str(telemetry_id)
        self._name = name
        self._faktor = faktor
        self._byte_count = byte_count
        self._signed = signed
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
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default
        self._data_source = "telemetry"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    async def _async_register_data_source(self) -> None:
        """Start polling this telemetry ID now that the entity is live."""
        if not self._override_uuid:
            return
        await self.coordinator.register_telemetry(
            device_uuid=self._override_uuid,
            telemetry_id=self._id,
            faktor=self._faktor,
            signed=self._signed,
            byte_count=self._byte_count,
        )
        await self._async_request_coordinator_refresh()

    async def _async_unregister_data_source(self) -> None:
        """Stop polling this telemetry ID once the entity goes away."""
        if self._override_uuid:
            await self.coordinator.unregister_telemetry(self._override_uuid, self._id)

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_telemetry_value(self._override_uuid, self._id)
            self._state = value
        except KeyError, TypeError, ValueError:
            _LOGGER.debug("Error updating telemetry %s", self._id, exc_info=True)
            self._state = None
        self.async_write_ha_state()


class ComfoClimePropertySensor(ComfoClimeBaseEntity, CoordinatorEntity, SensorEntity):
    """Sensor for property data using coordinator for batched fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimePropertyCoordinator,
        path: str,
        name: str,
        translation_key: str | bool,
        *,
        unit: str | None = None,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        entity_category: str | None = None,
        mapping_key: str | None = None,
        device: DeviceConfig | None = None,
        override_device_uuid: str | None = None,
        entry: ConfigEntry,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._path = path
        self._name = name
        self._faktor = faktor
        self._byte_count = byte_count
        self._signed = signed
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
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default
        self._data_source = "property"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    async def _async_register_data_source(self) -> None:
        """Start polling this property now that the entity is live."""
        if not self._override_uuid:
            return
        await self.coordinator.register_property(
            device_uuid=self._override_uuid,
            property_path=self._path,
            faktor=self._faktor,
            signed=self._signed,
            byte_count=self._byte_count,
        )
        await self._async_request_coordinator_refresh()

    async def _async_unregister_data_source(self) -> None:
        """Stop polling this property once the entity goes away."""
        if self._override_uuid:
            await self.coordinator.unregister_property(self._override_uuid, self._path)

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_property_value(self._override_uuid, self._path)
            if self._mapping_key and self._mapping_key in VALUE_MAPPINGS:
                self._state = VALUE_MAPPINGS[self._mapping_key].get(value, value)
            else:
                self._state = value
        except KeyError, TypeError, ValueError:
            _LOGGER.debug("Error fetching property %s", self._path, exc_info=True)
            self._state = None
        self.async_write_ha_state()


class ComfoClimeDefinitionSensor(ComfoClimeBaseEntity, CoordinatorEntity, SensorEntity):
    """Sensor for definition data using coordinator for batched fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ComfoClimeDefinitionCoordinator,
        key: str,
        name: str,
        translation_key: str | bool,
        *,
        unit: str | None = None,
        device_class: str | None = None,
        state_class: str | None = None,
        entity_category: str | None = None,
        device: DeviceConfig | None = None,
        override_device_uuid: str | None = None,
        entry: ConfigEntry,
        entity_registry_enabled_default: bool = True,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._key = key
        self._name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = SensorDeviceClass(device_class) if device_class else None
        self._attr_state_class = SensorStateClass(state_class) if state_class else None
        self._attr_entity_category = EntityCategory(entity_category) if entity_category else None
        self._device = device
        self._override_uuid = override_device_uuid
        self._state = None
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_definition_{override_device_uuid}_{key}"
        self._attr_entity_registry_enabled_default = entity_registry_enabled_default
        self._data_source = "definition"
        if not translation_key:
            self._attr_name = name
        else:
            self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            definition_data = self.coordinator.get_definition_data(self._override_uuid)
            if definition_data:
                if isinstance(definition_data, BaseModel):
                    snake_case_key = self._camel_to_snake(self._key)
                    self._state = getattr(definition_data, snake_case_key, None)
                else:
                    self._state = definition_data.get(self._key)
            else:
                self._state = None
        except KeyError, TypeError, ValueError:
            _LOGGER.debug("Error retrieving definition %s", self._key, exc_info=True)
            self._state = None
        self.async_write_ha_state()
