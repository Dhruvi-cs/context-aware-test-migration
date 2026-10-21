#!/usr/bin/env python
"""Evaluate the AST Rule-Based Transpiled Suite against the TaskBoard SUT with real-time logging."""
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_free_port():
    for port in range(8081, 8990):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 8089

def main():
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    sut_app = os.path.join(ROOT, "sut", "todo_app", "app.py")
    env = dict(os.environ, PORT=str(port), BASE_URL=base_url)

    server_proc = subprocess.Popen([sys.executable, sut_app], cwd=os.path.join(ROOT, "sut", "todo_app"),
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                if "ok" in urlopen(f"{base_url}/health", timeout=1).read().decode():
                    break
            except Exception:
                time.sleep(0.1)
        else:
            print("Failed to start SUT server")
            sys.exit(1)

        print(f"SUT running on {base_url}")
        test_script = os.path.join(ROOT, "tests_tgt", "target_rule_based.py")
        p = subprocess.Popen([sys.executable, test_script], cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        passed = 0
        failed = 0
        for line in p.stdout:
            print(line, end="", flush=True)
            if line.startswith("PASS"):
                passed += 1
            elif line.startswith("FAIL"):
                failed += 1
        p.wait()
        total = passed + failed
        print(f"\n=== SUMMARY ===")
        print(f"Total: {total}, Passed: {passed}, Failed: {failed}")
        if total > 0:
            print(f"Pass Rate (EXR): {passed/total*100:.1f}%")
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3)
        except Exception:
            server_proc.kill()

if __name__ == "__main__":
    main()
