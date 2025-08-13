# tests/e2e/test_ui_stats_playwright.py
import re
import time
import pytest
from playwright.sync_api import Page, expect
import requests

pytestmark = pytest.mark.e2e

def _unique_username(prefix="ui"):
    return f"{prefix}_{int(time.time()*1000)}"

def _register_user(username: str, password: str):
    r = requests.post("http://127.0.0.1:8000/api/auth/register",
                      json={"username": username, "password": password})
    assert r.status_code in (200, 201, 409), r.text

def ui_login(page: Page, username: str, password: str):
    page.goto("http://127.0.0.1:8000/auth/login")
    page.get_by_label(re.compile("username", re.I)).fill(username)
    page.get_by_label(re.compile("password", re.I)).fill(password)
    page.get_by_role("button", name=re.compile("^log ?in$", re.I)).click()
    # Wait for dashboard to load
    expect(page.get_by_text(re.compile("dashboard|calculations app", re.I))).to_be_visible()

def _navigate_to_stats(page: Page):
    """If stats are on a separate view, navigate there."""
    try:
        page.get_by_role("link", name=re.compile("stats", re.I)).click(timeout=2000)
    except Exception:
        pass  # If stats are already visible on dashboard

def _read_stat_number(page: Page, label_regex: str) -> float:
    label = page.get_by_text(re.compile(label_regex, re.I)).first
    expect(label).to_be_visible(timeout=5000)
    container = label.locator(
        "xpath=ancestor-or-self::*[contains(@class,'card') or contains(@class,'Stats') or name()='div'][1]"
    )
    text = container.text_content()
    m = re.search(rf"{label_regex}.*?([-+]?\d+(\.\d+)?)", text, re.I | re.S)
    if not m:
        m = re.search(r"([-+]?\d+(\.\d+)?)", text)
    assert m, f"Could not extract number for '{label_regex}' from: {text}"
    return float(m.group(1))

def _fill_numbers(page: Page, value: str):
    candidates = [
        page.get_by_label(re.compile("numbers", re.I)),
        page.get_by_placeholder(re.compile("numbers", re.I)),
        page.locator("input[name='numbers']"),
        page.locator("textarea[name='numbers']"),
    ]
    for c in candidates:
        if c.count() > 0:
            c.first.fill(value)
            return
    raise AssertionError("Numbers input not found")

def test_stats_updates_after_new_calculation(page: Page):
    username = _unique_username("stats")
    password = "Abcd1234!"
    _register_user(username, password)
    ui_login(page, username, password)

    # Go to stats section if needed
    _navigate_to_stats(page)

    # Snapshot stats BEFORE
    total_before = _read_stat_number(page, r"Total Calculations")
    avg_before = _read_stat_number(page, r"Average Operands")

    # Go back to main calculation area if needed
    try:
        page.get_by_role("link", name=re.compile("dashboard|home|calculations", re.I)).click(timeout=2000)
    except Exception:
        pass

    # Create new calculation
    _fill_numbers(page, "2, 7")
    comboboxes = page.get_by_role("combobox")
    if comboboxes.count() > 0:
        try:
            comboboxes.first.select_option(label="Addition")
        except Exception:
            pass
    page.get_by_role("button", name=re.compile("calculate|add|create|compute", re.I)).click()
    expect(page.get_by_text(re.compile(r"\b9\b"))).to_be_visible(timeout=5000)

    # Revisit stats to verify
    _navigate_to_stats(page)
    total_after = _read_stat_number(page, r"Total Calculations")
    avg_after = _read_stat_number(page, r"Average Operands")

    assert total_after == total_before + 1, f"total_before={total_before}, total_after={total_after}"
    assert isinstance(avg_after, float)
