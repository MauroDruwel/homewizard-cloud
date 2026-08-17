"""HomeWizard Cloud Python Library.

Async library for the HomeWizard Cloud API: authentication, P1 device
discovery and two WebSocket streams (state + realtime wattage).
"""

__version__ = "1.0.2"

from .client import HomeWizardCloudClient, apply_patch
from .exceptions import APIError, AuthenticationError, HomeWizardCloudError
from .models import Location, P1Device, RealtimeMeasurement

__all__ = [
    "APIError",
    "AuthenticationError",
    "HomeWizardCloudClient",
    "HomeWizardCloudError",
    "Location",
    "P1Device",
    "RealtimeMeasurement",
    "apply_patch",
]
