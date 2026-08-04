"""Tests for coordinator registration and its entity lifecycle.

This is the mechanism that replaces the old options-based entity selection.
Home Assistant never adds a disabled entity, so if registration happens in
``async_added_to_hass`` and unregistration in ``async_will_remove_from_hass``,
a disabled entity costs zero API requests. These tests pin that down, because
if registration drifted back to setup time the integration would silently
start polling values nobody asked for again.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.comfoclime.coordinator import (
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
)

DEVICE = "SIT123"


@pytest.fixture
def telemetry_coordinator(hass):
    return ComfoClimeTelemetryCoordinator(hass, MagicMock(), devices=[], sensor_delay=0)


@pytest.fixture
def property_coordinator(hass):
    return ComfoClimePropertyCoordinator(hass, MagicMock(), devices=[], sensor_delay=0)


class TestTelemetryRegistry:
    async def test_register_then_unregister_empties_the_registry(self, telemetry_coordinator):
        await telemetry_coordinator.register_telemetry(DEVICE, "4193", faktor=0.1, signed=True, byte_count=2)
        assert telemetry_coordinator._telemetry_registry[DEVICE]["4193"].byte_count == 2

        await telemetry_coordinator.unregister_telemetry(DEVICE, "4193")

        assert DEVICE not in telemetry_coordinator._telemetry_registry

    async def test_unregister_keeps_siblings(self, telemetry_coordinator):
        await telemetry_coordinator.register_telemetry(DEVICE, "4193")
        await telemetry_coordinator.register_telemetry(DEVICE, "4194")

        await telemetry_coordinator.unregister_telemetry(DEVICE, "4193")

        assert set(telemetry_coordinator._telemetry_registry[DEVICE]) == {"4194"}

    async def test_unregister_unknown_is_harmless(self, telemetry_coordinator):
        await telemetry_coordinator.unregister_telemetry(DEVICE, "9999")
        await telemetry_coordinator.register_telemetry(DEVICE, "4193")
        await telemetry_coordinator.unregister_telemetry(DEVICE, "9999")

        assert set(telemetry_coordinator._telemetry_registry[DEVICE]) == {"4193"}

    async def test_unregistered_telemetry_is_not_fetched(self, telemetry_coordinator):
        telemetry_coordinator.api.async_read_telemetry_for_device = AsyncMock(return_value=MagicMock(scaled_value=21.5))
        await telemetry_coordinator.register_telemetry(DEVICE, "4193")
        await telemetry_coordinator.register_telemetry(DEVICE, "4194")
        await telemetry_coordinator.unregister_telemetry(DEVICE, "4194")

        await telemetry_coordinator._async_update_data()

        fetched = {
            call.kwargs["telemetry_id"]
            for call in telemetry_coordinator.api.async_read_telemetry_for_device.call_args_list
        }
        assert fetched == {"4193"}


class TestPropertyRegistryRefcounting:
    """A path may back several entities; the last one out clears it."""

    async def test_two_entities_one_path(self, property_coordinator):
        await property_coordinator.register_property(DEVICE, "23/1/4", faktor=0.1, signed=True, byte_count=2)
        await property_coordinator.register_property(DEVICE, "23/1/4", faktor=0.1, signed=True, byte_count=2)

        await property_coordinator.unregister_property(DEVICE, "23/1/4")
        assert "23/1/4" in property_coordinator._property_registry[DEVICE], (
            "one entity still wants this property, so it must keep being polled"
        )

        await property_coordinator.unregister_property(DEVICE, "23/1/4")
        assert DEVICE not in property_coordinator._property_registry

    async def test_conflicting_parameters_keep_the_first_registration(self, property_coordinator, caplog):
        """Disagreeing definitions must not silently overwrite each other."""
        await property_coordinator.register_property(DEVICE, "23/1/4", faktor=0.1, signed=True, byte_count=2)
        await property_coordinator.register_property(DEVICE, "23/1/4", faktor=1.0, signed=False, byte_count=1)

        entry = property_coordinator._property_registry[DEVICE]["23/1/4"]
        assert (entry.faktor, entry.signed, entry.byte_count) == (0.1, True, 2)
        assert "Conflicting decode parameters" in caplog.text

    async def test_unregistered_property_is_not_fetched(self, property_coordinator):
        property_coordinator.api.async_read_property_for_device = AsyncMock(return_value=MagicMock(scaled_value=1))
        await property_coordinator.register_property(DEVICE, "29/1/2")
        await property_coordinator.register_property(DEVICE, "29/1/3")
        await property_coordinator.unregister_property(DEVICE, "29/1/2")

        await property_coordinator._async_update_data()

        fetched = {
            call.kwargs["property_path"]
            for call in property_coordinator.api.async_read_property_for_device.call_args_list
        }
        assert fetched == {"29/1/3"}


class TestEntityLifecycle:
    """Registration must be tied to the entity being live, not to setup."""

    @staticmethod
    def _telemetry_sensor(coordinator, entry):
        from custom_components.comfoclime.sensor import ComfoClimeTelemetrySensor

        sensor = ComfoClimeTelemetrySensor(
            hass=MagicMock(),
            coordinator=coordinator,
            telemetry_id=4193,
            name="Supply Air Temperature",
            translation_key="supply_air_temperature",
            unit="°C",
            faktor=0.1,
            signed=True,
            byte_count=2,
            override_device_uuid=DEVICE,
            entry=entry,
        )
        sensor.async_write_ha_state = MagicMock()
        return sensor

    async def test_setup_alone_registers_nothing(self, telemetry_coordinator, mock_config_entry):
        """Constructing the entity must not touch the coordinator registry."""
        self._telemetry_sensor(telemetry_coordinator, mock_config_entry)

        assert telemetry_coordinator._telemetry_registry == {}

    async def test_added_to_hass_registers_and_refreshes(self, telemetry_coordinator, mock_config_entry):
        sensor = self._telemetry_sensor(telemetry_coordinator, mock_config_entry)
        telemetry_coordinator.async_request_refresh = AsyncMock()

        await sensor._async_register_data_source()

        assert telemetry_coordinator._telemetry_registry[DEVICE]["4193"].faktor == 0.1
        telemetry_coordinator.async_request_refresh.assert_awaited_once()

    async def test_removal_unregisters(self, telemetry_coordinator, mock_config_entry):
        sensor = self._telemetry_sensor(telemetry_coordinator, mock_config_entry)
        telemetry_coordinator.async_request_refresh = AsyncMock()

        await sensor._async_register_data_source()
        await sensor._async_unregister_data_source()

        assert telemetry_coordinator._telemetry_registry == {}

    async def test_missing_device_uuid_registers_nothing(self, telemetry_coordinator, mock_config_entry):
        from custom_components.comfoclime.sensor import ComfoClimeTelemetrySensor

        sensor = ComfoClimeTelemetrySensor(
            hass=MagicMock(),
            coordinator=telemetry_coordinator,
            telemetry_id=4193,
            name="n",
            translation_key="t",
            unit=None,
            override_device_uuid=None,
            entry=mock_config_entry,
        )

        await sensor._async_register_data_source()
        await sensor._async_unregister_data_source()

        assert telemetry_coordinator._telemetry_registry == {}


class TestHookChain:
    """The mixin's hooks only run if it precedes CoordinatorEntity in the MRO.

    If a subclass were declared as (CoordinatorEntity, ComfoClimeBaseEntity, ...)
    or overrode async_added_to_hass without calling super(), registration would
    silently stop happening and telemetry entities would sit at unknown forever.
    """

    @staticmethod
    def _entity_classes():
        import importlib

        from custom_components.comfoclime.entity_base import ComfoClimeBaseEntity

        classes = []
        for module_name in ("sensor", "switch", "number", "select", "fan", "climate"):
            module = importlib.import_module(f"custom_components.comfoclime.{module_name}")
            classes.extend(
                obj
                for obj in vars(module).values()
                if isinstance(obj, type) and issubclass(obj, ComfoClimeBaseEntity) and obj is not ComfoClimeBaseEntity
            )
        return classes

    def test_mixin_precedes_coordinator_entity(self):
        from homeassistant.helpers.update_coordinator import CoordinatorEntity

        from custom_components.comfoclime.entity_base import ComfoClimeBaseEntity

        classes = self._entity_classes()
        assert classes, "no entity classes found"

        for entity_class in classes:
            mro = entity_class.__mro__
            if CoordinatorEntity not in mro:
                continue
            assert mro.index(ComfoClimeBaseEntity) < mro.index(CoordinatorEntity), (
                f"{entity_class.__name__} lists CoordinatorEntity before ComfoClimeBaseEntity, "
                "so the registration hooks would never run"
            )

    def test_overrides_delegate_to_the_mixin(self):
        """Any subclass override must chain, or registration is lost."""
        import inspect

        from custom_components.comfoclime.entity_base import ComfoClimeBaseEntity

        for entity_class in self._entity_classes():
            for hook in ("async_added_to_hass", "async_will_remove_from_hass"):
                override = vars(entity_class).get(hook)
                if override is None:
                    continue
                source = inspect.getsource(override)
                assert f"super().{hook}()" in source, (
                    f"{entity_class.__name__}.{hook} overrides the mixin without calling super()"
                )

        # Sanity check that the mixin still defines both hooks at all.
        assert "async_added_to_hass" in vars(ComfoClimeBaseEntity)
        assert "async_will_remove_from_hass" in vars(ComfoClimeBaseEntity)
