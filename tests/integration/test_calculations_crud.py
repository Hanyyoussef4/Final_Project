import pytest
import httpx
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER = ["/auth/register", "/api/auth/register"]
LOGIN_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_FORM = ["/auth/token", "/api/auth/token"]
CALC = ["/calculations", "/api/calculations"]

async def _reg(ac,u,p):
    full = {"first_name":"CRUD","last_name":"User","email":f"{u}@e.com","username":u,"password":p,"confirm_password":p}
    for pth in REGISTER:
        r = await ac.post(pth, json=full)
        if r.status_code in (200,201,409): return

async def _login(ac,u,p):
    for pth in LOGIN_JSON:
        r = await ac.post(pth, json={"username":u,"password":p})
        if r.status_code==200 and "access_token" in r.json(): return r.json()["access_token"]
    for pth in LOGIN_FORM:
        r = await ac.post(pth, data={"username":u,"password":p})
        if r.status_code==200 and "access_token" in r.json(): return r.json()["access_token"]
    raise AssertionError("login failed")

def _bearer(t): return {"Authorization": f"Bearer {t}"}

async def _first_working(ac, paths):
    for p in paths:
        # probe GET list (authorized) for existence
        r = await ac.get(p, headers=_bearer("x")) if False else None
    return paths[0]  # we will just try them in order for POST/GET/PUT/DELETE

async def test_crud_roundtrip():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        u,p = "crud_user","Abcd1234!"
        await _reg(ac,u,p)
        tok = await _login(ac,u,p)
        h = _bearer(tok)

        # CREATE
        post_url = CALC[0]
        r = await ac.post(post_url, json={"type":"Addition","inputs":[5,7]}, headers=h)
        assert r.status_code in (200,201), r.text
        obj = r.json()
        calc_id = obj.get("id") or obj.get("calc_id") or obj.get("id_")

        # LIST
        r = await ac.get(post_url, headers=h)
        assert r.status_code == 200

        # READ
        r = await ac.get(f"{post_url}/{calc_id}", headers=h)
        assert r.status_code == 200

        # UPDATE
        r = await ac.put(f"{post_url}/{calc_id}", json={"type":"Subtraction","inputs":[10,3]}, headers=h)
        assert r.status_code in (200,202)

        # DELETE
        r = await ac.delete(f"{post_url}/{calc_id}", headers=h)
        assert r.status_code in (200,202,204)
