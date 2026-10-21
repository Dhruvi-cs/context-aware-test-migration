#!/usr/bin/env python
"""Run the 27 target Playwright tests against an ephemeral TaskBoard SUT instance."""
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_free_port():
    # Pick a port between 8080 and 8999 that is free and safe in Chromium
    for port in range(8081, 8990):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 8088

def main():
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    sut_app = os.path.join(ROOT, "sut", "todo_app", "app.py")

    print(f"=== Starting TaskBoard SUT on {base_url} ===")
    env = dict(os.environ, PORT=str(port), BASE_URL=base_url)
    server_proc = subprocess.Popen(
        [sys.executable, sut_app],
        cwd=os.path.join(ROOT, "sut", "todo_app"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        healthy = False
        for _ in range(50):
            try:
                res = urlopen(f"{base_url}/health", timeout=1).read().decode()
                if "ok" in res:
                    healthy = True
                    break
            except Exception:
                time.sleep(0.1)

        if not healthy:
            print(f"[FAIL] Could not connect to SUT on port {port}")
            sys.exit(1)

        print(f"=== Running 27 Migrated Playwright Tests against {base_url} ===")
        test_script = os.path.join(ROOT, "tests_tgt", "target_playwright.py")
        res = subprocess.run([sys.executable, test_script], cwd=ROOT, env=env)
        if res.returncode == 0:
            print("\n[SUCCESS] All 27 Playwright test scenarios passed.")
        else:
            print("\n[FAIL] Some Playwright tests failed.")
        sys.exit(res.returncode)
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

if __name__ == "__main__":
    main()
