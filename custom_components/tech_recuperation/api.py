"""eMODUL API client for Tech Recuperation integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class TechApiError(Exception):
    """Base exception for Tech API errors."""


class TechAuthError(TechApiError):
    """Authentication failed."""


class TechConnectionError(TechApiError):
    """Connection to API failed."""


class TechAPI:
    """Client for the eMODUL (Tech Controllers) API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._session = session

    def _headers(self, token: str) -> dict[str, str]:
        """Build request headers with auth token."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        token: str | None = None,
        json_data: dict | None = None,
    ) -> Any:
        """Make an API request."""
        url = f"{API_BASE_URL}/{path}"
        headers = self._headers(token) if token else {"Content-Type": "application/json"}

        try:
            async with self._session.request(
                method, url, headers=headers, json=json_data, timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    raise TechAuthError("Authentication failed or token expired")
                if not (200 <= resp.status < 300):
                    text = await resp.text()
                    # Truncate response body to avoid leaking sensitive data in logs/exceptions
                    safe_text = (text[:200] + "…") if len(text) > 200 else text
                    raise TechApiError(
                        f"API request failed: {resp.status} {safe_text}"
                    )
                return await resp.json()
        except TechApiError:
            raise
        except (ValueError, aiohttp.ContentTypeError) as err:
            raise TechApiError(
                f"Invalid response body: {type(err).__name__}"
            ) from err
        except aiohttp.ClientError as err:
            raise TechConnectionError(
                f"Connection error: {type(err).__name__}"
            ) from err

    # ---- Authentication ----

    async def authenticate(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """Authenticate with eMODUL and return user_id + token.

        Returns:
            {"authenticated": True, "user_id": int, "token": str}

        Raises:
            TechAuthError: If credentials are invalid.
            TechApiError: If response is missing required fields.
        """
        result = await self._request(
            "POST",
            "authentication",
            json_data={"username": username, "password": password},
        )
        if not result.get("authenticated"):
            raise TechAuthError("Invalid username or password")
        if "user_id" not in result or "token" not in result:
            raise TechApiError(
                "Authentication response missing user_id or token"
            )
        return result

    # ---- Module endpoints ----

    async def get_modules(
        self, user_id: int, token: str
    ) -> list[dict[str, Any]]:
        """List all modules for a user."""
        result = await self._request(
            "GET", f"users/{user_id}/modules", token=token
        )
        # The API returns a list directly for this endpoint
        if isinstance(result, list):
            return result
        return result.get("elements", [result])

    async def get_module_data(
        self, user_id: int, token: str, udid: str
    ) -> dict[str, Any]:
        """Get full module data (tiles, zones, etc.)."""
        return await self._request(
            "GET", f"users/{user_id}/modules/{udid}", token=token
        )

    # ---- Menu endpoints ----

    async def get_menu(
        self, user_id: int, token: str, udid: str
    ) -> dict[str, Any]:
        """Get the user menu (MU) with schedules and controls."""
        return await self._request(
            "GET", f"users/{user_id}/modules/{udid}/menu/MU", token=token
        )

    async def set_schedule(
        self,
        user_id: int,
        token: str,
        udid: str,
        element_id: int,
        slots: list[dict[str, int]],
    ) -> dict[str, Any]:
        """Write a day's schedule.

        Args:
            element_id: The menu element ID for the day (e.g., 10000 for Monday).
            slots: List of 5 slot dicts, each with keys:
                   start (int), end (int), interval (int), temp (int).
                   start/end are minutes since midnight (0-1439).
                   interval is gear (0-3).
                   temp is degrees C (10-30).
        """
        _LOGGER.debug(
            "Setting schedule for element %s (%d slots)", element_id, len(slots)
        )
        return await self._request(
            "POST",
            f"users/{user_id}/modules/{udid}/menu/MU/ido/{element_id}",
            token=token,
            json_data={"universal_schedule": slots},
        )

    async def set_control_value(
        self,
        user_id: int,
        token: str,
        udid: str,
        menu_id: int,
        value: int,
    ) -> dict[str, Any]:
        """Set a control value (on/off, number, etc.).

        Args:
            menu_id: The menu element ID (e.g., 1049 for on/off).
            value: The value to set.
        """
        _LOGGER.debug("Setting menu %s to value %s", menu_id, value)
        return await self._request(
            "POST",
            f"users/{user_id}/modules/{udid}/menu/MU/ido/{menu_id}",
            token=token,
            json_data={"value": value},
        )
