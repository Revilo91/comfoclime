"""Tests for the config entry migrations.

Version 1 stored per-entity selection in the entry options. Version 2 hands
that job to the entity registry. The translation has to be exact in both
directions: an entity the user had switched off must end up disabled, and an
entity they kept must be left alone.

Version 2.2 adds the device UUID to the unique IDs of bus-device entities, so
two devices of the same model no longer collide. Existing registry entries are
renamed in place to keep history, names and areas.
"""

import logging

import pytest
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoclime import async_migrate_entry
from custom_components.comfoclime.config_flow import ComfoClimeConfigFlow
from custom_components.comfoclime.constants import DOMAIN
from custom_components.comfoclime.entities.number_definitions import NUMBER_ENTITIES
from custom_components.comfoclime.entities.sensor_definitions import (
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
)
from custom_components.comfoclime.entities.switch_definitions import SWITCHES
from custom_components.comfoclime.migration import (
    async_migrate_bus_device_unique_ids,
    build_option_id_map,
    legacy_bus_id_rewriter,
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


# ---------------------------------------------------------------------------
# Version 2.1 -> 2.2: device UUID in the unique IDs of bus-device entities
# ---------------------------------------------------------------------------

AIR_UUID = "DEM9876543210"
CLIME_UUID = "SIT0123456789"


class TestLegacyBusIdRewriter:
    """The pure matching part: which old IDs are rewritten, and into what."""

    @pytest.mark.parametrize(
        ("domain", "old", "new"),
        [
            ("sensor", f"{ENTRY_ID}_telemetry_117", f"{ENTRY_ID}_telemetry_{AIR_UUID}_117"),
            ("sensor", f"{ENTRY_ID}_property_1_1_4", f"{ENTRY_ID}_property_{AIR_UUID}_1_1_4"),
            ("number", f"{ENTRY_ID}_property_number_29_1_10", f"{ENTRY_ID}_property_number_{AIR_UUID}_29_1_10"),
            ("select", f"{ENTRY_ID}_select_29_1_15", f"{ENTRY_ID}_select_{AIR_UUID}_29_1_15"),
        ],
    )
    def test_old_patterns_are_rewritten(self, domain, old, new):
        rewrite = legacy_bus_id_rewriter(ENTRY_ID, domain, old)
        assert rewrite is not None
        assert rewrite(AIR_UUID) == new

    @pytest.mark.parametrize(
        ("domain", "unique_id"),
        [
            # Main-device entities never had the collision problem.
            ("climate", f"{ENTRY_ID}_climate"),
            ("fan", f"{ENTRY_ID}_fan_speed"),
            ("switch", f"{ENTRY_ID}_switch_season.status"),
            ("select", f"{ENTRY_ID}_select_temperatureProfile"),
            ("number", f"{ENTRY_ID}_temperature.manualTemperature"),
            ("sensor", f"{ENTRY_ID}_dashboard_indoorTemperature"),
            ("sensor", f"{ENTRY_ID}_definition_{AIR_UUID}_indoorTemperature"),
            # Already migrated: must not match again (idempotency).
            ("sensor", f"{ENTRY_ID}_telemetry_{AIR_UUID}_117"),
            ("sensor", f"{ENTRY_ID}_property_{AIR_UUID}_1_1_4"),
            ("number", f"{ENTRY_ID}_property_number_{AIR_UUID}_29_1_10"),
            ("select", f"{ENTRY_ID}_select_{AIR_UUID}_29_1_15"),
            # Right shape, wrong platform or wrong entry.
            ("sensor", f"{ENTRY_ID}_select_29_1_15"),
            ("number", f"{ENTRY_ID}_telemetry_117"),
            ("sensor", "other_entry_telemetry_117"),
        ],
    )
    def test_everything_else_is_left_alone(self, domain, unique_id):
        assert legacy_bus_id_rewriter(ENTRY_ID, domain, unique_id) is None


@pytest.fixture
def config_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.168.1.100"}, version=2, minor_version=1)
    entry.add_to_hass(hass)
    return entry


def _device(hass, entry, uuid):
    return dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, uuid)})


def _entity(hass, entry, domain, unique_id, device=None):
    return er.async_get(hass).async_get_or_create(
        domain, DOMAIN, unique_id, config_entry=entry, device_id=device.id if device else None
    )


class TestMigrateBusDeviceUniqueIds:
    """The registry-facing part, against real registries."""

    async def test_each_old_pattern_gets_its_devices_uuid(self, hass, config_entry):
        eid = config_entry.entry_id
        air = _device(hass, config_entry, AIR_UUID)
        clime = _device(hass, config_entry, CLIME_UUID)
        telemetry = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_4145", clime)
        prop = _entity(hass, config_entry, "sensor", f"{eid}_property_1_1_4", air)
        number = _entity(hass, config_entry, "number", f"{eid}_property_number_29_1_10", air)
        select = _entity(hass, config_entry, "select", f"{eid}_select_29_1_15", air)

        assert await async_migrate_bus_device_unique_ids(hass, eid) == 4

        registry = er.async_get(hass)
        assert registry.async_get(telemetry.entity_id).unique_id == f"{eid}_telemetry_{CLIME_UUID}_4145"
        assert registry.async_get(prop.entity_id).unique_id == f"{eid}_property_{AIR_UUID}_1_1_4"
        assert registry.async_get(number.entity_id).unique_id == f"{eid}_property_number_{AIR_UUID}_29_1_10"
        assert registry.async_get(select.entity_id).unique_id == f"{eid}_select_{AIR_UUID}_29_1_15"

    async def test_entity_id_and_customisations_survive(self, hass, config_entry):
        """The point of migrating instead of recreating: history and names stay."""
        eid = config_entry.entry_id
        air = _device(hass, config_entry, AIR_UUID)
        entity = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_117", air)
        registry = er.async_get(hass)
        registry.async_update_entity(entity.entity_id, name="Abluft-Lüfter", area_id="keller")

        await async_migrate_bus_device_unique_ids(hass, eid)

        migrated = registry.async_get(entity.entity_id)
        assert migrated.id == entity.id
        assert migrated.name == "Abluft-Lüfter"
        assert migrated.area_id == "keller"

    async def test_main_device_entities_are_untouched(self, hass, config_entry):
        eid = config_entry.entry_id
        clime = _device(hass, config_entry, CLIME_UUID)
        unchanged = {
            _entity(hass, config_entry, "climate", f"{eid}_climate", clime).entity_id: f"{eid}_climate",
            _entity(hass, config_entry, "switch", f"{eid}_switch_season.status", clime).entity_id: (
                f"{eid}_switch_season.status"
            ),
            _entity(hass, config_entry, "select", f"{eid}_select_temperatureProfile", clime).entity_id: (
                f"{eid}_select_temperatureProfile"
            ),
        }

        assert await async_migrate_bus_device_unique_ids(hass, eid) == 0

        registry = er.async_get(hass)
        for entity_id, unique_id in unchanged.items():
            assert registry.async_get(entity_id).unique_id == unique_id

    async def test_entity_without_device_is_left_alone(self, hass, config_entry, caplog):
        eid = config_entry.entry_id
        orphan = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_117")

        with caplog.at_level(logging.WARNING):
            assert await async_migrate_bus_device_unique_ids(hass, eid) == 0

        assert er.async_get(hass).async_get(orphan.entity_id).unique_id == f"{eid}_telemetry_117"
        assert orphan.entity_id in caplog.text

    async def test_device_without_comfoclime_identifier_is_left_alone(self, hass, config_entry, caplog):
        eid = config_entry.entry_id
        foreign = dr.async_get(hass).async_get_or_create(config_entry_id=eid, identifiers={("other_domain", AIR_UUID)})
        entity = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_117", foreign)

        with caplog.at_level(logging.WARNING):
            assert await async_migrate_bus_device_unique_ids(hass, eid) == 0

        assert er.async_get(hass).async_get(entity.entity_id).unique_id == f"{eid}_telemetry_117"
        assert entity.entity_id in caplog.text

    async def test_collision_is_skipped_not_raised(self, hass, config_entry, caplog):
        """If the new ID is already taken, keep both entities as they are."""
        eid = config_entry.entry_id
        air = _device(hass, config_entry, AIR_UUID)
        old = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_117", air)
        new = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_{AIR_UUID}_117", air)

        with caplog.at_level(logging.WARNING):
            assert await async_migrate_bus_device_unique_ids(hass, eid) == 0

        registry = er.async_get(hass)
        assert registry.async_get(old.entity_id).unique_id == f"{eid}_telemetry_117"
        assert registry.async_get(new.entity_id).unique_id == f"{eid}_telemetry_{AIR_UUID}_117"
        assert old.entity_id in caplog.text

    async def test_second_run_is_a_noop(self, hass, config_entry):
        eid = config_entry.entry_id
        air = _device(hass, config_entry, AIR_UUID)
        entity = _entity(hass, config_entry, "sensor", f"{eid}_telemetry_117", air)

        assert await async_migrate_bus_device_unique_ids(hass, eid) == 1
        assert await async_migrate_bus_device_unique_ids(hass, eid) == 0

        assert er.async_get(hass).async_get(entity.entity_id).unique_id == f"{eid}_telemetry_{AIR_UUID}_117"

    async def test_other_config_entries_are_not_touched(self, hass, config_entry):
        other = MockConfigEntry(domain=DOMAIN, data={"host": "192.168.1.101"}, version=2, minor_version=1)
        other.add_to_hass(hass)
        air = _device(hass, other, AIR_UUID)
        foreign = _entity(hass, other, "sensor", f"{other.entry_id}_telemetry_117", air)

        assert await async_migrate_bus_device_unique_ids(hass, config_entry.entry_id) == 0

        assert er.async_get(hass).async_get(foreign.entity_id).unique_id == f"{other.entry_id}_telemetry_117"


# ---------------------------------------------------------------------------
# async_migrate_entry: the version chain
# ---------------------------------------------------------------------------


def _registry_entity(hass, entry, domain, unique_id, device_uuid):
    """Create a real registry entry attached to a ComfoClime device."""
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, device_uuid)})
    return er.async_get(hass).async_get_or_create(domain, DOMAIN, unique_id, config_entry=entry, device_id=device.id)


async def test_async_migrate_entry_2_1_adds_device_uuid_to_unique_ids(hass):
    """2.1 -> 2.2 renames bus-device unique IDs in place and bumps the minor version."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"}, version=2, minor_version=1)
    entry.add_to_hass(hass)
    entity = _registry_entity(hass, entry, "sensor", f"{entry.entry_id}_telemetry_117", AIR_UUID)

    assert await async_migrate_entry(hass, entry) is True

    assert (entry.version, entry.minor_version) == (2, 2)
    migrated = er.async_get(hass).async_get(entity.entity_id)
    assert migrated.unique_id == f"{entry.entry_id}_telemetry_{AIR_UUID}_117"


async def test_async_migrate_entry_1_chains_through_to_2_2(hass):
    """A version 1 entry gets both migrations, in order, and ends at 2.2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "1.2.3.4"},
        options={"enabled_connected_device_telemetry": [], "polling_interval": 45},
        version=1,
    )
    entry.add_to_hass(hass)
    entity = _registry_entity(hass, entry, "sensor", f"{entry.entry_id}_telemetry_117", AIR_UUID)

    assert await async_migrate_entry(hass, entry) is True

    assert (entry.version, entry.minor_version) == (2, 2)
    assert "enabled_connected_device_telemetry" not in entry.options
    assert entry.options["polling_interval"] == 45
    migrated = er.async_get(hass).async_get(entity.entity_id)
    # Disabled by the v1 step (matched on the old ID), then renamed by the 2.2 step.
    assert migrated.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert migrated.unique_id == f"{entry.entry_id}_telemetry_{AIR_UUID}_117"


async def test_async_migrate_entry_at_2_2_does_not_touch_the_registry(hass):
    """At the current version nothing is rewritten, even IDs that look old."""
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"}, version=2, minor_version=2)
    entry.add_to_hass(hass)
    entity = _registry_entity(hass, entry, "sensor", f"{entry.entry_id}_telemetry_117", AIR_UUID)

    assert await async_migrate_entry(hass, entry) is True

    assert (entry.version, entry.minor_version) == (2, 2)
    assert er.async_get(hass).async_get(entity.entity_id).unique_id == f"{entry.entry_id}_telemetry_117"


def test_config_flow_creates_entries_at_2_2():
    """New entries start at the version the migration chain ends at."""
    assert (ComfoClimeConfigFlow.VERSION, ComfoClimeConfigFlow.MINOR_VERSION) == (2, 2)
