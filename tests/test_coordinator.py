"""Unit tests for coordinator schedule backup/restore flows."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.tech_recuperation.coordinator import TechRecuperationCoordinator


@pytest.fixture
def sample_slots() -> list[dict[str, int]]:
    """Valid 5-slot schedule."""
    return [
        {"start": 0, "end": 360, "interval": 1, "temp": 20},
        {"start": 360, "end": 720, "interval": 1, "temp": 20},
        {"start": 720, "end": 1080, "interval": 2, "temp": 21},
        {"start": 1080, "end": 1320, "interval": 2, "temp": 21},
        {"start": 1320, "end": 1439, "interval": 3, "temp": 22},
    ]


@pytest.fixture
def coordinator(sample_slots: list[dict[str, int]]) -> TechRecuperationCoordinator:
    """Coordinator with mocked API and storage."""
    api = SimpleNamespace(
        set_schedule=AsyncMock(return_value={"ok": True}),
        get_module_data=AsyncMock(return_value={"tiles": []}),
        get_menu=AsyncMock(return_value={"data": {"elements": []}}),
        authenticate=AsyncMock(return_value={"user_id": 1, "token": "token"}),
    )
    store = SimpleNamespace(
        async_load=AsyncMock(return_value=None),
        async_save=AsyncMock(),
    )
    config_entry = SimpleNamespace(
        data={"user_id": 1, "token": "token", "username": "u", "password": "p"},
        entry_id="test_entry_id",
    )
    coord = TechRecuperationCoordinator(
        hass=SimpleNamespace(),
        api=api,
        user_id=1,
        token="token",
        udid="module-1",
        backup_store=store,
        config_entry=config_entry,
    )
    coord.data = {"schedules": {1: [dict(slot) for slot in sample_slots]}}
    return coord


@pytest.mark.asyncio
async def test_set_gear_now_creates_backup_only_once(
    coordinator: TechRecuperationCoordinator,
) -> None:
    """First gear override creates backup and persists once."""
    await coordinator.async_set_gear_now(day_id=1, gear=3)
    await coordinator.async_set_gear_now(day_id=1, gear=2)

    assert 1 in coordinator.schedule_backups
    assert coordinator._backup_store.async_save.await_count == 1
    assert coordinator.api.set_schedule.await_count == 2


@pytest.mark.asyncio
async def test_set_day_schedule_creates_backup(
    coordinator: TechRecuperationCoordinator,
    sample_slots: list[dict[str, int]],
) -> None:
    """Setting full schedule also snapshots original schedule."""
    updated = [dict(slot) for slot in sample_slots]
    updated[2]["interval"] = 0

    await coordinator.async_set_day_schedule(day_id=1, slots=updated)

    assert 1 in coordinator.schedule_backups
    assert coordinator._backup_store.async_save.await_count == 1
    assert coordinator.api.set_schedule.await_count == 1


@pytest.mark.asyncio
async def test_restore_day_schedule_writes_backup_and_clears_it(
    coordinator: TechRecuperationCoordinator,
) -> None:
    """Restore uses backup, then removes it and persists removal."""
    original = coordinator.get_day_schedule(1)
    coordinator.schedule_backups[1] = [dict(slot) for slot in original]

    await coordinator.async_restore_day_schedule(1)

    assert 1 not in coordinator.schedule_backups
    assert coordinator.api.set_schedule.await_count == 1
    assert coordinator._backup_store.async_save.await_count == 1


@pytest.mark.asyncio
async def test_restore_day_schedule_raises_when_backup_missing(
    coordinator: TechRecuperationCoordinator,
) -> None:
    """Restore fails if no backup exists for target day."""
    with pytest.raises(HomeAssistantError, match="No backup schedule"):
        await coordinator.async_restore_day_schedule(1)


@pytest.mark.asyncio
async def test_load_backups_discards_invalid_entries(
    coordinator: TechRecuperationCoordinator,
) -> None:
    """Persisted backups are validated via normalize_slots."""
    coordinator._backup_store.async_load.return_value = {
        "1": [
            {"start": 0, "end": 360, "interval": 1, "temp": 20},
            {"start": 360, "end": 720, "interval": 1, "temp": 20},
            {"start": 720, "end": 1080, "interval": 2, "temp": 21},
            {"start": 1080, "end": 1320, "interval": 2, "temp": 21},
            {"start": 1320, "end": 1439, "interval": 3, "temp": 22},
        ],
        "bad": [
            {"start": 0, "end": 100, "interval": 1, "temp": 20},
        ],
    }

    await coordinator.async_load_backups()

    assert list(coordinator.schedule_backups) == [1]
