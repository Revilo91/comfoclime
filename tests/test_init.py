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
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_api, mock_coordinator, mock_thermalprofile_coordinator, mock_device):
    """Test async_setup_entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
    mock_hass.services = MagicMock()
    mock_hass.services.async_register = MagicMock()

    with patch("custom_components.comfoclime.ComfoClimeAPI") as mock_api_class:
        with patch("custom_components.comfoclime.ComfoClimeDashboardCoordinator") as mock_db_coord:
            with patch("custom_components.comfoclime.ComfoClimeThermalprofileCoordinator") as mock_tp_coord:
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

                # Call async_setup_entry
                result = await async_setup_entry(mock_hass, mock_config_entry)

                # Verify setup was successful
                assert result is True

                # Verify data was stored in hass.data
                assert "comfoclime" in mock_hass.data
                assert "test_entry_id" in mock_hass.data["comfoclime"]

                # Verify platforms were set up
                mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
                platforms = mock_hass.config_entries.async_forward_entry_setups.call_args[0][1]
                assert "sensor" in platforms
                assert "switch" in platforms
                assert "number" in platforms
                assert "select" in platforms
                assert "fan" in platforms
                assert "climate" in platforms

                # Verify services were registered
                assert mock_hass.services.async_register.call_count == 2


@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_config_entry):
    """Test async_unload_entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_unload = AsyncMock(return_value=True)
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {}
        }
    }

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    assert "test_entry_id" not in mock_hass.data["comfoclime"]

    # Verify all platforms were unloaded
    assert mock_hass.config_entries.async_forward_entry_unload.call_count == 6
