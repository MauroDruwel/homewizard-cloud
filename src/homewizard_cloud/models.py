"""Dataclass models representing HomeWizard Cloud data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Location",
    "P1Device",
    "RealtimeMeasurement",
]


@dataclass
class Location:
    """A HomeWizard home (location) in the cloud account."""

    id: str
    name: str
    devices: list[P1Device] = field(default_factory=list)


@dataclass
class P1Device:
    """A cloud P1 dongle (e.g. ``p1dongle/5c2faf3c6a8a``)."""

    device_id: str
    name: str
    location_id: str | None = None
    location_name: str | None = None


@dataclass
class RealtimeMeasurement:
    """A second-by-second wattage measurement from the tsdb stream."""

    timestamp: float
    wattage: int
    wattages: list[int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "wattage": self.wattage,
            "wattages": self.wattages,
        }
