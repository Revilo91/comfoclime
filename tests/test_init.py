"""Tests for ComfoClime integration setup."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.comfoclime import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)


@pytest.mark.asyncio
async def test_async_setup():
    """Test async_setup returns True."""
    mock_hass = MagicMock()
    config = {}

    result = await async_setup(mock_hass, config)

    assert result is True


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
    mock_hass.services = MagicMock()
    mock_hass.services.async_register = MagicMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch(
            "custom_components.comfoclime.ComfoClimeDashboardCoordinator"
        ) as mock_db_coord:
            with patch(
                "custom_components.comfoclime.ComfoClimeThermalprofileCoordinator"
            ) as mock_tp_coord:
                with patch(
                    "custom_components.comfoclime.ComfoClimeMonitoringCoordinator"
                ) as mock_mon_coord:
                    with patch(
                        "custom_components.comfoclime.ComfoClimeTelemetryCoordinator"
                    ) as mock_tl_coord:
                        with patch(
                            "custom_components.comfoclime.ComfoClimePropertyCoordinator"
                        ) as mock_prop_coord:
                            with patch(
                                "custom_components.comfoclime.ComfoClimeDefinitionCoordinator"
                            ) as mock_def_coord:
                                # Setup mocks
                                mock_api_instance = MagicMock()
                                mock_api_instance.async_get_connected_devices = AsyncMock(
                                    return_value=[mock_device]
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

                                # Verify data was stored in hass.data
                            assert "comfoclime" in mock_hass.data
                            assert "test_entry_id" in mock_hass.data["comfoclime"]

                            # Verify platforms were set up
                            mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
                            platforms = (
                                mock_hass.config_entries.async_forward_entry_setups.call_args[0][1]
                            )
                            assert "sensor" in platforms
                            assert "switch" in platforms
                            assert "number" in platforms
                            assert "select" in platforms
                            assert "fan" in platforms
                            assert "climate" in platforms

                            # Verify services were registered (set_property, reset_system, set_scenario_mode)
                            assert mock_hass.services.async_register.call_count == 3


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
    mock_hass.services = MagicMock()
    mock_hass.services.async_register = MagicMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch(
            "custom_components.comfoclime.ComfoClimeDashboardCoordinator"
        ) as mock_db_coord:
            with patch(
                "custom_components.comfoclime.ComfoClimeThermalprofileCoordinator"
            ) as mock_tp_coord:
                with patch(
                    "custom_components.comfoclime.ComfoClimeMonitoringCoordinator"
                ) as mock_mon_coord:
                    with patch(
                        "custom_components.comfoclime.ComfoClimeTelemetryCoordinator"
                    ) as mock_tl_coord:
                        with patch(
                            "custom_components.comfoclime.ComfoClimePropertyCoordinator"
                        ) as mock_prop_coord:
                            with patch(
                                "custom_components.comfoclime.ComfoClimeDefinitionCoordinator"
                            ) as mock_def_coord:
                                # Setup mocks
                                mock_api_instance = MagicMock()
                                mock_api_instance.async_get_connected_devices = AsyncMock(
                                    return_value=[mock_device]
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
                                db_coord_kwargs = mock_db_coord.call_args[1]
                                assert isinstance(db_coord_kwargs["polling_interval"], int)
                                assert db_coord_kwargs["polling_interval"] == 60


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test async_unload_entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    mock_hass.data = {"comfoclime": {"test_entry_id": {}}}

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    assert "test_entry_id" not in mock_hass.data["comfoclime"]

    # Verify all platforms were unloaded
    assert mock_hass.config_entries.async_forward_entry_unload.call_count == 6
