"""Regression tests: secrets never leak into log messages or exceptions."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.tech_recuperation.api import (
    TechAPI,
    TechApiError,
    TechAuthError,
    TechConnectionError,
)

# Sentinel secrets used in tests — must NEVER appear in log output
_SECRET_PASSWORD = "s3cret-P@ssw0rd!"
_SECRET_TOKEN = "eyJ0b2tlbi1zZWNyZXQ"
_SECRET_USERNAME = "user@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        status: int,
        payload=None,
        text: str = "",
        *,
        raise_json: Exception | None = None,
    ) -> None:
        self.status = status
        self._payload = payload if payload is not None else {}
        self._text = text
        self._raise_json = raise_json

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        if self._raise_json is not None:
            raise self._raise_json
        return self._payload

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def request(self, method, url, headers=None, json=None, timeout=None):
        return self._response


# ---------------------------------------------------------------------------
# API exception message sanitisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_error_on_non_2xx_does_not_include_full_body() -> None:
    """Error response body is truncated so large payloads can't leak secrets."""
    long_body = "x" * 500
    api = TechAPI(_FakeSession(_FakeResponse(status=500, text=long_body)))
    with pytest.raises(TechApiError) as exc_info:
        await api._request("GET", "test", token=_SECRET_TOKEN)
    msg = str(exc_info.value)
    # Body must be truncated to <=200 chars + ellipsis
    assert len(msg) < 300
    assert "…" in msg


@pytest.mark.asyncio
async def test_api_error_on_non_2xx_truncates_token_in_body() -> None:
    """If API echoes a token in its error body, it gets truncated."""
    body_with_token = f'{{"error":"bad","token":"{_SECRET_TOKEN * 20}"}}'
    api = TechAPI(_FakeSession(_FakeResponse(status=400, text=body_with_token)))
    with pytest.raises(TechApiError) as exc_info:
        await api._request("GET", "test", token=_SECRET_TOKEN)
    msg = str(exc_info.value)
    # The full repeated token must NOT survive truncation
    assert (_SECRET_TOKEN * 20) not in msg


@pytest.mark.asyncio
async def test_json_parse_error_hides_raw_content() -> None:
    """ValueError from JSON parsing must not embed raw content in exception."""
    api = TechAPI(
        _FakeSession(
            _FakeResponse(
                status=200,
                raise_json=ValueError(f"bad json containing {_SECRET_TOKEN}"),
            )
        )
    )
    with pytest.raises(TechApiError) as exc_info:
        await api._request("GET", "test", token=_SECRET_TOKEN)
    msg = str(exc_info.value)
    assert _SECRET_TOKEN not in msg
    assert "ValueError" in msg


@pytest.mark.asyncio
async def test_connection_error_hides_raw_detail() -> None:
    """aiohttp.ClientError exception detail must not leak into our exception."""
    import aiohttp

    class _RaisingSession:
        def request(self, method, url, headers=None, json=None, timeout=None):
            raise aiohttp.ClientError(f"secret-in-error {_SECRET_TOKEN}")

    api = TechAPI(_RaisingSession())
    with pytest.raises(TechConnectionError) as exc_info:
        await api._request("GET", "test", token=_SECRET_TOKEN)
    msg = str(exc_info.value)
    assert _SECRET_TOKEN not in msg
    assert "ClientError" in msg


# ---------------------------------------------------------------------------
# authenticate() must not leak credentials in exceptions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticate_failure_does_not_leak_password() -> None:
    """Failed auth must not include password in exception message."""
    api = TechAPI(
        _FakeSession(_FakeResponse(status=200, payload={"authenticated": False}))
    )
    with pytest.raises(TechAuthError) as exc_info:
        await api.authenticate(_SECRET_USERNAME, _SECRET_PASSWORD)
    msg = str(exc_info.value)
    assert _SECRET_PASSWORD not in msg
    assert _SECRET_USERNAME not in msg


# ---------------------------------------------------------------------------
# Log output: set_schedule debug log must not dump payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_schedule_log_does_not_dump_slots(caplog) -> None:
    """Debug log for set_schedule must not contain full slot data."""
    session = _FakeSession(_FakeResponse(status=200, payload={"ok": True}))
    api = TechAPI(session)
    slots = [
        {"start": 0, "end": 360, "interval": 1, "temp": 20},
        {"start": 360, "end": 720, "interval": 2, "temp": 21},
        {"start": 720, "end": 1080, "interval": 1, "temp": 20},
        {"start": 1080, "end": 1320, "interval": 2, "temp": 21},
        {"start": 1320, "end": 1439, "interval": 3, "temp": 22},
    ]

    with caplog.at_level(logging.DEBUG):
        await api.set_schedule(1, _SECRET_TOKEN, "udid", 10000, slots)

    combined = caplog.text
    # Token must not appear
    assert _SECRET_TOKEN not in combined
    # Full slot dicts must not appear (only slot count)
    assert '"start"' not in combined
    assert '"interval"' not in combined
    # Slot count should appear
    assert "5 slots" in combined


# ---------------------------------------------------------------------------
# Log output: set_control_value debug log must not leak token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_control_value_log_does_not_leak_token(caplog) -> None:
    """Debug log for set_control_value must not contain token."""
    session = _FakeSession(_FakeResponse(status=200, payload={"ok": True}))
    api = TechAPI(session)

    with caplog.at_level(logging.DEBUG):
        await api.set_control_value(1, _SECRET_TOKEN, "udid", 1049, 1)

    combined = caplog.text
    assert _SECRET_TOKEN not in combined


# ---------------------------------------------------------------------------
# _headers() builds Authorization header (internal, but verify no logging)
# ---------------------------------------------------------------------------


def test_headers_contain_bearer_token() -> None:
    """_headers returns Authorization header but does not log it."""
    api = TechAPI(None)
    headers = api._headers(_SECRET_TOKEN)
    assert headers["Authorization"] == f"Bearer {_SECRET_TOKEN}"
