"""Tests for data models in models.py"""

import pytest

from custom_components.comfoclime.models import (
    DeviceConfig,
    TelemetryReading,
    PropertyReading,
    DashboardData,
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
        """Test that empty uuid raises ValueError."""
        with pytest.raises(ValueError, match="uuid cannot be empty"):
            DeviceConfig(uuid="", model_type_id=1)

    def test_device_config_negative_model_type_id(self):
        """Test that negative model_type_id raises ValueError."""
        with pytest.raises(ValueError, match="model_type_id must be non-negative"):
            DeviceConfig(uuid="abc123", model_type_id=-1)

    def test_device_config_immutable(self):
        """Test that DeviceConfig is immutable (frozen)."""
        config = DeviceConfig(uuid="abc123", model_type_id=1)

        with pytest.raises(AttributeError):
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
        """Test that empty device_uuid raises ValueError."""
        with pytest.raises(ValueError, match="device_uuid cannot be empty"):
            TelemetryReading(device_uuid="", telemetry_id="10", raw_value=100)

    def test_telemetry_reading_empty_telemetry_id(self):
        """Test that empty telemetry_id raises ValueError."""
        with pytest.raises(ValueError, match="telemetry_id cannot be empty"):
            TelemetryReading(device_uuid="abc123", telemetry_id="", raw_value=100)

    def test_telemetry_reading_invalid_faktor(self):
        """Test that invalid faktor raises ValueError."""
        with pytest.raises(ValueError, match="faktor must be greater than 0"):
            TelemetryReading(
                device_uuid="abc123", telemetry_id="10", raw_value=100, faktor=0
            )

        with pytest.raises(ValueError, match="faktor must be greater than 0"):
            TelemetryReading(
                device_uuid="abc123", telemetry_id="10", raw_value=100, faktor=-1.0
            )

    def test_telemetry_reading_invalid_byte_count(self):
        """Test that invalid byte_count raises ValueError."""
        with pytest.raises(ValueError, match="byte_count must be 1 or 2"):
            TelemetryReading(
                device_uuid="abc123", telemetry_id="10", raw_value=100, byte_count=3
            )


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
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="path cannot be empty"):
            PropertyReading(device_uuid="abc123", path="", raw_value=100)


class TestDashboardData:
    """Tests for DashboardData dataclass."""

    def test_create_dashboard_data(self):
        """Test creating a valid DashboardData."""
        data = DashboardData(
            temperature=22.5,
            target_temperature=21.0,
            fan_speed=50,
            season="heating",
            hp_standby=False,
        )

        assert data.temperature == 22.5
        assert data.target_temperature == 21.0
        assert data.fan_speed == 50
        assert data.season == "heating"
        assert data.hp_standby is False

    def test_dashboard_data_default_values(self):
        """Test DashboardData with default values."""
        data = DashboardData()

        assert data.temperature is None
        assert data.target_temperature is None
        assert data.fan_speed is None
        assert data.season is None
        assert data.hp_standby is None

    def test_dashboard_data_invalid_fan_speed(self):
        """Test that invalid fan_speed raises ValueError."""
        with pytest.raises(ValueError, match="fan_speed must be between 0 and 100"):
            DashboardData(fan_speed=-1)

        with pytest.raises(ValueError, match="fan_speed must be between 0 and 100"):
            DashboardData(fan_speed=101)

    def test_dashboard_data_mutable(self):
        """Test that DashboardData is mutable (not frozen)."""
        data = DashboardData(temperature=22.5)

        # Should be able to update values
        data.temperature = 23.0
        assert data.temperature == 23.0
