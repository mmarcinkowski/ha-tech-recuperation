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
    def __init__(self, status: int, payload=None, text: str = "", *, raise_json: Exception | None = None) -> None:
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
        self.last_request = None

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.last_request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        }
        return self._response


@pytest.mark.asyncio
async def test_request_raises_auth_error_on_401() -> None:
    """401 responses are mapped to auth failures."""
    api = TechAPI(_FakeSession(_FakeResponse(status=401)))
    with pytest.raises(TechAuthError):
        await api._request("GET", "users/1/modules", token="token")


@pytest.mark.asyncio
async def test_request_raises_api_error_on_non_2xx() -> None:
    """Non-2xx responses raise TechApiError with response text."""
    api = TechAPI(_FakeSession(_FakeResponse(status=500, text="boom")))
    with pytest.raises(TechApiError, match="500"):
        await api._request("GET", "users/1/modules", token="token")

    # 301 is also non-2xx
    api_301 = TechAPI(_FakeSession(_FakeResponse(status=301, text="redirect")))
    with pytest.raises(TechApiError, match="301"):
        await api_301._request("GET", "users/1/modules", token="token")


@pytest.mark.asyncio
async def test_request_accepts_2xx_range() -> None:
    """Any 2xx response is accepted without error."""
    api = TechAPI(_FakeSession(_FakeResponse(status=201, payload={"created": True})))
    result = await api._request("POST", "users/1/modules", token="token")
    assert result == {"created": True}


@pytest.mark.asyncio
async def test_request_sends_timeout() -> None:
    """Requests include the module-level timeout."""
    from custom_components.tech_recuperation.api import REQUEST_TIMEOUT
    session = _FakeSession(_FakeResponse(status=200, payload={"ok": True}))
    api = TechAPI(session)
    await api._request("GET", "users/1/modules", token="token")
    assert session.last_request["timeout"] is REQUEST_TIMEOUT


@pytest.mark.asyncio
async def test_request_raises_on_malformed_json() -> None:
    """Malformed JSON body raises TechApiError."""
    api = TechAPI(_FakeSession(_FakeResponse(status=200, raise_json=ValueError("bad json"))))
    with pytest.raises(TechApiError, match="Invalid response body"):
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


@pytest.mark.asyncio
async def test_authenticate_validates_response_fields() -> None:
    """authenticate raises TechApiError if user_id or token missing."""
    # Missing user_id
    api_no_uid = TechAPI(_FakeSession(_FakeResponse(
        status=200,
        payload={"authenticated": True, "token": "t"},
    )))
    with pytest.raises(TechApiError, match="missing user_id or token"):
        await api_no_uid.authenticate("user", "pass")

    # Missing token
    api_no_tok = TechAPI(_FakeSession(_FakeResponse(
        status=200,
        payload={"authenticated": True, "user_id": 1},
    )))
    with pytest.raises(TechApiError, match="missing user_id or token"):
        await api_no_tok.authenticate("user", "pass")


@pytest.mark.asyncio
async def test_authenticate_raises_on_bad_credentials() -> None:
    """authenticate raises TechAuthError on failed authentication."""
    api = TechAPI(_FakeSession(_FakeResponse(
        status=200,
        payload={"authenticated": False},
    )))
    with pytest.raises(TechAuthError, match="Invalid username"):
        await api.authenticate("user", "pass")


@pytest.mark.asyncio
async def test_authenticate_success() -> None:
    """authenticate returns result dict on success."""
    api = TechAPI(_FakeSession(_FakeResponse(
        status=200,
        payload={"authenticated": True, "user_id": 42, "token": "tok123"},
    )))
    result = await api.authenticate("user", "pass")
    assert result["user_id"] == 42
    assert result["token"] == "tok123"
