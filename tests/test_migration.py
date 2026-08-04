"""Tests for the version 1 -> 2 config entry migration.

Version 1 stored per-entity selection in the entry options. Version 2 hands
that job to the entity registry. The translation has to be exact in both
directions: an entity the user had switched off must end up disabled, and an
entity they kept must be left alone.
"""

from custom_components.comfoclime.entities.number_definitions import NUMBER_ENTITIES
from custom_components.comfoclime.entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
)
from custom_components.comfoclime.entities.switch_definitions import SWITCHES
from custom_components.comfoclime.migration import (
    build_option_id_map,
    matches,
    unique_ids_to_disable,
)

ENTRY_ID = "abc123"


def _option_id_for(unique_id: str) -> str:
    """Reverse-look-up the legacy option ID that maps to a unique ID."""
    for option_id, (_group, mapped) in build_option_id_map(ENTRY_ID).items():
        if mapped == unique_id:
            return option_id
    raise AssertionError(f"no legacy option ID maps to {unique_id}")


def test_option_id_map_covers_every_definition():
    """Every definition contributes exactly one legacy option ID."""
    mapping = build_option_id_map(ENTRY_ID)

    expected_minimum = (
        len(DASHBOARD_SENSORS)
        + len(SWITCHES)
        + len(NUMBER_ENTITIES)
        + len(ACCESS_TRACKING_SENSORS)
        + sum(len(defs) for defs in CONNECTED_DEVICE_SENSORS.values())
    )
    assert len(mapping) >= expected_minimum

    # Unique IDs must be unique, or the migration would disable the wrong thing.
    unique_ids = [unique_id for _group, unique_id in mapping.values()]
    assert len(unique_ids) == len(set(unique_ids))


def test_untouched_groups_are_left_alone():
    """Options with no selection lists mean the user never configured anything."""
    assert unique_ids_to_disable({}, ENTRY_ID) == set()
    assert unique_ids_to_disable({"polling_interval": 60}, ENTRY_ID) == set()


def test_deselected_dashboard_sensor_is_disabled():
    """A sensor missing from a configured list was deliberately switched off."""
    keep = _option_id_for(f"{ENTRY_ID}_dashboard_indoorTemperature")
    drop = _option_id_for(f"{ENTRY_ID}_dashboard_outdoorTemperature")

    to_disable = unique_ids_to_disable({"enabled_dashboard": [keep]}, ENTRY_ID)

    assert f"{ENTRY_ID}_dashboard_outdoorTemperature" in to_disable
    assert f"{ENTRY_ID}_dashboard_indoorTemperature" not in to_disable
    assert drop  # the reverse lookup found a real option ID


def test_other_groups_unaffected_by_one_configured_group():
    """Configuring dashboards says nothing about switches or numbers."""
    keep = _option_id_for(f"{ENTRY_ID}_dashboard_indoorTemperature")

    to_disable = unique_ids_to_disable({"enabled_dashboard": [keep]}, ENTRY_ID)

    assert not any(unique_id.startswith(f"{ENTRY_ID}_switch_") for unique_id in to_disable)
    assert not any(unique_id.startswith(f"{ENTRY_ID}_telemetry_") for unique_id in to_disable)


def test_empty_list_disables_the_whole_group():
    """An empty selection meant 'none of these'."""
    to_disable = unique_ids_to_disable({"enabled_switches": []}, ENTRY_ID)

    for switch_def in SWITCHES:
        assert f"{ENTRY_ID}_switch_{switch_def.key}" in to_disable


def test_legacy_alias_keys_are_honoured():
    """Even older entries used enabled_connected_telemetry without 'device'."""
    kept = _option_id_for(f"{ENTRY_ID}_telemetry_4145")

    to_disable = unique_ids_to_disable({"enabled_connected_telemetry": [kept]}, ENTRY_ID)

    assert f"{ENTRY_ID}_telemetry_4145" not in to_disable
    assert f"{ENTRY_ID}_telemetry_4193" in to_disable


def test_core_entity_booleans():
    """Climate and fan were plain booleans rather than list entries."""
    assert unique_ids_to_disable({"enabled_climate": False}, ENTRY_ID) == {f"{ENTRY_ID}_climate"}
    assert unique_ids_to_disable({"enabled_fan": False}, ENTRY_ID) == {f"{ENTRY_ID}_fan_speed"}
    assert unique_ids_to_disable({"enabled_climate": True, "enabled_fan": True}, ENTRY_ID) == set()


def test_definition_sensor_wildcard_matching():
    """Definition unique IDs embed a device UUID that migration cannot know."""
    to_disable = unique_ids_to_disable({"enabled_connected_device_definition": []}, ENTRY_ID)

    assert matches(f"{ENTRY_ID}_definition_SIT12345_indoorTemperature", to_disable)
    assert matches(f"{ENTRY_ID}_definition_OTHERUUID_supplyTemperature", to_disable)
    assert not matches(f"{ENTRY_ID}_dashboard_indoorTemperature", to_disable)


def test_matches_is_exact_for_plain_ids():
    """Without a wildcard, matching must not be a prefix match."""
    patterns = {f"{ENTRY_ID}_telemetry_419"}

    assert matches(f"{ENTRY_ID}_telemetry_419", patterns)
    assert not matches(f"{ENTRY_ID}_telemetry_4193", patterns)
