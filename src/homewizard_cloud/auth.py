"""Authentication helpers for the HomeWizard Cloud API."""

from __future__ import annotations

import base64
from typing import Any

import requests

from .constants import AUTH_URL, REQUEST_TIMEOUT
from .exceptions import APIError, AuthenticationError

__all__ = ["get_access_token"]


def get_access_token(email: str, password: str) -> str:
    """Authenticate with email/password and return the access token.

    The cloud auth endpoint uses HTTP Basic auth (base64 email:password).
    """
    if not email or not password:
        raise AuthenticationError("Email and password are required")

    basic = base64.b64encode(f"{email}:{password}".encode()).decode()
    try:
        resp = requests.get(
            AUTH_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise APIError(f"Authentication request failed: {exc}") from exc

    try:
        data: Any = resp.json()
    except ValueError as exc:
        raise APIError(
            f"Authentication failed (HTTP {resp.status_code}): non-JSON response"
        ) from exc

    if resp.status_code != 200:
        raise AuthenticationError(f"Authentication failed: HTTP {resp.status_code} - {data}")

    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise AuthenticationError(f"No access_token in response: {data}")

    return token
