#!/usr/bin/env python
"""Run the unit tests and reference HTTP verification suite.
Automatically starts a local ephemeral SUT instance on a clean port for testing.
"""
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def main():
    print("=== Running Metric Unit Tests ===")
    r1 = subprocess.run([sys.executable, "-m", "pytest", "tests/test_metrics.py", "-v"], cwd=ROOT)
    if r1.returncode != 0:
        print("[FAIL] Metric unit tests failed!")
        sys.exit(r1.returncode)

    print("\n=== Running Reference SUT HTTP Tests with Ephemeral Server ===")
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    sut_app = os.path.join(ROOT, "sut", "todo_app", "app.py")

    env = dict(os.environ, PORT=str(port), BASE_URL=base_url)
    server_proc = subprocess.Popen(
        [sys.executable, sut_app],
        cwd=os.path.join(ROOT, "sut", "todo_app"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        # Wait for server to become healthy
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
            print(f"[FAIL] Could not start ephemeral SUT server on port {port}")
            sys.exit(1)

        print(f"Ephemeral SUT running at {base_url} (healthy)")
        r2 = subprocess.run(
            [sys.executable, "-m", "pytest", "sut/todo_app/reference_http_tests.py", "-v"],
            cwd=ROOT,
            env=env
        )
        if r2.returncode != 0:
            print("[FAIL] Reference HTTP tests failed!")
            sys.exit(r2.returncode)

        print("\n[SUCCESS] All baseline verification tests passed cleanly.")
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

if __name__ == "__main__":
    main()
