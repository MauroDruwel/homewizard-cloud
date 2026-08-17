# HomeWizard Cloud

Async Python library for the [HomeWizard](https://www.homewizard.com/) Cloud API —
stream your P1 meter from the cloud over WebSocket. No local device access needed.

Based on the cloud API research by [Sven Serlier](https://github.com/smarthomesven/homey-homewizard-energy-cloud)
and the implementation in [jtebbens/com.homewizard](https://github.com/jtebbens/com.homewizard).

## Install

```bash
pip install homewizard-cloud
```

## Usage

```python
import asyncio
from homewizard_cloud import HomeWizardCloudClient


async def main():
    client = HomeWizardCloudClient(email="you@example.com", password="secret")
    await client.authenticate()

    # Find your P1 dongle
    for device in await client.get_p1_devices():
        print(device.device_id, device.name)

    # Stream live data
    await client.listen(
        "p1dongle/5c2faf3c6a8a",
        on_state=lambda device_id, state: print("state:", state["active_power_w"]),
        on_realtime=lambda m: print("live wattage:", m.wattage),
    )


asyncio.run(main())
```

## How it works

1. **Auth** — `GET api.homewizardeasyonline.com/v1/auth/account/token` with HTTP Basic
   auth (email:password) returns an access token.
2. **Discovery** — `GET homes.api.homewizard.com/locations` lists your homes and P1
   devices (`type == "p1dongle"`, id like `p1dongle/5c2faf3c6a8a`).
3. **State stream** — `wss://energy-app-ws.homewizard.com/ws/` sends a `hello` message
   (masquerading as the Android energy app, which the server requires), then
   `subscribe_device`. Full `p1dongle` states and `json_patch` deltas follow.
4. **Realtime stream** — `wss://tsdb-reader.homewizard.com/devices/date/now` pushes
   second-by-second wattage.

Both streams auto-reconnect and the token is refreshed when the server rejects it.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```
