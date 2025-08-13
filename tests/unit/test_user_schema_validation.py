# tests/unit/test_user_schema_validation.py
import pytest
from app.schemas.user import UserCreate  # adjust if your name differs

def test_usercreate_happy():
    u = UserCreate(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        username="jdoe",
        password="Abcd1234!",
        confirm_password="Abcd1234!",
    )
    assert u.username == "jdoe"

def test_usercreate_mismatched_confirm_password():
    with pytest.raises(Exception):
        UserCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            username="jdoe",
            password="Abcd1234!",
            confirm_password="wrong",
        )

def test_usercreate_invalid_email():
    with pytest.raises(Exception):
        UserCreate(
            first_name="John",
            last_name="Doe",
            email="not-an-email",
            username="jdoe",
            password="Abcd1234!",
            confirm_password="Abcd1234!",
        )
