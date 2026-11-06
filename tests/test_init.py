"""Tests for ComfoClime integration setup."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.comfoclime import (
    _remove_legacy_access_tracking_entities,
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.comfoclime.models import ConnectedDevicesResponse
from custom_components.comfoclime.runtime_data import ComfoClimeRuntimeData


@pytest.fixture(autouse=True)
def _mock_entity_registry():
    """Keep the setup-time registry access away from the bare mock hass."""
    with (
        patch("custom_components.comfoclime.er.async_get", return_value=MagicMock()),
        patch("custom_components.comfoclime.dr.async_get", return_value=MagicMock()),
    ):
        yield


@pytest.mark.asyncio
async def test_async_setup():
    """Test async_setup returns True and registers services."""
    mock_hass = MagicMock()
    mock_hass.services = MagicMock()
    mock_hass.services.async_register = MagicMock()
    config = {}

    result = await async_setup(mock_hass, config)

    assert result is True

    # Verify all three services were registered
    service_names = {call[0][1] for call in mock_hass.services.async_register.call_args_list}
    assert "set_property" in service_names
    assert "reset_system" in service_names
    assert "set_scenario_mode" in service_names


@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_hass,
    mock_config_entry,
    mock_api,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_device,
):
    """Test async_setup_entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as mock_db_coord:
            with patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as mock_tp_coord:
                with patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as mock_mon_coord:
                    with patch("custom_components.comfoclime.ComfoClimeTelemetryCoordinator") as mock_tl_coord:
                        with patch("custom_components.comfoclime.ComfoClimePropertyCoordinator") as mock_prop_coord:
                            with patch(
                                "custom_components.comfoclime.ComfoClimeDefinitionCoordinator"
                            ) as mock_def_coord:
                                # Setup mocks
                                mock_api_instance = MagicMock()
                                mock_api_instance.async_get_connected_devices = AsyncMock(
                                    return_value=ConnectedDevicesResponse(devices=[mock_device])
                                )
                                mock_api_class.return_value = mock_api_instance

                                mock_db_coord_instance = MagicMock()
                                mock_db_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_db_coord.return_value = mock_db_coord_instance

                                mock_tp_coord_instance = MagicMock()
                                mock_tp_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_tp_coord.return_value = mock_tp_coord_instance

                                mock_mon_coord_instance = MagicMock()
                                mock_mon_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_mon_coord.return_value = mock_mon_coord_instance

                                mock_tl_coord_instance = MagicMock()
                                mock_tl_coord.return_value = mock_tl_coord_instance

                                mock_prop_coord_instance = MagicMock()
                                mock_prop_coord.return_value = mock_prop_coord_instance

                                mock_def_coord_instance = MagicMock()
                                mock_def_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_def_coord.return_value = mock_def_coord_instance

                                # Call async_setup_entry
                                result = await async_setup_entry(mock_hass, mock_config_entry)

                                # Verify setup was successful
                                assert result is True

                            # Verify runtime data was stored on the entry
                            runtime_data = mock_config_entry.runtime_data
                            assert isinstance(runtime_data, ComfoClimeRuntimeData)
                            assert runtime_data.api is mock_api_instance
                            assert runtime_data.coordinator is mock_db_coord_instance
                            assert runtime_data.tpcoordinator is mock_tp_coord_instance
                            assert runtime_data.monitoringcoordinator is mock_mon_coord_instance
                            assert runtime_data.tlcoordinator is mock_tl_coord_instance
                            assert runtime_data.propcoordinator is mock_prop_coord_instance
                            assert runtime_data.definitioncoordinator is mock_def_coord_instance
                            assert runtime_data.devices == [mock_device]
                            assert runtime_data.main_device == mock_device
                            assert "comfoclime" not in mock_hass.data

                            # Verify platforms were set up
                            mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
                            platforms = mock_hass.config_entries.async_forward_entry_setups.call_args[0][1]
                            assert "sensor" in platforms
                            assert "switch" in platforms
                            assert "number" in platforms
                            assert "select" in platforms
                            assert "fan" in platforms
                            assert "climate" in platforms

                            # Reloads come from the config/options flow, not a listener
                            mock_config_entry.add_update_listener.assert_not_called()

                            # Services are registered in async_setup, not async_setup_entry


@pytest.mark.asyncio
async def test_async_setup_entry_with_float_max_retries(
    mock_hass,
    mock_config_entry,
    mock_api,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_device,
):
    """Test that integer config values are converted from float to int."""
    # Set all integer config values as floats (which can happen from NumberSelector)
    mock_config_entry.options = {
        "read_timeout": 10.0,
        "write_timeout": 30.0,
        "polling_interval": 60.0,
        "cache_ttl": 30.0,
        "max_retries": 3.0,
        # Float values should remain as float
        "min_request_interval": 0.1,
        "write_cooldown": 2.0,
        "request_debounce": 0.3,
    }
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as mock_db_coord:
            with patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as mock_tp_coord:
                with patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as mock_mon_coord:
                    with patch("custom_components.comfoclime.ComfoClimeTelemetryCoordinator") as mock_tl_coord:
                        with patch("custom_components.comfoclime.ComfoClimePropertyCoordinator") as mock_prop_coord:
                            with patch(
                                "custom_components.comfoclime.ComfoClimeDefinitionCoordinator"
                            ) as mock_def_coord:
                                # Setup mocks
                                mock_api_instance = MagicMock()
                                mock_api_instance.async_get_connected_devices = AsyncMock(
                                    return_value=ConnectedDevicesResponse(devices=[mock_device])
                                )
                                mock_api_class.return_value = mock_api_instance

                                mock_db_coord_instance = MagicMock()
                                mock_db_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_db_coord.return_value = mock_db_coord_instance

                                mock_tp_coord_instance = MagicMock()
                                mock_tp_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_tp_coord.return_value = mock_tp_coord_instance

                                mock_mon_coord_instance = MagicMock()
                                mock_mon_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_mon_coord.return_value = mock_mon_coord_instance

                                mock_tl_coord_instance = MagicMock()
                                mock_tl_coord.return_value = mock_tl_coord_instance

                                mock_prop_coord_instance = MagicMock()
                                mock_prop_coord.return_value = mock_prop_coord_instance

                                mock_def_coord_instance = MagicMock()
                                mock_def_coord_instance.async_config_entry_first_refresh = AsyncMock()
                                mock_def_coord.return_value = mock_def_coord_instance

                                # Call async_setup_entry
                                result = await async_setup_entry(mock_hass, mock_config_entry)

                                # Verify setup was successful
                                assert result is True

                                # Verify integer values were passed as int to API constructor
                                api_kwargs = mock_api_class.call_args[1]
                                assert isinstance(api_kwargs["read_timeout"], int)
                                assert api_kwargs["read_timeout"] == 10
                                assert isinstance(api_kwargs["write_timeout"], int)
                                assert api_kwargs["write_timeout"] == 30
                                assert isinstance(api_kwargs["cache_ttl"], int)
                                assert api_kwargs["cache_ttl"] == 30
                                assert isinstance(api_kwargs["max_retries"], int)
                                assert api_kwargs["max_retries"] == 3

                                # Verify float values remain as float
                                assert isinstance(api_kwargs["min_request_interval"], float)
                                assert api_kwargs["min_request_interval"] == 0.1
                                assert isinstance(api_kwargs["write_cooldown"], float)
                                assert api_kwargs["write_cooldown"] == 2.0
                                assert isinstance(api_kwargs["request_debounce"], float)
                                assert api_kwargs["request_debounce"] == 0.3

                                # Verify polling_interval was passed as int to coordinators
                                # Dashboard/Thermal/Monitoring keep base polling interval.
                                # Telemetry/Property/Definition use staggered intervals to reduce API load.
                                # polling interval is passed as positional argument:
                                # - index 2 for dashboard/thermal/monitoring
                                # - index 3 for telemetry/property/definition (devices arg at index 2)
                                db_coord_args = mock_db_coord.call_args[0]
                                assert isinstance(db_coord_args[2], int)
                                assert db_coord_args[2] == 60

                                tp_coord_args = mock_tp_coord.call_args[0]
                                assert isinstance(tp_coord_args[2], int)
                                assert tp_coord_args[2] == 60

                                mon_coord_args = mock_mon_coord.call_args[0]
                                assert isinstance(mon_coord_args[2], int)
                                assert mon_coord_args[2] == 60

                                tl_coord_args = mock_tl_coord.call_args[0]
                                assert isinstance(tl_coord_args[3], int)
                                assert tl_coord_args[3] == 120

                                prop_coord_args = mock_prop_coord.call_args[0]
                                assert isinstance(prop_coord_args[3], int)
                                assert prop_coord_args[3] == 180

                                def_coord_args = mock_def_coord.call_args[0]
                                assert isinstance(def_coord_args[3], int)
                                assert def_coord_args[3] == 240


@pytest.mark.asyncio
async def test_async_setup_entry_coordinator_first_refresh_failure(
    mock_hass,
    mock_config_entry,
    mock_device,
):
    """A coordinator that fails its first refresh aborts setup with ConfigEntryNotReady.

    Coordinators are refreshed concurrently (see async_setup_entry), so this also
    covers that a single failure among several concurrent refreshes is still
    detected and reported with the failing coordinator's name.
    """
    from homeassistant.exceptions import ConfigEntryNotReady

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as mock_db_coord:
            with patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as mock_tp_coord:
                with patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as mock_mon_coord:
                    with patch("custom_components.comfoclime.ComfoClimeDefinitionCoordinator") as mock_def_coord:
                        mock_api_instance = MagicMock()
                        mock_api_instance.async_get_connected_devices = AsyncMock(
                            return_value=ConnectedDevicesResponse(devices=[mock_device])
                        )
                        mock_api_class.return_value = mock_api_instance

                        mock_db_coord_instance = MagicMock()
                        mock_db_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_db_coord.return_value = mock_db_coord_instance

                        mock_tp_coord_instance = MagicMock()
                        mock_tp_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_tp_coord.return_value = mock_tp_coord_instance

                        mock_mon_coord_instance = MagicMock()
                        mock_mon_coord_instance.async_config_entry_first_refresh = AsyncMock(
                            side_effect=RuntimeError("boom")
                        )
                        mock_mon_coord.return_value = mock_mon_coord_instance

                        mock_def_coord_instance = MagicMock()
                        mock_def_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_def_coord.return_value = mock_def_coord_instance

                        with pytest.raises(ConfigEntryNotReady, match="monitoring"):
                            await async_setup_entry(mock_hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_coordinator_first_refresh_cancelled(
    mock_hass,
    mock_config_entry,
    mock_device,
):
    """A cancelled first refresh (e.g. setup task cancelled by a concurrent reload)
    propagates as CancelledError instead of being masked as ConfigEntryNotReady.
    """
    import asyncio

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as mock_db_coord:
            with patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as mock_tp_coord:
                with patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as mock_mon_coord:
                    with patch("custom_components.comfoclime.ComfoClimeDefinitionCoordinator") as mock_def_coord:
                        mock_api_instance = MagicMock()
                        mock_api_instance.async_get_connected_devices = AsyncMock(
                            return_value=ConnectedDevicesResponse(devices=[mock_device])
                        )
                        mock_api_class.return_value = mock_api_instance

                        mock_db_coord_instance = MagicMock()
                        mock_db_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_db_coord.return_value = mock_db_coord_instance

                        mock_tp_coord_instance = MagicMock()
                        mock_tp_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_tp_coord.return_value = mock_tp_coord_instance

                        mock_mon_coord_instance = MagicMock()
                        mock_mon_coord_instance.async_config_entry_first_refresh = AsyncMock(
                            side_effect=asyncio.CancelledError()
                        )
                        mock_mon_coord.return_value = mock_mon_coord_instance

                        mock_def_coord_instance = MagicMock()
                        mock_def_coord_instance.async_config_entry_first_refresh = AsyncMock()
                        mock_def_coord.return_value = mock_def_coord_instance

                        with pytest.raises(asyncio.CancelledError):
                            await async_setup_entry(mock_hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry, make_runtime_data):
    """Test async_unload_entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    api = MagicMock()
    api.close = AsyncMock()
    mock_config_entry.runtime_data = make_runtime_data(api=api)
    hass_data_before = dict(mock_hass.data)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    api.close.assert_awaited_once()
    assert mock_hass.data == hass_data_before


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_api_open_when_unload_fails(mock_hass, mock_config_entry, make_runtime_data):
    """A failed platform unload must not close the still-used API session."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    api = MagicMock()
    api.close = AsyncMock()
    mock_config_entry.runtime_data = make_runtime_data(api=api)

    assert await async_unload_entry(mock_hass, mock_config_entry) is False
    api.close.assert_not_called()

    # Verify platforms were unloaded via the HA helper
    mock_hass.config_entries.async_unload_platforms.assert_called_once()


def test_remove_legacy_access_tracking_entities(mock_hass, mock_config_entry):
    """Only this entry's former access-tracking sensors are removed."""
    entry_id = mock_config_entry.entry_id
    stale = [
        SimpleNamespace(entity_id="sensor.a", unique_id=f"{entry_id}_access_dashboard_per_minute"),
        SimpleNamespace(entity_id="sensor.b", unique_id=f"{entry_id}_access_total_per_hour"),
    ]
    kept = [
        SimpleNamespace(entity_id="sensor.c", unique_id=f"{entry_id}_telemetry_4145"),
        SimpleNamespace(entity_id="sensor.d", unique_id=None),
        SimpleNamespace(entity_id="sensor.e", unique_id="other_entry_access_total_per_hour"),
    ]
    mock_registry = MagicMock()

    with (
        patch("custom_components.comfoclime.er.async_get", return_value=mock_registry),
        patch(
            "custom_components.comfoclime.er.async_entries_for_config_entry",
            return_value=[*stale, *kept],
        ) as mock_entries,
    ):
        removed = _remove_legacy_access_tracking_entities(mock_hass, mock_config_entry)

    mock_entries.assert_called_once_with(mock_registry, entry_id)
    assert removed == 2
    assert [c.args[0] for c in mock_registry.async_remove.call_args_list] == ["sensor.a", "sensor.b"]


def test_remove_legacy_access_tracking_entities_noop_when_none(mock_hass, mock_config_entry):
    """A clean registry is left untouched."""
    mock_registry = MagicMock()
    with (
        patch("custom_components.comfoclime.er.async_get", return_value=mock_registry),
        patch("custom_components.comfoclime.er.async_entries_for_config_entry", return_value=[]),
    ):
        assert _remove_legacy_access_tracking_entities(mock_hass, mock_config_entry) == 0

    mock_registry.async_remove.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_runs_access_tracking_cleanup(mock_hass, mock_config_entry, mock_device):
    """Setup calls the registry cleanup for existing installations."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with (
        patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class,
        patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as c1,
        patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as c2,
        patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as c3,
        patch("custom_components.comfoclime.ComfoClimeDefinitionCoordinator") as c4,
        patch("custom_components.comfoclime.ComfoClimeTelemetryCoordinator"),
        patch("custom_components.comfoclime.ComfoClimePropertyCoordinator"),
        patch("custom_components.comfoclime._remove_legacy_access_tracking_entities") as mock_cleanup,
    ):
        mock_api_class.return_value.async_get_connected_devices = AsyncMock(
            return_value=ConnectedDevicesResponse(devices=[mock_device])
        )
        for coord in (c1, c2, c3, c4):
            coord.return_value.async_config_entry_first_refresh = AsyncMock()

        assert await async_setup_entry(mock_hass, mock_config_entry) is True

    mock_cleanup.assert_called_once_with(mock_hass, mock_config_entry)


async def _run_setup(mock_hass, mock_config_entry, devices, device_registry):
    """Run async_setup_entry with all coordinators/API mocked."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

    with (
        patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class,
        patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as c1,
        patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as c2,
        patch("custom_components.comfoclime.ComfoClimeMonitoringCoordinator") as c3,
        patch("custom_components.comfoclime.ComfoClimeDefinitionCoordinator") as c4,
        patch("custom_components.comfoclime.ComfoClimeTelemetryCoordinator"),
        patch("custom_components.comfoclime.ComfoClimePropertyCoordinator"),
        patch("custom_components.comfoclime.dr.async_get", return_value=device_registry),
    ):
        mock_api_class.return_value.async_get_connected_devices = AsyncMock(
            return_value=ConnectedDevicesResponse(devices=devices)
        )
        for coord in (c1, c2, c3, c4):
            coord.return_value.async_config_entry_first_refresh = AsyncMock()

        assert await async_setup_entry(mock_hass, mock_config_entry) is True


@pytest.mark.asyncio
async def test_async_setup_entry_registers_main_device(mock_hass, mock_config_entry, mock_device):
    """The ComfoClime device is registered up front and its registry id stored."""
    registry = MagicMock()
    registry.async_get_or_create.return_value = SimpleNamespace(id="registry-id-1")

    await _run_setup(mock_hass, mock_config_entry, [mock_device], registry)

    registry.async_get_or_create.assert_called_once()
    kwargs = registry.async_get_or_create.call_args.kwargs
    assert kwargs["config_entry_id"] == "test_entry_id"
    assert kwargs["identifiers"] == {("comfoclime", "test-device-uuid")}
    assert kwargs["manufacturer"] == "Zehnder"
    assert kwargs["name"] == "ComfoClime Test"
    assert mock_config_entry.runtime_data.main_device_registry_id == "registry-id-1"


@pytest.mark.asyncio
async def test_async_setup_entry_without_main_device(mock_hass, mock_config_entry, mock_connected_device):
    """Without a ComfoClime device nothing is registered and the id is None."""
    registry = MagicMock()

    await _run_setup(mock_hass, mock_config_entry, [mock_connected_device], registry)

    registry.async_get_or_create.assert_not_called()
    assert mock_config_entry.runtime_data.main_device_registry_id is None


@pytest.mark.asyncio
async def test_async_migrate_entry_disables_deselected_entities(mock_hass, mock_config_entry):
    """A version 1 entry's deselections become registry disables, not deletions."""
    mock_config_entry.version = 1
    mock_config_entry.options = {
        "enabled_fan": False,
        "polling_interval": 45,
    }
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_update_entry = MagicMock()

    stale_fan = SimpleNamespace(
        entity_id="fan.comfoclime_fan_speed",
        unique_id=f"{mock_config_entry.entry_id}_fan_speed",
        disabled=False,
    )
    kept_climate = SimpleNamespace(
        entity_id="climate.comfoclime",
        unique_id=f"{mock_config_entry.entry_id}_climate",
        disabled=False,
    )
    mock_registry = MagicMock()

    with (
        patch("custom_components.comfoclime.er.async_get", return_value=mock_registry),
        patch(
            "custom_components.comfoclime.er.async_entries_for_config_entry",
            return_value=[stale_fan, kept_climate],
        ),
    ):
        assert await async_migrate_entry(mock_hass, mock_config_entry) is True

    mock_registry.async_remove.assert_not_called()
    mock_registry.async_update_entity.assert_called_once()
    assert mock_registry.async_update_entity.call_args.args[0] == "fan.comfoclime_fan_speed"

    new_options = mock_hass.config_entries.async_update_entry.call_args.kwargs["options"]
    assert "enabled_fan" not in new_options
    assert new_options["polling_interval"] == 45
    assert mock_hass.config_entries.async_update_entry.call_args.kwargs["version"] == 2


@pytest.mark.asyncio
async def test_async_migrate_entry_is_a_noop_at_current_version(mock_hass, mock_config_entry):
    """Already-migrated entries are left untouched."""
    mock_config_entry.version = 2
    mock_hass.config_entries = MagicMock()

    assert await async_migrate_entry(mock_hass, mock_config_entry) is True

    mock_hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_connection_error(mock_hass, mock_config_entry):
    """Test async_setup_entry raises ConfigEntryNotReady on connection error."""
    import aiohttp
    from homeassistant.exceptions import ConfigEntryNotReady

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_update_entry = MagicMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        # Setup mock to raise connection error
        mock_api_instance = MagicMock()
        mock_api_instance.async_get_connected_devices = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(
                connection_key=MagicMock(), os_error=OSError(113, "Connect call failed ('10.0.2.27', 80)")
            )
        )
        mock_api_instance.close = AsyncMock()
        mock_api_class.return_value = mock_api_instance

        # Call async_setup_entry and expect ConfigEntryNotReady
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(mock_hass, mock_config_entry)

        # Verify error message contains the host
        assert "192.168.1.100" in str(exc_info.value)

        # Verify API session was closed
        mock_api_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_timeout_error(mock_hass, mock_config_entry):
    """Test async_setup_entry raises ConfigEntryNotReady on timeout."""
    from homeassistant.exceptions import ConfigEntryNotReady

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_update_entry = MagicMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        # Setup mock to raise timeout error
        mock_api_instance = MagicMock()
        mock_api_instance.async_get_connected_devices = AsyncMock(side_effect=TimeoutError("Connection timeout"))
        mock_api_instance.close = AsyncMock()
        mock_api_class.return_value = mock_api_instance

        # Call async_setup_entry and expect ConfigEntryNotReady
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(mock_hass, mock_config_entry)

        # Verify error message contains the host
        assert "192.168.1.100" in str(exc_info.value)

        # Verify API session was closed
        mock_api_instance.close.assert_called_once()
