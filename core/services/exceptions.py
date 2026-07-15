"""
Domain exceptions for the service layer.

Kept in one module so every service raises from the same vocabulary
instead of each inventing its own ad-hoc exception classes.
"""


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class NotFoundError(ServiceError):
    """Raised when a requested entity doesn't exist."""


class InvalidStageTransitionError(ServiceError):
    """Raised when a batch stage transition is not the next legal stage."""


class ValidationError(ServiceError):
    """Raised when caller-supplied input fails a business rule."""
