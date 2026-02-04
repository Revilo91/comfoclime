"""Tests for validators module."""

from custom_components.comfoclime.validators import (
    validate_host,
    validate_property_path,
    validate_byte_value,
    validate_duration,
)


class TestValidateHost:
    """Tests for validate_host function."""

    def test_valid_ipv4_address(self):
        """Test valid IPv4 addresses."""
        is_valid, error = validate_host("192.168.1.100")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_host("10.0.0.1")
        assert is_valid is True
        assert error is None

    def test_valid_hostname(self):
        """Test valid hostnames."""
        is_valid, error = validate_host("comfoclime.local")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_host("my-device-123")
        assert is_valid is True
        assert error is None

    def test_empty_host(self):
        """Test empty host is rejected."""
        is_valid, error = validate_host("")
        assert is_valid is False
        assert "empty" in error.lower()

        is_valid, error = validate_host("   ")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_command_injection_characters(self):
        """Test that command injection characters are rejected."""
        dangerous_chars = [";", "&", "|", "`", "$"]
        for char in dangerous_chars:
            is_valid, error = validate_host(f"evil.com{char}rm -rf /")
            assert is_valid is False
            assert "Invalid characters" in error

    def test_url_scheme_rejected(self):
        """Test that URL schemes are rejected."""
        is_valid, error = validate_host("http://192.168.1.100")
        assert is_valid is False
        assert "URL scheme" in error

        is_valid, error = validate_host("https://comfoclime.local")
        assert is_valid is False
        assert "URL scheme" in error

    def test_loopback_rejected(self):
        """Test that loopback addresses are rejected."""
        is_valid, error = validate_host("127.0.0.1")
        assert is_valid is False
        assert "Invalid IP address range" in error

        is_valid, error = validate_host("::1")
        assert is_valid is False
        assert "Invalid IP address range" in error

    def test_link_local_rejected(self):
        """Test that link-local addresses are rejected."""
        is_valid, error = validate_host("169.254.1.1")
        assert is_valid is False
        assert "Invalid IP address range" in error

    def test_multicast_rejected(self):
        """Test that multicast addresses are rejected."""
        is_valid, error = validate_host("224.0.0.1")
        assert is_valid is False
        assert "Invalid IP address range" in error

    def test_invalid_hostname_format(self):
        """Test invalid hostname formats."""
        # Hostname starting with dash
        is_valid, error = validate_host("-invalid")
        assert is_valid is False
        assert "Invalid hostname format" in error

        # Hostname with invalid characters
        is_valid, error = validate_host("host_name")
        assert is_valid is False
        assert "Invalid hostname format" in error


class TestValidatePropertyPath:
    """Tests for validate_property_path function."""

    def test_valid_path(self):
        """Test valid property paths."""
        is_valid, error = validate_property_path("29/1/10")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_property_path("0/0/0")
        assert is_valid is True
        assert error is None

        is_valid, error = validate_property_path("255/255/255")
        assert is_valid is True
        assert error is None

    def test_empty_path(self):
        """Test empty path is rejected."""
        is_valid, error = validate_property_path("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_wrong_format(self):
        """Test paths with wrong format are rejected."""
        # Too few parts
        is_valid, error = validate_property_path("29/1")
        assert is_valid is False
        assert "X/Y/Z" in error

        # Too many parts
        is_valid, error = validate_property_path("29/1/10/5")
        assert is_valid is False
        assert "X/Y/Z" in error

        # Single value
        is_valid, error = validate_property_path("29")
        assert is_valid is False
        assert "X/Y/Z" in error

    def test_non_numeric_parts(self):
        """Test paths with non-numeric parts are rejected."""
        is_valid, error = validate_property_path("abc/1/10")
        assert is_valid is False
        assert "numeric" in error.lower()

        is_valid, error = validate_property_path("29/test/10")
        assert is_valid is False
        assert "numeric" in error.lower()

    def test_out_of_range_values(self):
        """Test paths with out-of-range values are rejected."""
        is_valid, error = validate_property_path("256/1/10")
        assert is_valid is False
        assert "0-255" in error

        is_valid, error = validate_property_path("29/300/10")
        assert is_valid is False
        assert "0-255" in error

        is_valid, error = validate_property_path("-1/1/10")
        assert is_valid is False
        # Negative numbers won't pass isdigit() check
        assert "numeric" in error.lower()


class TestValidateByteValue:
    """Tests for validate_byte_value function."""

    def test_valid_unsigned_1_byte(self):
        """Test valid unsigned 1-byte values."""
        is_valid, error = validate_byte_value(0, 1, signed=False)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(127, 1, signed=False)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(255, 1, signed=False)
        assert is_valid is True
        assert error is None

    def test_valid_signed_1_byte(self):
        """Test valid signed 1-byte values."""
        is_valid, error = validate_byte_value(-128, 1, signed=True)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(0, 1, signed=True)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(127, 1, signed=True)
        assert is_valid is True
        assert error is None

    def test_valid_unsigned_2_bytes(self):
        """Test valid unsigned 2-byte values."""
        is_valid, error = validate_byte_value(0, 2, signed=False)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(32767, 2, signed=False)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(65535, 2, signed=False)
        assert is_valid is True
        assert error is None

    def test_valid_signed_2_bytes(self):
        """Test valid signed 2-byte values."""
        is_valid, error = validate_byte_value(-32768, 2, signed=True)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(0, 2, signed=True)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_byte_value(32767, 2, signed=True)
        assert is_valid is True
        assert error is None

    def test_invalid_byte_count(self):
        """Test invalid byte counts are rejected."""
        is_valid, error = validate_byte_value(100, 0, signed=False)
        assert is_valid is False
        assert "byte_count must be 1 or 2" in error

        is_valid, error = validate_byte_value(100, 3, signed=False)
        assert is_valid is False
        assert "byte_count must be 1 or 2" in error

    def test_out_of_range_unsigned_1_byte(self):
        """Test out-of-range unsigned 1-byte values are rejected."""
        is_valid, error = validate_byte_value(-1, 1, signed=False)
        assert is_valid is False
        assert "must be between 0 and 255" in error

        is_valid, error = validate_byte_value(256, 1, signed=False)
        assert is_valid is False
        assert "must be between 0 and 255" in error

    def test_out_of_range_signed_1_byte(self):
        """Test out-of-range signed 1-byte values are rejected."""
        is_valid, error = validate_byte_value(-129, 1, signed=True)
        assert is_valid is False
        assert "must be between -128 and 127" in error

        is_valid, error = validate_byte_value(128, 1, signed=True)
        assert is_valid is False
        assert "must be between -128 and 127" in error

    def test_out_of_range_unsigned_2_bytes(self):
        """Test out-of-range unsigned 2-byte values are rejected."""
        is_valid, error = validate_byte_value(-1, 2, signed=False)
        assert is_valid is False
        assert "must be between 0 and 65535" in error

        is_valid, error = validate_byte_value(65536, 2, signed=False)
        assert is_valid is False
        assert "must be between 0 and 65535" in error

    def test_out_of_range_signed_2_bytes(self):
        """Test out-of-range signed 2-byte values are rejected."""
        is_valid, error = validate_byte_value(-32769, 2, signed=True)
        assert is_valid is False
        assert "must be between -32768 and 32767" in error

        is_valid, error = validate_byte_value(32768, 2, signed=True)
        assert is_valid is False
        assert "must be between -32768 and 32767" in error


class TestValidateDuration:
    """Tests for validate_duration function."""

    def test_valid_integer_duration(self):
        """Test valid integer durations."""
        is_valid, error = validate_duration(1)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_duration(30)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_duration(1440)
        assert is_valid is True
        assert error is None

    def test_valid_float_duration(self):
        """Test valid float durations."""
        is_valid, error = validate_duration(0.5)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_duration(1.5)
        assert is_valid is True
        assert error is None

        is_valid, error = validate_duration(30.25)
        assert is_valid is True
        assert error is None

    def test_zero_duration(self):
        """Test that zero duration is rejected."""
        is_valid, error = validate_duration(0)
        assert is_valid is False
        assert "positive" in error.lower()

    def test_negative_duration(self):
        """Test that negative durations are rejected."""
        is_valid, error = validate_duration(-1)
        assert is_valid is False
        assert "positive" in error.lower()

        is_valid, error = validate_duration(-10.5)
        assert is_valid is False
        assert "positive" in error.lower()


class TestValidationIntegration:
    """Integration tests for validator usage in realistic scenarios."""

    def test_property_path_and_value_validation(self):
        """Test combined property path and value validation."""
        # Valid scenario
        path = "29/1/10"
        value = 100
        byte_count = 1
        signed = False

        is_valid_path, _ = validate_property_path(path)
        is_valid_value, _ = validate_byte_value(value, byte_count, signed)

        assert is_valid_path is True
        assert is_valid_value is True

    def test_scenario_mode_duration_validation(self):
        """Test scenario mode duration validation."""
        # Valid durations for different scenarios
        cooking_duration = 30
        party_duration = 60
        away_duration = 1440  # 24 hours
        boost_duration = 15

        for duration in [
            cooking_duration,
            party_duration,
            away_duration,
            boost_duration,
        ]:
            is_valid, error = validate_duration(duration)
            assert is_valid is True
            assert error is None

    def test_edge_case_boundary_values(self):
        """Test boundary values for all validators."""
        # Property path boundaries
        assert validate_property_path("0/0/0")[0] is True
        assert validate_property_path("255/255/255")[0] is True

        # Byte value boundaries
        assert validate_byte_value(0, 1, signed=False)[0] is True
        assert validate_byte_value(255, 1, signed=False)[0] is True
        assert validate_byte_value(-128, 1, signed=True)[0] is True
        assert validate_byte_value(127, 1, signed=True)[0] is True

        # Duration boundary
        assert validate_duration(0.001)[0] is True
        assert validate_duration(10000)[0] is True
