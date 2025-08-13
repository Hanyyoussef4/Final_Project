import pytest
from httpx import AsyncClient

BASE_USER = {
    "username": "reportuser",
    "password": "Abcd1234!",
    "confirm_password": "Abcd1234!",
    "email": "reportuser@example.com",
    "first_name": "Report",
    "last_name": "User"
}

@pytest.mark.asyncio
async def test_reports_summary_flow(async_client: AsyncClient):
    # 1. Register the user
    res = await async_client.post("/auth/register", json=BASE_USER)
    assert res.status_code == 201, f"Registration failed: {res.text}"

    # 2. Login to get JWT token
    login_payload = {
        "username": BASE_USER["username"],
        "password": BASE_USER["password"]
    }
    res = await async_client.post("/auth/login", json=login_payload)
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create some calculations
    calc_payloads = [
        {"type": "add", "inputs": [1, 2]},
        {"type": "multiply", "inputs": [3, 4]},
        {"type": "subtract", "inputs": [10, 5]},
    ]
    for payload in calc_payloads:
        res = await async_client.post("/calculations", json=payload, headers=headers)
        assert res.status_code == 201, f"Calculation create failed: {res.text}"

    # 4. Call /reports/summary
    res = await async_client.get("/reports/summary", headers=headers)
    assert res.status_code == 200, f"Summary endpoint failed: {res.text}"
    data = res.json()

    # 5. Verify structure
    assert "total_calculations" in data
    assert isinstance(data["total_calculations"], int)
    assert data["total_calculations"] >= 3

    assert "by_type" in data
    assert isinstance(data["by_type"], dict)
    assert "add" in data["by_type"]
    assert "multiply" in data["by_type"]
    assert "subtract" in data["by_type"]

    # Optional: check counts match
    for t in ["add", "multiply", "subtract"]:
        assert data["by_type"][t] >= 1
