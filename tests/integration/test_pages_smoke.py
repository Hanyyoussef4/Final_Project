import pytest
import httpx
from app.main import app

pytestmark = pytest.mark.asyncio

async def test_public_pages_load():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        for path in ("/", "/openapi.json", "/docs", "/redoc", "/login", "/register", "/health"):
            r = await ac.get(path)
            assert r.status_code == 200, f"{path} -> {r.status_code} {getattr(r,'text','')[:200]}"
