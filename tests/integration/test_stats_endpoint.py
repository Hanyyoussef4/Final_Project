# tests/integration/test_stats_endpoint.py
import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

REGISTER_PATHS = ["/auth/register", "/api/auth/register"]
LOGIN_PATHS_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_PATHS_FORM = ["/auth/token", "/api/auth/token"]

# Try these for reading stats (first 200 wins)
STATS_ENDPOINTS = [
    "/reports/summary",
    "/stats",
    "/calculations/stats",
    "/dashboard/stats",
]

# Try both calculation endpoints in case your app is mounted under /api
CALC_POST_CANDIDATES = ["/calculations", "/api/calculations"]


async def _register(ac: httpx.AsyncClient, username="apiuser", password="Abcd1234!"):
    body_full = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    body_min = {"username": username, "password": password}
    last = None
    for path in REGISTER_PATHS:
        for body in (body_full, body_min):
            r = await ac.post(path, json=body)
            last = r
            if r.status_code in (200, 201, 409):
                return
    raise AssertionError(
        f"Register failed on all endpoints. Last: {getattr(last,'status_code',None)} {getattr(last,'text','')}"
    )


async def _login(ac: httpx.AsyncClient, username="apiuser", password="Abcd1234!"):
    # JSON first
    for path in LOGIN_PATHS_JSON:
        r = await ac.post(path, json={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    # Form fallback
    for path in LOGIN_PATHS_FORM:
        r = await ac.post(path, data={"username": username, "password": password})
        if r.status_code == 200 and "access_token" in r.json():
            return r.json()["access_token"]
    raise AssertionError("Login failed on known endpoints (no access_token returned)")


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_calc(ac: httpx.AsyncClient, headers, calc_type: str, inputs: list[int | float]):
    # Your API expects {"type": ..., "inputs": ...}
    payload = {"type": calc_type, "inputs": inputs}
    last = None
    for path in CALC_POST_CANDIDATES:
        r = await ac.post(path, json=payload, headers=headers)
        last = r
        if r.status_code in (201, 200):
            return
    raise AssertionError(
        f"Create calculation failed. Last: {getattr(last,'request',None).url if last else 'n/a'} "
        f"-> {getattr(last,'status_code',None)} {getattr(last,'text','')}"
    )


async def _get_stats(ac: httpx.AsyncClient, headers):
    last = None
    for path in STATS_ENDPOINTS:
        r = await ac.get(path, headers=headers)
        last = r
        if r.status_code == 200:
            return r.json()
    raise AssertionError(
        f"Stats endpoint not found/200. Last tried: {getattr(last,'request',None).url if last else 'n/a'} "
        f"-> {getattr(last,'status_code',None)} {getattr(last,'text','')}"
    )


async def test_stats_aggregate_counts_and_average():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # auth
        await _register(ac, "stats_user", "Abcd1234!")
        token = await _login(ac, "stats_user", "Abcd1234!")
        headers = _bearer(token)

        # seed calculations (schema lowercases internally, "Addition"/"Division" are fine)
        await _create_calc(ac, headers, "Addition", [2, 7])      # 2 operands
        await _create_calc(ac, headers, "Addition", [1, 2, 3])   # 3 operands
        await _create_calc(ac, headers, "Division", [10, 5])     # 2 operands

        stats = await _get_stats(ac, headers)

        # Basic shape checks
        assert isinstance(stats, dict), stats

        # Total should be >= 3 after seeding
        total = stats.get("total") or stats.get("count") or stats.get("total_calculations")
        assert isinstance(total, int) and total >= 3, f"bad total: {total}"

        # Average operands should be >= 2.0 ((2+3+2)/3 = 2.33)
        avg = stats.get("average_operands") or stats.get("avg_operands") or stats.get("average")
        assert isinstance(avg, (int, float)) and avg >= 2.0, f"bad average: {avg}"

        # Operation counts
        counts = stats.get("counts_by_operation") or stats.get("counts") or {}
        k = {str(k).lower(): v for k, v in counts.items()} if isinstance(counts, dict) else {}
        assert k.get("addition", 0) >= 2, f"addition count bad: {counts}"
        assert k.get("division", 0) >= 1, f"division count bad: {counts}"
