"""Unit tests for TechAPI request handling and payload shaping."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.tech_recuperation.api import (
    TechAPI,
    TechApiError,
    TechAuthError,
)


class _FakeResponse:
    def __init__(self, status: int, payload=None, text: str = "") -> None:
        self.status = status
        self._payload = payload if payload is not None else {}
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._payload

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.last_request = None

    def request(self, method, url, headers=None, json=None):
        self.last_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
        }
        return self._response


@pytest.mark.asyncio
async def test_request_raises_auth_error_on_401() -> None:
    """401 responses are mapped to auth failures."""
    api = TechAPI(_FakeSession(_FakeResponse(status=401)))
    with pytest.raises(TechAuthError):
        await api._request("GET", "users/1/modules", token="token")


@pytest.mark.asyncio
async def test_request_raises_api_error_on_non_200() -> None:
    """Non-200 responses raise TechApiError with response text."""
    api = TechAPI(_FakeSession(_FakeResponse(status=500, text="boom")))
    with pytest.raises(TechApiError, match="500"):
        await api._request("GET", "users/1/modules", token="token")


@pytest.mark.asyncio
async def test_get_modules_handles_list_and_object_shapes() -> None:
    """get_modules handles both raw list and object payloads."""
    list_api = TechAPI(_FakeSession(_FakeResponse(status=200, payload=[{"udid": "a"}])))
    obj_api = TechAPI(
        _FakeSession(_FakeResponse(status=200, payload={"elements": [{"udid": "b"}]}))
    )

    assert await list_api.get_modules(1, "token") == [{"udid": "a"}]
    assert await obj_api.get_modules(1, "token") == [{"udid": "b"}]


@pytest.mark.asyncio
async def test_set_schedule_posts_universal_schedule_payload() -> None:
    """set_schedule POST includes expected universal_schedule body."""
    session = _FakeSession(_FakeResponse(status=200, payload={"ok": True}))
    api = TechAPI(session)
    slots = [{"start": 0, "end": 1439, "interval": 1, "temp": 20}]

    await api.set_schedule(1, "token", "udid", 10000, slots)

    assert session.last_request is not None
    assert session.last_request["method"] == "POST"
    assert session.last_request["json"] == {"universal_schedule": slots}
