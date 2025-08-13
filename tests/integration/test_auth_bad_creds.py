import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER = ["/auth/register", "/api/auth/register"]
LOGIN_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_FORM = ["/auth/token", "/api/auth/token"]

async def _register(ac, u, p):
    body = {
        "first_name": "Bad", "last_name": "Creds",
        "email": f"{u}@example.com",
        "username": u, "password": p, "confirm_password": p
    }
    for path in REGISTER:
        r = await ac.post(path, json=body)
        if r.status_code in (200, 201, 409):
            return
    raise AssertionError("register failed")

async def test_login_form_wrong_password_and_missing_fields():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        u, p = "form_user", "Abcd1234!"
        await _register(ac, u, p)

        # wrong password -> unauthorized
        for path in LOGIN_FORM:
            r = await ac.post(path, data={"username": u, "password": "wrong"})
            if r.status_code != status.HTTP_404_NOT_FOUND:
                assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # missing fields -> 422
        for path in LOGIN_FORM:
            r = await ac.post(path, data={"username": u})  # no password
            if r.status_code != status.HTTP_404_NOT_FOUND:
                assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text
