"""ComfoClime Data Update Coordinators.

This module provides Home Assistant data update coordinators for polling
ComfoClime device data at regular intervals. Each coordinator is responsible
for fetching a specific type of data and distributing it to entities.

The coordinators implement batched updates to minimize API load on the
Airduino board. Instead of each entity making individual API calls, the
coordinators fetch all required data in a single update cycle.

Available Coordinators:
    - ComfoClimeDashboardCoordinator: Real-time dashboard data (temp, fan, season)
    - ComfoClimeMonitoringCoordinator: Device monitoring data (uptime, UUID)
    - ComfoClimeThermalprofileCoordinator: Thermal profile settings
    - ComfoClimeTelemetryCoordinator: Batched telemetry data from all devices
    - ComfoClimePropertyCoordinator: Batched property data from all devices
    - ComfoClimeDefinitionCoordinator: Device definition data (mainly for ComfoAirQ)

Example:
    >>> coordinator = ComfoClimeDashboardCoordinator(hass, api)
    >>> await coordinator.async_config_entry_first_refresh()
    >>> dashboard_data = coordinator.data
    >>> print(f"Indoor temp: {dashboard_data.indoor_temperature}°C")

Note:
    All coordinators poll every 60 seconds by default (DEFAULT_POLLING_INTERVAL_SECONDS)
    to balance freshness and API load. This can be configured per coordinator.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .comfoclime_api import ComfoClimeAPI
    from .infrastructure import AccessTracker
    from .models import DashboardData, DeviceDefinitionData, MonitoringPing, ThermalProfileData

from .constants import API_DEFAULTS
from .models import PropertyRegistryEntry, TelemetryRegistryEntry

_LOGGER = logging.getLogger(__name__)

# Default polling interval to reduce API load on the Airduino board
DEFAULT_POLLING_INTERVAL_SECONDS = API_DEFAULTS.POLLING_INTERVAL


class ComfoClimeBaseCoordinator(DataUpdateCoordinator):
    """Base coordinator with shared init and update pattern.

    Subclasses only need to set ``_coordinator_name`` and implement
    ``_fetch_data()`` to return the result of the appropriate API call.
    """

    _coordinator_name: str = "Base"

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        name: str,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=polling_interval),
            config_entry=config_entry,
        )
        self.api = api
        self._access_tracker = access_tracker

    async def _fetch_data(self):
        """Fetch data from the API. Override in subclasses."""
        raise NotImplementedError

    async def _async_update_data(self):
        try:
            result = await self._fetch_data()
            if self._access_tracker:
                self._access_tracker.record_access(self._coordinator_name)
            return result
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.warning("Error fetching %s data: %s", self._coordinator_name, e)
            raise UpdateFailed(f"Error fetching {self._coordinator_name} data: {e}") from e


class ComfoClimeDashboardCoordinator(ComfoClimeBaseCoordinator):
    """Coordinator for fetching real-time dashboard data from ComfoClime device."""

    _coordinator_name = "Dashboard"

    def __init__(
        self,
        hass,
        api,
        polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ):
        super().__init__(
            hass, api, "ComfoClime Dashboard",
            polling_interval=polling_interval,
            access_tracker=access_tracker,
            config_entry=config_entry,
        )

    async def _fetch_data(self) -> DashboardData:
        return await self.api.async_get_dashboard_data()


class ComfoClimeMonitoringCoordinator(ComfoClimeBaseCoordinator):
    """Coordinator for fetching device monitoring and health data."""

    _coordinator_name = "Monitoring"

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass, api, "ComfoClime Monitoring",
            polling_interval=polling_interval,
            access_tracker=access_tracker,
            config_entry=config_entry,
        )

    async def _fetch_data(self) -> MonitoringPing:
        _LOGGER.debug("MonitoringCoordinator: Fetching monitoring data from API")
        result = await self.api.async_get_monitoring_ping()
        _LOGGER.debug("MonitoringCoordinator: Received data: %s", result)
        return result


class ComfoClimeThermalprofileCoordinator(ComfoClimeBaseCoordinator):
    """Coordinator for fetching thermal profile configuration data."""

    _coordinator_name = "Thermalprofile"

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        super().__init__(
            hass, api, "ComfoClime Thermalprofile",
            polling_interval=polling_interval,
            access_tracker=access_tracker,
            config_entry=config_entry,
        )

    async def _fetch_data(self) -> ThermalProfileData:
        return await self.api.async_get_thermal_profile()


class ComfoClimeTelemetryCoordinator(DataUpdateCoordinator):
    """Coordinator for batching telemetry requests from all devices.

    Instead of each sensor making individual API calls, this coordinator
    collects all telemetry requests and fetches them in a single batched
    update cycle. This significantly reduces API load on the Airduino board.

    Sensors register their telemetry needs using register_telemetry(), and
    the coordinator fetches all values during each update. Sensors then
    retrieve their values using get_telemetry_value().

    Attributes:
        api: ComfoClimeAPI instance for device communication
        devices: List of connected devices

    Example:
        >>> coordinator = ComfoClimeTelemetryCoordinator(hass, api, devices)
        >>> # Register a sensor
        >>> await coordinator.register_telemetry(
        ...     device_uuid="abc123",
        ...     telemetry_id="100",
        ...     faktor=0.1,
        ...     signed=True,
        ...     byte_count=2
        ... )
        >>> await coordinator.async_config_entry_first_refresh()
        >>> # Retrieve value
        >>> value = coordinator.get_telemetry_value("abc123", "100")
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        devices: list[dict[str, Any]] | None = None,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        """Initialize the telemetry data coordinator.

        Args:
            hass: Home Assistant instance
            api: ComfoClimeAPI instance for device communication
            devices: List of connected devices
            polling_interval: Update interval in seconds (default: 60)
            access_tracker: Optional access tracker for monitoring API calls
        """
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Telemetry",
            update_interval=timedelta(seconds=polling_interval),
            config_entry=config_entry,
        )
        self.api = api
        self.devices = devices or []
        self._access_tracker = access_tracker
        # Registry of telemetry requests: {device_uuid: {telemetry_id: TelemetryRegistryEntry}}
        self._telemetry_registry: dict[str, dict[str, TelemetryRegistryEntry]] = {}
        # Lock to prevent concurrent modifications during iteration
        self._registry_lock = asyncio.Lock()

    async def register_telemetry(
        self,
        device_uuid: str,
        telemetry_id: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> None:
        """Register a telemetry sensor to be fetched during updates.

        Sensors should call this during their initialization to register
        their telemetry needs. The coordinator will then fetch this value
        during each update cycle.

        Args:
            device_uuid: UUID of the device to read from
            telemetry_id: Telemetry sensor ID to fetch
            faktor: Scaling factor to multiply the raw value by (default: 1.0)
            signed: If True, interpret as signed integer (default: True)
            byte_count: Number of bytes to read (1 or 2, auto-detected if None)

        Example:
            >>> await coordinator.register_telemetry(
            ...     device_uuid="abc123",
            ...     telemetry_id="100",
            ...     faktor=0.1,  # Temperature in 0.1°C units
            ...     signed=True,
            ...     byte_count=2
            ... )
        """
        async with self._registry_lock:
            if device_uuid not in self._telemetry_registry:
                self._telemetry_registry[device_uuid] = {}

            self._telemetry_registry[device_uuid][str(telemetry_id)] = TelemetryRegistryEntry(
                faktor=faktor,
                signed=signed,
                byte_count=byte_count,
            )
            _LOGGER.debug("Registered telemetry %s for device %s", telemetry_id, device_uuid)

    async def _async_update_data(self) -> dict[str, DeviceDefinitionData]:
        """Fetch all registered telemetry data in a batched manner.

        Iterates through all registered telemetry sensors and fetches
        their values from the API. Failed reads are logged but don't
        fail the entire update.

        Returns:
            Nested dictionary: {device_uuid: {telemetry_id: value}}
            Values are None if read failed.
        """
        result: dict[str, dict[str, Any]] = {}

        async with self._registry_lock:
            # Create a snapshot of the registry while holding the lock
            registry_snapshot = {
                device_uuid: dict(telemetry_items) for device_uuid, telemetry_items in self._telemetry_registry.items()
            }

        # Now iterate over the snapshot without holding the lock
        for device_uuid, telemetry_items in registry_snapshot.items():
            result[device_uuid] = {}

            for telemetry_id, params in telemetry_items.items():
                try:
                    reading = await self.api.async_read_telemetry_for_device(
                        device_uuid=device_uuid,
                        telemetry_id=telemetry_id,
                        faktor=params.faktor,
                        signed=params.signed,
                        byte_count=params.byte_count,
                    )
                    # Store the scaled value for backward compatibility with sensors
                    result[device_uuid][telemetry_id] = reading.scaled_value if reading else None
                    # Track each individual API call
                    if self._access_tracker:
                        self._access_tracker.record_access("Telemetry")
                except (TimeoutError, aiohttp.ClientError) as e:
                    _LOGGER.debug(
                        "Error fetching telemetry %s for device %s: %s",
                        telemetry_id,
                        device_uuid,
                        e,
                    )
                    result[device_uuid][telemetry_id] = None

        return result

    def get_telemetry_value(self, device_uuid: str, telemetry_id: str | int) -> Any:
        """Get a cached telemetry value from the last update.

        Retrieves a telemetry value that was fetched during the last
        coordinator update. Returns None if the value doesn't exist or
        if the read failed.

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry sensor ID (string or int)

        Returns:
            The cached telemetry value, or None if not found/failed.

        Example:
            >>> temp = coordinator.get_telemetry_value("abc123", "100")
            >>> if temp is not None:
            ...     print(f"Temperature: {temp}°C")
        """
        if not self.data:
            return None

        device_data = self.data.get(device_uuid, {})
        return device_data.get(str(telemetry_id))


class ComfoClimePropertyCoordinator(DataUpdateCoordinator):
    """Coordinator for batching property requests from all devices.

    Instead of each sensor/number/select making individual API calls,
    this coordinator collects all property requests and fetches them
    in a single batched update cycle. This significantly reduces API
    load on the Airduino board.

    Entities register their property needs using register_property(), and
    the coordinator fetches all values during each update. Entities then
    retrieve their values using get_property_value().

    Attributes:
        api: ComfoClimeAPI instance for device communication
        devices: List of connected devices

    Example:
        >>> coordinator = ComfoClimePropertyCoordinator(hass, api, devices)
        >>> # Register a property
        >>> await coordinator.register_property(
        ...     device_uuid="abc123",
        ...     property_path="29/1/10",
        ...     faktor=0.1,
        ...     byte_count=2
        ... )
        >>> await coordinator.async_config_entry_first_refresh()
        >>> # Retrieve value
        >>> value = coordinator.get_property_value("abc123", "29/1/10")
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        devices: list[dict[str, Any]] | None = None,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        """Initialize the property data coordinator.

        Args:
            hass: Home Assistant instance
            api: ComfoClimeAPI instance for device communication
            devices: List of connected devices
            polling_interval: Update interval in seconds (default: 60)
            access_tracker: Optional access tracker for monitoring API calls
        """
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Properties",
            update_interval=timedelta(seconds=polling_interval),
            config_entry=config_entry,
        )
        self.api = api
        self.devices = devices or []
        self._access_tracker = access_tracker
        # Registry of property requests: {device_uuid: {path: PropertyRegistryEntry}}
        self._property_registry: dict[str, dict[str, PropertyRegistryEntry]] = {}
        # Lock to prevent concurrent modifications during iteration
        self._registry_lock = asyncio.Lock()

    async def register_property(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> None:
        """Register a property to be fetched during updates.

        Entities should call this during their initialization to register
        their property needs. The coordinator will then fetch this value
        during each update cycle.

        Args:
            device_uuid: UUID of the device to read from
            property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
            faktor: Scaling factor to multiply numeric values by (default: 1.0)
            signed: If True, interpret numeric values as signed (default: True)
            byte_count: Number of bytes (1-2 for numeric, 3+ for string)

        Example:
            >>> await coordinator.register_property(
            ...     device_uuid="abc123",
            ...     property_path="29/1/10",
            ...     faktor=0.1,
            ...     signed=True,
            ...     byte_count=2
            ... )
        """
        async with self._registry_lock:
            if device_uuid not in self._property_registry:
                self._property_registry[device_uuid] = {}

            self._property_registry[device_uuid][property_path] = PropertyRegistryEntry(
                faktor=faktor,
                signed=signed,
                byte_count=byte_count,
            )
            _LOGGER.debug("Registered property %s for device %s", property_path, device_uuid)

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all registered property data in a batched manner.

        Iterates through all registered properties and fetches their
        values from the API. Failed reads are logged but don't fail
        the entire update.

        Returns:
            Nested dictionary: {device_uuid: {property_path: value}}
            Values are None if read failed.
        """
        result: dict[str, dict[str, Any]] = {}

        async with self._registry_lock:
            # Create a snapshot of the registry while holding the lock
            registry_snapshot = {
                device_uuid: dict(property_items) for device_uuid, property_items in self._property_registry.items()
            }

        # Now iterate over the snapshot without holding the lock
        for device_uuid, property_items in registry_snapshot.items():
            result[device_uuid] = {}

            for property_path, params in property_items.items():
                try:
                    reading = await self.api.async_read_property_for_device(
                        device_uuid=device_uuid,
                        property_path=property_path,
                        faktor=params.faktor,
                        signed=params.signed,
                        byte_count=params.byte_count,
                    )
                    # Store the scaled value for backward compatibility with sensors
                    result[device_uuid][property_path] = reading.scaled_value if reading else None
                    # Track each individual API call
                    if self._access_tracker:
                        self._access_tracker.record_access("Property")
                except (TimeoutError, aiohttp.ClientError) as e:
                    _LOGGER.debug(
                        "Error fetching property %s for device %s: %s",
                        property_path,
                        device_uuid,
                        e,
                    )
                    result[device_uuid][property_path] = None

        return result

    def get_property_value(self, device_uuid: str, property_path: str) -> Any:
        """Get a cached property value from the last update.

        Retrieves a property value that was fetched during the last
        coordinator update. Returns None if the value doesn't exist or
        if the read failed.

        Args:
            device_uuid: UUID of the device
            property_path: Property path (e.g., "29/1/10")

        Returns:
            The cached property value (float or string), or None if not found/failed.

        Example:
            >>> value = coordinator.get_property_value("abc123", "29/1/10")
            >>> if value is not None:
            ...     print(f"Property value: {value}")
        """
        if not self.data:
            return None

        device_data = self.data.get(device_uuid, {})
        return device_data.get(property_path)


class ComfoClimeDefinitionCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching device definition data.

    Fetches definition data for connected devices, particularly useful
    for ComfoAirQ devices (modelTypeId=1) which provide detailed sensor
    and control point definitions. ComfoClime devices provide less useful
    definition data and are skipped.

    Attributes:
        api: ComfoClimeAPI instance for device communication
        devices: List of connected devices

    Example:
        >>> coordinator = ComfoClimeDefinitionCoordinator(hass, api, devices)
        >>> await coordinator.async_config_entry_first_refresh()
        >>> definition = coordinator.get_definition_data("abc123")
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ComfoClimeAPI,
        devices: list[dict[str, Any]] | None = None,
        polling_interval: int = DEFAULT_POLLING_INTERVAL_SECONDS,
        access_tracker: AccessTracker | None = None,
        config_entry=None,
    ) -> None:
        """Initialize the device definition coordinator.

        Args:
            hass: Home Assistant instance
            api: ComfoClimeAPI instance for device communication
            devices: List of connected devices
            polling_interval: Update interval in seconds (default: 60)
            access_tracker: Optional access tracker for monitoring API calls
        """
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Device Definition",
            update_interval=timedelta(seconds=polling_interval),
            config_entry=config_entry,
        )
        self.api = api
        self.devices = devices or []
        self._access_tracker = access_tracker

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch definition data for ComfoAirQ devices.

        Only fetches definitions for ComfoAirQ devices (modelTypeId=1)
        as ComfoClime devices provide minimal useful definition data.
        Failed reads are logged but don't fail the entire update.

        Returns:
            Dictionary mapping device_uuid to definition data.
            Values are None if read failed or device skipped.
        """
        result: dict[str, DeviceDefinitionData] = {}

        for device in self.devices:
            # Support both Pydantic models (DeviceConfig) and dicts
            if hasattr(device, "uuid"):
                device_uuid = device.uuid
                model_type_id = device.model_type_id
            else:
                device_uuid = device.get("uuid")
                model_type_id = device.get("modelTypeId")

            # Only fetch definition for ComfoAirQ devices (modelTypeId = 1)
            # ComfoClime devices don't provide much useful info
            if model_type_id != 1:
                _LOGGER.debug(
                    "Skipping definition fetch for device %s with modelTypeId %s (not ComfoAirQ)",
                    device_uuid,
                    model_type_id,
                )
                continue

            try:
                definition_data = await self.api.async_get_device_definition(device_uuid=device_uuid)
                result[device_uuid] = definition_data
                # Track each individual API call
                if self._access_tracker:
                    self._access_tracker.record_access("Definition")
                _LOGGER.debug("Successfully fetched definition for device %s", device_uuid)
            except (TimeoutError, aiohttp.ClientError) as e:
                _LOGGER.debug("Error fetching definition for device %s: %s", device_uuid, e)
                result[device_uuid] = None

        return result

    def get_definition_data(self, device_uuid: str) -> DeviceDefinitionData | None:
        """Get cached definition data for a device.

        Retrieves definition data that was fetched during the last
        coordinator update. Returns None if the device doesn't exist,
        wasn't fetched, or if the read failed.

        Args:
            device_uuid: UUID of the device

        Returns:
            Dictionary containing device definition data, or None if not found.

        Example:
            >>> definition = coordinator.get_definition_data("abc123")
            >>> if definition:
            ...     print(f"Device has {len(definition.get('sensors', []))} sensors")
        """
        if not self.data:
            return None

        return self.data.get(device_uuid)
