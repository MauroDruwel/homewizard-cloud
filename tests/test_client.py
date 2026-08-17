"""Tests for client lifecycle and token handling."""

from __future__ import annotations

import asyncio
import inspect

from homewizard_cloud.client import HomeWizardCloudClient
from homewizard_cloud.constants import TOKEN_LIFETIME, TOKEN_RENEW_MARGIN


def test_reconnect_sleep_is_a_client_method() -> None:
    client = HomeWizardCloudClient("user@example.com", "password")

    assert inspect.iscoroutinefunction(client._sleep_or_stop)


def test_token_is_renewed_before_expiry() -> None:
    async def _check() -> None:
        client = HomeWizardCloudClient("user@example.com", "password")
        client.access_token = "token"
        client._token_fetched_at = asyncio.get_running_loop().time()
        assert client._token_is_valid()

        client._token_fetched_at -= TOKEN_LIFETIME - TOKEN_RENEW_MARGIN + 1
        assert not client._token_is_valid()

    asyncio.run(_check())
