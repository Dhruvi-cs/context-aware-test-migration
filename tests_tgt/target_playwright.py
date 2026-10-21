"""Target Playwright Python tests for TaskBoard SUT (Framework Ft = Playwright/Python).
Implements the 27 test scenarios using native Playwright sync API.
Usage: BASE_URL=http://127.0.0.1:5000 python target_playwright.py [--list] [--only NAME ...]
"""
import argparse, os, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
_pw = None
_browser = None
_context = None
_page = None


def get_page():
    global _pw, _browser, _context, _page
    if _pw is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=os.environ.get("HEADLESS", "1") != "0")
        _context = _browser.new_context()
        _page = _context.new_page()
    return _page


def reset_server():
    urllib.request.urlopen(urllib.request.Request(BASE + "/__reset", method="POST", data=b""), timeout=5).read()


def click_nav(locator):
    p = get_page()
    with p.expect_navigation():
        locator.click()


def fresh(login=True):
    reset_server()
    p = get_page()
    _context.clear_cookies()
    try:
        p.evaluate("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
    except Exception:
        pass
    p.goto(BASE + "/login")
    if login:
        do_login("demo", "demo123")
        p.locator("#task-list").wait_for(state="attached")
    return p


def do_login(user, pw):
    p = get_page()
    p.goto(BASE + "/login")
    p.fill("#username", user)
    p.fill("#password", pw)
    click_nav(p.locator("#login-btn"))


def type_task(text):
    p = get_page()
    p.locator("#task-input").fill("")
    p.locator("#task-input").press_sequentially(text)


def add_task(text):
    type_task(text)
    click_nav(get_page().locator("#add-btn"))


def titles():
    p = get_page()
    return [el.inner_text().strip() for el in p.locator("#task-list .task-title").all()]


def remaining():
    return int(get_page().locator("#remaining").inner_text().strip())


def row(n):
    return get_page().locator(f"#task-{n}")


def is_done(n):
    cls = row(n).get_attribute("class") or ""
    return "done" in cls.split()


# ---------------- authentication ----------------
def test_login_success():
    p = fresh(login=False)
    do_login("demo", "demo123")
    assert p.url.rstrip("/") == BASE.rstrip("/"), p.url
    p.locator("#add-form").wait_for(state="attached")


def test_login_invalid_password_rejected():
    p = fresh(login=False)
    do_login("demo", "wrong")
    assert p.locator("#login-error").inner_text().strip() == "Invalid credentials"
    p.goto(BASE + "/")
    assert p.url.endswith("/login")


def test_login_wrong_username_rejected():
    p = fresh(login=False)
    do_login("other", "demo123")
    assert p.locator("#login-error").inner_text().strip() == "Invalid credentials"


def test_login_page_no_error_initially():
    p = fresh(login=False)
    p.goto(BASE + "/login")
    p.locator("#login-form").wait_for(state="attached")
    assert p.locator("#login-error").count() == 0


def test_protected_page_redirects_to_login():
    p = fresh(login=False)
    p.goto(BASE + "/")
    assert p.url.endswith("/login")


def test_logout_ends_session():
    p = fresh()
    click_nav(p.locator("#logout"))
    assert p.url.endswith("/login")
    p.goto(BASE + "/")
    assert p.url.endswith("/login")


# ---------------- add / client-side validation ----------------
def test_add_task_appears():
    fresh(); add_task("Buy milk")
    assert titles() == ["Buy milk"] and remaining() == 1


def test_add_trims_whitespace():
    fresh(); add_task("  padded  ")
    assert titles() == ["padded"]


def test_add_multiple_preserves_order():
    fresh(); add_task("A"); add_task("B"); add_task("C")
    assert titles() == ["A", "B", "C"] and remaining() == 3


def test_add_button_disabled_when_empty():
    fresh()
    assert not get_page().locator("#add-btn").is_enabled()


def test_add_button_enabled_after_typing():
    fresh(); type_task("x")
    assert get_page().locator("#add-btn").is_enabled()


def test_add_button_disabled_for_whitespace_only():
    fresh(); type_task("     ")
    assert not get_page().locator("#add-btn").is_enabled()


def test_add_button_enabled_at_100_chars():
    fresh(); type_task("a" * 100)
    assert get_page().locator("#add-btn").is_enabled()


def test_add_button_disabled_at_101_chars():
    fresh(); type_task("a" * 101)
    assert not get_page().locator("#add-btn").is_enabled()


def test_char_counter_updates_while_typing():
    fresh()
    assert get_page().locator("#char-count").inner_text().strip() == "100"
    type_task("abcde")
    assert get_page().locator("#char-count").inner_text().strip() == "95"


def test_char_counter_goes_negative_when_too_long():
    fresh(); type_task("a" * 103)
    assert get_page().locator("#char-count").inner_text().strip() == "-3"


# ---------------- server-side validation reached through browser ----------------
def _force_submit():
    p = get_page()
    with p.expect_navigation():
        p.evaluate("document.getElementById('add-form').submit();")


def test_server_rejects_empty_title():
    fresh(); type_task("   "); _force_submit()
    assert get_page().locator("#flash").inner_text().strip() == "Title is required"
    assert titles() == []


def test_server_rejects_title_over_100():
    fresh(); type_task("a" * 101); _force_submit()
    assert get_page().locator("#flash").inner_text().strip() == "Title too long"
    assert titles() == []


def test_server_accepts_title_of_exactly_100():
    fresh(); type_task("a" * 100); _force_submit()
    assert titles() == ["a" * 100]


# ---------------- toggle / delete / filters ----------------
def test_toggle_marks_done_and_updates_remaining():
    fresh(); add_task("A"); add_task("B")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    assert is_done(1) and not is_done(2) and remaining() == 1


def test_toggle_twice_restores_active():
    fresh(); add_task("A")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    click_nav(p.locator("#task-1 .toggle-btn"))
    assert not is_done(1) and remaining() == 1


def test_delete_removes_only_target():
    fresh(); add_task("A"); add_task("B"); add_task("C")
    p = get_page()
    click_nav(p.locator("#task-2 .delete-btn"))
    assert titles() == ["A", "C"] and remaining() == 2


def test_filter_active_shows_only_active():
    fresh(); add_task("A"); add_task("B")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    click_nav(p.locator("#filter-active"))
    assert titles() == ["B"]


def test_filter_done_shows_only_done():
    fresh(); add_task("A"); add_task("B")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    click_nav(p.locator("#filter-done"))
    assert titles() == ["A"]


def test_filter_all_shows_everything():
    fresh(); add_task("A"); add_task("B")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    click_nav(p.locator("#filter-done"))
    click_nav(p.locator("#filter-all"))
    assert titles() == ["A", "B"]


def test_remaining_ignores_active_filter():
    fresh(); add_task("A"); add_task("B"); add_task("C")
    p = get_page()
    click_nav(p.locator("#task-1 .toggle-btn"))
    click_nav(p.locator("#filter-done"))
    assert remaining() == 2


def test_clear_completed_removes_only_done():
    fresh(); add_task("A"); add_task("B")
    p = get_page()
    click_nav(p.locator("#task-2 .toggle-btn"))
    click_nav(p.locator("#clear-completed"))
    assert titles() == ["A"] and remaining() == 1


def _all():
    return {k: v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    tests = _all()
    if a.list:
        print("\n".join(tests)); sys.exit(0)
    if a.only:
        tests = {k: v for k, v in tests.items() if k in a.only}
    failed = 0
    try:
        for n, f in tests.items():
            try:
                f(); print("PASS", n, flush=True)
            except Exception as e:
                failed += 1
                msg = str(e).splitlines()[0][:100] if str(e) else ""
                print("FAIL", n, type(e).__name__, msg, flush=True)
    finally:
        if _browser is not None:
            try: _browser.close()
            except Exception: pass
        if _pw is not None:
            try: _pw.stop()
            except Exception: pass
    sys.exit(1 if failed else 0)
