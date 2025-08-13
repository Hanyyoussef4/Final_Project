import pytest
import httpx
from datetime import datetime, timedelta, timezone
from jose import jwt as jose_jwt
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

# Try to read secret/algorithm from your settings; fall back to sane defaults
try:
    from app.core.config import settings
    SECRET = getattr(settings, "SECRET_KEY", None) \
          or getattr(settings, "JWT_SECRET_KEY", None) \
          or getattr(settings, "JWT_SECRET", None) \
          or "secret"
    ALG = getattr(settings, "ALGORITHM", None) \
       or getattr(settings, "JWT_ALGORITHM", None) \
       or "HS256"
except Exception:
    SECRET, ALG = "secret", "HS256"

PROTECTED_ENDPOINTS = ["/calculations", "/api/calculations", "/reports/summary"]


async def _first_protected(ac: httpx.AsyncClient) -> str:
    """Pick the first working protected endpoint (one that returns 401/403 when unauth)."""
    for p in PROTECTED_ENDPOINTS:
        r = await ac.get(p)
        if r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422):
            return p
    # Fallback to calculations – your app has it
    return "/calculations"


def _bearer(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


async def test_jwt_error_paths_block_access():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        protected = await _first_protected(ac)

        # 1) Wrong secret -> invalid signature branch
        bad_secret_tok = jose_jwt.encode(
            {"sub": "some-user", "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=5)},
            "WRONG_SECRET", algorithm=ALG
        )
        r = await ac.get(protected, headers=_bearer(bad_secret_tok))
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # 2) Expired token -> expired branch
        expired_tok = jose_jwt.encode(
            {"sub": "some-user", "exp": datetime.now(tz=timezone.utc) - timedelta(minutes=1)},
            SECRET, algorithm=ALG
        )
        r = await ac.get(protected, headers=_bearer(expired_tok))
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # 3) Missing "sub" claim -> invalid claims branch
        missing_sub_tok = jose_jwt.encode(
            {"exp": datetime.now(tz=timezone.utc) + timedelta(minutes=5)},
            SECRET, algorithm=ALG
        )
        r = await ac.get(protected, headers=_bearer(missing_sub_tok))
        assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
