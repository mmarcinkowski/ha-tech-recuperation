"""Unit tests for config flow behavior."""

from __future__ import annotations

import pytest

from custom_components.tech_recuperation.config_flow import TechRecuperationConfigFlow


class _FakeApi:
    def __init__(self, auth_result=None, modules=None, auth_exc: Exception | None = None):
        self._auth_result = auth_result or {"user_id": 1, "token": "token"}
        self._modules = modules if modules is not None else []
        self._auth_exc = auth_exc

    async def authenticate(self, _username, _password):
        if self._auth_exc is not None:
            raise self._auth_exc
        return self._auth_result

    async def get_modules(self, _user_id, _token):
        return self._modules


@pytest.mark.asyncio
async def test_user_step_invalid_auth_shows_form(monkeypatch) -> None:
    """Invalid auth returns user form with invalid_auth error."""
    from custom_components.tech_recuperation import config_flow as cf
    from custom_components.tech_recuperation.api import TechAuthError

    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: None)
    monkeypatch.setattr(cf, "TechAPI", lambda _session: _FakeApi(auth_exc=TechAuthError("bad")))

    flow = TechRecuperationConfigFlow()
    flow.hass = object()
    result = await flow.async_step_user({"username": "u", "password": "p"})

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_user_step_single_module_creates_entry(monkeypatch) -> None:
    """Single module is auto-selected and creates entry."""
    from custom_components.tech_recuperation import config_flow as cf

    modules = [{"udid": "m1", "name": "Main Unit"}]
    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: None)
    monkeypatch.setattr(cf, "TechAPI", lambda _session: _FakeApi(modules=modules))

    flow = TechRecuperationConfigFlow()
    flow.hass = object()
    result = await flow.async_step_user({"username": "u", "password": "p"})

    assert result["type"] == "create_entry"
    assert result["title"] == "Main Unit"
    assert result["data"]["module_udid"] == "m1"
    assert result["data"]["username"] == "u"


@pytest.mark.asyncio
async def test_user_step_multiple_modules_moves_to_selection(monkeypatch) -> None:
    """Multiple modules lead to select_module form."""
    from custom_components.tech_recuperation import config_flow as cf

    modules = [{"udid": "m1", "name": "A"}, {"udid": "m2", "name": "B"}]
    monkeypatch.setattr(cf, "async_get_clientsession", lambda _hass: None)
    monkeypatch.setattr(cf, "TechAPI", lambda _session: _FakeApi(modules=modules))

    flow = TechRecuperationConfigFlow()
    flow.hass = object()
    result = await flow.async_step_user({"username": "u", "password": "p"})

    assert result["type"] == "form"
    assert result["step_id"] == "select_module"


@pytest.mark.asyncio
async def test_select_module_step_creates_entry() -> None:
    """Selecting a module creates an entry for that module."""
    flow = TechRecuperationConfigFlow()
    flow._username = "u"
    flow._password = "p"
    flow._user_id = 7
    flow._token = "t"
    flow._modules = [{"udid": "m1", "name": "Unit 1"}, {"udid": "m2", "name": "Unit 2"}]

    result = await flow.async_step_select_module({"module_udid": "m2"})

    assert result["type"] == "create_entry"
    assert result["title"] == "Unit 2"
    assert result["data"]["module_udid"] == "m2"
