"""Custom exception hierarchy for the homewizard_cloud library."""

from __future__ import annotations

__all__ = [
    "APIError",
    "AuthenticationError",
    "HomeWizardCloudError",
]


class HomeWizardCloudError(Exception):
    """Base exception for all homewizard_cloud errors."""


class AuthenticationError(HomeWizardCloudError):
    """Authentication or login failed."""


class APIError(HomeWizardCloudError):
    """API request failed or returned unexpected data.

    Attributes:
        status_code: HTTP status code when available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
