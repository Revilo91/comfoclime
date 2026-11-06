"""Tests for ComfoClime sensor entities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.comfoclime.coordinator import ComfoClimeAlarmsCoordinator, ComfoClimeHealthCoordinator
from custom_components.comfoclime.entities.sensor_definitions import ALARM_SENSORS
from custom_components.comfoclime.models import (
    AlarmsResponse,
    DashboardData,
    DeviceConfig,
    DeviceDefinitionData,
    MonitoringHealth,
    MonitoringPing,
)
from custom_components.comfoclime.sensor import (
    ComfoClimeAlarmSensor,
    ComfoClimeDefinitionSensor,
    ComfoClimePropertySensor,
    ComfoClimeSensor,
    ComfoClimeTelemetrySensor,
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

        # Set hass attribute and mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        assert sensor._state == 22.5

    def test_sensor_value_mapping(self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry):
        """Test sensor value mapping for temperatureProfile."""
        mock_coordinator.data = DashboardData(temperature_profile=0)

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

    def _make_sensor(self, mock_hass, mock_coordinator, mock_api, device, mock_config_entry):
        return ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_coordinator,
            api=mock_api,
            sensor_type="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            device=device,
            entry=mock_config_entry,
        )

    def test_connected_device_links_to_main_device(
        self,
        mock_hass,
        mock_coordinator,
        mock_api,
        mock_device,
        mock_connected_device,
        mock_config_entry,
        make_runtime_data,
    ):
        """Separate bus products point at the ComfoClime registry device."""
        mock_config_entry.runtime_data = make_runtime_data(
            main_device=mock_device, main_device_registry_id="registry-id-1"
        )
        mock_hass.config_entries.async_get_entry.return_value = mock_config_entry
        sensor = self._make_sensor(mock_hass, mock_coordinator, mock_api, mock_connected_device, mock_config_entry)
        sensor.hass = mock_hass

        assert sensor.device_info["via_device_id"] == "registry-id-1"

    def test_main_device_has_no_via_device(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry, make_runtime_data
    ):
        """The ComfoClime device is the gateway and must not link to itself."""
        mock_config_entry.runtime_data = make_runtime_data(
            main_device=mock_device, main_device_registry_id="registry-id-1"
        )
        mock_hass.config_entries.async_get_entry.return_value = mock_config_entry
        sensor = self._make_sensor(mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry)
        sensor.hass = mock_hass

        assert "via_device_id" not in sensor.device_info

    def test_no_main_device_means_no_via_device(
        self, mock_hass, mock_coordinator, mock_api, mock_connected_device, mock_config_entry, make_runtime_data
    ):
        """Without a registered gateway there is nothing to link to, and nothing crashes."""
        mock_config_entry.runtime_data = make_runtime_data(main_device=None, main_device_registry_id=None)
        mock_hass.config_entries.async_get_entry.return_value = mock_config_entry
        sensor = self._make_sensor(mock_hass, mock_coordinator, mock_api, mock_connected_device, mock_config_entry)
        sensor.hass = mock_hass

        assert "via_device_id" not in sensor.device_info

    def test_device_info_without_hass_is_safe(
        self, mock_hass, mock_coordinator, mock_api, mock_connected_device, mock_config_entry
    ):
        """device_info before the entity is attached to hass has no via link."""
        sensor = self._make_sensor(mock_hass, mock_coordinator, mock_api, mock_connected_device, mock_config_entry)
        sensor.hass = None

        assert "via_device_id" not in sensor.device_info

    def test_monitoring_sensor_update(self, mock_hass, mock_config_entry):
        """Test monitoring sensor state update from MonitoringPing coordinator.

        The uptime device class needs the point in time of the last restart, so
        the raw second count from the device is converted to an aware datetime.
        """
        # Create a mock monitoring coordinator with MonitoringPing data
        device_now = datetime.now(UTC).replace(microsecond=0)
        mock_monitoring_coordinator = MagicMock()
        mock_monitoring_coordinator.data = MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp=int(device_now.timestamp()),
        )
        mock_monitoring_coordinator.last_update_success_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=mock_monitoring_coordinator,
            api=MagicMock(),
            sensor_type="up_time_seconds",
            name="Uptime",
            translation_key="uptime",
            unit=None,
            device_class="uptime",
            state_class=None,
            entity_category="diagnostic",
            device=None,
            entry=mock_config_entry,
        )

        # Set hass attribute and patch async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # The raw value stays available as an attribute, the state is the boot time
        assert sensor._raw_value == 123456
        assert sensor.native_value == device_now - timedelta(seconds=123456)
        assert sensor.native_value.tzinfo is not None
        assert sensor.extra_state_attributes["raw_value"] == 123456

    def test_sensor_extra_state_attributes_dashboard(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test extra_state_attributes contains data_source and last_update for dashboard sensor."""
        mock_coordinator.last_update_success_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

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
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()
        sensor._handle_coordinator_update()

        attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "dashboard"
        assert attrs["last_update"] == "2024-01-15T10:30:00+00:00"
        assert "raw_value" in attrs

    def test_sensor_extra_state_attributes_last_update_none(
        self, mock_hass, mock_coordinator, mock_api, mock_device, mock_config_entry
    ):
        """Test extra_state_attributes last_update is None when coordinator has no timestamp."""
        mock_coordinator.last_update_success_time = None

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

        attrs = sensor.extra_state_attributes
        assert attrs["last_update"] is None


class TestComfoClimeTelemetrySensor:
    """Test ComfoClimeTelemetrySensor class."""

    def test_telemetry_sensor_initialization(
        self, mock_hass, mock_telemetry_coordinator, mock_device, mock_config_entry
    ):
        """Test telemetry sensor initialization."""
        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            coordinator=mock_telemetry_coordinator,
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
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        assert sensor._id == "123"
        assert sensor._name == "Test Telemetry"
        assert sensor._faktor == 0.1
        assert sensor._signed is True
        assert sensor._byte_count == 2
        assert sensor._attr_unique_id == "test_entry_id_telemetry_test-device-uuid_123"

    def test_telemetry_sensor_update(self, mock_hass, mock_telemetry_coordinator, mock_device, mock_config_entry):
        """Test telemetry sensor update from coordinator."""
        mock_telemetry_coordinator.get_telemetry_value.return_value = 25.5

        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            coordinator=mock_telemetry_coordinator,
            telemetry_id=123,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        assert sensor._state == 25.5
        mock_telemetry_coordinator.get_telemetry_value.assert_called_once_with("test-device-uuid", "123")

    def test_telemetry_sensor_update_with_override_uuid(
        self, mock_hass, mock_telemetry_coordinator, mock_device, mock_config_entry
    ):
        """Test telemetry sensor update with override UUID."""
        override_uuid = "override-uuid-123"
        mock_telemetry_coordinator.get_telemetry_value.return_value = 30.0

        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            coordinator=mock_telemetry_coordinator,
            telemetry_id=456,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            device=mock_device,
            override_device_uuid=override_uuid,
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Should use override_uuid
        mock_telemetry_coordinator.get_telemetry_value.assert_called_once_with(override_uuid, "456")

    def test_telemetry_sensor_negative_temperature(
        self, mock_hass, mock_telemetry_coordinator, mock_device, mock_config_entry
    ):
        """Test telemetry sensor with negative temperature value."""
        # Simulate a negative temperature value (-5.5°C)
        mock_telemetry_coordinator.get_telemetry_value.return_value = -5.5

        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            coordinator=mock_telemetry_coordinator,
            telemetry_id=4145,  # tpma_temperature
            name="TPMA Temperature",
            translation_key="tpma_temperature",
            unit="°C",
            device_class="temperature",
            faktor=0.1,
            signed=True,  # Important: must be signed for negative values
            byte_count=2,
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Verify sensor is correctly configured for signed values
        assert sensor._signed is True
        assert sensor._faktor == 0.1
        assert sensor._byte_count == 2

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Verify negative temperature is correctly read
        assert sensor._state == -5.5
        mock_telemetry_coordinator.get_telemetry_value.assert_called_once_with("test-device-uuid", "4145")

    def test_telemetry_sensor_extra_state_attributes(
        self, mock_hass, mock_telemetry_coordinator, mock_device, mock_config_entry
    ):
        """Test extra_state_attributes contains data_source and last_update for telemetry sensor."""
        mock_telemetry_coordinator.last_update_success_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        sensor = ComfoClimeTelemetrySensor(
            hass=mock_hass,
            coordinator=mock_telemetry_coordinator,
            telemetry_id=123,
            name="Test Telemetry",
            translation_key="test_telemetry",
            unit="°C",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "telemetry"
        assert attrs["last_update"] == "2024-01-15T10:30:00+00:00"


class TestComfoClimePropertySensor:
    """Test ComfoClimePropertySensor class."""

    def test_property_sensor_initialization(self, mock_hass, mock_property_coordinator, mock_device, mock_config_entry):
        """Test property sensor initialization."""
        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            path="29/1/10",
            name="Test Property",
            translation_key="test_property",
            unit="V",
            faktor=0.01,
            signed=False,
            byte_count=2,
            device_class="voltage",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        assert sensor._path == "29/1/10"
        assert sensor._name == "Test Property"
        assert sensor._faktor == 0.01
        assert sensor._signed is False
        assert sensor._byte_count == 2
        assert sensor._attr_unique_id == "test_entry_id_property_test-device-uuid_29_1_10"

    def test_property_sensor_update(self, mock_hass, mock_property_coordinator, mock_device, mock_config_entry):
        """Test property sensor update from coordinator."""
        mock_property_coordinator.get_property_value.return_value = 230

        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            path="29/1/10",
            name="Test Property",
            translation_key="test_property",
            unit="V",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        assert sensor._state == 230
        mock_property_coordinator.get_property_value.assert_called_once_with("test-device-uuid", "29/1/10")

    def test_property_sensor_update_with_mapping(
        self, mock_hass, mock_property_coordinator, mock_device, mock_config_entry
    ):
        """Test property sensor update with value mapping."""
        mock_property_coordinator.get_property_value.return_value = 0

        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            path="test/path",
            name="Temperature Profile",
            translation_key="temperature_profile",
            mapping_key="temperatureProfile",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Should map 0 to "comfort"
        assert sensor._state == "comfort"

    def test_property_sensor_extra_state_attributes(
        self, mock_hass, mock_property_coordinator, mock_device, mock_config_entry
    ):
        """Test extra_state_attributes contains data_source and last_update for property sensor."""
        mock_property_coordinator.last_update_success_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        sensor = ComfoClimePropertySensor(
            hass=mock_hass,
            coordinator=mock_property_coordinator,
            path="29/1/10",
            name="Test Property",
            translation_key="test_property",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "property"
        assert attrs["last_update"] == "2024-01-15T10:30:00+00:00"


@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_hass,
    mock_config_entry,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_telemetry_coordinator,
    mock_property_coordinator,
    mock_definition_coordinator,
    mock_device,
    mock_api,
    make_runtime_data,
):
    """Test async_setup_entry for sensors."""
    # Setup mock data
    mock_api.uuid = "test-device-uuid"

    # Create a mock monitoring coordinator
    mock_monitoring_coordinator = MagicMock()
    mock_monitoring_coordinator.data = MonitoringPing(
        uuid="test-uuid",
        up_time_seconds=123456,
        timestamp=1705314600,
    )

    mock_config_entry.runtime_data = make_runtime_data(
        api=mock_api,
        coordinator=mock_coordinator,
        tpcoordinator=mock_thermalprofile_coordinator,
        monitoringcoordinator=mock_monitoring_coordinator,
        tlcoordinator=mock_telemetry_coordinator,
        propcoordinator=mock_property_coordinator,
        definitioncoordinator=mock_definition_coordinator,
        devices=[mock_device],
        main_device=mock_device,
    )

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Verify entities were added
    assert async_add_entities.called


@pytest.mark.asyncio
async def test_async_setup_entry_skips_diagnostic_telemetry_when_disabled(
    mock_hass,
    mock_config_entry,
    mock_coordinator,
    mock_thermalprofile_coordinator,
    mock_telemetry_coordinator,
    mock_property_coordinator,
    mock_definition_coordinator,
    mock_device,
    mock_api,
    make_runtime_data,
):
    """Diagnostic telemetry sensors must not be registered when diagnostics are disabled."""
    mock_api.uuid = "test-device-uuid"

    # Keep default behavior (diagnostics disabled unless explicitly enabled)
    mock_config_entry.options = {}

    mock_monitoring_coordinator = MagicMock()
    mock_monitoring_coordinator.data = MonitoringPing(
        uuid="test-uuid",
        up_time_seconds=123456,
        timestamp=1705314600,
    )

    mock_config_entry.runtime_data = make_runtime_data(
        api=mock_api,
        coordinator=mock_coordinator,
        tpcoordinator=mock_thermalprofile_coordinator,
        monitoringcoordinator=mock_monitoring_coordinator,
        tlcoordinator=mock_telemetry_coordinator,
        propcoordinator=mock_property_coordinator,
        definitioncoordinator=mock_definition_coordinator,
        devices=[mock_device],
        main_device=mock_device,
    )

    async_add_entities = MagicMock()
    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    registered_ids = {
        call.kwargs["telemetry_id"]
        for call in mock_telemetry_coordinator.register_telemetry.await_args_list
        if "telemetry_id" in call.kwargs
    }
    diagnostic_ids = {"4195", "4196", "4197", "4202", "4203", "4204", "4205", "4206", "4207", "4208"}

    assert registered_ids.isdisjoint(diagnostic_ids)


class TestComfoClimeDefinitionSensor:
    """Test ComfoClimeDefinitionSensor class."""

    def test_definition_sensor_initialization(
        self, mock_hass, mock_definition_coordinator, mock_device, mock_config_entry
    ):
        """Test definition sensor initialization."""
        sensor = ComfoClimeDefinitionSensor(
            hass=mock_hass,
            coordinator=mock_definition_coordinator,
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class="temperature",
            state_class="measurement",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        assert sensor._key == "indoorTemperature"
        assert sensor._name == "Indoor Temperature"
        assert sensor._attr_native_unit_of_measurement == "°C"
        assert sensor._attr_device_class == "temperature"
        assert sensor._attr_state_class == "measurement"
        assert sensor._attr_unique_id == "test_entry_id_definition_test-device-uuid_indoorTemperature"

    def test_definition_sensor_update(self, mock_hass, mock_definition_coordinator, mock_device, mock_config_entry):
        """Test definition sensor update from coordinator."""
        sensor = ComfoClimeDefinitionSensor(
            hass=mock_hass,
            coordinator=mock_definition_coordinator,
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device_class="temperature",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        assert sensor._state == 21.4
        mock_definition_coordinator.get_definition_data.assert_called_once_with("test-device-uuid")

    def test_definition_sensor_update_missing_key(
        self, mock_hass, mock_definition_coordinator, mock_device, mock_config_entry
    ):
        """Test definition sensor update with missing key in definition data."""
        # Create a mock that returns definition data without the requested key
        mock_definition_coordinator.get_definition_data.return_value = DeviceDefinitionData(
            outdoorTemperature=1.1,
        )

        sensor = ComfoClimeDefinitionSensor(
            hass=mock_hass,
            coordinator=mock_definition_coordinator,
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Should be None since key doesn't exist in definition data
        assert sensor._state is None

    def test_definition_sensor_update_no_data(
        self, mock_hass, mock_definition_coordinator, mock_device, mock_config_entry
    ):
        """Test definition sensor update when coordinator has no data."""
        # Mock coordinator returns None for definition data
        mock_definition_coordinator.get_definition_data.return_value = None

        sensor = ComfoClimeDefinitionSensor(
            hass=mock_hass,
            coordinator=mock_definition_coordinator,
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            unit="°C",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        # Mock async_write_ha_state
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()

        # Trigger coordinator update
        sensor._handle_coordinator_update()

        # Should be None when coordinator has no definition data
        assert sensor._state is None

    def test_definition_sensor_extra_state_attributes(
        self, mock_hass, mock_definition_coordinator, mock_device, mock_config_entry
    ):
        """Test extra_state_attributes contains data_source and last_update for definition sensor."""
        mock_definition_coordinator.last_update_success_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        sensor = ComfoClimeDefinitionSensor(
            hass=mock_hass,
            coordinator=mock_definition_coordinator,
            key="indoorTemperature",
            name="Indoor Temperature",
            translation_key="indoor_temperature",
            device=mock_device,
            override_device_uuid="test-device-uuid",
            entry=mock_config_entry,
        )

        attrs = sensor.extra_state_attributes
        assert attrs["data_source"] == "definition"
        assert attrs["last_update"] == "2024-01-15T10:30:00+00:00"


def _health_coordinator(data=None):
    coordinator = MagicMock(spec=ComfoClimeHealthCoordinator)
    coordinator.data = data
    coordinator.last_update_success_time = None
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _alarms_coordinator(data=None):
    coordinator = MagicMock(spec=ComfoClimeAlarmsCoordinator)
    coordinator.data = data
    coordinator.last_update_success_time = None
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def _alarm_payload(errors_by_uuid):
    return AlarmsResponse.from_api(
        {"devices": [{"uuid": uuid, "modelTypeId": 1, "errors": errors} for uuid, errors in errors_by_uuid.items()]}
    )


class TestHealthSensor:
    """ComfoClimeSensor backed by the lazy health coordinator."""

    def _sensor(self, mock_hass, mock_config_entry, coordinator, key="total_free_bytes"):
        sensor = ComfoClimeSensor(
            hass=mock_hass,
            coordinator=coordinator,
            api=MagicMock(),
            sensor_type=key,
            name=key,
            translation_key=key,
            unit="B",
            device_class="data_size",
            state_class="measurement",
            entity_category="diagnostic",
            device=None,
            entry=mock_config_entry,
            entity_registry_enabled_default=False,
        )
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()
        return sensor

    def test_unique_id_and_data_source(self, mock_hass, mock_config_entry):
        sensor = self._sensor(mock_hass, mock_config_entry, _health_coordinator())

        assert sensor._data_source == "health"
        assert sensor._attr_unique_id == "test_entry_id_health_total_free_bytes"

    def test_reads_value_from_health_model(self, mock_hass, mock_config_entry):
        coordinator = _health_coordinator(MonitoringHealth(total_free_bytes=96612, twai_arb_lost_count=4437))
        memory = self._sensor(mock_hass, mock_config_entry, coordinator)
        arbitration = self._sensor(mock_hass, mock_config_entry, coordinator, key="twai_arb_lost_count")

        memory._handle_coordinator_update()
        arbitration._handle_coordinator_update()

        assert memory.native_value == 96612
        assert arbitration.native_value == 4437

    @pytest.mark.asyncio
    async def test_first_refresh_is_requested_when_coordinator_has_no_data(self, mock_hass, mock_config_entry):
        """The lazy coordinator is never refreshed at setup, so the first enabled entity must."""
        coordinator = _health_coordinator(data=None)
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator)

        await sensor._async_register_data_source()

        coordinator.async_request_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_extra_refresh_when_coordinator_already_has_data(self, mock_hass, mock_config_entry):
        coordinator = _health_coordinator(MonitoringHealth(total_free_bytes=1))
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator)

        await sensor._async_register_data_source()

        coordinator.async_request_refresh.assert_not_awaited()


class TestComfoClimeAlarmSensor:
    """One alarm counter per bus device, attached to that device."""

    @staticmethod
    def _device(uuid="SIT00000000", model_type_id=1):
        return DeviceConfig(uuid=uuid, display_name="ComfoAir Q", model_type_id=model_type_id)

    def _sensor(self, mock_hass, mock_config_entry, coordinator, device=None):
        sensor = ComfoClimeAlarmSensor(
            hass=mock_hass,
            coordinator=coordinator,
            device=device or self._device(),
            entry=mock_config_entry,
            definition=ALARM_SENSORS[0],
        )
        sensor.hass = mock_hass
        sensor.async_write_ha_state = MagicMock()
        return sensor

    def test_unique_id_contains_device_uuid(self, mock_hass, mock_config_entry):
        sensor = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator())

        assert sensor._attr_unique_id == "test_entry_id_alarms_SIT00000000"

    def test_two_devices_get_distinct_unique_ids(self, mock_hass, mock_config_entry):
        first = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator(), self._device("SIT00000000"))
        second = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator(), self._device("SIT00000001"))

        assert first._attr_unique_id != second._attr_unique_id

    def test_is_diagnostic_and_disabled_by_default(self, mock_hass, mock_config_entry):
        sensor = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator())

        assert sensor.entity_category == "diagnostic"
        assert sensor.entity_registry_enabled_default is False

    def test_counts_active_alarms_of_its_own_device(self, mock_hass, mock_config_entry):
        errors = [0] * 32
        errors[12] = 16
        coordinator = _alarms_coordinator(_alarm_payload({"SIT00000000": errors, "MBE00000000": [0] * 32}))
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator)

        sensor._handle_coordinator_update()

        assert sensor.native_value == 1
        assert sensor.extra_state_attributes["active_errors"] == {"12": 16}

    def test_other_devices_alarms_are_not_counted(self, mock_hass, mock_config_entry):
        errors = [0] * 32
        errors[12] = 16
        coordinator = _alarms_coordinator(_alarm_payload({"SIT00000000": errors, "MBE00000000": [0] * 32}))
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator, self._device("MBE00000000", 20))

        sensor._handle_coordinator_update()

        assert sensor.native_value == 0
        assert sensor.extra_state_attributes["active_errors"] == {}

    def test_state_is_none_when_device_missing_in_response(self, mock_hass, mock_config_entry):
        coordinator = _alarms_coordinator(_alarm_payload({"MBE00000000": [0] * 32}))
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator)

        sensor._handle_coordinator_update()

        assert sensor.native_value is None

    def test_state_is_none_before_first_refresh(self, mock_hass, mock_config_entry):
        sensor = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator(data=None))

        sensor._handle_coordinator_update()

        assert sensor.native_value is None

    def test_attached_to_its_own_device(self, mock_hass, mock_config_entry):
        sensor = self._sensor(mock_hass, mock_config_entry, _alarms_coordinator())

        assert ("comfoclime", "SIT00000000") in sensor.device_info["identifiers"]

    @pytest.mark.asyncio
    async def test_first_refresh_is_requested_when_coordinator_has_no_data(self, mock_hass, mock_config_entry):
        coordinator = _alarms_coordinator(data=None)
        sensor = self._sensor(mock_hass, mock_config_entry, coordinator)

        await sensor._async_register_data_source()

        coordinator.async_request_refresh.assert_awaited_once()


class TestHealthAndAlarmSetup:
    """async_setup_entry only creates the opt-in sensors when their coordinators exist."""

    @staticmethod
    def _run(mock_config_entry, make_runtime_data, mock_api, fixtures, **overrides):
        mock_api.uuid = "test-device-uuid"
        mock_config_entry.runtime_data = make_runtime_data(api=mock_api, **fixtures, **overrides)
        async_add_entities = MagicMock()
        return async_add_entities

    @pytest.fixture
    def fixtures(
        self,
        mock_coordinator,
        mock_thermalprofile_coordinator,
        mock_telemetry_coordinator,
        mock_property_coordinator,
        mock_definition_coordinator,
        mock_device,
    ):
        return {
            "coordinator": mock_coordinator,
            "tpcoordinator": mock_thermalprofile_coordinator,
            "tlcoordinator": mock_telemetry_coordinator,
            "propcoordinator": mock_property_coordinator,
            "definitioncoordinator": mock_definition_coordinator,
            "devices": [
                mock_device,
                DeviceConfig(uuid="SIT00000000", display_name="ComfoAir Q", model_type_id=1),
                DeviceConfig(uuid="NULL", display_name="Broken", model_type_id=1),
            ],
            "main_device": mock_device,
        }

    @pytest.mark.asyncio
    async def test_creates_health_and_one_alarm_sensor_per_valid_bus_device(
        self, mock_hass, mock_config_entry, mock_api, make_runtime_data, fixtures
    ):
        add = self._run(
            mock_config_entry,
            make_runtime_data,
            mock_api,
            fixtures,
            healthcoordinator=_health_coordinator(),
            alarmscoordinator=_alarms_coordinator(),
        )

        await async_setup_entry(mock_hass, mock_config_entry, add)

        entities = add.call_args.args[0]
        alarm_ids = sorted(e._attr_unique_id for e in entities if isinstance(e, ComfoClimeAlarmSensor))
        health_ids = [e._attr_unique_id for e in entities if getattr(e, "_data_source", "") == "health"]
        assert alarm_ids == [
            "test_entry_id_alarms_SIT00000000",
            "test_entry_id_alarms_test-device-uuid",
        ]
        assert len(health_ids) == 6
        assert all(
            not e.entity_registry_enabled_default
            for e in entities
            if isinstance(e, ComfoClimeAlarmSensor) or getattr(e, "_data_source", "") == "health"
        )

    @pytest.mark.asyncio
    async def test_creates_neither_without_coordinators(
        self, mock_hass, mock_config_entry, mock_api, make_runtime_data, fixtures
    ):
        add = self._run(mock_config_entry, make_runtime_data, mock_api, fixtures)

        await async_setup_entry(mock_hass, mock_config_entry, add)

        entities = add.call_args.args[0]
        assert not any(isinstance(e, ComfoClimeAlarmSensor) for e in entities)
        assert not any(getattr(e, "_data_source", "") == "health" for e in entities)
