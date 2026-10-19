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


def test_client_accepts_ssl_context() -> None:
    import ssl

    context = ssl.create_default_context()
    client = HomeWizardCloudClient("user@example.com", "password", ssl=context)
    assert client.ssl is context


def test_auth_failure_triggers_callback_and_raises() -> None:
    from unittest.mock import AsyncMock, patch

    from homewizard_cloud.exceptions import AuthenticationError

    async def _check() -> None:
        client = HomeWizardCloudClient("user@example.com", "password")
        auth_failed_mock = AsyncMock()

        with patch.object(
            client,
            "_ensure_token",
            side_effect=AuthenticationError("Invalid credentials"),
        ):
            try:
                await client.listen(
                    "p1_test",
                    on_auth_failed=auth_failed_mock,
                )
            except AuthenticationError:
                pass
            else:
                assert False, "Expected AuthenticationError was not raised"

            assert auth_failed_mock.called

    asyncio.run(_check())
