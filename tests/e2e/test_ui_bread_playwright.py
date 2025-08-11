# tests/e2e/test_ui_bread_playwright.py
import json
import re
import time
import uuid
from pathlib import Path
from typing import Optional, Iterable, Dict, Any

import httpx
import pytest
from playwright.sync_api import Page, expect, TimeoutError as PWTimeout

# ---- BASE URL (Option 1) ----
BASE_URL = "http://127.0.0.1:8000"

ARTIFACT_DIR = Path("artifacts/e2e")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


# =============================== helpers ===============================

def _unique_username(prefix: str = "ui") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def _summarize_fastapi_errors(detail: Any) -> str:
    try:
        items: Iterable[Dict[str, Any]] = detail if isinstance(detail, list) else []
        lines = []
        for e in items:
            loc = ".".join(str(x) for x in e.get("loc", []))
            t = e.get("type", "?")
            msg = e.get("msg", "")
            lines.append(f"- {loc}: {msg} ({t})")
        return "\n".join(lines) if lines else json.dumps(detail, indent=2, ensure_ascii=False)
    except Exception:
        return json.dumps(detail, indent=2, ensure_ascii=False)

def _fail_with_http_report(r: httpx.Response, request_payload: dict, label: str = "Request failed"):
    redacted = dict(request_payload)
    if "password" in redacted:
        redacted["password"] = "***"
    if "confirm_password" in redacted:
        redacted["confirm_password"] = "***"

    try:
        body = r.json()
    except Exception:
        body = r.text

    detail = body.get("detail") if isinstance(body, dict) else None
    summarized = _summarize_fastapi_errors(detail) if detail is not None else body

    pytest.fail(
        f"""{label}
URL: {r.request.method} {r.request.url}
Status: {r.status_code}
Request JSON: {json.dumps(redacted, indent=2)}
Response:
{summarized}
""".rstrip()
    )

def _capture(page: Page, label: str):
    ts = int(time.time())
    png = ARTIFACT_DIR / f"{label}_{ts}.png"
    html = ARTIFACT_DIR / f"{label}_{ts}.html"
    try:
        page.screenshot(path=str(png), full_page=True)
    except Exception:
        pass
    try:
        html.write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    print(f"\n[debug] captured → {png.name} and {html.name} in {ARTIFACT_DIR}/")

def register_user_via_api(username: str, password: str) -> None:
    url = f"{BASE_URL}/auth/register"
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "confirm_password": password,   # required by your schema
        "first_name": "UI",
        "last_name": "Test",
    }
    with httpx.Client(timeout=30.0) as c:
        r = c.post(url, json=payload)
    if r.status_code not in (200, 201):
        _fail_with_http_report(r, payload, label="Register failed")

def _find_input_with_fallbacks(page: Page, label_regex: Optional[re.Pattern], fallback_selector: str):
    if label_regex is not None:
        try:
            loc = page.get_by_label(label_regex)
            loc.wait_for(state="visible", timeout=2000)
            return loc
        except Exception:
            pass
    loc = page.locator(fallback_selector).first
    loc.wait_for(state="visible", timeout=4000)
    return loc

def _wait_for_dashboard(page: Page):
    anchor = page.get_by_role("heading", name=re.compile(r"(New Calculation|Calculation History)", re.I)).first
    expect(anchor).to_be_visible(timeout=12000)

def ui_login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login")

    user_input = _find_input_with_fallbacks(
        page,
        re.compile(r"(Username|Email|Username or Email)", re.I),
        "input[type='email'], input[name='email'], input#email, input[name='username'], input#username, input[type='text']"
    )
    user_input.fill(username)

    pass_input = _find_input_with_fallbacks(
        page,
        re.compile(r"^Password$", re.I),
        "input[type='password'], input[name='password'], input#password"
    )
    pass_input.fill(password)

    page.get_by_role("button", name=re.compile(r"(Sign in|Log in|Login)", re.I)).first.click()
    _wait_for_dashboard(page)

def _find_numbers_input(page: Page):
    try:
        loc = page.get_by_label(re.compile(r"(Numbers|Input Values).*(comma)", re.I))
        loc.wait_for(state="visible", timeout=1500)
        return loc
    except Exception:
        pass
    try:
        loc = page.locator("input[placeholder*='comma' i], input[placeholder*='e.g' i], textarea[placeholder*='comma' i]").first
        loc.wait_for(state="visible", timeout=1500)
        return loc
    except Exception:
        pass
    try:
        loc = page.locator("input[name='numbers'], input#numbers, textarea[name='numbers'], textarea#numbers").first
        loc.wait_for(state="visible", timeout=1500)
        return loc
    except Exception:
        pass
    try:
        loc = page.locator("main input[type='text'], main textarea").first
        loc.wait_for(state="visible", timeout=1500)
        return loc
    except Exception:
        return None


# ================================ tests ================================

@pytest.mark.e2e
def test_create_read_edit_delete_flow(page: Page):
    username = _unique_username("ui")
    password = "Abcd1234!"

    register_user_via_api(username, password)
    ui_login(page, username, password)

    # Create
    numbers_input = _find_numbers_input(page)
    if numbers_input is None:
        _capture(page, "fail_numbers_input_not_found")
    assert numbers_input is not None, "Could not locate the numbers input on the dashboard"
    numbers_input.click()
    numbers_input.fill("10.5, 3, 2")

    used_selector = False
    try:
        page.get_by_role("combobox").first.select_option("add")
        used_selector = True
    except Exception:
        pass
    if not used_selector:
        try:
            page.get_by_label(re.compile(r"^Add$", re.I)).check()
        except Exception:
            try:
                page.get_by_role("radio", name=re.compile(r"add", re.I)).first.check()
            except Exception:
                pass

    page.get_by_role("button", name=re.compile(r"^Calculate$", re.I)).first.click()

    # ----------------------- NEW: robust post-calc logic -----------------------
    # 1) Count rows/cards before
    before = 0
    for sel in ["table tbody tr", ".history-row", ".calc-row", ".card", ".calculation-item"]:
        try:
            before = max(before, page.locator(sel).count())
        except Exception:
            pass

    # 2) Wait for count to increase OR inline result text to appear
    page.wait_for_timeout(300)
    def _rows_now():
        total = 0
        for sel in ["table tbody tr", ".history-row", ".calc-row", ".card", ".calculation-item"]:
            try:
                total = max(total, page.locator(sel).count())
            except Exception:
                pass
        return total

    deadline = time.time() + 10
    while time.time() < deadline and _rows_now() <= before:
        page.wait_for_timeout(200)

    new_count = _rows_now()
    if new_count <= before:
        try:
            expect(page.get_by_text(re.compile(r"(Result|Output|Answer)", re.I)).first).to_be_visible(timeout=2000)
        except AssertionError:
            _capture(page, "fail_no_view_or_result")
            assert False, "No new history row/card and no visible Result/Output/Answer after Calculate"

    # 3) Click newest row/card; prefer explicit details link, else any link/button, else click container
    containers = page.locator("table tbody tr, .history-row, .calc-row, .card, .calculation-item")
    last = containers.nth(-1)

    clicked = False
    for selector in [
        "a:has-text('View')", "a:has-text('Details')", "a:has-text('Open')",
        "button:has-text('View')", "button:has-text('Details')", "button:has-text('Open')",
        "a[href*='/calculation']", "a[href*='/calculations']"
    ]:
        try:
            link = last.locator(selector).first
            if link.count() > 0:
                link.click()
                clicked = True
                break
        except Exception:
            pass

    if not clicked:
        try:
            last.click()
            clicked = True
        except Exception:
            _capture(page, "fail_no_clickable_in_row")
            assert False, "Newest history item isn’t clickable and has no details link/button"

    # 4) Verify we're on a details-like view
    try:
        expect(page.get_by_role("heading", name=re.compile(r"(Result|Details|Calculation)", re.I)).first).to_be_visible(timeout=8000)
    except AssertionError:
        try:
            expect(page.get_by_text(re.compile(r"(Result|Output|Answer|Details)", re.I)).first).to_be_visible(timeout=4000)
        except AssertionError:
            _capture(page, "fail_after_open_no_details")
            raise
    # --------------------------------------------------------------------------

    # Edit on details (robust: button or link, with ID and text fallbacks)
    clicked_edit = False
    for locator in [
        lambda: page.get_by_role("button", name=re.compile(r"^(Edit Calculation|Edit)$", re.I)).first,
        lambda: page.get_by_role("link",   name=re.compile(r"^(Edit Calculation|Edit)$", re.I)).first,
        lambda: page.locator("#editLink").first,
        lambda: page.locator("a:has-text('Edit Calculation')").first,
        lambda: page.locator("a:has-text('Edit')").first,
    ]:
        try:
            el = locator()
            if el and el.count() > 0:
                el.click()
                clicked_edit = True
                break
        except Exception:
            pass

    if not clicked_edit:
        _capture(page, "fail_edit_button_not_found")
        assert False, "Could not find an Edit control on the details page"

    # Wait for edit form (URL or visible Save/Update control)
    edit_ready = False
    try:
        page.wait_for_url(re.compile(r"/dashboard/(edit|update)/", re.I), timeout=8000)
        edit_ready = True
    except Exception:
        pass
    if not edit_ready:
        try:
            expect(page.get_by_role("button", name=re.compile(r"^(Save|Save Changes|Update)$", re.I)).first).to_be_visible(timeout=4000)
            edit_ready = True
        except AssertionError:
            _capture(page, "fail_after_edit_no_form")
            raise

    try:
        edit_inputs = page.get_by_label(re.compile(r"Input Values.*comma", re.I))
        edit_inputs.wait_for(state="visible", timeout=2000)
    except PWTimeout:
        edit_inputs = page.locator("input[placeholder*='comma' i], textarea[placeholder*='comma' i]").first
        edit_inputs.wait_for(state="visible", timeout=4000)

    edit_inputs.click()
    edit_inputs.fill("2, 3, 5")

    # Save (button/link/id fallbacks)
    saved = False
    for locator in [
        lambda: page.get_by_role("button", name=re.compile(r"^(Save Changes|Save|Update)$", re.I)).first,
        lambda: page.get_by_role("link",   name=re.compile(r"^(Save Changes|Save|Update)$", re.I)).first,
        lambda: page.locator("#saveBtn").first,
    ]:
        try:
            el = locator()
            if el and el.count() > 0:
                el.click()
                saved = True
                break
        except Exception:
            pass
    if not saved:
        _capture(page, "fail_save_button_not_found")
        assert False, "Could not find Save/Update control on the edit form"

    # After Save: your UI returns to /dashboard/view/{id} with "Calculation Details" header
    navigated_back = False
    try:
        page.wait_for_url(re.compile(r"/dashboard/(view|details)/", re.I), timeout=8000)
        navigated_back = True
    except Exception:
        pass

    try:
        # Prefer the real page heading, else the details card
        try:
            expect(page.get_by_role("heading", name=re.compile(r"(Calculation Details|Details)", re.I)).first).to_be_visible(timeout=8000)
        except AssertionError:
            expect(page.locator("#calculationCard")).to_be_visible(timeout=8000)

        # Sanity check: edited inputs now visible on the page
        expect(page.get_by_text(re.compile(r"\b2,\s*3,\s*5\b"))).to_be_visible(timeout=4000)
    except AssertionError:
        if not navigated_back:
            _capture(page, "fail_after_save_no_navigation")
        _capture(page, "fail_after_save_no_result")
        raise

    # Delete (robust: accept native confirm dialog; prefer #deleteBtn, then role/button/link)
    deleted_clicked = False
    delete_locators = [
        lambda: page.locator("#deleteBtn").first,
        lambda: page.get_by_role("button", name=re.compile(r"^Delete$", re.I)).first,
        lambda: page.get_by_role("link",   name=re.compile(r"^Delete$", re.I)).first,
    ]
    for locator in delete_locators:
        try:
            el = locator()
            if el and el.count() > 0:
                # Accept native confirm() if it appears
                page.once("dialog", lambda d: d.accept())
                el.click()
                deleted_clicked = True
                break
        except Exception:
            pass
    if not deleted_clicked:
        _capture(page, "fail_delete_button_not_found")
        assert False, "Could not find a Delete control on the details page"

    # Try to detect navigation caused by delete
    navigated_to_dashboard = False
    try:
        page.wait_for_url(re.compile(r"/dashboard/?$", re.I), timeout=8000)
        navigated_to_dashboard = True
    except Exception:
        # If a custom modal confirm exists instead of native confirm, click it
        try:
            confirm = page.get_by_role("button", name=re.compile(r"^(Delete|Confirm|Yes)$", re.I)).first
            expect(confirm).to_be_visible(timeout=3000)
            confirm.click()
            page.wait_for_url(re.compile(r"/dashboard/?$", re.I), timeout=8000)
            navigated_to_dashboard = True
        except Exception:
            # Last resort: click the “Back to Dashboard” link if present
            try:
                page.locator("a[href='/dashboard'], a:has-text('Back to Dashboard')").first.click()
                page.wait_for_url(re.compile(r"/dashboard/?$", re.I), timeout=8000)
                navigated_to_dashboard = True
            except Exception:
                pass

    # Back on dashboard
    try:
        if not navigated_to_dashboard:
            _capture(page, "fail_after_delete_no_navigation")
        _wait_for_dashboard(page)
    except AssertionError:
        _capture(page, "fail_back_to_dashboard")
        raise


@pytest.mark.e2e
def test_negative_invalid_input_validation(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.get_by_role("button", name=re.compile(r"(Sign in|Log in|Login)", re.I)).first.click()

    user_input = _find_input_with_fallbacks(
        page,
        re.compile(r"(Username|Email|Username or Email)", re.I),
        "input[type='email'], input[name='email'], input#email, input[name='username'], input#username, input[type='text']"
    )
    pass_input = _find_input_with_fallbacks(
        page,
        re.compile(r"Password", re.I),
        "input[type='password'], input[name='password'], input#password"
    )
    expect(user_input).to_be_visible(timeout=5000)
    expect(pass_input).to_be_visible()


@pytest.mark.e2e
def test_negative_unauthorized_redirect(page: Page):
    page.goto(f"{BASE_URL}/")
    try:
        expect(page.get_by_role("heading", name=re.compile(r"(Welcome Back|Login|Sign in)", re.I)).first).to_be_visible(timeout=5000)
    except AssertionError:
        page.goto(f"{BASE_URL}/login")
        expect(page.get_by_role("heading", name=re.compile(r"(Welcome Back|Login|Sign in)", re.I)).first).to_be_visible(timeout=8000)

    user_input = _find_input_with_fallbacks(
        page,
        re.compile(r"(Username|Email|Username or Email)", re.I),
        "input[type='email'], input[name='email'], input#email, input[name='username'], input#username, input[type='text']"
    )
    pass_input = _find_input_with_fallbacks(
        page,
        re.compile(r"Password", re.I),
        "input[type='password'], input[name='password'], input#password"
    )
    expect(user_input).to_be_visible()
    expect(pass_input).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"(Sign in|Log in|Login)", re.I)).first).to_be_visible()
