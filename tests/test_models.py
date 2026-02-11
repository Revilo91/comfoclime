"""Tests for data models in models.py"""

import pytest
from pydantic import ValidationError

from custom_components.comfoclime.models import (
    DashboardData,
    DeviceConfig,
    PropertyReading,
    SeasonData,
    TelemetryReading,
    TemperatureControlData,
    ThermalProfileData,
    ThermalProfileSeasonData,
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
            "season": {"status": 1, "season": 2, "heatingThresholdTemperature": 14.0, "coolingThresholdTemperature": 17.0},
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
