"""Tests for how entity visibility and naming defaults are derived.

Since the options flow no longer selects entities, two things carry the whole
weight of "what does the user see out of the box": the entity category on each
definition, and the translation key that gives the entity its name. Both are
easy to get wrong silently, so both are checked exhaustively here.
"""

import ast
import importlib
import json
import pathlib
import re

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
    ALARM_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    HEALTH_SENSORS,
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
    *HEALTH_SENSORS,
    *ALARM_SENSORS,
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


EXCEPTION_CLASSES = {"HomeAssistantError", "ServiceValidationError", "ConfigEntryNotReady", "UpdateFailed"}
COMPONENT_DIR = pathlib.Path("custom_components/comfoclime")


def _raised_translation_keys() -> dict[str, list[tuple[str, set[str]]]]:
    """Map every translation_key passed to a raised HA exception to (raise site, placeholder names)."""
    found: dict[str, list[tuple[str, set[str]]]] = {}
    for path in sorted(COMPONENT_DIR.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name not in EXCEPTION_CLASSES:
                continue
            keywords = {kw.arg: kw.value for kw in node.exc.keywords}
            key = keywords.get("translation_key")
            site = f"{path}:{node.lineno}"
            assert isinstance(key, ast.Constant), f"{site}: {name} needs a literal translation_key"
            domain = keywords.get("translation_domain")
            assert domain is not None, f"{site}: {name} sets translation_key without translation_domain"
            assert not node.exc.args, f"{site}: {name} must not carry a hardcoded message"
            placeholders = keywords.get("translation_placeholders")
            names = (
                {k.value for k in placeholders.keys if isinstance(k, ast.Constant)}
                if isinstance(placeholders, ast.Dict)
                else set()
            )
            found.setdefault(key.value, []).append((site, names))
    return found


@pytest.mark.parametrize("language", ["en", "de"])
class TestExceptionTranslations:
    """Every raised exception needs a translated message, and no message may be unused."""

    @staticmethod
    def _exceptions_section(language: str) -> dict:
        return json.loads((TRANSLATIONS_DIR / f"{language}.json").read_text()).get("exceptions", {})

    def test_raise_sites_are_translated(self, language):
        raised = _raised_translation_keys()
        assert raised, "expected the integration to raise translated exceptions"
        missing = sorted(set(raised) - set(self._exceptions_section(language)))
        assert not missing, f"{language}.json has no exceptions entry for {missing}"

    def test_no_orphaned_exception_keys(self, language):
        orphaned = sorted(set(self._exceptions_section(language)) - set(_raised_translation_keys()))
        assert not orphaned, f"{language}.json has unused exceptions entries {orphaned}"

    def test_placeholders_match_message(self, language):
        section = self._exceptions_section(language)
        for key, sites in _raised_translation_keys().items():
            message = section.get(key, {}).get("message", "")
            assert message, f"{language}.json exceptions.{key} has no message"
            in_message = set(re.findall(r"\{(\w+)\}", message))
            for site, passed in sites:
                assert passed == in_message, f"{site}: placeholders {passed} != {in_message} in {language}.json {key}"


def test_strings_json_matches_english_translation():
    assert (COMPONENT_DIR / "strings.json").read_text() == (TRANSLATIONS_DIR / "en.json").read_text()


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


# Quality scale rule "parallel-updates": every platform sets PARALLEL_UPDATES explicitly.
# Sensors only read coordinator data (no limit needed); action platforms write to a
# single device that enforces a write cooldown, so commands are sent one at a time.
EXPECTED_PARALLEL_UPDATES = {
    "sensor": 0,
    "climate": 1,
    "fan": 1,
    "number": 1,
    "select": 1,
    "switch": 1,
}


@pytest.mark.parametrize(("platform", "expected"), EXPECTED_PARALLEL_UPDATES.items())
def test_platform_sets_parallel_updates(platform: str, expected: int) -> None:
    module = importlib.import_module(f"custom_components.comfoclime.{platform}")
    assert getattr(module, "PARALLEL_UPDATES", None) == expected


# Quality scale rule "icon-translations": icons live in icons.json, never in code.
INTEGRATION_DIR = pathlib.Path("custom_components/comfoclime")


class TestIconTranslations:
    @staticmethod
    def _icons() -> dict:
        return json.loads((INTEGRATION_DIR / "icons.json").read_text(encoding="utf-8"))

    def test_every_service_has_an_icon(self):
        import yaml

        services = yaml.safe_load((INTEGRATION_DIR / "services.yaml").read_text(encoding="utf-8"))
        icons = self._icons().get("services", {})
        assert set(services) <= set(icons)
        for name in services:
            assert icons[name]["service"].startswith("mdi:"), name

    def test_entity_icon_keys_exist_in_strings(self):
        strings = json.loads((INTEGRATION_DIR / "strings.json").read_text(encoding="utf-8"))
        for platform, entries in self._icons().get("entity", {}).items():
            known = set(strings["entity"].get(platform, {}))
            assert set(entries) <= known, f"{platform}: unknown translation keys {set(entries) - known}"
            for key, spec in entries.items():
                assert spec["default"].startswith("mdi:"), f"{platform}.{key}"

    def test_no_hardcoded_icons_in_source(self):
        pattern = re.compile(r"_attr_icon|\bicon\s*=|\bdef icon\b|\"icon\"\s*:")
        offenders = [
            str(path) for path in INTEGRATION_DIR.rglob("*.py") if pattern.search(path.read_text(encoding="utf-8"))
        ]
        assert offenders == []


# hassfest rejects placeholders wrapped in single quotes ("'{name}'") in translations.
QUOTED_PLACEHOLDER = re.compile(r"'\{[^}]+\}'")
TRANSLATION_FILES = ["strings.json", "translations/en.json", "translations/de.json"]


def _iter_strings(node: object):
    if isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
    elif isinstance(node, str):
        yield node


@pytest.mark.parametrize("relative_path", TRANSLATION_FILES)
def test_translations_have_no_single_quoted_placeholders(relative_path: str) -> None:
    path = pathlib.Path(__file__).parent.parent / "custom_components" / "comfoclime" / relative_path
    data = json.loads(path.read_text(encoding="utf-8"))
    offenders = [s for s in _iter_strings(data) if QUOTED_PLACEHOLDER.search(s)]
    assert offenders == []
