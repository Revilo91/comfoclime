"""Tests for ComfoClime number entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.comfoclime.entities.number_definitions import (
    NumberDefinition,
    PropertyNumberDefinition,
)
from custom_components.comfoclime.number import (
    ComfoClimePropertyNumber,
    ComfoClimeTemperatureNumber,
    async_setup_entry,
)


class TestComfoClimeTemperatureNumber:
    """Test ComfoClimeTemperatureNumber class."""

    def test_temperature_number_initialization(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test temperature number entity initialization."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert number._key_path == ["temperature", "manualTemperature"]
        assert number._name == "Manual Temperature"
        assert number.native_min_value == 10.0
        assert number.native_max_value == 30.0
        assert number.native_step == 0.5
        assert number._attr_unique_id == "test_entry_id_temperature.manualTemperature"

    def test_temperature_number_value_update(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test temperature number value update from coordinator."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        mock_thermalprofile_coordinator.data = {"temperature": {"manualTemperature": 22.5}}

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute for async_write_ha_state to work
        number.hass = mock_hass
        number.async_write_ha_state = MagicMock()

        number._handle_coordinator_update()

        assert number.native_value == 22.5

    @pytest.mark.asyncio
    async def test_temperature_number_set_value(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test setting temperature number value."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        # Set manual mode (status = 0)
        mock_thermalprofile_coordinator.data = {"temperature": {"status": 0, "manualTemperature": 22.0}}

        mock_hass.add_job = MagicMock()

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        await number.async_set_native_value(23.5)

        # Verify API was called
        mock_api.async_update_thermal_profile.assert_called_once_with(manual_temperature=23.5)

    def test_temperature_number_availability_when_automatic(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test temperature number availability when automatic mode is enabled."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        # Set automatic mode (status = 1)
        mock_thermalprofile_coordinator.data = {"temperature": {"status": 1, "manualTemperature": 22.0}}

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Should not be available when automatic mode is enabled
        assert number.available is False

    def test_temperature_number_availability_when_manual(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test temperature number availability when manual mode is enabled."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        # Set manual mode (status = 0)
        mock_thermalprofile_coordinator.data = {"temperature": {"status": 0, "manualTemperature": 22.0}}

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Should be available when manual mode is enabled
        assert number.available is True

    def test_temperature_number_device_info(
        self,
        mock_hass,
        mock_thermalprofile_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test temperature number device info."""
        config = NumberDefinition(
            key="temperature.manualTemperature",
            name="Manual Temperature",
            translation_key="manual_temperature",
            min=10.0,
            max=30.0,
            step=0.5,
        )

        number = ComfoClimeTemperatureNumber(
            hass=mock_hass,
            coordinator=mock_thermalprofile_coordinator,
            api=mock_api,
            conf=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = number.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]


class TestComfoClimePropertyNumber:
    """Test ComfoClimePropertyNumber class."""

    def test_property_number_initialization(
        self,
        mock_hass,
        mock_property_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test property number entity initialization."""
        config = PropertyNumberDefinition(
            property="29/1/20",
            name="Fan Speed Setpoint",
            translation_key="fan_speed_setpoint",
            min=0,
            max=100,
            step=5,
            unit="%",
            faktor=1.0,
            byte_count=1,
        )

        number = ComfoClimePropertyNumber(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            api=mock_api,
            config=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        assert number._property_path == "29/1/20"
        assert number._attr_native_min_value == 0
        assert number._attr_native_max_value == 100
        assert number._attr_native_step == 5
        assert number._attr_native_unit_of_measurement == "%"
        assert number._attr_unique_id == "test_entry_id_property_number_29_1_20"

    def test_property_number_update(
        self,
        mock_hass,
        mock_property_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test property number update from coordinator."""
        config = PropertyNumberDefinition(
            property="29/1/20",
            name="Fan Speed Setpoint",
            translation_key="fan_speed_setpoint",
            min=0,
            max=100,
            step=5,
            unit="%",
            faktor=1.0,
            byte_count=1,
        )

        mock_property_coordinator.get_property_value.return_value = 75

        number = ComfoClimePropertyNumber(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            api=mock_api,
            config=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        number.hass = mock_hass
        number.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        number._handle_coordinator_update()

        assert number.native_value == 75
        mock_property_coordinator.get_property_value.assert_called_once_with("test-device-uuid", "29/1/20")

    @pytest.mark.asyncio
    async def test_property_number_async_set_value(
        self,
        mock_hass,
        mock_property_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test property number async set value."""
        config = PropertyNumberDefinition(
            property="29/1/20",
            name="Fan Speed Setpoint",
            translation_key="fan_speed_setpoint",
            min=0,
            max=100,
            step=5,
            unit="%",
            faktor=1.0,
            byte_count=1,
        )

        number = ComfoClimePropertyNumber(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            api=mock_api,
            config=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        await number.async_set_native_value(80)

        # The actual implementation doesn't pass signed parameter
        mock_api.async_set_property_for_device.assert_called_once_with(
            device_uuid="test-device-uuid",
            property_path="29/1/20",
            value=80,
            byte_count=1,
            faktor=1.0,
        )

    def test_property_number_device_info(
        self,
        mock_hass,
        mock_property_coordinator,
        mock_api,
        mock_device,
        mock_config_entry,
    ):
        """Test property number device info."""
        config = PropertyNumberDefinition(
            property="29/1/20",
            name="Fan Speed Setpoint",
            translation_key="fan_speed_setpoint",
            min=0,
            max=100,
            step=5,
            unit="%",
        )

        number = ComfoClimePropertyNumber(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            api=mock_api,
            config=config,
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = number.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]


@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_hass,
    mock_config_entry,
    mock_thermalprofile_coordinator,
    mock_property_coordinator,
    mock_device,
    mock_api,
):
    """Test async_setup_entry for number entities."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "tpcoordinator": mock_thermalprofile_coordinator,
                "propcoordinator": mock_property_coordinator,
                "devices": [mock_device],
                "main_device": mock_device,
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
