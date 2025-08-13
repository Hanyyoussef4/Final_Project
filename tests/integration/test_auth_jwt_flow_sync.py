# tests/integration/test_auth_jwt_flow_sync.py
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app
import time

client = TestClient(app)

REGISTER_PATH = "/auth/register"
LOGIN_JSON_PATH = "/auth/login"   # JSON login
LOGIN_FORM_PATH = "/auth/token"   # OAuth2 form login

# Candidate protected endpoints in your app (from your route dump)
CANDIDATE_GETS = [
    "/reports/summary",   # likely protected
    "/calculations",      # may be public in your app, we’ll detect & skip if so
]
CANDIDATE_POSTS = [
    ("/calculations", {"operation": "Addition", "numbers": [1, 2]}),
]

def _register(username: str, password: str):
    uniq = int(time.time() * 1000)
    body = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}_{uniq}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    r = client.post(REGISTER_PATH, json=body)
    assert r.status_code in (200, 201, 409), f"{REGISTER_PATH} -> {r.status_code} {r.text}"

def _login(username: str, password: str) -> str:
    # Try JSON login first
    r = client.post(LOGIN_JSON_PATH, json={"username": username, "password": password})
    if r.status_code == 200 and "access_token" in r.json():
        return r.json()["access_token"]
    # Fallback: form login
    r = client.post(LOGIN_FORM_PATH, data={"username": username, "password": password})
    assert r.status_code == 200 and "access_token" in r.json(), r.text
    return r.json()["access_token"]

def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def _find_protected_route():
    # Prefer a GET that returns 401/403/422 without token
    for path in CANDIDATE_GETS:
        r = client.get(path)  # no Authorization
        if r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422):
            return ("GET", path, None)

    # Otherwise, try a POST that rejects missing token
    for path, payload in CANDIDATE_POSTS:
        r = client.post(path, json=payload)
        if r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422):
            return ("POST", path, payload)

    raise AssertionError(
        "No protected route found. Checked GETS="
        f"{CANDIDATE_GETS} and POSTS={[p for p,_ in CANDIDATE_POSTS]}. "
        "If all are public in your app, add one here that requires auth."
    )

def _call(method: str, path: str, token: str | None, payload: dict | None):
    headers = _bearer(token) if token else None
    if method == "GET":
        return client.get(path, headers=headers)
    else:
        return client.post(path, json=payload, headers=headers)

def test_jwt_allows_access_and_invalid_is_blocked():
    username, password = "jwt_sync_user", "Abcd1234!"
    _register(username, password)
    token = _login(username, password)

    method, path, payload = _find_protected_route()

    # Valid token -> OK
    r = _call(method, path, token, payload)
    assert r.status_code == status.HTTP_200_OK, f"{method} {path} not accessible with valid token; got {r.status_code} {r.text}"

    # Missing token -> blocked
    r = _call(method, path, None, payload)
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 422), f"Expected unauthorized without token on {method} {path}, got {r.status_code}"

    # Tampered token -> blocked (signature invalid)
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")
    r = _call(method, path, bad, payload)
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN), f"Expected failure with bad token on {method} {path}, got {r.status_code}"
