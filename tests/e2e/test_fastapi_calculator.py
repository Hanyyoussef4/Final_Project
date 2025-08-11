from datetime import datetime, timezone
from uuid import uuid4
import pytest
import requests

from app.models.calculation import Calculation

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _parse_datetime(dt_str: str) -> datetime:
    """Helper function to parse datetime strings from API responses."""
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)

def register_and_login(api_base_url: str, user_data: dict) -> dict:
    """
    Registers a new user and logs in, returning the token response data.
    """
    reg_url = f"{api_base_url}/auth/register"
    login_url = f"{api_base_url}/auth/login"

    reg_response = requests.post(reg_url, json=user_data)
    assert reg_response.status_code == 201, f"User registration failed: {reg_response.text}"

    login_payload = {
        "username": user_data["username"],
        "password": user_data["password"],
    }
    login_response = requests.post(login_url, json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    return login_response.json()

# ---------------------------------------------------------------------------
# Health and Auth Endpoint Tests
# ---------------------------------------------------------------------------
def test_health_endpoint(api_base_url: str):
    url = f"{api_base_url}/health"
    response = requests.get(url)
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}. Response: {response.text}"
    assert response.json() == {"status": "ok"}, "Unexpected response from /health."

def test_user_registration(api_base_url: str):
    url = f"{api_base_url}/auth/register"
    # Make username/email UNIQUE per run to avoid DB integrity errors → 500
    u = uuid4().hex[:8]
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": f"alice.smith+{u}@example.com",
        "username": f"alicesmith_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 201, f"Expected 201 but got {response.status_code}. Response: {response.text}"
    data = response.json()
    for key in ["id", "username", "email", "first_name", "last_name", "is_active", "is_verified"]:
        assert key in data, f"Field '{key}' missing in registration response."
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["is_active"] is True
    assert data["is_verified"] is False

def test_user_login(api_base_url: str):
    reg_url = f"{api_base_url}/auth/register"
    login_url = f"{api_base_url}/auth/login"
    u = uuid4().hex[:8]
    test_user = {
        "first_name": "Bob",
        "last_name": "Jones",
        "email": f"bob.jones+{u}@example.com",
        "username": f"bobjones_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    reg_response = requests.post(reg_url, json=test_user)
    assert reg_response.status_code == 201, f"User registration failed: {reg_response.text}"

    login_payload = {
        "username": test_user["username"],
        "password": test_user["password"],
    }
    login_response = requests.post(login_url, json=login_payload)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"

    login_data = login_response.json()
    required_fields = {
        "access_token": str,
        "refresh_token": str,
        "token_type": str,
        "expires_at": str,
        "user_id": str,
        "username": str,
        "email": str,
        "first_name": str,
        "last_name": str,
        "is_active": bool,
        "is_verified": bool,
    }
    for field, expected_type in required_fields.items():
        assert field in login_data, f"Missing field: {field}"
        assert isinstance(login_data[field], expected_type), f"Field {field} has wrong type. Expected {expected_type}, got {type(login_data[field])}"
    assert login_data["token_type"].lower() == "bearer"
    assert len(login_data["access_token"]) > 0
    assert len(login_data["refresh_token"]) > 0

    assert login_data["username"] == test_user["username"]
    assert login_data["email"] == test_user["email"]
    assert login_data["first_name"] == test_user["first_name"]
    assert login_data["last_name"] == test_user["last_name"]
    assert login_data["is_active"] is True

    expires_at = _parse_datetime(login_data["expires_at"])
    current_time = datetime.now(timezone.utc)
    assert expires_at.tzinfo is not None
    assert current_time.tzinfo is not None
    assert expires_at > current_time

# ---------------------------------------------------------------------------
# Calculations Endpoints Integration Tests
# ---------------------------------------------------------------------------
def test_create_calculation_addition(api_base_url: str):
    u = uuid4().hex[:8]
    user_data = {
        "first_name": "Calc",
        "last_name": "Adder",
        "email": f"calc.adder{u}@example.com",
        "username": f"calc_adder_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(api_base_url, user_data)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    url = f"{api_base_url}/calculations"
    payload = {"type": "addition", "inputs": [10.5, 3, 2], "user_id": "ignored"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json().get("result") == 15.5

def test_create_calculation_subtraction(api_base_url: str):
    u = uuid4().hex[:8]
    user_data = {
        "first_name": "Calc",
        "last_name": "Subtractor",
        "email": f"calc.sub{u}@example.com",
        "username": f"calc_sub_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(api_base_url, user_data)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    url = f"{api_base_url}/calculations"
    payload = {"type": "subtraction", "inputs": [10, 3, 2], "user_id": "ignored"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json().get("result") == 5

def test_create_calculation_multiplication(api_base_url: str):
    u = uuid4().hex[:8]
    user_data = {
        "first_name": "Calc",
        "last_name": "Multiplier",
        "email": f"calc.mult{u}@example.com",
        "username": f"calc_mult_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(api_base_url, user_data)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    url = f"{api_base_url}/calculations"
    payload = {"type": "multiplication", "inputs": [2, 3, 4], "user_id": "ignored"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json().get("result") == 24

def test_create_calculation_division(api_base_url: str):
    u = uuid4().hex[:8]
    user_data = {
        "first_name": "Calc",
        "last_name": "Divider",
        "email": f"calc.div{u}@example.com",
        "username": f"calc_div_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(api_base_url, user_data)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    url = f"{api_base_url}/calculations"
    payload = {"type": "division", "inputs": [100, 2, 5], "user_id": "ignored"}
    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json().get("result") == 10

def test_list_get_update_delete_calculation(api_base_url: str):
    u = uuid4().hex[:8]
    user_data = {
        "first_name": "Calc",
        "last_name": "CRUD",
        "email": f"calc.crud{u}@example.com",
        "username": f"calc_crud_{u}",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    token_data = register_and_login(api_base_url, user_data)
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    create_url = f"{api_base_url}/calculations"
    payload = {"type": "multiplication", "inputs": [3, 4], "user_id": "ignored"}
    create_response = requests.post(create_url, json=payload, headers=headers)
    assert create_response.status_code == 201, create_response.text
    calc_id = create_response.json()["id"]

    list_url = f"{api_base_url}/calculations"
    assert any(c["id"] == calc_id for c in requests.get(list_url, headers=headers).json())

    get_url = f"{api_base_url}/calculations/{calc_id}"
    assert requests.get(get_url, headers=headers).status_code == 200

    update_url = f"{api_base_url}/calculations/{calc_id}"
    updated_calc = requests.put(update_url, json={"inputs": [5, 6]}, headers=headers).json()
    assert updated_calc["result"] == 30

    delete_url = f"{api_base_url}/calculations/{calc_id}"
    assert requests.delete(delete_url, headers=headers).status_code == 204
    assert requests.get(get_url, headers=headers).status_code == 404

# ---------------------------------------------------------------------------
# Direct Model Tests
# ---------------------------------------------------------------------------
def test_model_addition():
    assert Calculation.create("addition", uuid4(), [1, 2, 3]).get_result() == 6

def test_model_subtraction():
    assert Calculation.create("subtraction", uuid4(), [10, 3, 2]).get_result() == 5

def test_model_multiplication():
    assert Calculation.create("multiplication", uuid4(), [2, 3, 4]).get_result() == 24

def test_model_division():
    assert Calculation.create("division", uuid4(), [100, 2, 5]).get_result() == 10
    with pytest.raises(ValueError):
        Calculation.create("division", uuid4(), [100, 0]).get_result()
