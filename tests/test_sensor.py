"""Tests for ComfoClime sensor entities."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.comfoclime.sensor import (
    ComfoClimeSensor,
    ComfoClimeTelemetrySensor,
    ComfoClimePropertySensor,
    async_setup_entry,
)


class TestComfoClimeSensor:
    """Test ComfoClimeSensor class."""

    def test_sensor_initialization(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test sensor initialization."""
        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            sensor_type="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class="temperature",
            state_class="measurement",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert sensor._type == "indoorTemperature"
        assert sensor._name == "Indoor Temperature"
        assert sensor._attr_native_unit_of_measurement == "°C"
        assert sensor._attr_device_class == "temperature"
        assert sensor._attr_state_class == "measurement"
        assert sensor._attr_unique_id == "test_entry_id_dashboard_indoorTemperature"

    def test_sensor_state_update(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test sensor state update from coordinator."""
        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            sensor_type="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class="temperature",
            device=mock_device,
            entry=mock_config_entry,
        )
        
        # Set hass attribute and patch async_write_ha_state for async_write_ha_state to work
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        assert sensor._state == 22.5

    def test_sensor_value_mapping(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test sensor value mapping for temperatureProfile."""
        mock_coordinator.data = {"temperatureProfile": 0}
        
        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            sensor_type="temperatureProfile",
            name="Temperature Profile",
            translation_key="temperature_profile",
            device=mock_device,
            entry=mock_config_entry,
        )

        # Set hass attribute and patch async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        sensor._handle_coordinator_update()

        # Should map 0 to "comfort"
        assert sensor._state == "comfort"

    def test_sensor_device_info(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test sensor device info."""
        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            sensor_type="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            device=mock_device,
            entry=mock_config_entry,
        )

        device_info = sensor.device_info

        assert device_info is not None
        assert ("comfoclime", "test-device-uuid") in device_info["identifiers"]
        assert device_info["name"] == "ComfoClime Test"
        assert device_info["manufacturer"] == "Zehnder"


class TestComfoClimeTelemetrySensor:
    """Test ComfoClimeTelemetrySensor class."""

    def test_telemetry_sensor_initialization(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test telemetry sensor initialization."""
        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            api=mock_api,
            telemetry_id=123,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            faktor=0.1,
            signed=True,
            byte_count=2,
            device_class="temperature",
            state_class="measurement",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert sensor._id == 123
        assert sensor._name == "Test Telemetry"
        assert sensor._faktor == 0.1
        assert sensor._signed is True
        assert sensor._byte_count == 2
        assert sensor._attr_unique_id == "test_entry_id_telemetry_123"

    @pytest.mark.asyncio
    async def test_telemetry_sensor_update(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test telemetry sensor async update."""
        mock_api.async_read_telemetry_for_device.return_value = 25.5

        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            api=mock_api,
            telemetry_id=123,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            device=mock_device,
            entry=mock_config_entry,
        )

        await sensor.async_update()

        assert sensor._state == 25.5
        mock_api.async_read_telemetry_for_device.assert_called_once()

    @pytest.mark.asyncio
    async def test_telemetry_sensor_update_with_override_uuid(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test telemetry sensor update with override UUID."""
        override_uuid = "override-uuid-123"
        
        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            api=mock_api,
            telemetry_id=456,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            device=mock_device,
            override_device_uuid=override_uuid,
            entry=mock_config_entry,
        )

        await sensor.async_update()

        # Should use override_uuid instead of api.uuid
        call_args = mock_api.async_read_telemetry_for_device.call_args
        assert call_args[0][1] == override_uuid


class TestComfoClimePropertySensor:
    """Test ComfoClimePropertySensor class."""

    def test_property_sensor_initialization(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test property sensor initialization."""
        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            api=mock_api,
            path="29/1/10",
            name="Test Property",
            translation_key="test_property",
            unit="V",
            faktor=0.01,
            signed=False,
            byte_count=2,
            device_class="voltage",
            device=mock_device,
            entry=mock_config_entry,
        )

        assert sensor._path == "29/1/10"
        assert sensor._name == "Test Property"
        assert sensor._faktor == 0.01
        assert sensor._signed is False
        assert sensor._byte_count == 2
        assert sensor._attr_unique_id == "test_entry_id_property_29_1_10"

    @pytest.mark.asyncio
    async def test_property_sensor_update(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test property sensor async update."""
        mock_api.async_read_property_for_device.return_value = 230

        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            api=mock_api,
            path="29/1/10",
            name="Test Property",
            translation_key="test_property",
            unit="V",
            device=mock_device,
            entry=mock_config_entry,
        )

        await sensor.async_update()

        assert sensor._state == 230
        mock_api.async_read_property_for_device.assert_called_once()

    @pytest.mark.asyncio
    async def test_property_sensor_update_with_mapping(self, mock_hass, mock_api, mock_device, mock_config_entry):
        """Test property sensor update with value mapping."""
        mock_api.async_read_property_for_device.return_value = 0

        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            api=mock_api,
            path="test/path",
            name="Temperature Profile",
            translation_key="temperature_profile",
            mapping_key="temperatureProfile",
            device=mock_device,
            entry=mock_config_entry,
        )

        await sensor.async_update()

        # Should map 0 to "comfort"
        assert sensor._state == "comfort"


@pytest.mark.asyncio
async def test_async_setup_entry(mock_hass, mock_config_entry, mock_api, mock_coordinator, mock_thermalprofile_coordinator, mock_device):
    """Test async_setup_entry for sensors."""
    # Setup mock data
    mock_hass.data = {
        "comfoclime": {
            "test_entry_id": {
                "api": mock_api,
                "coordinator": mock_coordinator,
                "devices": [mock_device],
                "main_device": mock_device,
            }
        }
    }

    # Make sure async_get_uuid is properly mocked
    mock_api.async_get_uuid = AsyncMock(return_value="test-uuid-12345")

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called
