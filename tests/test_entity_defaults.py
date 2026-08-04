"""Tests for how entity visibility and naming defaults are derived.

Since the options flow no longer selects entities, two things carry the whole
weight of "what does the user see out of the box": the entity category on each
definition, and the translation key that gives the entity its name. Both are
easy to get wrong silently, so both are checked exhaustively here.
"""

import json
import pathlib

import pytest

from custom_components.comfoclime.entities.base_definitions import (
    enabled_by_default,
    entity_category_for,
)
from custom_components.comfoclime.entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)
from custom_components.comfoclime.entities.select_definitions import (
    PROPERTY_SELECT_ENTITIES,
    SELECT_ENTITIES,
)
from custom_components.comfoclime.entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    THERMALPROFILE_SENSORS,
    SensorDefinition,
    TelemetrySensorDefinition,
)
from custom_components.comfoclime.entities.switch_definitions import SWITCHES

TRANSLATIONS_DIR = pathlib.Path("custom_components/comfoclime/translations")


def _flat(per_model: dict) -> list:
    return [definition for definitions in per_model.values() for definition in definitions]


ALL_SENSOR_DEFS = [
    *DASHBOARD_SENSORS,
    *THERMALPROFILE_SENSORS,
    *MONITORING_SENSORS,
    *ACCESS_TRACKING_SENSORS,
    *_flat(CONNECTED_DEVICE_SENSORS),
    *_flat(CONNECTED_DEVICE_PROPERTIES),
    *_flat(CONNECTED_DEVICE_DEFINITION_SENSORS),
]

DEFS_BY_PLATFORM = {
    "sensor": ALL_SENSOR_DEFS,
    "number": [*NUMBER_ENTITIES, *_flat(CONNECTED_DEVICE_NUMBER_PROPERTIES)],
    "select": [*SELECT_ENTITIES, *_flat(PROPERTY_SELECT_ENTITIES)],
    "switch": SWITCHES,
}


class TestEnabledDefaults:
    """entity_category drives entity_registry_enabled_default."""

    def test_plain_sensor_is_enabled(self):
        definition = SensorDefinition(key="k", name="N", translation_key="t")
        assert entity_category_for(definition) is None
        assert enabled_by_default(definition) is True

    def test_diagnostic_sensor_is_disabled(self):
        definition = SensorDefinition(key="k", name="N", translation_key="t", entity_category="diagnostic")
        assert entity_category_for(definition) == "diagnostic"
        assert enabled_by_default(definition) is False

    def test_diagnose_telemetry_is_treated_as_diagnostic(self):
        """`diagnose` marks unverified telemetry; it must not show up by default."""
        definition = TelemetrySensorDefinition(name="N", translation_key="t", telemetry_id=1, diagnose=True)
        assert entity_category_for(definition) == "diagnostic"
        assert enabled_by_default(definition) is False

    def test_explicit_category_wins_over_diagnose(self):
        definition = TelemetrySensorDefinition(
            name="N",
            translation_key="t",
            telemetry_id=1,
            diagnose=True,
            entity_category="config",
        )
        assert entity_category_for(definition) == "config"

    def test_core_sensors_stay_visible(self):
        """The everyday values must not accidentally become diagnostic."""
        by_key = {definition.key: definition for definition in DASHBOARD_SENSORS}
        for key in ("indoorTemperature", "outdoorTemperature", "supplyAirFlow", "fanSpeed"):
            assert enabled_by_default(by_key[key]) is True, f"{key} should be visible by default"

    def test_thermalprofile_sensors_are_diagnostic(self):
        """Each one mirrors a writable number/select/switch on the same device.

        Keeping them enabled means every thermal profile value appears twice,
        which is what the diagnostic category exists to prevent.
        """
        for definition in THERMALPROFILE_SENSORS:
            assert entity_category_for(definition) == "diagnostic", (
                f"{definition.key} duplicates a control entity and should be diagnostic"
            )

    def test_access_tracking_is_diagnostic(self):
        for definition in ACCESS_TRACKING_SENSORS:
            assert enabled_by_default(definition) is False


class TestNoDuplicateNames:
    """Two entities on one device must not resolve to the same name."""

    def test_comfoairq_definition_and_telemetry_keys_are_distinct(self):
        """Both sets land on the ComfoAirQ device, so their keys must differ."""
        telemetry_keys = {definition.translation_key for definition in CONNECTED_DEVICE_SENSORS[1]}
        definition_keys = {definition.translation_key for definition in CONNECTED_DEVICE_DEFINITION_SENSORS[1]}
        assert telemetry_keys & definition_keys == set()

    def test_telemetry_ids_are_unique_per_model(self):
        for model_id, definitions in CONNECTED_DEVICE_SENSORS.items():
            ids = [definition.telemetry_id for definition in definitions]
            assert len(ids) == len(set(ids)), f"duplicate telemetry id for model {model_id}"

    def test_property_paths_are_unique_per_model(self):
        for model_id, definitions in CONNECTED_DEVICE_PROPERTIES.items():
            paths = [definition.path for definition in definitions]
            assert len(paths) == len(set(paths)), f"duplicate property path for model {model_id}"

    def test_shared_property_paths_agree_on_decoding(self):
        """A path read by both a sensor and a number shares one registration.

        The property coordinator keys its registry by (device, path), so two
        definitions for the same path must decode it identically or one of the
        two entities silently shows a wrong value.
        """
        for model_id, sensor_defs in CONNECTED_DEVICE_PROPERTIES.items():
            numbers = {n.property: n for n in CONNECTED_DEVICE_NUMBER_PROPERTIES.get(model_id, [])}
            for sensor_def in sensor_defs:
                number = numbers.get(sensor_def.path)
                if number is None:
                    continue
                assert (sensor_def.faktor, sensor_def.signed, sensor_def.byte_count) == (
                    number.faktor,
                    number.signed,
                    number.byte_count,
                ), f"sensor and number disagree on how to decode {sensor_def.path} (model {model_id})"


@pytest.mark.parametrize("language", ["en", "de"])
class TestTranslationCompleteness:
    """Every translation_key must exist under its own platform, and vice versa."""

    @staticmethod
    def _entity_section(language: str) -> dict:
        return json.loads((TRANSLATIONS_DIR / f"{language}.json").read_text()).get("entity", {})

    def test_no_missing_keys(self, language):
        section = self._entity_section(language)
        for platform, definitions in DEFS_BY_PLATFORM.items():
            wanted = {definition.translation_key for definition in definitions}
            missing = sorted(wanted - set(section.get(platform, {})))
            assert not missing, f"{language}.json has no entity.{platform} entry for {missing}"

    def test_no_orphaned_keys(self, language):
        """An unused key is usually a rename that left the old entry behind."""
        section = self._entity_section(language)
        for platform, definitions in DEFS_BY_PLATFORM.items():
            wanted = {definition.translation_key for definition in definitions}
            orphaned = sorted(set(section.get(platform, {})) - wanted)
            assert not orphaned, f"{language}.json has unused entity.{platform} entries {orphaned}"


@pytest.mark.parametrize("language", ["en", "de"])
class TestFlowTranslations:
    """The translation files must describe the flow that actually exists."""

    @staticmethod
    def _load(language: str) -> dict:
        return json.loads((TRANSLATIONS_DIR / f"{language}.json").read_text())

    def test_options_steps_match_the_flow(self, language):
        from custom_components.comfoclime.config_flow import ComfoClimeOptionsFlow

        implemented = {
            name.removeprefix("async_step_") for name in vars(ComfoClimeOptionsFlow) if name.startswith("async_step_")
        }
        translated = set(self._load(language)["options"]["step"])

        assert translated == implemented, (
            f"{language}.json describes options steps {sorted(translated)} "
            f"but the flow implements {sorted(implemented)}"
        )

    def test_config_steps_match_the_flow(self, language):
        from custom_components.comfoclime.config_flow import ComfoClimeConfigFlow

        # Only steps this flow defines itself; ConfigFlow inherits a long list
        # of discovery handlers (dhcp, zeroconf, ...) that need no translation.
        implemented = {
            name.removeprefix("async_step_") for name in vars(ComfoClimeConfigFlow) if name.startswith("async_step_")
        }
        translated = set(self._load(language)["config"]["step"])

        assert translated == implemented

    def test_every_option_field_is_labelled(self, language):
        """A field with no label renders as a raw key in the UI."""
        from custom_components.comfoclime.config_flow import DEFAULT_OPTIONS

        labelled = set()
        for step in self._load(language)["options"]["step"].values():
            labelled.update(step.get("data", {}))

        assert set(DEFAULT_OPTIONS) == labelled, (
            f"{language}.json labels {sorted(labelled)} but the flow stores {sorted(DEFAULT_OPTIONS)}"
        )
