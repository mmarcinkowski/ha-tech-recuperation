"""Config flow for Tech Recuperation integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TechAPI, TechApiError, TechAuthError, TechConnectionError
from .const import CONF_MODULE_NAME, CONF_MODULE_UDID, CONF_TOKEN, CONF_USER_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class TechRecuperationConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for Tech Recuperation."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_id: int | None = None
        self._token: str | None = None
        self._username: str | None = None
        self._password: str | None = None
        self._modules: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step: credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            api = TechAPI(session)

            try:
                result = await api.authenticate(
                    self._username, self._password
                )
                self._user_id = result["user_id"]
                self._token = result["token"]
            except TechAuthError:
                errors["base"] = "invalid_auth"
            except TechConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"

            if not errors:
                # Fetch modules for selection
                try:
                    self._modules = await api.get_modules(
                        self._user_id, self._token
                    )
                except TechAuthError:
                    errors["base"] = "invalid_auth"
                except TechConnectionError:
                    errors["base"] = "cannot_connect"
                except TechApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Failed to fetch modules")
                    errors["base"] = "unknown"

            if not errors:
                if len(self._modules) == 1:
                    # Auto-select single module
                    module = self._modules[0]
                    return await self._create_entry(module)
                if len(self._modules) > 1:
                    return await self.async_step_select_module()
                return self.async_abort(reason="no_modules")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_module(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle module selection when multiple modules exist."""
        if user_input is not None:
            udid = user_input[CONF_MODULE_UDID]
            module = next(
                (m for m in self._modules if str(m.get("udid")) == udid),
                None,
            )
            if module is None:
                return self.async_abort(reason="unknown")
            return await self._create_entry(module)

        module_options = {
            str(m.get("udid", "")): m.get("name", m.get("udid", "Unknown"))
            for m in self._modules
            if m.get("udid")
        }

        return self.async_show_form(
            step_id="select_module",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODULE_UDID): vol.In(module_options),
                }
            ),
        )

    async def _create_entry(
        self, module: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry after setting unique id."""
        udid = str(module.get("udid", ""))
        name = module.get("name", "Tech Recuperation")

        await self.async_set_unique_id(udid)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_USER_ID: self._user_id,
                CONF_TOKEN: self._token,
                CONF_MODULE_UDID: udid,
                CONF_MODULE_NAME: name,
            },
        )
