"""Switch entities for Tech Recuperation integration."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TechApiError
from .const import DOMAIN, MENU_ID_BYPASS_ONOFF, TILE_TYPE_RELAY
from .entity import TechRecuperationEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])
    async_add_entities([BypassSwitch(coordinator, udid)])


class BypassSwitch(TechRecuperationEntity, SwitchEntity):
    """Bypass on/off switch."""

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_bypass"
        self._attr_name = "Bypass"

    @property
    def available(self) -> bool:
        """Available when menu control or relay tile exists."""
        if not super().available:
            return False
        ctrl = self.coordinator.data.get("menu_controls", {}).get(MENU_ID_BYPASS_ONOFF)
        if ctrl:
            return True
        for tile in self.coordinator.data.get("tiles", {}).values():
            if tile.get("type") == TILE_TYPE_RELAY and tile.get("menuId") == MENU_ID_BYPASS_ONOFF:
                return True
        return False

    @property
    def is_on(self) -> bool:
        # Prefer menu control value if present
        ctrl = self.coordinator.data.get("menu_controls", {}).get(MENU_ID_BYPASS_ONOFF)
        if ctrl:
            return bool(ctrl.get("params", {}).get("value", 0))

        # Fallback to relay tile state
        for tile in self.coordinator.data.get("tiles", {}).values():
            if tile.get("type") == TILE_TYPE_RELAY and tile.get("menuId") == MENU_ID_BYPASS_ONOFF:
                return bool(tile.get("params", {}).get("workingStatus", False))
        return False

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self.coordinator._async_api_call(
                lambda: self.coordinator.api.set_control_value(
                    self.coordinator.user_id,
                    self.coordinator.token,
                    self.coordinator.udid,
                    MENU_ID_BYPASS_ONOFF,
                    1,
                )
            )
        except TechApiError as err:
            _LOGGER.error("Failed to turn on bypass: %s", err)
            raise
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        try:
            await self.coordinator._async_api_call(
                lambda: self.coordinator.api.set_control_value(
                    self.coordinator.user_id,
                    self.coordinator.token,
                    self.coordinator.udid,
                    MENU_ID_BYPASS_ONOFF,
                    0,
                )
            )
        except TechApiError as err:
            _LOGGER.error("Failed to turn off bypass: %s", err)
            raise
        await self.coordinator.async_request_refresh()
