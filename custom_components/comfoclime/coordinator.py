import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

# Default polling interval to reduce API load on the Airduino board
DEFAULT_POLLING_INTERVAL_SECONDS = 60


class ComfoClimeDashboardCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching dashboard data from the ComfoClime device.

    Fetches dashboard data including temperature, fan speed, season, and heat pump status.
    """

    def __init__(self, hass, api, polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Dashboard",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch dashboard data from the API."""
        try:
            return await self.api.async_get_dashboard_data()
        except Exception as e:
            _LOGGER.debug(f"Error fetching dashboard data: {e}")
            raise UpdateFailed(f"Error fetching dashboard data: {e}") from e


class ComfoClimeThermalprofileCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching thermal profile data from the ComfoClime device.

    Fetches thermal profile settings including season, temperature profiles,
    and heating/cooling parameters.
    """

    def __init__(self, hass, api, polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Thermalprofile",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch thermal profile data from the API."""
        try:
            return await self.api.async_get_thermal_profile()
        except Exception as e:
            _LOGGER.debug(f"Error fetching thermal profile data: {e}")
            raise UpdateFailed(f"Error fetching thermal profile data: {e}") from e


class ComfoClimeTelemetryCoordinator(DataUpdateCoordinator):
    """Coordinator for batching telemetry requests from all devices.

    Instead of each sensor making individual API calls, this coordinator
    fetches all registered telemetry values in a single update cycle,
    significantly reducing API load on the Airduino board.
    """

    def __init__(self, hass, api, devices=None, polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Telemetry",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api = api
        self.devices = devices or []
        # Registry of telemetry requests: {device_uuid: {telemetry_id: {faktor, signed, byte_count}}}
        self._telemetry_registry: dict[str, dict[str, dict]] = {}
        # Lock to prevent concurrent modifications during iteration
        self._registry_lock = asyncio.Lock()

    async def register_telemetry(
        self,
        device_uuid: str,
        telemetry_id: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        """Register a telemetry value to be fetched during updates.

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry ID to fetch
            faktor: Factor to multiply the value by
            signed: Whether the value is signed
            byte_count: Number of bytes to read
        """
        async with self._registry_lock:
            if device_uuid not in self._telemetry_registry:
                self._telemetry_registry[device_uuid] = {}

            self._telemetry_registry[device_uuid][str(telemetry_id)] = {
                "faktor": faktor,
                "signed": signed,
                "byte_count": byte_count,
            }
            _LOGGER.debug(f"Registered telemetry {telemetry_id} for device {device_uuid}")

    async def _async_update_data(self):
        """Fetch all registered telemetry data for all devices in batched manner."""
        result: dict[str, dict[str, Any]] = {}

        async with self._registry_lock:
            # Create a snapshot of the registry while holding the lock
            registry_snapshot = {
                device_uuid: dict(telemetry_items)
                for device_uuid, telemetry_items in self._telemetry_registry.items()
            }

        # Now iterate over the snapshot without holding the lock
        for device_uuid, telemetry_items in registry_snapshot.items():
            result[device_uuid] = {}

            for telemetry_id, params in telemetry_items.items():
                try:
                    value = await self.api.async_read_telemetry_for_device(
                        device_uuid=device_uuid,
                        telemetry_id=telemetry_id,
                        faktor=params["faktor"],
                        signed=params["signed"],
                        byte_count=params["byte_count"],
                    )
                    result[device_uuid][telemetry_id] = value
                except Exception as e:  # noqa: PERF203
                    _LOGGER.debug(
                        f"Error fetching telemetry {telemetry_id} for device {device_uuid}: {e}"
                    )
                    result[device_uuid][telemetry_id] = None

        return result

    def get_telemetry_value(self, device_uuid: str, telemetry_id: str | int) -> Any:
        """Get a cached telemetry value from the last update.

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry ID

        Returns:
            The cached value or None if not found
        """
        if not self.data:
            return None

        device_data = self.data.get(device_uuid, {})
        return device_data.get(str(telemetry_id))


class ComfoClimePropertyCoordinator(DataUpdateCoordinator):
    """Coordinator for batching property requests from all devices.

    Instead of each sensor/number/select making individual API calls,
    this coordinator fetches all registered property values in a single
    update cycle, significantly reducing API load on the Airduino board.
    """

    def __init__(self, hass, api, devices=None, polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Properties",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api = api
        self.devices = devices or []
        # Registry of property requests: {device_uuid: {path: {faktor, signed, byte_count}}}
        self._property_registry: dict[str, dict[str, dict]] = {}
        # Lock to prevent concurrent modifications during iteration
        self._registry_lock = asyncio.Lock()

    async def register_property(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        """Register a property value to be fetched during updates.

        Args:
            device_uuid: UUID of the device
            property_path: Property path (e.g., "29/1/10")
            faktor: Factor to multiply the value by
            signed: Whether the value is signed
            byte_count: Number of bytes to read
        """
        async with self._registry_lock:
            if device_uuid not in self._property_registry:
                self._property_registry[device_uuid] = {}

            self._property_registry[device_uuid][property_path] = {
                "faktor": faktor,
                "signed": signed,
                "byte_count": byte_count,
            }
            _LOGGER.debug(f"Registered property {property_path} for device {device_uuid}")

    async def _async_update_data(self):
        """Fetch all registered property data for all devices in batched manner."""
        result: dict[str, dict[str, Any]] = {}

        async with self._registry_lock:
            # Create a snapshot of the registry while holding the lock
            registry_snapshot = {
                device_uuid: dict(property_items)
                for device_uuid, property_items in self._property_registry.items()
            }

        # Now iterate over the snapshot without holding the lock
        for device_uuid, property_items in registry_snapshot.items():
            result[device_uuid] = {}

            for property_path, params in property_items.items():
                try:
                    value = await self.api.async_read_property_for_device(
                        device_uuid=device_uuid,
                        property_path=property_path,
                        faktor=params["faktor"],
                        signed=params["signed"],
                        byte_count=params["byte_count"],
                    )
                    result[device_uuid][property_path] = value
                except Exception as e:  # noqa: PERF203
                    _LOGGER.debug(
                        f"Error fetching property {property_path} for device {device_uuid}: {e}"
                    )
                    result[device_uuid][property_path] = None

        return result

    def get_property_value(self, device_uuid: str, property_path: str) -> Any:
        """Get a cached property value from the last update.

        Args:
            device_uuid: UUID of the device
            property_path: Property path

        Returns:
            The cached value or None if not found
        """
        if not self.data:
            return None

        device_data = self.data.get(device_uuid, {})
        return device_data.get(property_path)


class ComfoClimeDefinitionCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching device definition data.

    Fetches definition data for connected devices, particularly useful
    for ComfoAirQ devices which provide detailed definition information.
    """

    def __init__(self, hass, api, devices=None, polling_interval=DEFAULT_POLLING_INTERVAL_SECONDS):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Device Definition",
            update_interval=timedelta(seconds=polling_interval),
        )
        self.api = api
        self.devices = devices or []

    async def _async_update_data(self):
        """Fetch definition data for all devices."""
        result: dict[str, dict] = {}

        for device in self.devices:
            device_uuid = device.get("uuid")
            model_type_id = device.get("modelTypeId")

            # Only fetch definition for ComfoAirQ devices (modelTypeId = 1)
            # ComfoClime devices don't provide much useful info
            if model_type_id != 1:
                _LOGGER.debug(
                    f"Skipping definition fetch for device {device_uuid} with modelTypeId {model_type_id} (not ComfoAirQ)"
                )
                continue

            try:
                definition_data = await self.api.async_get_device_definition(
                    device_uuid=device_uuid
                )
                result[device_uuid] = definition_data
                _LOGGER.debug(
                    f"Successfully fetched definition for device {device_uuid}"
                )
            except Exception as e:
                _LOGGER.debug(
                    f"Error fetching definition for device {device_uuid}: {e}"
                )
                result[device_uuid] = None

        return result

    def get_definition_data(self, device_uuid: str) -> dict | None:
        """Get cached definition data for a device.

        Args:
            device_uuid: UUID of the device

        Returns:
            The cached definition data or None if not found
        """
        if not self.data:
            return None

        return self.data.get(device_uuid)
