# tests/e2e/test_ui_bread.py

import httpx
import pytest
from typing import List

API = "http://localhost:8000"

TEST_USER = {
    "username": "hy326",                 # keep in sync with what you used in Swagger/UI
    "email": "hy326@njit.edu",
    "first_name": "Hany",
    "last_name": "Youssef",
    "password": "Abcd1234!",             # must satisfy your API’s password policy
    "confirm_password": "Abcd1234!",
}


def _calc_result(op: str, inputs: List[float]) -> float:
    """Small helper to compute expected results client-side."""
    if op == "addition":
        return float(sum(inputs))
    if op == "multiplication":
        res = 1.0
        for n in inputs:
            res *= float(n)
        return res
    raise ValueError(f"Unsupported op '{op}' used in test.")


def ensure_user_and_get_token() -> str:
    """
    Return "Bearer <token>" for TEST_USER.

    Strategy:
      1) Try to get a token first (user may already exist).
      2) If that fails, attempt to register. Treat any "already exists"
         response as OK regardless of status code.
      3) Request a token again.
    """
    with httpx.Client(timeout=20.0) as client:
        # 1) Try to login first
        form = {
            "grant_type": "password",
            "username": TEST_USER["username"],
            "password": TEST_USER["password"],
            "scope": "",
            "client_id": "",
            "client_secret": "",
        }
        t = client.post(
            f"{API}/auth/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if t.status_code == 200:
            return f"Bearer {t.json()['access_token']}"

        # 2) Try to register
        r = client.post(f"{API}/auth/register", json=TEST_USER)
        if r.status_code not in (200, 201):
            # Accept any 'already exist' detail as OK (400/409/422, etc.)
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = r.text
            if "already exist" not in str(detail).lower():
                raise AssertionError(f"Register failed: {r.status_code} {r.text}")

        # 3) Fetch token again
        t = client.post(
            f"{API}/auth/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert t.status_code == 200, f"Token failed: {t.status_code} {t.text}"
        return f"Bearer {t.json()['access_token']}"


def auth_headers() -> dict:
    return {"Authorization": ensure_user_and_get_token()}


@pytest.mark.e2e
def test_browse_list():
    """
    Browse (READ all) – should return 200 and a JSON list for the current user.
    """
    with httpx.Client(timeout=20.0) as client:
        g = client.get(f"{API}/calculations", headers=auth_headers())
        assert g.status_code == 200, f"GET /calculations failed: {g.status_code} {g.text}"
        data = g.json()
        assert isinstance(data, list), "Expected list of calculations"


@pytest.mark.e2e
def test_create_read_edit_delete_flow():
    """
    Full BREAD happy-path:
      - Create a multiplication calculation [3, 7]
      - Read it back
      - Edit (update inputs to [2, 3, 5] – keep same type)
      - Read again and check updated result
      - Delete
      - Confirm it’s gone
    """
    op = "multiplication"
    inputs_create = [3, 7]
    expected_create = _calc_result(op, inputs_create)

    with httpx.Client(timeout=20.0) as client:
        headers = {**auth_headers(), "Accept": "application/json"}

        # CREATE
        c = client.post(
            f"{API}/calculations",
            json={"type": op, "inputs": inputs_create},
            headers=headers,
        )
        assert c.status_code == 201, f"Create failed: {c.status_code} {c.text}"
        created = c.json()
        calc_id = created["id"]
        assert created["type"] == op
        assert created["inputs"] == inputs_create
        assert float(created["result"]) == pytest.approx(expected_create)

        # READ (by id)
        g = client.get(f"{API}/calculations/{calc_id}", headers=headers)
        assert g.status_code == 200, f"Get failed: {g.status_code} {g.text}"
        got = g.json()
        assert got["id"] == calc_id
        assert got["inputs"] == inputs_create
        assert float(got["result"]) == pytest.approx(expected_create)

        # UPDATE (keep type, change inputs)
        inputs_update = [2, 3, 5]
        expected_update = _calc_result(op, inputs_update)
        u = client.put(
            f"{API}/calculations/{calc_id}",
            json={"type": op, "inputs": inputs_update},
            headers=headers,
        )
        assert u.status_code in (200, 204), f"Update failed: {u.status_code} {u.text}"

        # READ again to confirm updated values
        g2 = client.get(f"{API}/calculations/{calc_id}", headers=headers)
        assert g2.status_code == 200, f"Get after update failed: {g2.status_code} {g2.text}"
        after = g2.json()
        assert after["id"] == calc_id
        assert after["inputs"] == inputs_update
        assert float(after["result"]) == pytest.approx(expected_update)

        # DELETE
        d = client.delete(f"{API}/calculations/{calc_id}", headers=headers)
        assert d.status_code in (200, 204), f"Delete failed: {d.status_code} {d.text}"

        # Confirm gone
        g3 = client.get(f"{API}/calculations/{calc_id}", headers=headers)
        assert g3.status_code == 404, f"Expected 404 after delete, got {g3.status_code} {g3.text}"


@pytest.mark.e2e
def test_invalid_input_validation():
    """
    Negative scenarios:
      - Unauthorized create should return 401
      - Invalid inputs should produce 422 (or 400 depending on implementation)
    """
    with httpx.Client(timeout=20.0) as client:
        # Unauthorized
        r = client.post(
            f"{API}/calculations",
            json={"type": "addition", "inputs": [1, 2]},
        )
        assert r.status_code == 401, f"Expected 401 unauthorized, got {r.status_code} {r.text}"

        # Bad inputs (non-numeric, or less than 2 numbers)
        headers = {**auth_headers(), "Accept": "application/json"}

        # Non-numeric values
        b1 = client.post(
            f"{API}/calculations",
            json={"type": "addition", "inputs": ["x", "y"]},
            headers=headers,
        )
        assert b1.status_code in (400, 422), f"Expected 400/422, got {b1.status_code} {b1.text}"

        # Not enough numbers
        b2 = client.post(
            f"{API}/calculations",
            json={"type": "addition", "inputs": [5]},
            headers=headers,
        )
        assert b2.status_code in (400, 422), f"Expected 400/422, got {b2.status_code} {b2.text}"
