"""Tests for ComfoClime integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
                                # polling_interval is passed as a positional argument (3rd position)
                                db_coord_args = mock_db_coord.call_args[0]
                                polling_interval_arg = db_coord_args[2]  # hass, api, polling_interval
                                assert isinstance(polling_interval_arg, int)
                                assert polling_interval_arg == 60
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
@pytest.mark.asyncio
async def test_async_unload_entry_closes_api(mock_hass, mock_config_entry):
    """Test async_unload_entry closes API session."""
    mock_api = MagicMock()
    mock_api.close = AsyncMock()

    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    mock_hass.data = {"comfoclime": {"test_entry_id": {"api": mock_api}}}

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    mock_api.close.assert_called_once()


# ============================================================================
# Validator tests for service input validation (coverage for __init__.py validation paths)
# ============================================================================


def test_validate_property_path_valid():
    """Test validate_property_path with valid paths."""
    from custom_components.comfoclime.validators import validate_property_path

    # Valid path format X/Y/Z
    is_valid, error = validate_property_path("29/1/10")
    assert is_valid is True
    assert error is None

    is_valid, error = validate_property_path("1/0/0")
    assert is_valid is True


def test_validate_property_path_invalid():
    """Test validate_property_path with invalid paths."""
    from custom_components.comfoclime.validators import validate_property_path

    # Invalid formats
    is_valid, error = validate_property_path("invalid")
    assert is_valid is False
    assert error is not None

    is_valid, error = validate_property_path("29/1")  # Missing part
    assert is_valid is False

    is_valid, error = validate_property_path("")  # Empty
    assert is_valid is False


def test_validate_byte_value_valid():
    """Test validate_byte_value with valid values."""
    from custom_components.comfoclime.validators import validate_byte_value

    # 1 byte unsigned: 0-255
    is_valid, error = validate_byte_value(0, 1, False)
    assert is_valid is True

    is_valid, error = validate_byte_value(255, 1, False)
    assert is_valid is True

    # 1 byte signed: -128 to 127
    is_valid, error = validate_byte_value(-128, 1, True)
    assert is_valid is True

    is_valid, error = validate_byte_value(127, 1, True)
    assert is_valid is True

    # 2 bytes unsigned: 0-65535
    is_valid, error = validate_byte_value(65535, 2, False)
    assert is_valid is True


def test_validate_byte_value_out_of_range():
    """Test validate_byte_value with out of range values."""
    from custom_components.comfoclime.validators import validate_byte_value

    # 1 byte unsigned overflow
    is_valid, error = validate_byte_value(256, 1, False)
    assert is_valid is False

    # 1 byte signed overflow
    is_valid, error = validate_byte_value(128, 1, True)
    assert is_valid is False

    # Negative value for unsigned
    is_valid, error = validate_byte_value(-1, 1, False)
    assert is_valid is False


def test_validate_duration_valid():
    """Test validate_duration with valid values."""
    from custom_components.comfoclime.validators import validate_duration

    is_valid, error = validate_duration(30)
    assert is_valid is True

    is_valid, error = validate_duration(1)
    assert is_valid is True

    is_valid, error = validate_duration(1440)  # 24 hours
    assert is_valid is True


def test_validate_duration_invalid():
    """Test validate_duration with invalid values."""
    from custom_components.comfoclime.validators import validate_duration

    # Negative duration
    is_valid, error = validate_duration(-10)
    assert is_valid is False
    assert error is not None

    # Zero duration
