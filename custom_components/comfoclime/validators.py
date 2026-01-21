"""Input validation and security functions for ComfoClime integration.

This module provides validation functions to ensure safe and correct input
for the ComfoClime Home Assistant integration. It includes validation for:
- Hostnames and IP addresses (command injection prevention)
- Property paths (format X/Y/Z)
- Byte values (range validation)
- Duration values (positive values)

These validators are used in config_flow, services, and API calls to prevent
security vulnerabilities and ensure data integrity.
"""

from __future__ import annotations

import ipaddress
import re


def validate_host(host: str) -> tuple[bool, str | None]:
    """Validate a host string for safety and correctness.

    Performs comprehensive validation to prevent command injection and ensure
    the host is a valid hostname or IP address. Rejects dangerous IP ranges
    (loopback, link-local, multicast).

    Args:
        host: Hostname or IP address to validate.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains description of the error.

    Example:
        >>> validate_host("192.168.1.100")
        (True, None)
        >>> validate_host("comfoclime.local")
        (True, None)
        >>> validate_host("evil.com; rm -rf /")
        (False, "Invalid characters in hostname")
        >>> validate_host("127.0.0.1")
        (False, "Invalid IP address range")
    """
    # Remove any whitespace
    host = host.strip()

    # Check for empty
    if not host:
        return False, "Host cannot be empty"

    # Check for dangerous characters (command injection prevention)
    if re.search(r'[;&|`$]', host):
        return False, "Invalid characters in hostname"

    # Check for URL scheme (should be just host)
    if "://" in host:
        return False, "Host should not include URL scheme"

    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(host)
        # Reject dangerous IP ranges
        if ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False, "Invalid IP address range"
        return True, None
    except ValueError:
        pass

    # Validate as hostname
    hostname_pattern = re.compile(
        r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.?$'
    )
    if not hostname_pattern.match(host):
        return False, "Invalid hostname format"

    return True, None


def validate_property_path(path: str) -> tuple[bool, str | None]:
    """Validate a property path format (X/Y/Z).

    Property paths must consist of exactly 3 numeric components separated by
    slashes, where each component is a value between 0 and 255 inclusive.
    This format is used by the ComfoClime API for property access.

    Args:
        path: Property path string to validate.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains description of the error.

    Example:
        >>> validate_property_path("29/1/10")
        (True, None)
        >>> validate_property_path("0/0/0")
        (True, None)
        >>> validate_property_path("invalid")
        (False, "Path must be in format X/Y/Z")
        >>> validate_property_path("256/1/1")
        (False, "Path components must be 0-255")
    """
    if not path:
        return False, "Path cannot be empty"

    parts = path.split("/")
    if len(parts) != 3:
        return False, "Path must be in format X/Y/Z"

    for part in parts:
        if not part.isdigit():
            return False, "Path components must be numeric"
        if int(part) < 0 or int(part) > 255:
            return False, "Path components must be 0-255"

    return True, None


def validate_byte_value(
    value: int,
    byte_count: int,
    signed: bool = False,
) -> tuple[bool, str | None]:
    """Validate a value fits in the specified byte count.

    Ensures that an integer value can be represented in the given number of
    bytes, respecting signed or unsigned representation. Used to validate
    values before writing to device properties.

    Args:
        value: The integer value to validate.
        byte_count: Number of bytes (1 or 2).
        signed: Whether the value is signed. Defaults to False (unsigned).

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains description of the error.

    Example:
        >>> validate_byte_value(100, 1, signed=False)
        (True, None)
        >>> validate_byte_value(-10, 1, signed=True)
        (True, None)
        >>> validate_byte_value(300, 1, signed=False)
        (False, "Value must be between 0 and 255")
        >>> validate_byte_value(-200, 1, signed=True)
        (False, "Value must be between -128 and 127")
    """
    if byte_count not in (1, 2):
        return False, "byte_count must be 1 or 2"

    if signed:
        min_val = -(2 ** (byte_count * 8 - 1))
        max_val = 2 ** (byte_count * 8 - 1) - 1
    else:
        min_val = 0
        max_val = 2 ** (byte_count * 8) - 1

    if not min_val <= value <= max_val:
        return False, f"Value must be between {min_val} and {max_val}"

    return True, None


def validate_duration(duration: int | float) -> tuple[bool, str | None]:
    """Validate scenario mode duration is positive.

    Ensures that duration values for scenario modes (cooking, party, away, boost)
    are positive numbers. Duration is typically specified in minutes.

    Args:
        duration: Duration value to validate (in minutes).

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid, otherwise contains description of the error.

    Example:
        >>> validate_duration(30)
        (True, None)
        >>> validate_duration(1.5)
        (True, None)
        >>> validate_duration(0)
        (False, "Duration must be positive")
        >>> validate_duration(-10)
        (False, "Duration must be positive")
    """
    if duration <= 0:
        return False, "Duration must be positive"

    return True, None
