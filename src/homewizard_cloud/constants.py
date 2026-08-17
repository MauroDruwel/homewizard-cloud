"""Public constants for the HomeWizard Cloud API."""

from __future__ import annotations

__all__ = [
    "AUTH_URL",
    "HELLO_COMPATIBILITY",
    "HELLO_OS",
    "HELLO_SOURCE",
    "HELLO_VERSION",
    "LOCATIONS_URL",
    "MAIN_WS_URL",
    "REALTIME_WS_URL",
    "REQUEST_TIMEOUT",
    "TOKEN_RENEW_MARGIN",
]

AUTH_URL = "https://api.homewizardeasyonline.com/v1/auth/account/token?include=account"
LOCATIONS_URL = "https://homes.api.homewizard.com/locations"

MAIN_WS_URL = "wss://energy-app-ws.homewizard.com/ws/"
REALTIME_WS_URL = "wss://tsdb-reader.homewizard.com/devices/date/now"

# The cloud WebSocket validates the client against the Android energy app
# identity — mismatched os/source/version are rejected with
# "Authentication is required".
HELLO_COMPATIBILITY = 5
HELLO_OS = "android"
HELLO_SOURCE = "nl.homewizard.android.energy"
HELLO_VERSION = (
    "nl.homewizard.android.energy/1.25.9(124) Dalvik/2.1.0 "
    "(Linux; U; Android 12; sdk_gphone64_x86_64 Build/SE1A.220826.008)"
)

REQUEST_TIMEOUT = 30
TOKEN_RENEW_MARGIN = 300
