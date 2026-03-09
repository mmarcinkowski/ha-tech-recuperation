"""Switch entities for Tech Recuperation integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MENU_ID_RECUPERATION_ONOFF, TILE_TYPE_RELAY
from .entity import TechRecuperationEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])
    async_add_entities([RecuperationPowerSwitch(coordinator, udid)])


class RecuperationPowerSwitch(TechRecuperationEntity, SwitchEntity):
    """Recuperation on/off switch."""

    def __init__(self, coordinator, udid: str) -> None:
        super().__init__(coordinator, udid)
        self._attr_unique_id = f"{udid}_recuperation_power"
        self._attr_name = "Recuperation"

    @property
    def is_on(self) -> bool:
        # Prefer menu control value if present
        ctrl = self.coordinator.data.get("menu_controls", {}).get(MENU_ID_RECUPERATION_ONOFF)
        if ctrl:
            return bool(ctrl.get("params", {}).get("value", 0))

        # Fallback to relay tile state
        for tile in self.coordinator.data.get("tiles", {}).values():
            if tile.get("type") == TILE_TYPE_RELAY and tile.get("menuId") == MENU_ID_RECUPERATION_ONOFF:
                return bool(tile.get("params", {}).get("workingStatus", False))
        return False

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.api.set_control_value(
            self.coordinator.user_id,
            self.coordinator.token,
            self.coordinator.udid,
            MENU_ID_RECUPERATION_ONOFF,
            1,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.set_control_value(
            self.coordinator.user_id,
            self.coordinator.token,
            self.coordinator.udid,
            MENU_ID_RECUPERATION_ONOFF,
            0,
        )
        await self.coordinator.async_request_refresh()
