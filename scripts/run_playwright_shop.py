#!/usr/bin/env python
"""Run the 15 Playwright tests for ShopCart SUT."""
import os, socket, subprocess, sys, time
from urllib.request import urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def main():
    port = 8096
    base_url = f"http://127.0.0.1:{port}"
    sut_app = os.path.join(ROOT, "sut", "shop_cart", "app.py")
    env = dict(os.environ, PORT=str(port), BASE_URL=base_url)

    server_proc = subprocess.Popen([sys.executable, sut_app], cwd=os.path.join(ROOT, "sut", "shop_cart"),
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                if "ok" in urlopen(f"{base_url}/health", timeout=1).read().decode():
                    break
            except Exception:
                time.sleep(0.1)
        else:
            print("Failed to start ShopCart server")
            sys.exit(1)

        print(f"=== Running 15 Target Playwright Tests against {base_url} ===")
        test_script = os.path.join(ROOT, "tests_tgt", "target_playwright_shop.py")
        res = subprocess.run([sys.executable, test_script], cwd=ROOT, env=env)
        sys.exit(res.returncode)
    finally:
        server_proc.terminate()
        try: server_proc.wait(timeout=3)
        except Exception: server_proc.kill()

if __name__ == "__main__":
    main()
