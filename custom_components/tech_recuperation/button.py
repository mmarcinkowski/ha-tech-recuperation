"""Button entities for Tech Recuperation integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import TechApiError
from .const import DOMAIN, MENU_ID_PARTY_MODE_TRIGGER
from .entity import TechRecuperationEntity
from .helpers import python_weekday_to_day_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])
    async_add_entities(
        [
            RestoreTodayScheduleButton(coordinator, udid),
            PartyModeTriggerButton(coordinator, udid),
        ]
    )


class RestoreTodayScheduleButton(TechRecuperationEntity, ButtonEntity):
    """Restore backed-up schedule for today."""

    _attr_icon = "mdi:backup-restore"

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_restore_today_schedule"
        self._attr_name = "Restore Today Schedule"

    @property
    def available(self) -> bool:
        day_id = python_weekday_to_day_id(dt_util.now().weekday())
        return super().available and day_id in self.coordinator.schedule_backups

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        attrs: dict[str, int] = {}
        day_id = python_weekday_to_day_id(dt_util.now().weekday())
        backup = self.coordinator.schedule_backups.get(day_id)
        if backup:
            attrs["backup_slots"] = len(backup)
        return attrs

    async def async_press(self) -> None:
        day_id = python_weekday_to_day_id(dt_util.now().weekday())
        await self.coordinator.async_restore_day_schedule(day_id)


class PartyModeTriggerButton(TechRecuperationEntity, ButtonEntity):
    """Trigger party mode."""

    _attr_icon = "mdi:party-popper"

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_party_mode_trigger"
        self._attr_name = "Activate Party Mode"

    @property
    def available(self) -> bool:
        return (
            super().available
            and MENU_ID_PARTY_MODE_TRIGGER
            in self.coordinator.data.get("menu_controls", {})
        )

    async def async_press(self) -> None:
        try:
            await self.coordinator._async_api_call(
                lambda: self.coordinator.api.set_control_value(
                    self.coordinator.user_id,
                    self.coordinator.token,
                    self.coordinator.udid,
                    MENU_ID_PARTY_MODE_TRIGGER,
                    1,
                )
            )
        except TechApiError as err:
            _LOGGER.error("Failed to trigger party mode: %s", err)
            raise
        await self.coordinator.async_request_refresh()
