"""Base entity class for Tech Recuperation."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TechRecuperationCoordinator


class TechRecuperationEntity(CoordinatorEntity[TechRecuperationCoordinator]):
    """Base class for all entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TechRecuperationCoordinator, udid: str) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._udid = udid

    @property
    def device_info(self) -> dict[str, Any]:
        """Return shared device info."""
        return {
            "identifiers": {(DOMAIN, self._udid)},
            "name": "Wanas Recuperation",
            "manufacturer": "Tech / Wanas",
            "model": "ST-340 V2",
        }
