"""Tests for the config-entry diagnostics download."""

import json
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.comfoclime.constants import DOMAIN
from custom_components.comfoclime.coordinator import (
    ComfoClimeAlarmsCoordinator,
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeHealthCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from custom_components.comfoclime.diagnostics import async_get_config_entry_diagnostics
from custom_components.comfoclime.models import (
    AlarmsResponse,
    DashboardData,
    DeviceConfig,
    DeviceDefinitionData,
    MonitoringHealth,
    MonitoringPing,
    ThermalProfileData,
)

HOST = "192.168.178.77"
CLIME_UUID = "SIT0123456789"
AIR_UUID = "DEM9876543210"
SERIAL = "SN-555-SECRET"
COORDINATOR_KEYS = {"dashboard", "thermalprofile", "monitoring", "telemetry", "property", "definition"}


@pytest.fixture
def entry(hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"ComfoClime @ {HOST}",
        unique_id=CLIME_UUID,
        data={"host": HOST},
        options={"polling_interval": 60},
        version=2,
    )
    config_entry.add_to_hass(hass)
    return config_entry


@pytest.fixture
async def loaded_entry(hass, entry, make_runtime_data):
    """Entry with real coordinators holding realistic data."""
    api = MagicMock()
    devices = [
        DeviceConfig(uuid=CLIME_UUID, model_type_id=20, display_name="ComfoClime", version="1.2.3"),
        DeviceConfig(uuid=AIR_UUID, model_type_id=1, display_name="ComfoAir Q"),
    ]
    dashboard = ComfoClimeDashboardCoordinator(hass, api, config_entry=entry)
    dashboard.data = DashboardData(indoorTemperature=22.5, fanSpeed=2)
    thermal = ComfoClimeThermalprofileCoordinator(hass, api, config_entry=entry)
    thermal.data = ThermalProfileData()
    monitoring = ComfoClimeMonitoringCoordinator(hass, api, config_entry=entry)
    monitoring.data = MonitoringPing(uuid=CLIME_UUID, uptime=3600, serialNumber=SERIAL)
    telemetry = ComfoClimeTelemetryCoordinator(hass, api, devices=devices, config_entry=entry)
    await telemetry.register_telemetry(CLIME_UUID, "4154", faktor=0.1, signed=True, byte_count=2)
    telemetry.data = {CLIME_UUID: {"4154": 21.4}}
    props = ComfoClimePropertyCoordinator(hass, api, devices=devices, config_entry=entry)
    await props.register_property(AIR_UUID, "29/1/10", faktor=0.1, byte_count=2)
    props.data = {AIR_UUID: {"29/1/10": 5.5}}
    definition = ComfoClimeDefinitionCoordinator(hass, api, devices=devices, config_entry=entry)
    definition.data = {AIR_UUID: DeviceDefinitionData(indoorTemperature=21.0, serialNumber=SERIAL)}

    entry.runtime_data = make_runtime_data(
        api=api,
        coordinator=dashboard,
        tpcoordinator=thermal,
        monitoringcoordinator=monitoring,
        tlcoordinator=telemetry,
        propcoordinator=props,
        definitioncoordinator=definition,
        devices=devices,
    )
    return entry


async def test_contains_all_six_coordinators(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert set(result["coordinators"]) == COORDINATOR_KEYS
    for info in result["coordinators"].values():
        assert info["update_interval"] == 60
        assert "last_update_success" in info
        assert "data" in info


async def test_result_is_json_serializable(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    json.dumps(result)


async def test_sensitive_values_are_not_in_output(hass, loaded_entry):
    dump = json.dumps(await async_get_config_entry_diagnostics(hass, loaded_entry))

    for secret in (HOST, CLIME_UUID, AIR_UUID, SERIAL):
        assert secret not in dump


async def test_debug_relevant_values_are_kept(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)
    dump = json.dumps(result)

    assert result["entry"]["version"] == 2
    assert result["entry"]["options"] == {"polling_interval": 60}
    assert sorted(d["model_type_id"] for d in result["devices"]) == [1, 20]
    assert result["devices"][0]["version"] == "1.2.3"
    assert "21.4" in dump
    assert "29/1/10" in dump


async def test_registry_entries_are_reported(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    telemetry = result["coordinators"]["telemetry"]
    assert telemetry["registered_count"] == 1
    assert next(iter(telemetry["registered"].values()))["4154"]["byte_count"] == 2
    assert result["coordinators"]["property"]["registered_count"] == 1


async def test_device_keys_stay_distinguishable(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert len(result["coordinators"]["property"]["data"]) == 1
    assert len(result["coordinators"]["telemetry"]["data"]) == 1
    assert set(result["coordinators"]["property"]["data"]) != set(result["coordinators"]["telemetry"]["data"])


async def test_coordinators_without_data(hass, entry, make_runtime_data):
    api = MagicMock()
    entry.runtime_data = make_runtime_data(
        coordinator=ComfoClimeDashboardCoordinator(hass, api, config_entry=entry),
        tpcoordinator=ComfoClimeThermalprofileCoordinator(hass, api, config_entry=entry),
        monitoringcoordinator=ComfoClimeMonitoringCoordinator(hass, api, config_entry=entry),
        tlcoordinator=ComfoClimeTelemetryCoordinator(hass, api, devices=[], config_entry=entry),
        propcoordinator=ComfoClimePropertyCoordinator(hass, api, devices=[], config_entry=entry),
        definitioncoordinator=ComfoClimeDefinitionCoordinator(hass, api, devices=[], config_entry=entry),
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert set(result["coordinators"]) == COORDINATOR_KEYS
    assert all(info["data"] is None for info in result["coordinators"].values())
    assert result["devices"] == []
    assert HOST not in json.dumps(result)


@pytest.fixture
def entry_with_health_and_alarms(hass, loaded_entry):
    """The loaded entry plus the two lazy coordinators, filled with data."""
    api = MagicMock()
    health = ComfoClimeHealthCoordinator(hass, api, config_entry=loaded_entry)
    health.data = MonitoringHealth(total_free_bytes=96612, twai_arb_lost_count=4437, open_sockets=[58, 59])
    alarms = ComfoClimeAlarmsCoordinator(hass, api, config_entry=loaded_entry)
    alarms.data = AlarmsResponse.from_api(
        {
            "devices": [
                {"uuid": AIR_UUID, "modelTypeId": 1, "variant": 1, "zoneId": 1, "errors": [0] * 12 + [16] + [0] * 19},
                {"uuid": CLIME_UUID, "modelTypeId": 20, "variant": 1, "zoneId": 1, "errors": [0] * 32},
            ]
        }
    )
    loaded_entry.runtime_data.healthcoordinator = health
    loaded_entry.runtime_data.alarmscoordinator = alarms
    return loaded_entry


async def test_lazy_coordinators_are_reported_when_present(hass, entry_with_health_and_alarms):
    result = await async_get_config_entry_diagnostics(hass, entry_with_health_and_alarms)

    assert set(result["coordinators"]) == COORDINATOR_KEYS | {"health", "alarms"}
    assert result["coordinators"]["health"]["data"]["total_free_bytes"] == 96612
    assert result["coordinators"]["health"]["data"]["twai_arb_lost_count"] == 4437


async def test_lazy_coordinators_are_omitted_when_absent(hass, loaded_entry):
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert "health" not in result["coordinators"]
    assert "alarms" not in result["coordinators"]


async def test_alarm_serial_numbers_are_redacted_but_alarm_values_kept(hass, entry_with_health_and_alarms):
    result = await async_get_config_entry_diagnostics(hass, entry_with_health_and_alarms)
    dump = json.dumps(result)

    for secret in (HOST, CLIME_UUID, AIR_UUID, SERIAL):
        assert secret not in dump
    devices = result["coordinators"]["alarms"]["data"]["devices"]
    assert [d["modelTypeId"] for d in devices] == [1, 20]
    assert devices[0]["errors"][12] == 16
