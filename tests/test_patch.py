"""Tests for the HomeWizard Cloud library."""

from __future__ import annotations

from homewizard_cloud.client import apply_patch


def test_apply_patch_strips_state_prefix() -> None:
    state: dict = {}
    apply_patch(
        state,
        [
            {"op": "replace", "path": "/state/counter", "value": 42},
            {"op": "replace", "path": "/state/active_power_w", "value": -5},
        ],
    )
    assert state == {"counter": 42, "active_power_w": -5}


def test_apply_patch_nested() -> None:
    state: dict = {}
    apply_patch(
        state,
        [{"op": "replace", "path": "/state/metadata/$wifi_strength", "value": 74}],
    )
    assert state == {"metadata": {"$wifi_strength": 74}}


def test_apply_patch_ignores_non_replace_and_empty() -> None:
    state: dict = {"a": 1}
    apply_patch(state, [{"op": "add", "path": "/b", "value": 2}])
    apply_patch(state, [])
    apply_patch(state, None)
    assert state == {"a": 1}


def test_apply_patch_accumulates() -> None:
    state: dict = {}
    apply_patch(state, [{"op": "replace", "path": "/counter", "value": 1}])
    apply_patch(state, [{"op": "replace", "path": "/counter", "value": 2}])
    apply_patch(state, [{"op": "replace", "path": "/active_power_w", "value": 10}])
    assert state == {"counter": 2, "active_power_w": 10}


def test_apply_patch_invalid_path() -> None:
    state: dict = {}
    apply_patch(state, [{"op": "replace", "path": "", "value": 1}])
    apply_patch(state, [{"op": "replace", "value": 1}])
    assert state == {}
