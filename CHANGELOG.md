# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-17

### Added
- First stable release. Published to PyPI.
- Async `HomeWizardCloudClient` for the HomeWizard Cloud API.
- Token auth via `api.homewizardeasyonline.com` (HTTP Basic auth).
- P1 device discovery via `homes.api.homewizard.com/locations`.
- Main state WebSocket (`energy-app-ws.homewizard.com`): hello handshake,
  `subscribe_device`, full `p1dongle` states and `json_patch` deltas.
- Realtime wattage WebSocket (`tsdb-reader.homewizard.com`): 1-second updates.
- Automatic reconnection for both streams.
- Automatic token refresh when the server rejects the token.
- Dataclasses for `Location`, `P1Device`, `RealtimeMeasurement`.
- `apply_patch` JSON-patch (RFC 6902) helper.

## [0.1.0] - 2026-08-17

### Added
- Initial async client implementation.