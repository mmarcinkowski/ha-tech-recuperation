"""Unit tests for select/switch/button/number entities."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.tech_recuperation.button import (
    PartyModeTriggerButton,
    RestoreTodayScheduleButton,
)
from custom_components.tech_recuperation import button as button_module
from custom_components.tech_recuperation.const import (
    MENU_ID_BYPASS_ONOFF,
    MENU_ID_PARTY_MODE_DURATION,
    MENU_ID_PARTY_MODE_TRIGGER,
)
from custom_components.tech_recuperation.number import MenuNumberEntity
from custom_components.tech_recuperation.select import CurrentGearSelect
from custom_components.tech_recuperation.switch import BypassSwitch


@pytest.fixture
def coordinator() -> SimpleNamespace:
    """Coordinator-like object used by entity tests."""

    async def _passthrough_api_call(coro_factory):
        return await coro_factory()

    return SimpleNamespace(
        user_id=1,
        token="token",
        udid="module-1",
        data={
            "current_gear": 2,
            "menu_controls": {
                MENU_ID_BYPASS_ONOFF: {"params": {"value": 1}},
                MENU_ID_PARTY_MODE_DURATION: {"params": {"value": 120}},
                MENU_ID_PARTY_MODE_TRIGGER: {"params": {"value": 0}},
            },
            "tiles": {},
        },
        schedule_backups={1: [{"start": 0, "end": 1439, "interval": 1, "temp": 20}]},
        api=SimpleNamespace(set_control_value=AsyncMock(return_value={"ok": True})),
        async_request_refresh=AsyncMock(),
        async_set_gear_now=AsyncMock(),
        async_restore_day_schedule=AsyncMock(),
        _async_api_call=AsyncMock(side_effect=_passthrough_api_call),
    )


@pytest.mark.asyncio
async def test_current_gear_select_triggers_schedule_override(
    coordinator: SimpleNamespace,
) -> None:
    """Selecting gear calls coordinator override with mapped value."""
    entity = CurrentGearSelect(coordinator, "module-1")
    assert entity.current_option == "gear_2"

    await entity.async_select_option("gear_3")

    coordinator.async_set_gear_now.assert_awaited_once()


@pytest.mark.asyncio
async def test_switch_turn_on_off_calls_menu_control(
    coordinator: SimpleNamespace,
) -> None:
    """Switch on/off writes expected control values."""
    entity = BypassSwitch(coordinator, "module-1")
    assert entity.is_on is True

    await entity.async_turn_off()
    await entity.async_turn_on()

    assert coordinator.api.set_control_value.await_count == 2


@pytest.mark.asyncio
async def test_party_button_press_triggers_control(
    coordinator: SimpleNamespace,
) -> None:
    """Party mode button sends trigger value and refreshes."""
    entity = PartyModeTriggerButton(coordinator, "module-1")
    assert entity.available is True

    await entity.async_press()

    coordinator.api.set_control_value.assert_awaited_once_with(
        coordinator.user_id,
        coordinator.token,
        coordinator.udid,
        MENU_ID_PARTY_MODE_TRIGGER,
        1,
    )


@pytest.mark.asyncio
async def test_restore_button_press_calls_restore(
    coordinator: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restore button forwards action to coordinator restore method."""
    monkeypatch.setattr(button_module.dt_util, "now", lambda: SimpleNamespace(weekday=lambda: 0))
    entity = RestoreTodayScheduleButton(coordinator, "module-1")

    assert entity.available is True
    await entity.async_press()

    coordinator.async_restore_day_schedule.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_menu_number_set_value_calls_control(
    coordinator: SimpleNamespace,
) -> None:
    """Number entity writes integer menu value."""
    entity = MenuNumberEntity(
        coordinator,
        "module-1",
        MENU_ID_PARTY_MODE_DURATION,
        "Party Mode Duration",
        15,
        720,
        1,
    )
    assert entity.native_value == 120.0

    await entity.async_set_native_value(180.0)

    coordinator.api.set_control_value.assert_awaited_with(
        coordinator.user_id,
        coordinator.token,
        coordinator.udid,
        MENU_ID_PARTY_MODE_DURATION,
        180,
    )
