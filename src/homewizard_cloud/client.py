"""Async client for the HomeWizard Cloud API.

Handles authentication, location/device discovery and the two WebSocket
streams (main state stream + realtime wattage stream), with automatic
reconnection and token refresh.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import requests
import websockets

from . import auth
from .constants import (
    HELLO_COMPATIBILITY,
    HELLO_OS,
    HELLO_SOURCE,
    HELLO_VERSION,
    LOCATIONS_URL,
    MAIN_WS_URL,
    REALTIME_WS_URL,
    REQUEST_TIMEOUT,
    TOKEN_LIFETIME,
    TOKEN_RENEW_MARGIN,
)
from .exceptions import APIError
from .models import Location, P1Device, RealtimeMeasurement

__all__ = ["HomeWizardCloudClient"]

logger = logging.getLogger(__name__)

StateCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]
RealtimeCallback = Callable[[RealtimeMeasurement], Awaitable[None] | None]
ConnectionCallback = Callable[[bool], Awaitable[None] | None]


class HomeWizardCloudClient:
    """Async client for the HomeWizard Cloud API."""

    def __init__(
        self,
        email: str,
        password: str,
        *,
        reconnect_delay: float = 5.0,
    ) -> None:
        self.email = email
        self.password = password
        self.reconnect_delay = reconnect_delay

        self.access_token: str | None = None
        self._token_fetched_at: float = 0.0
        self._token_ttl: float = TOKEN_LIFETIME
        self._auth_lock = asyncio.Lock()

        self._message_id = 0
        self._stop_event = asyncio.Event()
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------ auth

    async def authenticate(self) -> str:
        """Fetch (or refresh) the access token."""
        async with self._auth_lock:
            token = await asyncio.to_thread(auth.get_access_token, self.email, self.password)
            self.access_token = token
            self._token_fetched_at = asyncio.get_running_loop().time()
            return token

    def _token_is_valid(self) -> bool:
        if not self.access_token:
            return False
        if self._token_ttl == 0:
            return True
        elapsed = asyncio.get_running_loop().time() - self._token_fetched_at
        return elapsed < self._token_ttl - TOKEN_RENEW_MARGIN

    async def _ensure_token(self) -> str:
        if not self._token_is_valid():
            await self.authenticate()
        assert self.access_token is not None
        return self.access_token

    # ------------------------------------------------------------ http API

    async def get_locations(self) -> list[Location]:
        """List all locations (homes) with their P1 devices."""
        token = await self._ensure_token()

        def _fetch() -> Any:
            try:
                resp = requests.get(
                    LOCATIONS_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:
                raise APIError(f"Get locations request failed: {exc}") from exc
            if resp.status_code != 200:
                raise APIError(f"Get locations failed (HTTP {resp.status_code}): {resp.text[:300]}")
            return resp.json()

        data = await asyncio.to_thread(_fetch)
        if not isinstance(data, list):
            raise APIError(f"Expected list from locations, got {type(data).__name__}")

        locations: list[Location] = []
        for raw in data:
            if not isinstance(raw, dict):
                continue
            location = Location(id=str(raw.get("id", "")), name=raw.get("name", ""))
            for device_raw in raw.get("devices", []) or []:
                if not isinstance(device_raw, dict):
                    continue
                if device_raw.get("type") != "p1dongle":
                    continue
                location.devices.append(
                    P1Device(
                        device_id=device_raw.get("device_id", ""),
                        name=device_raw.get("name") or "P1 Meter",
                        location_id=location.id,
                        location_name=location.name,
                    )
                )
            locations.append(location)
        return locations

    async def get_p1_devices(self) -> list[P1Device]:
        """Return all P1 dongles across locations."""
        return [device for location in await self.get_locations() for device in location.devices]

    # ------------------------------------------------------------- streams

    async def listen(
        self,
        device_id: str,
        on_state: StateCallback | None = None,
        on_realtime: RealtimeCallback | None = None,
        on_connection: ConnectionCallback | None = None,
        on_realtime_connection: ConnectionCallback | None = None,
        *,
        three_phases: bool = False,
    ) -> None:
        """Subscribe to a device and stream updates until :meth:`close`.

        Runs the main state WebSocket (hello -> subscribe_device) and the
        realtime wattage WebSocket in parallel. Both reconnect
        automatically; the access token is refreshed when rejected.

        ``on_connection`` is called with ``True`` when the main stream is
        connected and subscribed, and ``False`` when it disconnects.
        ``on_realtime_connection`` reports the connection state of the
        second-by-second wattage stream.
        """
        self._stop_event.clear()
        tasks = [
            asyncio.create_task(self._run_main_stream(device_id, on_state, on_connection)),
            asyncio.create_task(
                self._run_realtime_stream(
                    device_id,
                    on_realtime,
                    three_phases,
                    on_realtime_connection,
                )
            ),
        ]
        self._tasks.update(tasks)
        try:
            await asyncio.gather(*tasks)
        finally:
            self._tasks.difference_update(tasks)

    def close(self) -> None:
        """Stop all streams. Tasks are cancelled in the event loop."""
        self._stop_event.set()
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self._tasks.clear()

    async def _run_main_stream(
        self,
        device_id: str,
        on_state: StateCallback | None,
        on_connection: ConnectionCallback | None = None,
    ) -> None:
        state: dict[str, Any] = {}
        connected = False

        async def set_connection(value: bool) -> None:
            nonlocal connected
            if connected == value:
                return
            connected = value
            if on_connection is not None:
                await self._maybe_await(on_connection(value))

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(MAIN_WS_URL) as ws:
                    await self._hello(ws)
                    authenticated = await self._await_hello_response(ws)
                    if not authenticated:
                        await self._handle_auth_rejection(ws, device_id)
                        await self._sleep_or_stop(self.reconnect_delay)
                        continue
                    await self._send(ws, {"type": "subscribe_device", "device": device_id})
                    await set_connection(True)
                    logger.info("Subscribed to device %s (main stream)", device_id)

                    async for raw in ws:
                        message = json.loads(raw)
                        msg_type = message.get("type")

                        if msg_type == "response" and message.get("status") in (401, 403):
                            logger.warning("Main stream subscription rejected: %s", message)
                            await set_connection(False)
                            await ws.close()
                            break
                        if msg_type == "error":
                            logger.warning("Main stream error: %s", message)
                            if "Authentication" in str(message.get("message", "")):
                                await set_connection(False)
                                await self._handle_auth_rejection(ws, device_id)
                                break
                        elif msg_type in ("p1dongle", "energysocket", "watermeter"):
                            state = message.get("state", {})
                            if on_state is not None:
                                await self._maybe_await(on_state(device_id, state))
                        elif msg_type == "json_patch":
                            apply_patch(state, message.get("patch", []))
                            if on_state is not None:
                                await self._maybe_await(on_state(device_id, state))
                    await set_connection(False)
                if not self._stop_event.is_set():
                    await self._sleep_or_stop(self.reconnect_delay)
            except asyncio.CancelledError:
                await set_connection(False)
                raise
            except (websockets.ConnectionClosed, OSError):
                await set_connection(False)
                if self._stop_event.is_set():
                    break
                logger.info(
                    "Main stream disconnected, reconnecting in %.0fs",
                    self.reconnect_delay,
                )
                await self._sleep_or_stop(self.reconnect_delay)
            except Exception:
                await set_connection(False)
                logger.exception("Main stream error")
                await self._sleep_or_stop(self.reconnect_delay)

    async def _run_realtime_stream(
        self,
        device_id: str,
        on_realtime: RealtimeCallback | None,
        three_phases: bool,
        on_connection: ConnectionCallback | None = None,
    ) -> None:
        if on_realtime is None and on_connection is None:
            return
        connected = False

        async def set_connection(value: bool) -> None:
            nonlocal connected
            if connected == value:
                return
            connected = value
            if on_connection is not None:
                await self._maybe_await(on_connection(value))

        while not self._stop_event.is_set():
            try:
                token = await self._ensure_token()
                async with websockets.connect(REALTIME_WS_URL) as ws:
                    await ws.send(
                        json.dumps(
                            {
                                "token": token,
                                "type": "main_connection",
                                "devices": [
                                    {
                                        "identifier": device_id,
                                        "measurementType": "main_connection",
                                    }
                                ],
                                "three_phases": three_phases,
                            }
                        )
                    )
                    await set_connection(True)
                    logger.info("Subscribed to device %s (realtime stream)", device_id)

                    async for raw in ws:
                        message = json.loads(raw)
                        if on_realtime is not None and "time" in message and "wattage" in message:
                            measurement = RealtimeMeasurement(
                                timestamp=message.get("time"),
                                wattage=message.get("wattage"),
                                wattages=message.get("wattages"),
                            )
                            await self._maybe_await(on_realtime(measurement))
                    await set_connection(False)
                if not self._stop_event.is_set():
                    await self._sleep_or_stop(self.reconnect_delay)
            except asyncio.CancelledError:
                await set_connection(False)
                raise
            except (websockets.ConnectionClosed, OSError):
                await set_connection(False)
                if self._stop_event.is_set():
                    break
                logger.info(
                    "Realtime stream disconnected, reconnecting in %.0fs",
                    self.reconnect_delay,
                )
                await self._sleep_or_stop(self.reconnect_delay)
            except Exception:
                await set_connection(False)
                logger.exception("Realtime stream error")
                await self._sleep_or_stop(self.reconnect_delay)

    # ------------------------------------------------------------ helpers

    async def _hello(self, ws) -> None:
        token = await self._ensure_token()
        await self._send(
            ws,
            {
                "type": "hello",
                "message_id": 0,
                "compatibility": HELLO_COMPATIBILITY,
                "os": HELLO_OS,
                "source": HELLO_SOURCE,
                "token": token,
                "version": HELLO_VERSION,
            },
        )

    async def _await_hello_response(self, ws) -> bool:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
        except (TimeoutError, websockets.ConnectionClosed):
            return False
        message = json.loads(raw)
        if message.get("type") == "response":
            return message.get("status") == 200
        return False

    async def _handle_auth_rejection(self, ws, device_id: str) -> None:
        logger.warning("Token rejected for %s, refreshing...", device_id)
        await self.authenticate()
        with contextlib.suppress(Exception):
            await ws.close()

    async def _send(self, ws, obj: dict) -> None:
        if "message_id" not in obj:
            self._message_id += 1
            obj["message_id"] = self._message_id
        await ws.send(json.dumps(obj))

    @staticmethod
    async def _maybe_await(result) -> None:
        if inspect.isawaitable(result):
            await result

    async def _sleep_or_stop(self, delay: float) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay)


def apply_patch(state: dict[str, Any], patch: list) -> None:
    """Apply a JSON patch (RFC 6902 replace ops) to a state dict.

    Cloud patches address the message root (e.g. ``/state/counter``), so
    the leading ``state`` segment is stripped before merging.
    """
    for operation in patch or []:
        if not isinstance(operation, dict) or operation.get("op") != "replace":
            continue
        path_parts = [p for p in str(operation.get("path", "")).split("/") if p]
        if path_parts and path_parts[0] == "state":
            path_parts = path_parts[1:]
        if not path_parts:
            continue
        target = state
        for part in path_parts[:-1]:
            target = target.setdefault(part, {})
        target[path_parts[-1]] = operation.get("value")
