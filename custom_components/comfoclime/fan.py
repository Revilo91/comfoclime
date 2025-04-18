import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)


class ComfoClimeFan(CoordinatorEntity, FanEntity):
    def __init__(self, hass, coordinator, api, device, entry):
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._device = device
        self._entry = entry
        self._current_speed = 0

        self._attr_has_entity_name = True
        self._attr_translation_key = "fan_speed"
        self._attr_unique_id = f"{entry.entry_id}_fan_speed"
        self._attr_config_entry_id = entry.entry_id

        # Setze percentage-Modus mit diskreten Stufen
        self._attr_available = True
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_speed_count = 3
        self._attr_percentage_step = 100 // (self._attr_speed_count)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version"),
        )

    @property
    def is_on(self) -> bool:
        return self._current_speed > 0

    @property
    def percentage(self) -> int | None:
        value = self._current_speed * 33
        if value == 99:
            value = 100
        return value  # 0, 33, 66, 99 ≈ 0%, 33%, 66%, 100%

    async def async_set_percentage(self, percentage: int) -> None:
        step = round(percentage / 33)
        step = max(0, min(step, 3))  # Clamp to 0–3
        try:
            await self._hass.async_add_executor_job(
                self._api.set_device_setting,
                None,  # temperature_profile
                step,  # fanSpeed
            )
            self._current_speed = step
            self.async_write_ha_state()
            self._hass.add_job(self.coordinator.async_request_refresh)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von fanSpeed: {e}")

    async def async_update(self):
        try:
            data = self.coordinator.data
            speed = data.get("fanSpeed", 0)
            self._current_speed = int(speed)
        except Exception as e:
            _LOGGER.warning(f"Fehler beim Abrufen von fanSpeed via dashboard: {e}")
            self._current_speed = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")

    try:
        await api.async_get_uuid(hass)
        devices = await api.async_get_connected_devices(hass)
        main_device = next((d for d in devices if d.get("modelTypeId") == 20), None)
        if not main_device:
            _LOGGER.warning("Kein Hauptgerät mit modelTypeId 20 gefunden.")
            return
        data = hass.data[DOMAIN][entry.entry_id]
        api = data["api"]
        coordinator = data["coordinator"]
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as e:
            _LOGGER.warning(f"Dashboard-Daten konnten nicht geladen werden: {e}")

        fan_entity = ComfoClimeFan(hass, coordinator, api, main_device, entry)
        async_add_entities([fan_entity], True)

    except Exception as e:
        _LOGGER.error(f"Fehler beim Setup der FanEntity: {e}")
