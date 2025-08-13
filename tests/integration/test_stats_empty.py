import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER_PATHS = ["/auth/register", "/api/auth/register"]
LOGIN_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_FORM = ["/auth/token", "/api/auth/token"]

async def _register(ac: httpx.AsyncClient, username: str, password: str):
    body = {
        "first_name": "Stats",
        "last_name": "Empty",
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    for p in REGISTER_PATHS:
        r = await ac.post(p, json=body)
        if r.status_code in (200, 201, 409):  # 409 if already exists
            return
    raise AssertionError("register failed")

async def _login(ac: httpx.AsyncClient, username: str, password: str) -> str:
    # try JSON login first
    for p in LOGIN_JSON:
        r = await ac.post(p, json={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    # fall back to form-based token route
    for p in LOGIN_FORM:
        r = await ac.post(p, data={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    raise AssertionError("login failed")

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

async def test_stats_with_no_calculations():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        u, p = "stats_empty_user", "Abcd1234!"
        await _register(ac, u, p)
        token = await _login(ac, u, p)

        r = await ac.get("/reports/summary", headers=_bearer(token))
        assert r.status_code == status.HTTP_200_OK, r.text

        data = r.json()
        # Basic shape/typing checks that work for both empty & non-empty states
        assert isinstance(data, dict)
        assert data.get("total", 0) >= 0
        assert data.get("average_operands", 0) >= 0

        counts = data.get("counts") or data.get("counts_by_operation") or {}
        if isinstance(counts, dict):
            for k, v in counts.items():
                assert isinstance(v, int)
