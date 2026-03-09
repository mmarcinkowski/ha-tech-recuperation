"""Unit tests for helper functions."""

from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.tech_recuperation.helpers import (
    apply_gear_now,
    apply_gear_until,
    hhmm_to_minutes,
    normalize_slots,
    python_weekday_to_day_id,
    resolve_day_id,
)


@pytest.fixture
def valid_slots() -> list[dict[str, int]]:
    """Return a valid 5-slot schedule covering a full day."""
    return [
        {"start": 0, "end": 360, "interval": 1, "temp": 20},
        {"start": 360, "end": 720, "interval": 1, "temp": 20},
        {"start": 720, "end": 1080, "interval": 2, "temp": 21},
        {"start": 1080, "end": 1320, "interval": 2, "temp": 21},
        {"start": 1320, "end": 1439, "interval": 3, "temp": 22},
    ]


def test_python_weekday_to_day_id_mapping() -> None:
    """Converts Python weekday to API day id."""
    assert python_weekday_to_day_id(0) == 1
    assert python_weekday_to_day_id(1) == 2
    assert python_weekday_to_day_id(2) == 3
    assert python_weekday_to_day_id(3) == 4
    assert python_weekday_to_day_id(4) == 5
    assert python_weekday_to_day_id(5) == 6
    assert python_weekday_to_day_id(6) == 0


def test_resolve_day_id_today_and_tomorrow() -> None:
    """Resolves dynamic day aliases using a fixed datetime."""
    now = datetime(2026, 3, 9, 12, 0)  # Monday
    assert resolve_day_id("today", now) == 1
    assert resolve_day_id("tomorrow", now) == 2


def test_hhmm_to_minutes() -> None:
    """Parses valid HH:MM values."""
    assert hhmm_to_minutes("00:00") == 0
    assert hhmm_to_minutes("12:34") == 754
    assert hhmm_to_minutes("23:59") == 1439


def test_hhmm_to_minutes_handles_hh_mm_ss() -> None:
    """Parses valid HH:MM:SS values (seconds silently discarded)."""
    assert hhmm_to_minutes("00:00:00") == 0
    assert hhmm_to_minutes("12:34:56") == 754
    assert hhmm_to_minutes("23:59:59") == 1439


def test_hhmm_to_minutes_rejects_invalid_values() -> None:
    """Rejects invalid HH:MM values."""
    with pytest.raises(ValueError):
        hhmm_to_minutes("24:00")
    with pytest.raises(ValueError):
        hhmm_to_minutes("10:60")


def test_normalize_slots_returns_sorted_and_normalized(valid_slots: list[dict[str, int]]) -> None:
    """Normalizes schedule slots and preserves full-day coverage."""
    unsorted = [valid_slots[2], valid_slots[0], valid_slots[1], valid_slots[4], valid_slots[3]]
    normalized = normalize_slots(unsorted)
    assert [slot["start"] for slot in normalized] == [0, 360, 720, 1080, 1320]
    assert normalized[0]["end"] == 360
    assert normalized[-1]["end"] == 1439


def test_normalize_slots_requires_exactly_five_slots(valid_slots: list[dict[str, int]]) -> None:
    """Rejects schedules with invalid slot count."""
    with pytest.raises(ValueError, match="Exactly 5 slots"):
        normalize_slots(valid_slots[:-1])


def test_apply_gear_now_does_not_change_slot_ending_now(valid_slots: list[dict[str, int]]) -> None:
    """Keeps slots ending exactly now unchanged (off-by-one fix)."""
    updated = apply_gear_now(valid_slots, gear=3, now_minute=720)
    assert updated[0]["interval"] == 1
    assert updated[1]["interval"] == 1
    assert updated[2]["interval"] == 3
    assert updated[3]["interval"] == 3
    assert updated[4]["interval"] == 3


def test_apply_gear_until_does_not_change_slot_ending_now(valid_slots: list[dict[str, int]]) -> None:
    """Keeps slots ending exactly now unchanged (off-by-one fix)."""
    updated = apply_gear_until(valid_slots, gear=3, until_minute=1000, now_minute=720)
    assert updated[0]["interval"] == 1
    assert updated[1]["interval"] == 1
    assert updated[2]["interval"] == 3
    assert updated[3]["interval"] == 2
    assert updated[4]["interval"] == 3


def test_apply_gear_until_applies_revert_gear_after_until(valid_slots: list[dict[str, int]]) -> None:
    """Applies revert gear to slots starting at/after until."""
    updated = apply_gear_until(
        valid_slots,
        gear=0,
        until_minute=1000,
        revert_gear=2,
        now_minute=700,
    )
    assert updated[2]["interval"] == 0
    assert updated[3]["interval"] == 2
    assert updated[4]["interval"] == 2


def test_apply_gear_until_rejects_past_until(valid_slots: list[dict[str, int]]) -> None:
    """Rejects until values not later than now."""
    with pytest.raises(ValueError, match="until must be later"):
        apply_gear_until(valid_slots, gear=1, until_minute=600, now_minute=600)
