"""Tests for custom exceptions."""

import pytest

from custom_components.comfoclime.exceptions import (
    ComfoClimeAPIError,
    ComfoClimeConnectionError,
    ComfoClimeError,
    ComfoClimeTimeoutError,
    ComfoClimeValidationError,
)


def test_base_exception():
    """Test that ComfoClimeError is the base exception."""
    error = ComfoClimeError("Test error")
    assert isinstance(error, Exception)
    assert str(error) == "Test error"


def test_connection_error_inheritance():
    """Test that ComfoClimeConnectionError inherits from ComfoClimeError."""
    error = ComfoClimeConnectionError("Connection failed")
    assert isinstance(error, ComfoClimeError)
    assert isinstance(error, Exception)
    assert str(error) == "Connection failed"


def test_api_error_inheritance():
    """Test that ComfoClimeAPIError inherits from ComfoClimeError."""
    error = ComfoClimeAPIError("API error")
    assert isinstance(error, ComfoClimeError)
    assert isinstance(error, Exception)
    assert str(error) == "API error"


def test_timeout_error_inheritance():
    """Test that ComfoClimeTimeoutError inherits from ComfoClimeError."""
    error = ComfoClimeTimeoutError("Timeout")
    assert isinstance(error, ComfoClimeError)
    assert isinstance(error, Exception)
    assert str(error) == "Timeout"


def test_validation_error_inheritance():
    """Test that ComfoClimeValidationError inherits from ComfoClimeError."""
    error = ComfoClimeValidationError("Invalid input")
    assert isinstance(error, ComfoClimeError)
    assert isinstance(error, Exception)
    assert str(error) == "Invalid input"


def test_exception_catching():
    """Test that custom exceptions can be caught properly."""
    # Test catching specific exception
    with pytest.raises(ComfoClimeConnectionError):
        raise ComfoClimeConnectionError("Test")

    # Test catching base exception
    with pytest.raises(ComfoClimeError):
        raise ComfoClimeAPIError("Test")

    # Test catching as Exception
    with pytest.raises(Exception):
        raise ComfoClimeTimeoutError("Test")


def test_exception_chaining():
    """Test that exceptions can be chained properly."""
    try:
        try:
            raise ValueError("Original error")
        except ValueError as e:
            raise ComfoClimeAPIError("API error") from e
    except ComfoClimeAPIError as api_error:
        assert str(api_error) == "API error"
        assert isinstance(api_error.__cause__, ValueError)
        assert str(api_error.__cause__) == "Original error"
