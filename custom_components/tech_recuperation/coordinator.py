"""DataUpdateCoordinator for Tech Recuperation."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TechAPI, TechApiError, TechAuthError
from .const import (
    DAY_ELEMENT_IDS,
    DOMAIN,
    MENU_ID_SCHEDULE_PARENT,
    MENU_TYPE_MULTI_TABLE_SCHEDULE,
    SCAN_INTERVAL,
    SCHEDULE_NUM_ROWS,
)
from .helpers import apply_gear_now, apply_gear_until, minutes_now, normalize_slots

_LOGGER = logging.getLogger(__name__)


def _python_weekday_to_day_id(weekday: int) -> int:
    """Convert Python weekday (0=Monday) to eMODUL dayId (0=Sunday).

    Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    eMODUL: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
    """
    return (weekday + 1) % 7


def _parse_schedules(
    menu_elements: list[dict[str, Any]],
) -> dict[int, list[dict[str, int]]]:
    """Parse schedule data from menu elements.

    Returns:
        Dict mapping dayId (0-6) to list of 5 slot dicts with keys:
        start, end, interval (gear), temp.
    """
    schedules: dict[int, list[dict[str, int]]] = {}

    for elem in menu_elements:
        if (
            elem.get("type") != MENU_TYPE_MULTI_TABLE_SCHEDULE
            or elem.get("parentId") != MENU_ID_SCHEDULE_PARENT
        ):
            continue

        params = elem.get("params", {})
        day_id = params.get("dayId")
        rows = params.get("rows", [])

        if day_id is None or not rows:
            continue

        slots = []
        for row in rows[:SCHEDULE_NUM_ROWS]:
            slots.append(
                {
                    "start": row.get("startTime", 0),
                    "end": row.get("endTime", 0),
                    "interval": row.get("valueFirstColumn", 1),  # gear
                    "temp": row.get("valueSecondColumn", 20),
                }
            )
        try:
            schedules[int(day_id)] = normalize_slots(slots)
        except ValueError:
            _LOGGER.debug("Skipping invalid schedule for day_id=%s", day_id)

    return schedules


def _get_current_gear(
    schedules: dict[int, list[dict[str, int]]], now: Any
) -> tuple[int, int]:
    """Get current gear and slot index from today's schedule.

    Returns:
        (gear, slot_index) tuple. gear is 0-3, slot_index is 0-4.
    """
    day_id = _python_weekday_to_day_id(now.weekday())
    slots = schedules.get(day_id, [])
    minutes = now.hour * 60 + now.minute

    for i, slot in enumerate(slots):
        start = int(slot["start"])
        end = int(slot["end"])
        is_last = i == len(slots) - 1
        if (start <= minutes < end) or (is_last and start <= minutes <= end):
            return slot["interval"], i

    # Fallback: return first slot's gear or 1
    if slots:
        return slots[0]["interval"], 0
    return 1, 0


class TechRecuperationCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from eMODUL API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: TechAPI,
        user_id: int,
        token: str,
        udid: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.api = api
        self.user_id = user_id
        self.token = token
        self.udid = udid
        self.username = username
        self.password = password
        self._schedule_backups: dict[int, list[dict[str, int]]] = {}

    @property
    def schedule_backups(self) -> dict[int, list[dict[str, int]]]:
        """Expose schedule backups for entities/services."""
        return self._schedule_backups

    async def _async_fetch(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch module and menu data, re-authenticating if needed."""
        try:
            module_data = await self.api.get_module_data(
                self.user_id, self.token, self.udid
            )
            menu_data = await self.api.get_menu(
                self.user_id, self.token, self.udid
            )
            return module_data, menu_data
        except TechAuthError as err:
            if not self.username or not self.password:
                raise UpdateFailed(f"Authentication failed: {err}") from err

            _LOGGER.info("Token expired, re-authenticating with eMODUL")
            auth = await self.api.authenticate(self.username, self.password)
            self.user_id = int(auth["user_id"])
            self.token = str(auth["token"])

            module_data = await self.api.get_module_data(
                self.user_id, self.token, self.udid
            )
            menu_data = await self.api.get_menu(
                self.user_id, self.token, self.udid
            )
            return module_data, menu_data

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            module_data, menu_data = await self._async_fetch()
        except TechAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except TechApiError as err:
            raise UpdateFailed(f"API error: {err}") from err

        # Parse tiles into a dict keyed by tile id
        tiles: dict[int, dict[str, Any]] = {}
        for tile in module_data.get("tiles", []):
            tiles[tile["id"]] = tile

        # Parse menu elements
        menu_elements = menu_data.get("data", {}).get("elements", [])

        # Parse schedules from menu
        schedules = _parse_schedules(menu_elements)

        # Parse menu controls (non-schedule elements at root level)
        menu_controls: dict[int, dict[str, Any]] = {}
        for elem in menu_elements:
            if elem.get("parentId") == 0 and elem.get("type") != 0:
                menu_controls[elem["id"]] = elem

        # Determine current gear from schedule
        now = dt_util.now()
        current_gear, current_slot_index = _get_current_gear(schedules, now)

        return {
            "tiles": tiles,
            "menu_elements": menu_elements,
            "menu_controls": menu_controls,
            "schedules": schedules,
            "current_gear": current_gear,
            "current_slot_index": current_slot_index,
            "raw_module": module_data,
        }

    def get_day_schedule(self, day_id: int) -> list[dict[str, int]]:
        """Return schedule for specific day id."""
        return self.data.get("schedules", {}).get(day_id, [])

    async def async_set_day_schedule(
        self, day_id: int, slots: list[dict[str, Any]]
    ) -> None:
        """Set full day schedule and refresh coordinator."""
        element_id = DAY_ELEMENT_IDS[day_id]
        normalized = normalize_slots(slots)
        await self.api.set_schedule(
            self.user_id,
            self.token,
            self.udid,
            element_id,
            normalized,
        )
        await self.async_request_refresh()

    async def async_set_gear_now(
        self, day_id: int, gear: int, temp: int | None = None
    ) -> None:
        """Set gear from now to end of day by rewriting day's schedule."""
        if gear < 0 or gear > 3:
            raise UpdateFailed(f"Invalid gear value: {gear}")
        slots = self.get_day_schedule(day_id)
        if not slots:
            raise UpdateFailed(f"No schedule found for day_id {day_id}")
        if day_id not in self._schedule_backups:
            self._schedule_backups[day_id] = [dict(slot) for slot in slots]

        now = dt_util.now()
        today_day_id = _python_weekday_to_day_id(now.weekday())
        effective_now = minutes_now(now) if day_id == today_day_id else 0
        updated = apply_gear_now(slots, gear, temp=temp, now_minute=effective_now)
        element_id = DAY_ELEMENT_IDS[day_id]
        await self.api.set_schedule(
            self.user_id,
            self.token,
            self.udid,
            element_id,
            updated,
        )
        await self.async_request_refresh()

    async def async_set_gear_until(
        self,
        day_id: int,
        gear: int,
        until_minute: int,
        temp: int | None = None,
        revert_gear: int | None = None,
    ) -> None:
        """Set gear until specific minute by rewriting day's schedule."""
        if gear < 0 or gear > 3:
            raise UpdateFailed(f"Invalid gear value: {gear}")
        if until_minute < 0 or until_minute > 1439:
            raise UpdateFailed(f"Invalid until minute: {until_minute}")
        if revert_gear is not None and (revert_gear < 0 or revert_gear > 3):
            raise UpdateFailed(f"Invalid revert gear value: {revert_gear}")

        slots = self.get_day_schedule(day_id)
        if not slots:
            raise UpdateFailed(f"No schedule found for day_id {day_id}")

        if day_id not in self._schedule_backups:
            self._schedule_backups[day_id] = [dict(slot) for slot in slots]

        now = dt_util.now()
        today_day_id = _python_weekday_to_day_id(now.weekday())
        effective_now = minutes_now(now) if day_id == today_day_id else 0
        updated = apply_gear_until(
            slots,
            gear,
            until_minute,
            temp=temp,
            revert_gear=revert_gear,
            now_minute=effective_now,
        )
        element_id = DAY_ELEMENT_IDS[day_id]
        await self.api.set_schedule(
            self.user_id,
            self.token,
            self.udid,
            element_id,
            updated,
        )
        await self.async_request_refresh()

    async def async_restore_day_schedule(self, day_id: int) -> None:
        """Restore previously backed-up schedule for a day."""
        backup = self._schedule_backups.get(day_id)
        if not backup:
            raise UpdateFailed(f"No backup schedule found for day_id {day_id}")

        element_id = DAY_ELEMENT_IDS[day_id]
        normalized = normalize_slots(backup)
        await self.api.set_schedule(
            self.user_id,
            self.token,
            self.udid,
            element_id,
            normalized,
        )
        del self._schedule_backups[day_id]
        await self.async_request_refresh()
