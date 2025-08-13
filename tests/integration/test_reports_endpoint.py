import uuid
import pytest
from typing import Dict
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    # If you already have a shared `client` fixture in conftest.py, remove this and use that one.
    return TestClient(app)


def _register_user(client: TestClient, username: str, password: str) -> Dict:
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": password,
        "confirm_password": password,
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code in (201, 400), r.text  # 400 if already exists
    return r.json() if r.status_code == 201 else {}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token, "No access_token returned"
    return token


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_calc(client: TestClient, token: str, calc_type: str, inputs):
    # inputs must be a JSON array of numbers to match your API
    r = client.post(
        "/calculations",
        json={"type": calc_type, "inputs": inputs},
        headers=_auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.integration
def test_reports_summary_happy_path(client: TestClient):
    """
    Flow:
      - register user
      - login (get JWT)
      - create several calculations via API (type + inputs[])
      - fetch /reports/summary and verify structure & values
    """
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "Abcd1234!"

    _register_user(client, username, password)
    token = _login(client, username, password)

    # Create 3 calculations
    _create_calc(client, token, "addition", [1, 2, 3])     # 3 operands
    _create_calc(client, token, "subtraction", [10, 5])    # 2 operands
    _create_calc(client, token, "addition", [4, 4])        # 2 operands

    # Fetch summary
    r = client.get("/reports/summary", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    data = r.json()

    # Response shape
    assert set(data.keys()) == {
        "total_calculations",
        "counts_by_operation",
        "average_operands",
        "recent_calculations",
    }

    # Totals & counts
    assert data["total_calculations"] == 3
    assert data["counts_by_operation"].get("addition") == 2
    assert data["counts_by_operation"].get("subtraction") == 1

    # Average operands = (3 + 2 + 2) / 3 = 2.333..., rounded to 2.33 by service
    assert round(float(data["average_operands"]), 2) == 2.33

    # Recent list (newest first); we last created the [4,4] addition
    recents = data["recent_calculations"]
    assert isinstance(recents, list) and len(recents) == 3
    assert recents[0]["type"] == "addition"
    assert recents[0]["inputs"] == [4, 4]
