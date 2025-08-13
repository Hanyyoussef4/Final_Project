import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER = ["/auth/register", "/api/auth/register"]

async def test_register_mismatched_confirm_and_bad_email():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # mismatched confirm_password -> 422
        body = {
            "first_name": "Val", "last_name": "Mismatch",
            "email": "mismatch@example.com",
            "username": "val_user_mis",
            "password": "Abcd1234!", "confirm_password": "Abcd1234!!",
        }
        seen_one = False
        for path in REGISTER:
            r = await ac.post(path, json=body)
            if r.status_code != status.HTTP_404_NOT_FOUND:
                seen_one = True
                assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text
        assert seen_one, "no /auth register endpoint found"

        # invalid email -> 422
        body_bad_email = {
            "first_name": "Val", "last_name": "Email",
            "email": "not-an-email",
            "username": "val_user_bademail",
            "password": "Abcd1234!", "confirm_password": "Abcd1234!",
        }
        for path in REGISTER:
            r = await ac.post(path, json=body_bad_email)
            if r.status_code != status.HTTP_404_NOT_FOUND:
                assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text
