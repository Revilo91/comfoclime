from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta
import logging

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
            return await self.api.async_get_dashboard_data(self.hass)
        except Exception as e:
            _LOGGER.warning(f"Fehler beim Abrufen der Dashboard-Daten: {e}")
            raise UpdateFailed(f"Fehler beim Abrufen der Dashboard-Daten: {e}")


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
            return await self.api.async_get_thermal_profile(self.hass)
        except Exception as e:
            raise UpdateFailed(f"Fehler beim Abrufen der Thermalprofile-Daten: {e}")

class ComfoClimeDeviceCoordinator(DataUpdateCoordinator):
    """Coordinator for polling specific device data (telemetry/properties)."""

    def __init__(self, hass, api, device_uuid, update_interval=timedelta(seconds=30)):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"ComfoClime Device {device_uuid}",
            update_interval=update_interval,
        )
        self.api = api
        self.device_uuid = device_uuid
        self._telemetry_ids = set()
        self._properties = set()  # Set of (unit, subunit, property, factor, signed) tuples

    def register_telemetry(self, telemetry_id):
        """Register a telemetry ID to be polled."""
        self._telemetry_ids.add(telemetry_id)

    def register_property(self, unit, subunit, prop, factor, signed):
        """Register a property to be polled."""
        self._properties.add((unit, subunit, prop, factor, signed))

    async def _async_update_data(self):
        """Fetch data from API."""
        data = {}

        # Poll telemetry
        for tid in self._telemetry_ids:
            try:
                # We use a small delay or just sequential await to avoid flooding
                # The lock in API class already handles concurrency, but we want to be nice
                val = await self.api.async_read_telemetry(self.device_uuid, tid)
                data[f"telemetry_{tid}"] = val
            except Exception as e:
                _LOGGER.warning(f"Error fetching telemetry {tid} for {self.device_uuid}: {e}")

        # Poll properties
        for unit, subunit, prop, factor, signed in self._properties:
            key = f"property_{unit}_{subunit}_{prop}"
            try:
                val = await self.api.async_read_property(
                    self.device_uuid, unit, subunit, prop, factor, signed
                )
                data[key] = val
            except Exception as e:
                _LOGGER.warning(f"Error fetching property {key} for {self.device_uuid}: {e}")

        return data
