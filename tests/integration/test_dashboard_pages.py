import pytest
import httpx
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER = ["/auth/register", "/api/auth/register"]
LOGIN_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_FORM = ["/auth/token", "/api/auth/token"]
CALC_POST_CANDIDATES = ["/calculations", "/api/calculations"]

async def _register(ac, u, p):
    body = {
        "first_name": "Dash", "last_name": "Board",
        "email": f"{u}@example.com",
        "username": u, "password": p, "confirm_password": p
    }
    for path in REGISTER:
        r = await ac.post(path, json=body)
        if r.status_code in (200, 201, 409):
            return
    raise AssertionError("register failed")

async def _login(ac, u, p):
    for path in LOGIN_JSON:
        r = await ac.post(path, json={"username": u, "password": p})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    for path in LOGIN_FORM:
        r = await ac.post(path, data={"username": u, "password": p})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    raise AssertionError("login failed")

def _bearer(tok): return {"Authorization": f"Bearer {tok}"}

async def _create_calc(ac, headers, typ, inputs):
    for path in CALC_POST_CANDIDATES:
        r = await ac.post(path, json={"type": typ, "inputs": inputs}, headers=headers)
        if r.status_code in (200, 201):
            return r.json()
    raise AssertionError("create calculation failed")

async def test_dashboard_pages_render_with_auth():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        u, p = "dash_user", "Abcd1234!"
        await _register(ac, u, p)
        tok = await _login(ac, u, p)
        h = _bearer(tok)

        obj = await _create_calc(ac, h, "Addition", [2, 5])
        calc_id = obj.get("id") or obj.get("calc_id") or obj.get("id_")

        # These three routes exist in your app and hit a bunch of main.py lines
        for path in ("/dashboard", f"/dashboard/view/{calc_id}", f"/dashboard/edit/{calc_id}"):
            r = await ac.get(path, headers=h)
            assert r.status_code == 200, f"{path} -> {r.status_code}"
