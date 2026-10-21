"""Selenium SOURCE tests for the TaskBoard SUT (the migration subjects, framework Fs = Selenium/Python).
Protocol identical to the HTTP reference tests: prints 'PASS name' / 'FAIL name reason' per test.
Usage:  BASE_URL=http://127.0.0.1:5000 python source_selenium.py [--list] [--only NAME ...]
Needs: selenium>=4.6 (Selenium Manager fetches the driver) and Chrome/Chromium. Env HEADLESS=0 shows the browser."""
import argparse, os, sys, urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
_driver = None


def driver():
    global _driver
    if _driver is None:
        opts = Options()
        if os.environ.get("HEADLESS", "1") != "0":
            opts.add_argument("--headless=new")
        for a in ("--no-sandbox", "--disable-dev-shm-usage", "--window-size=1200,900"):
            opts.add_argument(a)
        _driver = webdriver.Chrome(options=opts)
    return _driver


def wait():
    return WebDriverWait(driver(), 5)


def reset_server():
    urllib.request.urlopen(urllib.request.Request(BASE + "/__reset", method="POST", data=b""), timeout=5).read()


def fresh(login=True):
    """Reset server state, clear cookies, optionally log in through the real login form."""
    reset_server()
    d = driver()
    d.get(BASE + "/login")
    d.delete_all_cookies()
    if login:
        do_login("demo", "demo123")
        assert d.find_element(By.ID, "task-list")
    return d


def click_and_wait_nav(element):
    """Click and wait until the browser has navigated (page marker disappears)."""
    d = driver()
    d.execute_script("window.__marker = 1;")
    element.click()
    wait().until(lambda x: x.execute_script("return window.__marker === undefined;"))


def do_login(user, pw):
    d = driver()
    d.get(BASE + "/login")
    d.find_element(By.ID, "username").send_keys(user)
    d.find_element(By.ID, "password").send_keys(pw)
    click_and_wait_nav(d.find_element(By.ID, "login-btn"))


def type_task(text):
    box = driver().find_element(By.ID, "task-input")
    box.clear()
    box.send_keys(text)


def add_task(text):
    type_task(text)
    click_and_wait_nav(driver().find_element(By.ID, "add-btn"))


def titles():
    return [e.text for e in driver().find_elements(By.CSS_SELECTOR, "#task-list .task-title")]


def remaining():
    return int(driver().find_element(By.ID, "remaining").text)


def row(n):
    return driver().find_element(By.ID, f"task-{n}")


def is_done(n):
    return "done" in row(n).get_attribute("class").split()


# ---------------- authentication ----------------
def test_login_success():
    d = fresh(login=False)
    do_login("demo", "demo123")
    assert d.current_url.rstrip("/") == BASE.rstrip("/"), d.current_url
    assert d.find_element(By.ID, "add-form")

def test_login_invalid_password_rejected():
    d = fresh(login=False)
    do_login("demo", "wrong")
    assert d.find_element(By.ID, "login-error").text == "Invalid credentials"
    d.get(BASE + "/")
    assert d.current_url.endswith("/login")

def test_login_wrong_username_rejected():
    d = fresh(login=False)
    do_login("other", "demo123")
    assert d.find_element(By.ID, "login-error").text == "Invalid credentials"

def test_login_page_no_error_initially():
    d = fresh(login=False)
    d.get(BASE + "/login")
    assert d.find_element(By.ID, "login-form")
    assert d.find_elements(By.ID, "login-error") == []

def test_protected_page_redirects_to_login():
    d = fresh(login=False)
    d.get(BASE + "/")
    assert d.current_url.endswith("/login"), d.current_url

def test_logout_ends_session():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "logout"))
    assert d.current_url.endswith("/login")
    d.get(BASE + "/")
    assert d.current_url.endswith("/login")

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
    assert not driver().find_element(By.ID, "add-btn").is_enabled()

def test_add_button_enabled_after_typing():
    fresh(); type_task("x")
    assert driver().find_element(By.ID, "add-btn").is_enabled()

def test_add_button_disabled_for_whitespace_only():
    fresh(); type_task("     ")
    assert not driver().find_element(By.ID, "add-btn").is_enabled()

def test_add_button_enabled_at_100_chars():
    fresh(); type_task("a" * 100)
    assert driver().find_element(By.ID, "add-btn").is_enabled()

def test_add_button_disabled_at_101_chars():
    fresh(); type_task("a" * 101)
    assert not driver().find_element(By.ID, "add-btn").is_enabled()

def test_char_counter_updates_while_typing():
    fresh()
    assert driver().find_element(By.ID, "char-count").text == "100"
    type_task("abcde")
    assert driver().find_element(By.ID, "char-count").text == "95"

def test_char_counter_goes_negative_when_too_long():
    fresh(); type_task("a" * 103)
    assert driver().find_element(By.ID, "char-count").text == "-3"

# ---------------- server-side validation reached through the browser ----------------
def _force_submit():
    """Bypass the client-side validator by submitting the form from script."""
    d = driver()
    d.execute_script("window.__marker = 1; document.getElementById('add-form').submit();")
    wait().until(lambda x: x.execute_script("return window.__marker === undefined;"))

def test_server_rejects_empty_title():
    fresh(); type_task("   "); _force_submit()
    assert driver().find_element(By.ID, "flash").text == "Title is required"
    assert titles() == []

def test_server_rejects_title_over_100():
    fresh(); type_task("a" * 101); _force_submit()
    assert driver().find_element(By.ID, "flash").text == "Title too long"
    assert titles() == []

def test_server_accepts_title_of_exactly_100():
    fresh(); type_task("a" * 100); _force_submit()
    assert titles() == ["a" * 100]

# ---------------- toggle / delete / filters ----------------
def test_toggle_marks_done_and_updates_remaining():
    fresh(); add_task("A"); add_task("B")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    assert is_done(1) and not is_done(2) and remaining() == 1

def test_toggle_twice_restores_active():
    fresh(); add_task("A")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    assert not is_done(1) and remaining() == 1

def test_delete_removes_only_target():
    fresh(); add_task("A"); add_task("B"); add_task("C")
    click_and_wait_nav(row(2).find_element(By.CSS_SELECTOR, ".delete-btn"))
    assert titles() == ["A", "C"] and remaining() == 2

def test_filter_active_shows_only_active():
    fresh(); add_task("A"); add_task("B")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(driver().find_element(By.ID, "filter-active"))
    assert titles() == ["B"]

def test_filter_done_shows_only_done():
    fresh(); add_task("A"); add_task("B")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(driver().find_element(By.ID, "filter-done"))
    assert titles() == ["A"]

def test_filter_all_shows_everything():
    fresh(); add_task("A"); add_task("B")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(driver().find_element(By.ID, "filter-done"))
    click_and_wait_nav(driver().find_element(By.ID, "filter-all"))
    assert titles() == ["A", "B"]

def test_remaining_ignores_active_filter():
    fresh(); add_task("A"); add_task("B"); add_task("C")
    click_and_wait_nav(row(1).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(driver().find_element(By.ID, "filter-done"))
    assert remaining() == 2

def test_clear_completed_removes_only_done():
    fresh(); add_task("A"); add_task("B")
    click_and_wait_nav(row(2).find_element(By.CSS_SELECTOR, ".toggle-btn"))
    click_and_wait_nav(driver().find_element(By.ID, "clear-completed"))
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
                failed += 1; print("FAIL", n, type(e).__name__, str(e).splitlines()[0][:100] if str(e) else "", flush=True)
    finally:
        if _driver is not None:
            try: _driver.quit()
            except Exception: pass
    sys.exit(1 if failed else 0)
