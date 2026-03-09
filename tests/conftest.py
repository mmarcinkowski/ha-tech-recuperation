"""Test configuration for local unit tests.

This file stubs a minimal Home Assistant surface so integration modules can be
imported in a lightweight local pytest environment.
"""

from __future__ import annotations

import sys
import types
import importlib.util
from pathlib import Path


# ---- Minimal homeassistant stubs for unit tests ----

if "homeassistant" not in sys.modules:
    homeassistant_pkg = types.ModuleType("homeassistant")
    homeassistant_pkg.__path__ = []
    sys.modules["homeassistant"] = homeassistant_pkg

if "homeassistant.core" not in sys.modules:
    core_mod = types.ModuleType("homeassistant.core")

    class HomeAssistant:  # noqa: D101
        pass

    setattr(core_mod, "HomeAssistant", HomeAssistant)
    sys.modules["homeassistant.core"] = core_mod

if "homeassistant.config_entries" not in sys.modules:
    ce_mod = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:  # noqa: D101
        pass

    setattr(ce_mod, "ConfigEntry", ConfigEntry)
    sys.modules["homeassistant.config_entries"] = ce_mod

if "homeassistant.util" not in sys.modules:
    util_mod = types.ModuleType("homeassistant.util")
    sys.modules["homeassistant.util"] = util_mod

if "homeassistant.util.dt" not in sys.modules:
    from datetime import datetime

    dt_mod = types.ModuleType("homeassistant.util.dt")
    setattr(dt_mod, "now", datetime.now)
    sys.modules["homeassistant.util.dt"] = dt_mod

if "homeassistant.helpers" not in sys.modules:
    helpers_mod = types.ModuleType("homeassistant.helpers")
    helpers_mod.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers_mod

if "homeassistant.helpers.storage" not in sys.modules:
    storage_mod = types.ModuleType("homeassistant.helpers.storage")

    class Store:  # noqa: D101
        def __init__(self, hass, version, key):
            self.hass = hass
            self.version = version
            self.key = key

    setattr(storage_mod, "Store", Store)
    sys.modules["homeassistant.helpers.storage"] = storage_mod

if "homeassistant.helpers.entity" not in sys.modules:
    entity_mod = types.ModuleType("homeassistant.helpers.entity")

    class EntityCategory:  # noqa: D101
        CONFIG = "config"

    setattr(entity_mod, "EntityCategory", EntityCategory)
    sys.modules["homeassistant.helpers.entity"] = entity_mod

if "homeassistant.helpers.entity_platform" not in sys.modules:
    ep_mod = types.ModuleType("homeassistant.helpers.entity_platform")

    class AddEntitiesCallback:  # noqa: D101
        pass

    setattr(ep_mod, "AddEntitiesCallback", AddEntitiesCallback)
    sys.modules["homeassistant.helpers.entity_platform"] = ep_mod

if "homeassistant.helpers.update_coordinator" not in sys.modules:
    uc_mod = types.ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        """Raised when coordinator update fails."""

    class DataUpdateCoordinator:  # noqa: D101
        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = {}
            self._refresh_calls = 0

        async def async_request_refresh(self):
            self._refresh_calls += 1

    class CoordinatorEntity:  # noqa: D101
        def __init__(self, coordinator):
            self.coordinator = coordinator

        def __class_getitem__(cls, _item):
            return cls

        @property
        def available(self):
            return True

    setattr(uc_mod, "UpdateFailed", UpdateFailed)
    setattr(uc_mod, "DataUpdateCoordinator", DataUpdateCoordinator)
    setattr(uc_mod, "CoordinatorEntity", CoordinatorEntity)
    sys.modules["homeassistant.helpers.update_coordinator"] = uc_mod

if "homeassistant.components" not in sys.modules:
    components_mod = types.ModuleType("homeassistant.components")
    components_mod.__path__ = []
    sys.modules["homeassistant.components"] = components_mod

if "homeassistant.components.button" not in sys.modules:
    button_mod = types.ModuleType("homeassistant.components.button")

    class ButtonEntity:  # noqa: D101
        pass

    setattr(button_mod, "ButtonEntity", ButtonEntity)
    sys.modules["homeassistant.components.button"] = button_mod

if "homeassistant.components.number" not in sys.modules:
    number_mod = types.ModuleType("homeassistant.components.number")

    class NumberEntity:  # noqa: D101
        pass

    setattr(number_mod, "NumberEntity", NumberEntity)
    sys.modules["homeassistant.components.number"] = number_mod

if "homeassistant.components.select" not in sys.modules:
    select_mod = types.ModuleType("homeassistant.components.select")

    class SelectEntity:  # noqa: D101
        pass

    setattr(select_mod, "SelectEntity", SelectEntity)
    sys.modules["homeassistant.components.select"] = select_mod

if "homeassistant.components.switch" not in sys.modules:
    switch_mod = types.ModuleType("homeassistant.components.switch")

    class SwitchEntity:  # noqa: D101
        pass

    setattr(switch_mod, "SwitchEntity", SwitchEntity)
    sys.modules["homeassistant.components.switch"] = switch_mod

# ---- aiohttp fallback stub (only if aiohttp is unavailable) ----

if importlib.util.find_spec("aiohttp") is None:
    aiohttp_mod = types.ModuleType("aiohttp")

    class ClientError(Exception):
        """Fallback aiohttp client error."""

    class ClientSession:  # noqa: D101
        pass

    setattr(aiohttp_mod, "ClientError", ClientError)
    setattr(aiohttp_mod, "ClientSession", ClientSession)
    sys.modules["aiohttp"] = aiohttp_mod


ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
INTEGRATION_DIR = CUSTOM_COMPONENTS / "tech_recuperation"


if "custom_components" not in sys.modules:
    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [str(CUSTOM_COMPONENTS)]
    sys.modules["custom_components"] = custom_components_pkg

if "custom_components.tech_recuperation" not in sys.modules:
    integration_pkg = types.ModuleType("custom_components.tech_recuperation")
    integration_pkg.__path__ = [str(INTEGRATION_DIR)]
    sys.modules["custom_components.tech_recuperation"] = integration_pkg
