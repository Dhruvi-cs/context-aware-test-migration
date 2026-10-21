"""Baseline verification tests for ShopCart SUT."""
import os, sys, requests, subprocess, time

def test_shop_cart_baseline():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app_path = os.path.join(root, "sut", "shop_cart", "app.py")
    port = 8095
    base = f"http://127.0.0.1:{port}"
    env = dict(os.environ, PORT=str(port))
    p = subprocess.Popen([sys.executable, app_path], cwd=os.path.join(root, "sut", "shop_cart"), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                if requests.get(f"{base}/health", timeout=1).text == "ok":
                    break
            except Exception:
                time.sleep(0.1)
        else:
            assert False, "ShopCart failed to start"
            
        s = requests.Session()
        r = s.get(base + "/")
        assert "Tech Shop" in r.text
        assert "Mechanical Keyboard" in r.text
        
        # Add to cart
        r = s.post(base + "/add-to-cart/1", data={"quantity": "2"})
        assert r.status_code == 200
        assert 'id="subtotal">200<' in r.text
        assert 'id="tax">16.0<' in r.text
        assert 'id="grand-total">216.0<' in r.text
        
        # Apply coupon
        r = s.post(base + "/apply-coupon", data={"coupon": "SAVE10"})
        assert 'id="discount">20.0<' in r.text
        assert 'id="grand-total">194.4<' in r.text
        
        # Checkout
        r = s.post(base + "/checkout")
        assert "Order placed successfully!" in r.text
        
        # Reset
        r = s.post(base + "/__reset")
        assert r.json()["status"] == "reset"
        print("ShopCart baseline verified successfully!")
    finally:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()

if __name__ == "__main__":
    test_shop_cart_baseline()
