"""Number entities for Tech Recuperation integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MENU_ID_PARTY_MODE_DURATION, MENU_ID_RECUPERATION_PARAM
from .entity import TechRecuperationEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    udid = str(entry.data["module_udid"])
    async_add_entities(
        [
            MenuNumberEntity(
                coordinator,
                udid,
                MENU_ID_PARTY_MODE_DURATION,
                "Party Mode Duration",
                15,
                720,
                1,
            ),
            MenuNumberEntity(
                coordinator,
                udid,
                MENU_ID_RECUPERATION_PARAM,
                "Recuperation Parameter",
                0,
                30,
                1,
            ),
        ]
    )


class MenuNumberEntity(TechRecuperationEntity, NumberEntity):
    """Generic number entity mapped to menu id."""

    def __init__(
        self,
        coordinator,
        udid: str,
        menu_id: int,
        name: str,
        native_min_value: float,
        native_max_value: float,
        native_step: float,
    ) -> None:
        super().__init__(coordinator, udid)
        self._menu_id = menu_id
        self._attr_unique_id = f"{udid}_menu_{menu_id}_number"
        self._attr_name = name
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_native_step = native_step
        if menu_id == MENU_ID_PARTY_MODE_DURATION:
            self._attr_native_unit_of_measurement = "min"

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._menu_id in self.coordinator.data.get("menu_controls", {})
        )

    @property
    def native_value(self) -> float | None:
        ctrl = self.coordinator.data.get("menu_controls", {}).get(self._menu_id)
        if not ctrl:
            return None
        value = ctrl.get("params", {}).get("value")
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.set_control_value(
            self.coordinator.user_id,
            self.coordinator.token,
            self.coordinator.udid,
            self._menu_id,
            int(value),
        )
        await self.coordinator.async_request_refresh()
