"""Select entities for Tech Recuperation integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, GEAR_NAME_TO_VALUE, GEAR_OPTIONS, GEAR_VALUE_TO_NAME
from .entity import TechRecuperationEntity
from .helpers import python_weekday_to_day_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])
    async_add_entities([CurrentGearSelect(coordinator, udid)])


class CurrentGearSelect(TechRecuperationEntity, SelectEntity):
    """Select for setting current gear by rewriting today's schedule."""

    _attr_options = GEAR_OPTIONS
    _attr_entity_category = "config"

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_gear_select"
        self._attr_name = "Temporary Gear Override"

    @property
    def current_option(self) -> str | None:
        gear = self.coordinator.data.get("current_gear", 1)
        return GEAR_VALUE_TO_NAME.get(gear, "gear_1")

    async def async_select_option(self, option: str) -> None:
        gear = GEAR_NAME_TO_VALUE[option]
        day_id = python_weekday_to_day_id(dt_util.now().weekday())
        await self.coordinator.async_set_gear_now(day_id, gear)
