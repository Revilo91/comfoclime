import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class ComfoClimeDashboardCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Dashboard",
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.async_get_dashboard_data()
        except Exception as e:
            _LOGGER.warning(f"Fehler beim Abrufen der Dashboard-Daten: {e}")
            raise UpdateFailed(f"Fehler beim Abrufen der Dashboard-Daten: {e}") from e


class ComfoClimeThermalprofileCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Thermalprofile",
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self):
        try:
            return await self.api.async_get_thermal_profile()
        except Exception as e:
            raise UpdateFailed(f"Fehler beim Abrufen der Thermalprofile-Daten: {e}") from e


class ComfoClimeTelemetryCoordinator(DataUpdateCoordinator):
    """Coordinator for batching telemetry requests from all devices."""
    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Telemetry",
            update_interval=timedelta(seconds=30),
        )
        self.api = api
        # Cache for telemetry data: {device_uuid: {telemetry_id: value}}
        self._telemetry_cache = {}

    async def _async_update_data(self):
        """Fetch all telemetry data for all devices."""
        # This will be populated by the API layer
        # For now, just return empty dict - sensors will use async_read_telemetry_for_device
        return {}


class ComfoClimePropertyCoordinator(DataUpdateCoordinator):
    """Coordinator for batching property requests from all devices."""
    def __init__(self, hass, api):
        super().__init__(
            hass,
            _LOGGER,
            name="ComfoClime Properties",
            update_interval=timedelta(seconds=30),
        )
        self.api = api
        # Cache for property data: {device_uuid: {path: value}}
        self._property_cache = {}

    async def _async_update_data(self):
        """Fetch all property data for all devices."""
        # This will be populated by the API layer
        # For now, just return empty dict - sensors will use async_read_property_for_device
        return {}


