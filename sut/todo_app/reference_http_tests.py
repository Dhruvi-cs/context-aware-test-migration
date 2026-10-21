"""HTTP-level reference tests for the TaskBoard SUT (NOT the migration subjects).
Used to validate the SUT and the mutation/kill-matrix pipeline without a browser.
Usage: BASE_URL=http://127.0.0.1:5000 python reference_http_tests.py [--list]"""
import argparse, os, re, sys
import requests

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def fresh(login=True):
    s = requests.Session()
    s.post(BASE + "/__reset", timeout=5)
    if login:
        r = s.post(BASE + "/login", data={"username": "demo", "password": "demo123"}, timeout=5)
        assert r.status_code == 200 and 'id="task-list"' in r.text
    return s


def titles(html):
    return re.findall(r'class="task-title">(.*?)</span>', html)


def remaining(html):
    return int(re.search(r'id="remaining">(\d+)<', html).group(1))


def add(s, title):
    return s.post(BASE + "/add", data={"title": title}, timeout=5)


def test_health():
    assert requests.get(BASE + "/health", timeout=5).text == "ok"

def test_login_page_renders():
    r = requests.get(BASE + "/login", timeout=5)
    assert r.status_code == 200 and 'id="login-form"' in r.text and "login-error" not in r.text

def test_login_required_redirect():
    s = fresh(login=False)
    r = s.get(BASE + "/", allow_redirects=False, timeout=5)
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")

def test_login_invalid_rejected():
    s = fresh(login=False)
    r = s.post(BASE + "/login", data={"username": "demo", "password": "nope"}, timeout=5)
    assert "Invalid credentials" in r.text
    assert s.get(BASE + "/", allow_redirects=False, timeout=5).status_code == 302

def test_login_wrong_user_rejected():
    s = fresh(login=False)
    r = s.post(BASE + "/login", data={"username": "root", "password": "demo123"}, timeout=5)
    assert "Invalid credentials" in r.text

def test_logout_clears_session():
    s = fresh()
    s.get(BASE + "/logout", timeout=5)
    assert s.get(BASE + "/", allow_redirects=False, timeout=5).status_code == 302

def test_add_task():
    s = fresh()
    r = add(s, "Buy milk")
    assert titles(r.text) == ["Buy milk"] and remaining(r.text) == 1

def test_add_trims_whitespace():
    s = fresh()
    assert titles(add(s, "  padded  ").text) == ["padded"]

def test_add_empty_rejected():
    s = fresh()
    r = add(s, "   ")
    assert "Title is required" in r.text and titles(r.text) == []

def test_title_length_boundary():
    s = fresh()
    assert len(titles(add(s, "a" * 100).text)) == 1
    r = add(s, "b" * 101)
    assert "Title too long" in r.text and len(titles(r.text)) == 1

def test_ids_increment():
    s = fresh()
    add(s, "one"); add(s, "two")
    r = s.get(BASE + "/", timeout=5)
    assert 'id="task-1"' in r.text and 'id="task-2"' in r.text

def test_toggle_twice():
    s = fresh()
    add(s, "one")
    r = s.post(BASE + "/toggle/1", timeout=5)
    assert remaining(r.text) == 0 and 'class="task done"' in r.text
    r = s.post(BASE + "/toggle/1", timeout=5)
    assert remaining(r.text) == 1

def test_toggle_only_target():
    s = fresh()
    add(s, "A"); add(s, "B")
    r = s.post(BASE + "/toggle/2", timeout=5)
    assert remaining(r.text) == 1 and 'id="task-1" class="task"' in r.text

def test_filter_active_and_done():
    s = fresh()
    add(s, "A"); add(s, "B")
    s.post(BASE + "/toggle/1", timeout=5)
    assert titles(s.get(BASE + "/?filter=active", timeout=5).text) == ["B"]
    assert titles(s.get(BASE + "/?filter=done", timeout=5).text) == ["A"]
    assert titles(s.get(BASE + "/?filter=all", timeout=5).text) == ["A", "B"]

def test_delete_only_target():
    s = fresh()
    add(s, "A"); add(s, "B")
    assert titles(s.post(BASE + "/delete/1", timeout=5).text) == ["B"]

def test_clear_completed():
    s = fresh()
    add(s, "A"); add(s, "B")
    s.post(BASE + "/toggle/2", timeout=5)
    r = s.post(BASE + "/clear-completed", timeout=5)
    assert titles(r.text) == ["A"] and remaining(r.text) == 1

def test_mutations_require_login():
    s = fresh(login=False)
    for path in ("/add", "/toggle/1", "/delete/1", "/clear-completed"):
        r = s.post(BASE + path, data={"title": "x"}, allow_redirects=False, timeout=5)
        assert r.status_code == 302, path


def _all():
    return {k: v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--list", action="store_true")
    a = ap.parse_args(); tests = _all()
    if a.list:
        print("\n".join(tests)); sys.exit(0)
    failed = 0
    for n, f in tests.items():
        try:
            f(); print("PASS", n)
        except Exception as e:
            failed += 1; print("FAIL", n, type(e).__name__, str(e)[:100])
    sys.exit(1 if failed else 0)
