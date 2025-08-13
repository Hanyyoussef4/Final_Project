import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER_PATHS = ["/auth/register", "/api/auth/register"]
LOGIN_PATHS_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_PATHS_FORM = ["/auth/token", "/api/auth/token"]
PROTECTED_TRY = ["/reports/summary", "/api/calculations", "/calculations"]

async def _register(ac, username, password):
    full = {
        "first_name": "Edge", "last_name": "Case",
        "email": f"{username}@example.com",
        "username": username, "password": password, "confirm_password": password
    }
    for p in REGISTER_PATHS:
        r = await ac.post(p, json=full)
        if r.status_code in (200,201,409):
            return
    raise AssertionError("register failed")

async def _login(ac, username, password):
    for p in LOGIN_PATHS_JSON:
        r = await ac.post(p, json={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    for p in LOGIN_PATHS_FORM:
        r = await ac.post(p, data={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    raise AssertionError("login failed")

async def _pick_protected(ac):
    for p in PROTECTED_TRY:
        r = await ac.get(p)
        if r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422):
            return p
    return PROTECTED_TRY[-1]

def _bearer(tok): return {"Authorization": f"Bearer {tok}"}

async def test_auth_dependency_edge_paths():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        u, pw = "edge_user", "Abcd1234!"
        await _register(ac, u, pw)
        tok = await _login(ac, u, pw)
        protected = await _pick_protected(ac)

        # wrong scheme -> "invalid auth scheme" branch
        r = await ac.get(protected, headers={"Authorization": f"Token {tok}"})
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # malformed header -> "credentials not provided / malformed"
        r = await ac.get(protected, headers={"Authorization": "Bearer"})
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # very short/tampered token
        r = await ac.get(protected, headers=_bearer(tok[:-10]))
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
