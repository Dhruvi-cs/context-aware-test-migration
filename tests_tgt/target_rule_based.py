"""Rule-Based Transpiled Playwright Test Suite (Baseline-0)"""
import argparse, os, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
_pw = None; _browser = None; _context = None; _page = None

def get_page():
    global _pw, _browser, _context, _page
    if _pw is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=os.environ.get("HEADLESS", "1") != "0")
        _context = _browser.new_context()
        _page = _context.new_page()
        _page.set_default_timeout(2500)
    return _page

def driver():
    return get_page()

"""Selenium SOURCE tests for the TaskBoard SUT (the migration subjects, framework Fs = Selenium/Python).
Protocol identical to the HTTP reference tests: prints 'PASS name' / 'FAIL name reason' per test.
Usage:  BASE_URL=http://127.0.0.1:5000 python source_selenium.py [--list] [--only NAME ...]
Needs: selenium>=4.6 (Selenium Manager fetches the driver) and Chrome/Chromium. Env HEADLESS=0 shows the browser."""
import argparse, os, sys, urllib.request
BASE = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')
_driver = None

def reset_server():
    urllib.request.urlopen(urllib.request.Request(BASE + '/__reset', method='POST', data=b''), timeout=5).read()

def fresh(login=True):
    """Reset server state, clear cookies and storage, optionally log in through the real login form."""
    reset_server()
    d = driver()
    d.goto(BASE + '/login')
    _context.clear_cookies()
    try:
        d.execute_script('try { localStorage.clear(); sessionStorage.clear(); } catch(e){}')
    except Exception:
        pass
    if login:
        do_login('demo', 'demo123')
        assert d.locator('#task-list')
    return d

def do_login(user, pw):
    d = driver()
    d.goto(BASE + '/login')
    d.locator('#username').fill(user)
    d.locator('#password').fill(pw)
    d.locator('#login-btn').click()

def type_task(text):
    box = driver().locator('#task-input')
    box.clear()
    box.fill(text)

def add_task(text):
    type_task(text)
    driver().locator('#add-btn').click()

def titles():
    return [e.inner_text() for e in driver().locator('#task-list .task-title')]

def remaining():
    return int(driver().locator('#remaining').text)

def row(n):
    return driver().locator(f'task-{n}')

def is_done(n):
    return 'done' in row(n).get_attribute('class').split()

def test_login_success():
    d = fresh(login=False)
    do_login('demo', 'demo123')
    assert d.url.rstrip('/') == BASE.rstrip('/'), d.url
    assert d.locator('#add-form')

def test_login_invalid_password_rejected():
    d = fresh(login=False)
    do_login('demo', 'wrong')
    assert d.locator('#login-error').text == 'Invalid credentials'
    d.goto(BASE + '/')
    assert d.url.endswith('/login')

def test_login_wrong_username_rejected():
    d = fresh(login=False)
    do_login('other', 'demo123')
    assert d.locator('#login-error').text == 'Invalid credentials'

def test_login_page_no_error_initially():
    d = fresh(login=False)
    d.goto(BASE + '/login')
    assert d.locator('#login-form')
    assert d.locator('#login-error') == []

def test_protected_page_redirects_to_login():
    d = fresh(login=False)
    d.goto(BASE + '/')
    assert d.url.endswith('/login'), d.url

def test_logout_ends_session():
    d = fresh()
    d.locator('#logout').click()
    assert d.url.endswith('/login')
    d.goto(BASE + '/')
    assert d.url.endswith('/login')

def test_add_task_appears():
    fresh()
    add_task('Buy milk')
    assert titles() == ['Buy milk'] and remaining() == 1

def test_add_trims_whitespace():
    fresh()
    add_task('  padded  ')
    assert titles() == ['padded']

def test_add_multiple_preserves_order():
    fresh()
    add_task('A')
    add_task('B')
    add_task('C')
    assert titles() == ['A', 'B', 'C'] and remaining() == 3

def test_add_button_disabled_when_empty():
    fresh()
    assert not driver().locator('#add-btn').is_enabled()

def test_add_button_enabled_after_typing():
    fresh()
    type_task('x')
    assert driver().locator('#add-btn').is_enabled()

def test_add_button_disabled_for_whitespace_only():
    fresh()
    type_task('     ')
    assert not driver().locator('#add-btn').is_enabled()

def test_add_button_enabled_at_100_chars():
    fresh()
    type_task('a' * 100)
    assert driver().locator('#add-btn').is_enabled()

def test_add_button_disabled_at_101_chars():
    fresh()
    type_task('a' * 101)
    assert not driver().locator('#add-btn').is_enabled()

def test_char_counter_updates_while_typing():
    fresh()
    assert driver().locator('#char-count').text == '100'
    type_task('abcde')
    assert driver().locator('#char-count').text == '95'

def test_char_counter_goes_negative_when_too_long():
    fresh()
    type_task('a' * 103)
    assert driver().locator('#char-count').text == '-3'

def _force_submit():
    """Bypass the client-side validator by submitting the form from script."""
    d = driver()
    d.execute_script("window.__marker = 1; document.getElementById('add-form').submit();")
    wait().until(lambda x: x.execute_script('return window.__marker === undefined;'))

def test_server_rejects_empty_title():
    fresh()
    type_task('   ')
    _force_submit()
    assert driver().locator('#flash').text == 'Title is required'
    assert titles() == []

def test_server_rejects_title_over_100():
    fresh()
    type_task('a' * 101)
    _force_submit()
    assert driver().locator('#flash').text == 'Title too long'
    assert titles() == []

def test_server_accepts_title_of_exactly_100():
    fresh()
    type_task('a' * 100)
    _force_submit()
    assert titles() == ['a' * 100]

def test_toggle_marks_done_and_updates_remaining():
    fresh()
    add_task('A')
    add_task('B')
    row(1).locator('.toggle-btn').click()
    assert is_done(1) and (not is_done(2)) and (remaining() == 1)

def test_toggle_twice_restores_active():
    fresh()
    add_task('A')
    row(1).locator('.toggle-btn').click()
    row(1).locator('.toggle-btn').click()
    assert not is_done(1) and remaining() == 1

def test_delete_removes_only_target():
    fresh()
    add_task('A')
    add_task('B')
    add_task('C')
    row(2).locator('.delete-btn').click()
    assert titles() == ['A', 'C'] and remaining() == 2

def test_filter_active_shows_only_active():
    fresh()
    add_task('A')
    add_task('B')
    row(1).locator('.toggle-btn').click()
    driver().locator('#filter-active').click()
    assert titles() == ['B']

def test_filter_done_shows_only_done():
    fresh()
    add_task('A')
    add_task('B')
    row(1).locator('.toggle-btn').click()
    driver().locator('#filter-done').click()
    assert titles() == ['A']

def test_filter_all_shows_everything():
    fresh()
    add_task('A')
    add_task('B')
    row(1).locator('.toggle-btn').click()
    driver().locator('#filter-done').click()
    driver().locator('#filter-all').click()
    assert titles() == ['A', 'B']

def test_remaining_ignores_active_filter():
    fresh()
    add_task('A')
    add_task('B')
    add_task('C')
    row(1).locator('.toggle-btn').click()
    driver().locator('#filter-done').click()
    assert remaining() == 2

def test_clear_completed_removes_only_done():
    fresh()
    add_task('A')
    add_task('B')
    row(2).locator('.toggle-btn').click()
    driver().locator('#clear-completed').click()
    assert titles() == ['A'] and remaining() == 1

def _all():
    return {k: v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)}
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    tests = _all()
    if a.list:
        print('\n'.join(tests))
        sys.exit(0)
    if a.only:
        tests = {k: v for k, v in tests.items() if k in a.only}
    failed = 0
    try:
        for n, f in tests.items():
            try:
                f()
                print('PASS', n, flush=True)
            except Exception as e:
                failed += 1
                print('FAIL', n, type(e).__name__, str(e).splitlines()[0][:100] if str(e) else '', flush=True)
    finally:
        if _driver is not None:
            try:
                _driver.close()
            except Exception:
                pass
    sys.exit(1 if failed else 0)