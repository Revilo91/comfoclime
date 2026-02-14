"""Tests for data models in models.py"""

import pytest
from pydantic import ValidationError

from custom_components.comfoclime.models import (
    DashboardData,
    DashboardUpdateResponse,
    DeviceConfig,
    ConnectedDevicesResponse,
    MonitoringPing,
    PropertyReadResult,
    PropertyReading,
    PropertyRegistry,
    PropertyRegistryEntry,
    PropertyWriteRequest,
    PropertyWriteResponse,
    SeasonData,
    TelemetryReading,
    TelemetryRegistry,
    TelemetryRegistryEntry,
    TemperatureControlData,
    ThermalProfileData,
    ThermalProfileSeasonData,
    ThermalProfileUpdateResponse,
    bytes_to_signed_int,
    fix_signed_temperature,
    fix_signed_temperatures_in_dict,
    signed_int_to_bytes,
)


class TestDeviceConfig:
    """Tests for DeviceConfig dataclass."""

    def test_create_device_config(self):
        """Test creating a valid DeviceConfig."""
        config = DeviceConfig(
            uuid="abc123",
            model_type_id=1,
            display_name="Heat Pump",
            version="1.0.0",
        )

        assert config.uuid == "abc123"
        assert config.model_type_id == 1
        assert config.display_name == "Heat Pump"
        assert config.version == "1.0.0"

    def test_device_config_default_values(self):
        """Test DeviceConfig with default values."""
        config = DeviceConfig(uuid="abc123", model_type_id=1)

        assert config.display_name == "Unknown Device"
        assert config.version is None

    def test_device_config_empty_uuid(self):
        """Test that empty uuid raises ValidationError."""
        with pytest.raises(ValidationError):
            DeviceConfig(uuid="", model_type_id=1)

    def test_device_config_negative_model_type_id(self):
        """Test that negative model_type_id raises ValidationError."""
        with pytest.raises(ValidationError):
            DeviceConfig(uuid="abc123", model_type_id=-1)

    def test_device_config_immutable(self):
        """Test that DeviceConfig is immutable (frozen)."""
        config = DeviceConfig(uuid="abc123", model_type_id=1)

        with pytest.raises(ValidationError):
            config.uuid = "new_uuid"


class TestConnectedDevicesResponse:
    """Tests for ConnectedDevicesResponse parsing helpers."""

    def test_from_api_parses_devices(self):
        """Test parsing devices from API payload."""
        payload = {
            "devices": [
                {"uuid": "device-1", "modelTypeId": 1, "displayName": "Device 1"},
                {"uuid": "device-2", "modelTypeId": 20, "displayName": "Device 2", "version": "1.0"},
                {"uuid": "", "modelTypeId": "invalid"},
            ]
        }

        response = ConnectedDevicesResponse.from_api(payload)

        assert len(response.devices) == 2
        assert response.devices[0].uuid == "device-1"
        assert response.devices[1].version == "1.0"


class TestTelemetryReading:
    """Tests for TelemetryReading dataclass."""

    def test_create_telemetry_reading(self):
        """Test creating a valid TelemetryReading."""
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="10",
            raw_value=250,
            faktor=0.1,
            signed=False,
            byte_count=2,
        )

        assert reading.device_uuid == "abc123"
        assert reading.telemetry_id == "10"
        assert reading.raw_value == 250
        assert reading.faktor == 0.1
        assert reading.signed is False
        assert reading.byte_count == 2

    def test_telemetry_reading_scaled_value(self):
        """Test scaled_value calculation."""
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="10",
            raw_value=250,
            faktor=0.1,
        )

        assert reading.scaled_value == 25.0

    def test_telemetry_reading_signed_value(self):
        """Test signed value interpretation."""
        # Test 2-byte signed value
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="10",
            raw_value=65535,  # -1 in signed 16-bit
            faktor=1.0,
            signed=True,
            byte_count=2,
        )

        assert reading.scaled_value == -1.0

        # Test 1-byte signed value
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="10",
            raw_value=255,  # -1 in signed 8-bit
            faktor=1.0,
            signed=True,
            byte_count=1,
        )

        assert reading.scaled_value == -1.0

    def test_telemetry_reading_signed_negative_temperature(self):
        """Test signed negative temperature value (like tpma_temperature)."""
        # Test realistic negative temperature scenario
        # Raw value 65481 represents -5.5°C when interpreted as signed 16-bit with faktor 0.1
        # 65481 in signed 16-bit = -55, scaled by 0.1 = -5.5
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="4145",  # tpma_temperature
            raw_value=65481,  # -55 in signed 16-bit
            faktor=0.1,
            signed=True,
            byte_count=2,
        )

        assert reading.scaled_value == -5.5

        # Test another negative temperature: -10.0°C
        # Raw value 65436 = -100 in signed 16-bit, scaled by 0.1 = -10.0
        reading = TelemetryReading(
            device_uuid="abc123",
            telemetry_id="4145",
            raw_value=65436,  # -100 in signed 16-bit
            faktor=0.1,
            signed=True,
            byte_count=2,
        )

        assert reading.scaled_value == -10.0

    def test_telemetry_reading_empty_device_uuid(self):
        """Test that empty device_uuid raises ValidationError."""
        with pytest.raises(ValidationError):
            TelemetryReading(device_uuid="", telemetry_id="10", raw_value=100)

    def test_telemetry_reading_empty_telemetry_id(self):
        """Test that empty telemetry_id raises ValidationError."""
        with pytest.raises(ValidationError):
            TelemetryReading(device_uuid="abc123", telemetry_id="", raw_value=100)

    def test_telemetry_reading_invalid_faktor(self):
        """Test that invalid faktor raises ValidationError."""
        with pytest.raises(ValidationError):
            TelemetryReading(device_uuid="abc123", telemetry_id="10", raw_value=100, faktor=0)

        with pytest.raises(ValidationError):
            TelemetryReading(device_uuid="abc123", telemetry_id="10", raw_value=100, faktor=-1.0)

    def test_telemetry_reading_invalid_byte_count(self):
        """Test that invalid byte_count raises ValidationError."""
        with pytest.raises(ValidationError):
            TelemetryReading(device_uuid="abc123", telemetry_id="10", raw_value=100, byte_count=3)

    def test_telemetry_from_cached_value(self):
        """Test telemetry reconstruction from cached scaled value."""
        reading = TelemetryReading.from_cached_value(
            device_uuid="abc123",
            telemetry_id="10",
            cached_value=25.0,
            faktor=0.1,
            signed=True,
            byte_count=2,
        )

        assert reading is not None
        assert reading.raw_value == 250
        assert reading.scaled_value == 25.0

    def test_telemetry_from_raw_bytes(self):
        """Test telemetry parsing from raw bytes."""
        reading = TelemetryReading.from_raw_bytes(
            device_uuid="abc123",
            telemetry_id="10",
            data=[250, 0],
            faktor=0.1,
            signed=False,
            byte_count=2,
        )

        assert reading is not None
        assert reading.raw_value == 250
        assert reading.scaled_value == 25.0


class TestPropertyReading:
    """Tests for PropertyReading dataclass."""

    def test_create_property_reading(self):
        """Test creating a valid PropertyReading."""
        reading = PropertyReading(
            device_uuid="abc123",
            path="29/1/10",
            raw_value=123,
            faktor=1.0,
            signed=True,
            byte_count=2,
        )

        assert reading.device_uuid == "abc123"
        assert reading.path == "29/1/10"
        assert reading.raw_value == 123
        assert reading.faktor == 1.0
        assert reading.signed is True
        assert reading.byte_count == 2

    def test_property_reading_scaled_value(self):
        """Test scaled_value calculation."""
        reading = PropertyReading(
            device_uuid="abc123",
            path="29/1/10",
            raw_value=100,
            faktor=0.5,
        )

        assert reading.scaled_value == 50.0

    def test_property_reading_empty_path(self):
        """Test that empty path raises ValidationError."""
        with pytest.raises(ValidationError):
            PropertyReading(device_uuid="abc123", path="", raw_value=100)

    def test_property_from_cached_value(self):
        """Test property reconstruction from cached value."""
        reading = PropertyReading.from_cached_value(
            device_uuid="abc123",
            path="29/1/10",
            cached_value=50.0,
            faktor=0.5,
            signed=True,
            byte_count=2,
        )

        assert reading is not None
        assert reading.raw_value == 100
        assert reading.scaled_value == 50.0


class TestPropertyReadResult:
    """Tests for PropertyReadResult parsing."""

    def test_property_read_result_numeric(self):
        """Test numeric property parsing from raw bytes."""
        result = PropertyReadResult.from_raw_bytes(
            device_uuid="abc123",
            path="29/1/10",
            data=[100],
            faktor=1.0,
            signed=False,
            byte_count=1,
        )

        assert result.reading is not None
        assert result.cache_value == 100.0

    def test_property_read_result_string(self):
        """Test string property parsing from raw bytes."""
        result = PropertyReadResult.from_raw_bytes(
            device_uuid="abc123",
            path="29/1/10",
            data=[65, 0, 66],
            faktor=1.0,
            signed=False,
            byte_count=3,
        )

        assert result.reading is None
        assert result.cache_value == "AB"


class TestPropertyWriteRequest:
    """Tests for PropertyWriteRequest conversion helpers."""

    def test_property_write_request_to_wire_data(self):
        """Test conversion to wire data."""
        request = PropertyWriteRequest(
            device_uuid="abc123",
            path="29/1/10",
            value=22.5,
            byte_count=2,
            signed=True,
            faktor=0.1,
        )

        x, y, z, data = request.to_wire_data()

        assert (x, y, z) == (29, 1, 10)
        assert data == [225, 0]


class TestDashboardData:
    """Tests for DashboardData Pydantic model."""

    def test_create_dashboard_data(self):
        """Test creating a valid DashboardData with expanded fields."""
        data = DashboardData(
            indoor_temperature=22.5,
            outdoor_temperature=10.0,
            set_point_temperature=21.0,
            fan_speed=2,
            season=1,
            hp_standby=False,
        )

        assert data.indoor_temperature == 22.5
        assert data.outdoor_temperature == 10.0
        assert data.set_point_temperature == 21.0
        assert data.fan_speed == 2
        assert data.season == 1
        assert data.hp_standby is False

    def test_dashboard_data_default_values(self):
        """Test DashboardData with default values."""
        data = DashboardData()

        assert data.indoor_temperature is None
        assert data.outdoor_temperature is None
        assert data.set_point_temperature is None
        assert data.fan_speed is None
        assert data.season is None
        assert data.hp_standby is None

    def test_dashboard_data_field_aliases(self):
        """Test that field aliases work with camelCase API responses."""
        # Create with camelCase (API format)
        data = DashboardData(
            indoorTemperature=22.5,
            outdoorTemperature=10.0,
            setPointTemperature=21.0,
        )

        # Access with snake_case (Python format)
        assert data.indoor_temperature == 22.5
        assert data.outdoor_temperature == 10.0
        assert data.set_point_temperature == 21.0

    def test_dashboard_data_helper_properties(self):
        """Test helper properties for mode detection."""
        data_heating = DashboardData(season=1)
        assert data_heating.is_heating_mode is True
        assert data_heating.is_cooling_mode is False

        data_cooling = DashboardData(season=2)
        assert data_cooling.is_heating_mode is False
        assert data_cooling.is_cooling_mode is True

        data_manual = DashboardData(status=0)
        assert data_manual.is_manual_mode is True
        assert data_manual.is_auto_mode is False

        data_auto = DashboardData(status=1)
        assert data_auto.is_manual_mode is False
        assert data_auto.is_auto_mode is True

    def test_dashboard_data_invalid_fan_speed(self):
        """Test that invalid fan_speed raises ValidationError."""
        with pytest.raises(ValidationError):
            DashboardData(fan_speed=-1)

        with pytest.raises(ValidationError):
            DashboardData(fan_speed=4)  # Max is 3

    def test_dashboard_data_mutable(self):
        """Test that DashboardData is mutable (not frozen)."""
        data = DashboardData(indoor_temperature=22.5)

        # Should be able to update values
        data.indoor_temperature = 23.0
        assert data.indoor_temperature == 23.0


class TestUtilityFunctions:
    """Tests for utility functions moved to models.py."""

    def test_bytes_to_signed_int(self):
        """Test bytes_to_signed_int function."""
        # Test unsigned 2-byte value
        assert bytes_to_signed_int([0, 1], 2, signed=False) == 256

        # Test signed 2-byte negative value
        assert bytes_to_signed_int([255, 255], 2, signed=True) == -1

        # Test signed 1-byte negative value
        assert bytes_to_signed_int([255], 1, signed=True) == -1

    def test_signed_int_to_bytes(self):
        """Test signed_int_to_bytes function."""
        # Test signed negative value
        assert signed_int_to_bytes(-1, 2, signed=True) == [255, 255]

        # Test unsigned value
        assert signed_int_to_bytes(256, 2, signed=False) == [0, 1]

    def test_fix_signed_temperature(self):
        """Test fix_signed_temperature function."""
        # Test negative temperature
        result = fix_signed_temperature(6552.3)
        assert abs(result - (-1.3)) < 0.01

        # Test positive temperature (should remain unchanged)
        result = fix_signed_temperature(235.0)
        assert abs(result - 235.0) < 0.01

    def test_fix_signed_temperatures_in_dict(self):
        """Test fix_signed_temperatures_in_dict function."""
        data = {
            "indoorTemperature": 6552.3,
            "fanSpeed": 2,
            "outdoorTemperature": 235.0,
        }

        result = fix_signed_temperatures_in_dict(data)

        # Temperature fields should be fixed
        assert abs(result["indoorTemperature"] - (-1.3)) < 0.01
        assert abs(result["outdoorTemperature"] - 235.0) < 0.01

        # Non-temperature fields should be unchanged
        assert result["fanSpeed"] == 2


class TestSeasonData:
    """Tests for SeasonData Pydantic model."""

    def test_create_season_data(self):
        """Test creating a valid SeasonData."""
        data = SeasonData(
            status=1,
            season=1,
            heating_threshold_temperature=14.0,
            cooling_threshold_temperature=17.0,
        )

        assert data.status == 1
        assert data.season == 1
        assert data.heating_threshold_temperature == 14.0
        assert data.cooling_threshold_temperature == 17.0

    def test_season_data_field_aliases(self):
        """Test that field aliases work with camelCase API responses."""
        data = SeasonData(
            status=1,
            season=2,
            heatingThresholdTemperature=12.0,
            coolingThresholdTemperature=18.0,
        )

        assert data.heating_threshold_temperature == 12.0
        assert data.cooling_threshold_temperature == 18.0

    def test_season_data_invalid_status(self):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            SeasonData(status=-1)

        with pytest.raises(ValidationError):
            SeasonData(status=2)  # Max is 1

    def test_season_data_invalid_season(self):
        """Test that invalid season raises ValidationError."""
        with pytest.raises(ValidationError):
            SeasonData(season=-1)

        with pytest.raises(ValidationError):
            SeasonData(season=3)  # Max is 2

    def test_season_data_immutable(self):
        """Test that SeasonData is immutable (frozen)."""
        data = SeasonData(status=1, season=1)

        with pytest.raises(ValidationError):
            data.status = 0


class TestTemperatureControlData:
    """Tests for TemperatureControlData Pydantic model."""

    def test_create_temperature_control_data(self):
        """Test creating a valid TemperatureControlData."""
        data = TemperatureControlData(status=0, manual_temperature=22.0)

        assert data.status == 0
        assert data.manual_temperature == 22.0

    def test_temperature_control_field_aliases(self):
        """Test that field aliases work with camelCase API responses."""
        data = TemperatureControlData(status=1, manualTemperature=23.5)

        assert data.manual_temperature == 23.5

    def test_temperature_control_immutable(self):
        """Test that TemperatureControlData is immutable (frozen)."""
        data = TemperatureControlData(status=1)

        with pytest.raises(ValidationError):
            data.status = 0


class TestThermalProfileSeasonData:
    """Tests for ThermalProfileSeasonData Pydantic model."""

    def test_create_thermal_profile_season_data(self):
        """Test creating valid ThermalProfileSeasonData for heating."""
        data = ThermalProfileSeasonData(
            comfort_temperature=21.5,
            knee_point_temperature=12.5,
            reduction_delta_temperature=1.5,
        )

        assert data.comfort_temperature == 21.5
        assert data.knee_point_temperature == 12.5
        assert data.reduction_delta_temperature == 1.5
        assert data.temperature_limit is None  # Not used in heating

    def test_create_thermal_profile_season_data_cooling(self):
        """Test creating valid ThermalProfileSeasonData for cooling."""
        data = ThermalProfileSeasonData(
            comfort_temperature=24.0,
            knee_point_temperature=18.0,
            temperature_limit=26.0,
        )

        assert data.comfort_temperature == 24.0
        assert data.knee_point_temperature == 18.0
        assert data.temperature_limit == 26.0
        assert data.reduction_delta_temperature is None  # Not used in cooling

    def test_thermal_profile_season_data_field_aliases(self):
        """Test that field aliases work with camelCase API responses."""
        data = ThermalProfileSeasonData(
            comfortTemperature=22.0,
            kneePointTemperature=13.0,
            reductionDeltaTemperature=2.0,
        )

        assert data.comfort_temperature == 22.0
        assert data.knee_point_temperature == 13.0
        assert data.reduction_delta_temperature == 2.0

    def test_thermal_profile_season_data_immutable(self):
        """Test that ThermalProfileSeasonData is immutable (frozen)."""
        data = ThermalProfileSeasonData(comfort_temperature=22.0)

        with pytest.raises(ValidationError):
            data.comfort_temperature = 23.0


class TestThermalProfileData:
    """Tests for ThermalProfileData Pydantic model."""

    def test_create_thermal_profile_data(self):
        """Test creating a valid ThermalProfileData."""
        season = SeasonData(status=1, season=1)
        temperature = TemperatureControlData(status=1)
        heating_data = ThermalProfileSeasonData(
            comfort_temperature=21.5,
            knee_point_temperature=12.5,
            reduction_delta_temperature=1.5,
        )

        data = ThermalProfileData(
            season=season,
            temperature=temperature,
            temperature_profile=0,
            heating_thermal_profile_season_data=heating_data,
        )

        assert data.season == season
        assert data.temperature == temperature
        assert data.temperature_profile == 0
        assert data.heating_thermal_profile_season_data == heating_data

    def test_thermal_profile_data_from_api_response(self):
        """Test creating ThermalProfileData from API-like dict."""
        api_response = {
            "season": {
                "status": 1,
                "season": 2,
                "heatingThresholdTemperature": 14.0,
                "coolingThresholdTemperature": 17.0,
            },
            "temperature": {"status": 1, "manualTemperature": 26.0},
            "temperatureProfile": 0,
            "heatingThermalProfileSeasonData": {
                "comfortTemperature": 21.5,
                "kneePointTemperature": 12.5,
                "reductionDeltaTemperature": 1.5,
            },
            "coolingThermalProfileSeasonData": {
                "comfortTemperature": 24.0,
                "kneePointTemperature": 18.0,
                "temperatureLimit": 26.0,
            },
        }

        data = ThermalProfileData(**api_response)

        assert data.season.status == 1
        assert data.season.season == 2
        assert data.temperature.status == 1
        assert data.temperature_profile == 0
        assert data.heating_thermal_profile_season_data.comfort_temperature == 21.5
        assert data.cooling_thermal_profile_season_data.comfort_temperature == 24.0

    def test_thermal_profile_helper_properties(self):
        """Test helper properties for season detection."""
        # Test heating season
        data_heating = ThermalProfileData(season=SeasonData(season=1))
        assert data_heating.is_heating_season is True
        assert data_heating.is_cooling_season is False

        # Test cooling season
        data_cooling = ThermalProfileData(season=SeasonData(season=2))
        assert data_cooling.is_heating_season is False
        assert data_cooling.is_cooling_season is True

        # Test automatic season
        data_auto = ThermalProfileData(season=SeasonData(status=1))
        assert data_auto.is_automatic_season is True

        # Test manual season
        data_manual = ThermalProfileData(season=SeasonData(status=0))
        assert data_manual.is_automatic_season is False

        # Test automatic temperature
        data_auto_temp = ThermalProfileData(temperature=TemperatureControlData(status=1))
        assert data_auto_temp.is_automatic_temperature is True

        # Test manual temperature
        data_manual_temp = ThermalProfileData(temperature=TemperatureControlData(status=0))
        assert data_manual_temp.is_automatic_temperature is False

    def test_thermal_profile_data_mutable(self):
        """Test that ThermalProfileData is mutable (not frozen)."""
        data = ThermalProfileData(temperature_profile=0)

        # Should be able to update values
        data.temperature_profile = 1
        assert data.temperature_profile == 1

    def test_thermal_profile_data_invalid_temperature_profile(self):
        """Test that invalid temperature_profile raises ValidationError."""
        with pytest.raises(ValidationError):
            ThermalProfileData(temperature_profile=-1)

        with pytest.raises(ValidationError):
            ThermalProfileData(temperature_profile=3)  # Max is 2


class TestMonitoringPing:
    """Tests for MonitoringPing model."""

    def test_create_monitoring_ping_with_integer_timestamp(self):
        """Test creating MonitoringPing with integer timestamp."""
        ping = MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp=1705314600,
        )

        assert ping.uuid == "test-uuid"
        assert ping.up_time_seconds == 123456
        assert ping.timestamp == 1705314600

    def test_create_monitoring_ping_with_iso_timestamp(self):
        """Test creating MonitoringPing with ISO string timestamp."""
        ping = MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp="2026-02-12T12:18:02.0Z",
        )

        assert ping.uuid == "test-uuid"
        assert ping.up_time_seconds == 123456
        # Should be converted to Unix timestamp
        assert isinstance(ping.timestamp, int)
        assert ping.timestamp > 0

    def test_create_monitoring_ping_with_iso_timestamp_without_milliseconds(self):
        """Test creating MonitoringPing with ISO string timestamp without milliseconds."""
        ping = MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp="2024-01-15T10:30:00Z",
        )

        assert ping.uuid == "test-uuid"
        assert ping.up_time_seconds == 123456
        # Should be converted to Unix timestamp (approximately 1705314600)
        assert isinstance(ping.timestamp, int)
        assert 1705314000 < ping.timestamp < 1705315000

    def test_normalize_uptime_field(self):
        """Test that 'uptime' field is normalized to 'up_time_seconds'."""
        # Using 'uptime' instead of 'up_time_seconds'
        ping = MonitoringPing(
            uuid="test-uuid",
            uptime=123456,
            timestamp=1705314600,
        )

        assert ping.up_time_seconds == 123456

    def test_normalize_upTimeSeconds_field(self):
        """Test that 'upTimeSeconds' field is normalized to 'up_time_seconds'."""
        # Using camelCase 'upTimeSeconds'
        ping = MonitoringPing(
            uuid="test-uuid",
            upTimeSeconds=123456,
            timestamp=1705314600,
        )

        assert ping.up_time_seconds == 123456

    def test_monitoring_ping_optional_fields(self):
        """Test that all fields are optional."""
        ping = MonitoringPing()

        assert ping.uuid is None
        assert ping.up_time_seconds is None
        assert ping.timestamp is None

    def test_monitoring_ping_immutable(self):
        """Test that MonitoringPing is immutable (frozen)."""
        ping = MonitoringPing(uuid="test-uuid")

        with pytest.raises(ValidationError):
            ping.uuid = "new-uuid"

    def test_monitoring_ping_invalid_timestamp_string(self):
        """Test that invalid timestamp string is removed (set to None)."""
        # Invalid timestamp should be removed to avoid validation error
        ping = MonitoringPing(
            uuid="test-uuid",
            up_time_seconds=123456,
            timestamp="invalid-timestamp",
        )

        assert ping.uuid == "test-uuid"
        assert ping.up_time_seconds == 123456
        # Invalid timestamp should be removed
        assert ping.timestamp is None


class TestTelemetryRegistryEntry:
    """Tests for TelemetryRegistryEntry Pydantic model."""

    def test_create_telemetry_registry_entry(self):
        """Test creating a valid TelemetryRegistryEntry."""
        entry = TelemetryRegistryEntry(
            faktor=0.1,
            signed=True,
            byte_count=2,
        )

        assert entry.faktor == 0.1
        assert entry.signed is True
        assert entry.byte_count == 2

    def test_telemetry_registry_entry_defaults(self):
        """Test TelemetryRegistryEntry with default values."""
        entry = TelemetryRegistryEntry()

        assert entry.faktor == 1.0
        assert entry.signed is True
        assert entry.byte_count is None

    def test_telemetry_registry_entry_invalid_faktor(self):
        """Test that invalid faktor (zero or negative) raises ValidationError."""
        with pytest.raises(ValidationError):
            TelemetryRegistryEntry(faktor=0)

        with pytest.raises(ValidationError):
            TelemetryRegistryEntry(faktor=-0.5)

    def test_telemetry_registry_entry_immutable(self):
        """Test that TelemetryRegistryEntry is frozen (immutable)."""
        entry = TelemetryRegistryEntry(faktor=0.1)

        with pytest.raises(ValidationError):
            entry.faktor = 0.2


class TestPropertyRegistryEntry:
    """Tests for PropertyRegistryEntry Pydantic model."""

    def test_create_property_registry_entry(self):
        """Test creating a valid PropertyRegistryEntry."""
        entry = PropertyRegistryEntry(
            faktor=0.5,
            signed=False,
            byte_count=2,
        )

        assert entry.faktor == 0.5
        assert entry.signed is False
        assert entry.byte_count == 2

    def test_property_registry_entry_defaults(self):
        """Test PropertyRegistryEntry with default values."""
        entry = PropertyRegistryEntry()

        assert entry.faktor == 1.0
        assert entry.signed is True
        assert entry.byte_count is None

    def test_property_registry_entry_invalid_faktor(self):
        """Test that invalid faktor raises ValidationError."""
        with pytest.raises(ValidationError):
            PropertyRegistryEntry(faktor=0)

        with pytest.raises(ValidationError):
            PropertyRegistryEntry(faktor=-1.5)

    def test_property_registry_entry_immutable(self):
        """Test that PropertyRegistryEntry is frozen (immutable)."""
        entry = PropertyRegistryEntry(faktor=2.0)

        with pytest.raises(ValidationError):
            entry.faktor = 1.5


class TestTelemetryRegistry:
    """Tests for TelemetryRegistry Pydantic model."""

    def test_create_empty_telemetry_registry(self):
        """Test creating an empty TelemetryRegistry."""
        registry = TelemetryRegistry()

        assert registry.entries == {}

    def test_telemetry_registry_with_entries(self):
        """Test TelemetryRegistry with populated entries."""
        entries = {
            "device1": {
                "4145": TelemetryRegistryEntry(faktor=0.1, signed=True),
                "4154": TelemetryRegistryEntry(faktor=0.1, signed=True),
            },
            "device2": {
                "121": TelemetryRegistryEntry(faktor=1.0, signed=False),
            },
        }
        registry = TelemetryRegistry(entries=entries)

        assert "device1" in registry.entries
        assert "device2" in registry.entries
        assert "4145" in registry.entries["device1"]
        assert registry.entries["device1"]["4145"].faktor == 0.1

    def test_telemetry_registry_entry_access(self):
        """Test accessing TelemetryRegistry entries."""
        registry = TelemetryRegistry()
        entry = TelemetryRegistryEntry(faktor=0.1, signed=True, byte_count=2)

        # Add entries programmatically
        registry.entries["device1"] = {"4145": entry}

        assert registry.entries["device1"]["4145"].faktor == 0.1
        assert registry.entries["device1"]["4145"].signed is True
        assert registry.entries["device1"]["4145"].byte_count == 2

    def test_telemetry_registry_immutable(self):
        """Test that TelemetryRegistry is frozen (immutable)."""
        registry = TelemetryRegistry()

        with pytest.raises(ValidationError):
            registry.entries = {"new": {}}


class TestPropertyRegistry:
    """Tests for PropertyRegistry Pydantic model."""

    def test_create_empty_property_registry(self):
        """Test creating an empty PropertyRegistry."""
        registry = PropertyRegistry()

        assert registry.entries == {}

    def test_property_registry_with_entries(self):
        """Test PropertyRegistry with populated entries."""
        entries = {
            "device1": {
                "29/1/10": PropertyRegistryEntry(faktor=1.0, signed=True, byte_count=2),
                "29/1/6": PropertyRegistryEntry(faktor=0.5, signed=False, byte_count=1),
            },
            "device2": {
                "30/2/5": PropertyRegistryEntry(faktor=0.1, signed=False, byte_count=2),
            },
        }
        registry = PropertyRegistry(entries=entries)

        assert "device1" in registry.entries
        assert "device2" in registry.entries
        assert "29/1/10" in registry.entries["device1"]
        assert registry.entries["device1"]["29/1/10"].faktor == 1.0

    def test_property_registry_entry_access(self):
        """Test accessing PropertyRegistry entries."""
        registry = PropertyRegistry()
        entry = PropertyRegistryEntry(faktor=0.1, signed=True, byte_count=2)

        # Add entries programmatically
        registry.entries["device1"] = {"29/1/10": entry}

        assert registry.entries["device1"]["29/1/10"].faktor == 0.1
        assert registry.entries["device1"]["29/1/10"].signed is True
        assert registry.entries["device1"]["29/1/10"].byte_count == 2

    def test_property_registry_immutable(self):
        """Test that PropertyRegistry is frozen (immutable)."""
        registry = PropertyRegistry()

        with pytest.raises(ValidationError):
            registry.entries = {"new": {}}


class TestDashboardUpdateResponse:
    """Tests for DashboardUpdateResponse model."""

    def test_create_dashboard_update_response(self):
        """Test creating a valid DashboardUpdateResponse."""
        response = DashboardUpdateResponse(status=200)

        assert response.status == 200

    def test_dashboard_update_response_default(self):
        """Test DashboardUpdateResponse with default status."""
        response = DashboardUpdateResponse()

        assert response.status == 200


class TestThermalProfileUpdateResponse:
    """Tests for ThermalProfileUpdateResponse model."""

    def test_create_thermal_profile_update_response(self):
        """Test creating a valid ThermalProfileUpdateResponse."""
        response = ThermalProfileUpdateResponse(status=200)

        assert response.status == 200

    def test_thermal_profile_update_response_default(self):
        """Test ThermalProfileUpdateResponse with default status."""
        response = ThermalProfileUpdateResponse()

        assert response.status == 200


class TestPropertyWriteResponse:
    """Tests for PropertyWriteResponse model."""

    def test_create_property_write_response(self):
        """Test creating a valid PropertyWriteResponse."""
        response = PropertyWriteResponse(status=200)

        assert response.status == 200

    def test_property_write_response_default(self):
        """Test PropertyWriteResponse with default status."""
        response = PropertyWriteResponse()

        assert response.status == 200
