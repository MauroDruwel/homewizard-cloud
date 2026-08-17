#!/usr/bin/env python3
"""Stream your HomeWizard P1 meter via the cloud API.

pip install -e .
python example.py --email you@example.com --password secret [--device p1dongle/XXXX]
"""

from __future__ import annotations

import argparse
import asyncio
import os

from homewizard_cloud import HomeWizardCloudClient
from homewizard_cloud.models import RealtimeMeasurement


def on_state(device_id: str, state: dict) -> None:
    power = state.get("active_power_w")
    if power is not None:
        print(f"[{device_id}] power_w={power}", flush=True)


def on_realtime(measurement: RealtimeMeasurement) -> None:
    print(f"[realtime] w={measurement.wattage}", flush=True)


async def main(email: str, password: str, device_id: str | None) -> None:
    client = HomeWizardCloudClient(email=email, password=password)
    await client.authenticate()
    print("Authenticated")

    if not device_id:
        print("No device given, listing P1 devices:")
        for device in await client.get_p1_devices():
            print(f"  {device.device_id}  ({device.name} @ {device.location_name})")
        client.close()
        return

    if "/" not in device_id:
        device_id = f"p1dongle/{device_id}"

    try:
        await client.listen(
            device_id,
            on_state=on_state,
            on_realtime=on_realtime,
        )
    except asyncio.CancelledError:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HomeWizard Cloud P1 meter reader")
    parser.add_argument("--email", default=os.environ.get("HW_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("HW_PASSWORD"))
    parser.add_argument("--device", help="P1 device id (omit to list)")
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("email and password required (or set HW_EMAIL/HW_PASSWORD)")

    try:
        asyncio.run(main(args.email, args.password, args.device))
    except KeyboardInterrupt:
        print("\nBye")
