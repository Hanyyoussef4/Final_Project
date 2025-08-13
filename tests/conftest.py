# tests/conftest.py
from __future__ import annotations

import os
import socket
import time
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import pytest
import requests
from faker import Faker
from playwright.sync_api import sync_playwright, Browser, Page
from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, Session

# --- App imports --------------------------------------------------------------
from app.database import Base, get_engine
from app.models.user import User

# -----------------------------------------------------------------------------
# Paths / artifacts
# -----------------------------------------------------------------------------
ARTIFACT_DIR = Path("artifacts/e2e")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG = ARTIFACT_DIR / "server.log"

# -----------------------------------------------------------------------------
# DB config (match docker-compose)
# -----------------------------------------------------------------------------
PG_HOST = os.getenv("PGHOST", "127.0.0.1")
PG_PORT = int(os.getenv("PGPORT", "5432"))
PG_USER = os.getenv("PGUSER", "postgres")
PG_PASSWORD = os.getenv("PGPASSWORD", "postgres")
PG_DB_BASE = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "module14_is601"

fake = Faker()


def _wait_for_port(host: str, port: int, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                return
        except Exception as e:
            last_err = e
            time.sleep(0.5)
    raise RuntimeError(f"Postgres not reachable on {host}:{port}: {last_err}")


def _ensure_database_url() -> None:
    """
    Ensure DATABASE_URL is set for tests, preferring TEST_DATABASE_URL if available.
    """
    if not os.getenv("DATABASE_URL"):
        test_db_url = os.getenv("TEST_DATABASE_URL")
        if test_db_url:
            os.environ["DATABASE_URL"] = test_db_url
        else:
            os.environ["DATABASE_URL"] = (
                f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB_BASE}"
            )


# -----------------------------------------------------------------------------
# FastAPI server fixture (used by E2E tests)
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def fastapi_server() -> str:
    _wait_for_port(PG_HOST, PG_PORT, timeout=60)
    _ensure_database_url()

    if SERVER_LOG.exists():
        SERVER_LOG.unlink()

    with SERVER_LOG.open("w", encoding="utf-8") as log_fp:
        proc = subprocess.Popen(
            ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )

    base_url = "http://127.0.0.1:8000"

    # Wait for /health
    deadline = time.time() + 60
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/health", timeout=2.0)
            if r.status_code == 200:
                break
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        raise RuntimeError(
            "FastAPI server failed to start. "
            f"See {SERVER_LOG.resolve()} (last error: {last_err})"
        )

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


# -----------------------------------------------------------------------------
# Public base URL fixture for E2E tests ONLY
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session", name="api_base_url")
def api_base_url(fastapi_server: str) -> str:
    return fastapi_server.rstrip("/")


# -----------------------------------------------------------------------------
# Playwright fixtures (UI)
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def playwright_browser() -> Generator[Browser, None, None]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(playwright_browser: Browser) -> Generator[Page, None, None]:
    context = playwright_browser.new_context()
    pg = context.new_page()
    try:
        yield pg
    finally:
        context.close()


# -----------------------------------------------------------------------------
# Engine / schema setup for integration tests
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def engine() -> Engine:
    _wait_for_port(PG_HOST, PG_PORT, timeout=60)
    _ensure_database_url()
    eng = get_engine()
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def _ensure_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    # Ensure a clean slate at the start of the session
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))


# -----------------------------------------------------------------------------
# Per-test DB session: allow real commits/rollbacks, then clean up after the test
# -----------------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """
    Provide a normal Session. Tests can commit/rollback freely.
    After each test, we TRUNCATE users so no data leaks to the next test.
    """
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Clean up rows created by the test
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))


# -----------------------------------------------------------------------------
# Helpers used by integration tests
# -----------------------------------------------------------------------------
def create_fake_user(**overrides) -> dict:
    """
    Return a DICT of user fields (NOT an ORM instance).
    Many tests do:  user = User(**create_fake_user())
    """
    u = fake.uuid4()[:8]
    return {
        "first_name": overrides.get("first_name", fake.first_name()),
        "last_name": overrides.get("last_name", fake.last_name()),
        "email": overrides.get("email", f"{fake.user_name()}+{u}@example.com"),
        "username": overrides.get("username", f"user_{u}"),
        "password": overrides.get("password", "SecurePass123!"),
    }


def _persist_user(db: Session, **overrides) -> User:
    """
    Persist one user in the provided session and return the session-bound User.
    """
    data = create_fake_user(**overrides)
    user = User(**data)
    db.add(user)
    db.flush()  # assign PKs without a full commit
    return user


# Session-bound fixtures expected by tests
@pytest.fixture
def test_user(db_session: Session) -> User:
    return _persist_user(db_session)


@pytest.fixture
def seed_users(db_session: Session):
    return [_persist_user(db_session) for _ in range(5)]


# Auth tests expect a dict of valid registration credentials
@pytest.fixture
def fake_user_data(faker: Faker):
    u = f"{faker.user_name()}_{fake.uuid4()[:6]}"
    pw = "SecurePass123!"
    return {
        "first_name": faker.first_name(),
        "last_name": faker.last_name(),
        "username": u,
        "email": f"{u}@example.com",
        "password": pw,
        "confirm_password": pw,
    }


# -----------------------------------------------------------------------------
# Backward-compatible context manager some tests import directly
# -----------------------------------------------------------------------------
@contextmanager
def managed_db_session() -> Generator[Session, None, None]:
    """
    Context manager that yields a Session for ad-hoc DB work inside a test.
    Changes are visible during the 'with' block, then cleaned after.
    """
    _wait_for_port(PG_HOST, PG_PORT, timeout=60)
    _ensure_database_url()

    eng = get_engine()
    try:
        Base.metadata.create_all(bind=eng)
        SessionLocal = sessionmaker(bind=eng, autocommit=False, autoflush=False)
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()
            with eng.begin() as conn:
                conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
    finally:
        eng.dispose()
