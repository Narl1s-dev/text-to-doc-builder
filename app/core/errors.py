class AppError(Exception):
    """Base application exception."""


class ConfigurationError(AppError):
    """Raised when the application configuration is invalid."""

