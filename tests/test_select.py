"""Tests for ComfoClime select entities."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from custom_components.comfoclime.select import (
    ComfoClimeSelect,
    ComfoClimePropertySelect,
    async_setup_entry,
)


class TestComfoClimeSelect:
    """Test ComfoClimeSelect class."""

    def test_select_initialization(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test select entity initialization."""
        config = {
            "key": "temperatureProfile",
            "name": "Temperature Profile",
            "translation_key": "temperature_profile",
            "options": {0: "comfort", 1: "power", 2: "eco"},
        }

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert select._key == "temperatureProfile"
        assert select._name == "Temperature Profile"
        assert select.options == ["comfort", "power", "eco"]
        assert select._attr_unique_id == "test_entry_id_select_temperatureProfile"

    def test_select_current_option(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test select entity current option from coordinator."""
        config = {
            "key": "temperatureProfile",
            "name": "Temperature Profile",
            "translation_key": "temperature_profile",
            "options": {0: "comfort", 1: "power", 2: "eco"},
        }

        mock_thermalprofile_coordinator.data = {"temperatureProfile": 1}

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        select.hass = mock_hass
        select.async_write_ha_state = MagicMock()

        select._handle_coordinator_update()

        assert select.current_option == "power"

    def test_select_nested_key(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test select entity with nested key."""
        config = {
            "key": "season.mode",
            "name": "Season Mode",
            "translation_key": "season_mode",
            "options": {0: "auto", 1: "manual"},
        }

        mock_thermalprofile_coordinator.data = {
            "season": {"mode": 0}
        }

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        select.hass = mock_hass
        select.async_write_ha_state = MagicMock()

        select._handle_coordinator_update()

        assert select.current_option == "auto"

    @pytest.mark.asyncio
    async def test_select_option(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test selecting an option."""
        config = {
            "key": "season.status",
            "name": "Season Status",
            "translation_key": "season_status",
            "options": {0: "auto", 1: "manual"},
        }

        mock_hass.add_job = MagicMock()

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        await select.async_select_option("manual")

        # Verify API was called with correct parameter
        mock_api.async_update_thermal_profile.assert_called_once_with(season_status=1)

    @pytest.mark.asyncio
    async def test_select_temperature_profile_option(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test selecting temperature profile option uses thermal profile API."""
        config = {
            "key": "temperatureProfile",
            "name": "Temperature Profile",
            "translation_key": "temperature_profile",
            "options": {0: "comfort", 1: "power", 2: "eco"},
        }

        mock_hass.add_job = MagicMock()

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        await select.async_select_option("eco")

        # Should use async_update_thermal_profile for temperature profile
        mock_api.async_update_thermal_profile.assert_called_once_with(temperature_profile=2)

    def test_select_device_info(self, mock_hass, mock_thermalprofile_coordinator, mock_api, mock_device, mock_config_entry):
        """Test select entity device info."""
        config = {
            "key": "temperatureProfile",
            "name": "Temperature Profile",
            "translation_key": "temperature_profile",
            "options": {0: "comfort", 1: "power", 2: "eco"},
        }

        select = ComfoClimeSelect(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = select.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]


class TestComfoClimePropertySelect:
    """Test ComfoClimePropertySelect class."""

    def test_property_select_initialization(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test property select entity initialization."""
        config = {
            "path": "29/1/15",
            "name": "Ventilation Mode",
            "translation_key": "ventilation_mode",
            "options": {0: "auto", 1: "manual", 2: "boost"},
        }

        select = ComfoClimePropertySelect(
            hass=mock_hass,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert select._path == "29/1/15"
        assert select._name == "Ventilation Mode"
        assert select.options == ["auto", "manual", "boost"]
        assert select._attr_unique_id == "test_entry_id_select_29_1_15"

    @pytest.mark.asyncio
    async def test_property_select_async_update(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test property select async update."""
        config = {
            "path": "29/1/15",
            "name": "Ventilation Mode",
            "translation_key": "ventilation_mode",
            "options": {0: "auto", 1: "manual", 2: "boost"},
        }

        mock_api.async_read_property_for_device.return_value = 1

        select = ComfoClimePropertySelect(
            hass=mock_hass,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        await select.async_update()

        assert select.current_option == "manual"
        mock_api.async_read_property_for_device.assert_called_once_with(
            device_uuid="test-device-uuid", property_path="29/1/15", byte_count=1
        )

    def test_property_select_option(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test selecting a property option."""
        config = {
            "path": "29/1/15",
            "name": "Ventilation Mode",
            "translation_key": "ventilation_mode",
            "options": {0: "auto", 1: "manual", 2: "boost"},
        }

        select = ComfoClimePropertySelect(
            hass=mock_hass,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        select.select_option("boost")

        # Verify API was called
        mock_api.set_property_for_device.assert_called_once_with(
            "test-device-uuid", "29/1/15", 2, byte_count=1
        )


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_thermalprofile_coordinator, mock_device, mock_api):
    """Test async_setup_entry for select entities."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "tpcoordinator": mock_thermalprofile_coordinator,
                "devices": [mock_device],
                "main_device": mock_device,
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
