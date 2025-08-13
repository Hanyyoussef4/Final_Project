# tests/integration/test_auth_jwt_flow.py
import pytest
import httpx
from fastapi import status
from app.main import app

pytestmark = pytest.mark.asyncio

# --- Endpoint candidates (support both /auth/... and /api/auth/...) ---
REGISTER_PATHS = ["/auth/register", "/api/auth/register"]
LOGIN_PATHS_JSON = ["/auth/login", "/api/auth/login"]
LOGIN_PATHS_FORM = ["/auth/token", "/api/auth/token"]

# Routes that SHOULD be protected (we'll auto-pick one that 401/403/422 without a token)
PROTECTED_GET_CANDIDATES = [
    "/reports/summary",
    "/calculations",
    "/api/calculations",
]

async def _register(ac: httpx.AsyncClient, username: str, password: str):
    """Try multiple register endpoints until one works (200/201/409)."""
    payload_full = {
        # Many apps require these fields; harmless if ignored by your schema
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    payload_min = {"username": username, "password": password}

    last_resp = None
    for path in REGISTER_PATHS:
        # Try full payload first, then minimal payload
        for body in (payload_full, payload_min):
            r = await ac.post(path, json=body)
            last_resp = r
            if r.status_code in (200, 201, 409):
                return
    # If we get here, registration didn’t succeed on any known path
    raise AssertionError(
        f"Register failed on all endpoints. Last response: {last_resp.status_code if last_resp else 'n/a'} {getattr(last_resp,'text','')}"
    )

async def _login(ac: httpx.AsyncClient, username: str, password: str) -> str:
    """Try JSON login endpoints, then form endpoints, return access_token."""
    # JSON-style
    for path in LOGIN_PATHS_JSON:
        r = await ac.post(path, json={"username": username, "password": password})
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            token = r.json().get("access_token")
            if token:
                return token
    # Form-style (OAuth2)
    for path in LOGIN_PATHS_FORM:
        r = await ac.post(path, data={"username": username, "password": password})
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            token = r.json().get("access_token")
            if token:
                return token
    raise AssertionError("Login failed on known endpoints (no access_token returned)")

async def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

async def _discover_protected_path(ac: httpx.AsyncClient) -> str:
    """Return a path that requires auth by checking that no-token -> 401/403/422."""
    for path in PROTECTED_GET_CANDIDATES:
        r = await ac.get(path)  # no Authorization header
        if r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422):
            return path
    # If none appear protected, fall back to one that exists and hope it’s protected in your app
    return PROTECTED_GET_CANDIDATES[0]

@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

async def test_jwt_happy_path_allows_access_to_protected_route(client):
    username, password = "jwt_user1", "Abcd1234!"
    await _register(client, username, password)
    token = await _login(client, username, password)

    protected = await _discover_protected_path(client)

    r = await client.get(protected, headers=await _auth_headers(token))
    assert r.status_code == status.HTTP_200_OK, f"{protected} -> {r.status_code} {r.text}"

async def test_missing_bearer_token_is_unauthorized(client):
    protected = await _discover_protected_path(client)
    r = await client.get(protected)  # no Authorization header
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422), (
        f"Expected unauthorized without token on {protected}, got {r.status_code}"
    )

async def test_malformed_or_tampered_token_is_unauthorized(client):
    username, password = "jwt_user2", "Abcd1234!"
    await _register(client, username, password)
    token = await _login(client, username, password)

    # Tamper token (flip last char) -> invalid signature
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")

    protected = await _discover_protected_path(client)

    r = await client.get(protected, headers=await _auth_headers(bad))
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), (
        f"Expected failure with bad token on {protected}, got {r.status_code} {r.text}"
    )
