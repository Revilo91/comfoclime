"""Custom exceptions for ComfoClime integration."""


class ComfoClimeError(Exception):
    """Base exception for ComfoClime."""


class ComfoClimeConnectionError(ComfoClimeError):
    """Raised when connection to ComfoClime device fails."""


class ComfoClimeAPIError(ComfoClimeError):
    """Raised when API returns an error."""


class ComfoClimeTimeoutError(ComfoClimeError):
    """Raised when request times out."""


class ComfoClimeValidationError(ComfoClimeError):
    """Raised when input validation fails."""
