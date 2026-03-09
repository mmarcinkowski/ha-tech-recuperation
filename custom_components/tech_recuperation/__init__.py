"""Tech Recuperation integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import TechAPI
from .const import (
    ATTR_DAY,
    ATTR_GEAR,
    ATTR_SLOTS,
    CONF_MODULE_UDID,
    CONF_TOKEN,
    CONF_USER_ID,
    DOMAIN,
    GEAR_NAME_TO_VALUE,
    PLATFORMS,
    SERVICE_RESTORE_DAY_SCHEDULE,
    SERVICE_SET_DAY_SCHEDULE,
    SERVICE_SET_GEAR_NOW,
    SERVICE_SET_GEAR_UNTIL,
)
from .coordinator import TechRecuperationCoordinator
from .helpers import hhmm_to_minutes, resolve_day_id

_LOGGER = logging.getLogger(__name__)


SET_DAY_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DAY): str,
        vol.Required(ATTR_SLOTS): list,
    }
)

SET_GEAR_NOW_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DAY, default="today"): str,
        vol.Required(ATTR_GEAR): vol.Any(int, str),
        vol.Optional("temp"): int,
    }
)

SET_GEAR_UNTIL_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DAY, default="today"): str,
        vol.Required(ATTR_GEAR): vol.Any(int, str),
        vol.Required("until"): str,
        vol.Optional("temp"): int,
        vol.Optional("revert_gear"): vol.Any(int, str),
    }
)

RESTORE_DAY_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DAY, default="today"): str,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up via YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tech Recuperation from config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    api = TechAPI(session)

    user_id = int(entry.data[CONF_USER_ID])
    token = str(entry.data[CONF_TOKEN])
    udid = str(entry.data[CONF_MODULE_UDID])

    # Refresh token every startup to avoid stale token issues
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    if username and password:
        try:
            auth = await api.authenticate(username, password)
            user_id = int(auth["user_id"])
            token = str(auth["token"])
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_USER_ID: user_id,
                    CONF_TOKEN: token,
                },
            )
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Could not refresh token at startup, using stored token")

    backup_store: Store[dict[str, Any]] = Store(
        hass,
        1,
        f"{DOMAIN}.{entry.entry_id}.schedule_backups",
    )

    coordinator = TechRecuperationCoordinator(
        hass=hass,
        api=api,
        user_id=user_id,
        token=token,
        udid=udid,
        username=username,
        password=password,
        backup_store=backup_store,
    )
    await coordinator.async_load_backups()
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def async_handle_set_day_schedule(call: ServiceCall) -> None:
        day_id = resolve_day_id(call.data[ATTR_DAY], dt_util.now())
        await coordinator.async_set_day_schedule(day_id, call.data[ATTR_SLOTS])

    async def async_handle_set_gear_now(call: ServiceCall) -> None:
        day_id = resolve_day_id(call.data[ATTR_DAY], dt_util.now())
        gear_raw = call.data[ATTR_GEAR]
        gear = GEAR_NAME_TO_VALUE.get(gear_raw) if isinstance(gear_raw, str) else gear_raw
        if not isinstance(gear, int):
            raise ValueError(f"Unknown gear: {gear_raw}")
        await coordinator.async_set_gear_now(day_id, gear, call.data.get("temp"))

    async def async_handle_set_gear_until(call: ServiceCall) -> None:
        day_id = resolve_day_id(call.data[ATTR_DAY], dt_util.now())
        gear_raw = call.data[ATTR_GEAR]
        gear = GEAR_NAME_TO_VALUE.get(gear_raw) if isinstance(gear_raw, str) else gear_raw
        if not isinstance(gear, int):
            raise ValueError(f"Unknown gear: {gear_raw}")
        revert_raw = call.data.get("revert_gear")
        revert: int | None = None
        if revert_raw is not None:
            revert = (
                GEAR_NAME_TO_VALUE.get(revert_raw)
                if isinstance(revert_raw, str)
                else revert_raw
            )
            if not isinstance(revert, int):
                raise ValueError(f"Unknown revert_gear: {revert_raw}")
        until_minutes = hhmm_to_minutes(call.data["until"])
        await coordinator.async_set_gear_until(
            day_id,
            gear,
            until_minutes,
            temp=call.data.get("temp"),
            revert_gear=revert,
        )

    async def async_handle_restore_day_schedule(call: ServiceCall) -> None:
        day_id = resolve_day_id(call.data[ATTR_DAY], dt_util.now())
        await coordinator.async_restore_day_schedule(day_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DAY_SCHEDULE,
        async_handle_set_day_schedule,
        schema=SET_DAY_SCHEDULE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GEAR_NOW,
        async_handle_set_gear_now,
        schema=SET_GEAR_NOW_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GEAR_UNTIL,
        async_handle_set_gear_until,
        schema=SET_GEAR_UNTIL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTORE_DAY_SCHEDULE,
        async_handle_restore_day_schedule,
        schema=RESTORE_DAY_SCHEDULE_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_SET_DAY_SCHEDULE,
                SERVICE_SET_GEAR_NOW,
                SERVICE_SET_GEAR_UNTIL,
                SERVICE_RESTORE_DAY_SCHEDULE,
            ):
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)
    return unload_ok
