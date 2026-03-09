"""Helpers for schedule parsing and manipulation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import DAY_NAME_TO_ID, SCHEDULE_MAX_TIME, SCHEDULE_MIN_TIME


def python_weekday_to_day_id(weekday: int) -> int:
    """Convert Python weekday (0=Mon) to API day id (0=Sun)."""
    return (weekday + 1) % 7


def minutes_now(now: datetime | None = None) -> int:
    """Return current minute of day."""
    dt = now or datetime.now()
    return dt.hour * 60 + dt.minute


def hhmm_to_minutes(value: str) -> int:
    """Convert HH:MM string to minutes from midnight."""
    hour_s, minute_s = value.split(":", maxsplit=1)
    hour = int(hour_s)
    minute = int(minute_s)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time: {value}")
    return hour * 60 + minute


def to_minutes(value: int | str) -> int:
    """Convert int minutes or HH:MM string to minutes."""
    if isinstance(value, int):
        return value
    return hhmm_to_minutes(value)


def resolve_day_id(target_day: str, now: datetime | None = None) -> int:
    """Resolve service target day to day id."""
    dt = now or datetime.now()
    target = target_day.lower()
    if target == "today":
        return python_weekday_to_day_id(dt.weekday())
    if target == "tomorrow":
        return (python_weekday_to_day_id(dt.weekday()) + 1) % 7
    if target not in DAY_NAME_TO_ID:
        raise ValueError(f"Unknown day: {target_day}")
    return DAY_NAME_TO_ID[target]


def normalize_slots(slots: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Normalize and validate schedule slots."""
    if len(slots) != 5:
        raise ValueError("Exactly 5 slots are required")

    normalized: list[dict[str, int]] = []
    for slot in slots:
        start = to_minutes(slot["start"])
        end = to_minutes(slot["end"])
        interval = int(slot["gear"] if "gear" in slot else slot["interval"])
        temp = int(slot.get("temp", 20))

        if start < SCHEDULE_MIN_TIME or end > SCHEDULE_MAX_TIME or start >= end:
            raise ValueError(f"Invalid slot boundaries: {slot}")
        if interval < 0 or interval > 3:
            raise ValueError(f"Invalid gear: {interval}")
        if temp < 10 or temp > 30:
            raise ValueError(f"Invalid temp: {temp}")

        normalized.append(
            {"start": start, "end": end, "interval": interval, "temp": temp}
        )

    normalized.sort(key=lambda s: s["start"])

    if normalized[0]["start"] != SCHEDULE_MIN_TIME:
        raise ValueError("First slot must start at 00:00")
    if normalized[-1]["end"] != SCHEDULE_MAX_TIME:
        raise ValueError("Last slot must end at 23:59")

    for i in range(4):
        if normalized[i]["end"] != normalized[i + 1]["start"]:
            raise ValueError("Slots must be contiguous")

    return normalized


def apply_gear_now(
    slots: list[dict[str, int]],
    gear: int,
    temp: int | None = None,
    now_minute: int | None = None,
) -> list[dict[str, int]]:
    """Apply gear from current time to end of day."""
    if gear < 0 or gear > 3:
        raise ValueError(f"Invalid gear: {gear}")
    if temp is not None and (temp < 10 or temp > 30):
        raise ValueError(f"Invalid temp: {temp}")

    now_m = now_minute if now_minute is not None else minutes_now()
    out: list[dict[str, int]] = []

    for slot in slots:
        new_slot = dict(slot)
        if int(new_slot["end"]) >= now_m:
            new_slot["interval"] = gear
            if temp is not None:
                new_slot["temp"] = temp
        out.append(new_slot)

    return out


def apply_gear_until(
    slots: list[dict[str, int]],
    gear: int,
    until_minute: int,
    temp: int | None = None,
    revert_gear: int | None = None,
    now_minute: int | None = None,
) -> list[dict[str, int]]:
    """Apply gear for slots between now and until."""
    if gear < 0 or gear > 3:
        raise ValueError(f"Invalid gear: {gear}")
    if temp is not None and (temp < 10 or temp > 30):
        raise ValueError(f"Invalid temp: {temp}")
    if revert_gear is not None and (revert_gear < 0 or revert_gear > 3):
        raise ValueError(f"Invalid revert_gear: {revert_gear}")

    now_m = now_minute if now_minute is not None else minutes_now()
    if until_minute <= now_m:
        raise ValueError("until must be later than current time")
    if until_minute < SCHEDULE_MIN_TIME or until_minute > SCHEDULE_MAX_TIME:
        raise ValueError(f"Invalid until minute: {until_minute}")

    out: list[dict[str, int]] = []
    for slot in slots:
        new_slot = dict(slot)
        start = int(new_slot["start"])
        end = int(new_slot["end"])

        if end >= now_m and start < until_minute:
            new_slot["interval"] = gear
            if temp is not None:
                new_slot["temp"] = temp
        elif revert_gear is not None and start >= until_minute:
            new_slot["interval"] = revert_gear
            if temp is not None:
                new_slot["temp"] = temp
        out.append(new_slot)

    return out
