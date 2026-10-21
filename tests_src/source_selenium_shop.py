"""Source Selenium tests for ShopCart SUT (Framework Fs = Selenium WebDriver / Python).
15 end-to-end shopping cart and checkout scenarios.
"""
import argparse, os, sys, urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
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
        _driver.implicitly_wait(3)
    return _driver

def reset_server():
    urllib.request.urlopen(urllib.request.Request(BASE + "/__reset", method="POST", data=b""), timeout=5).read()

def fresh():
    reset_server()
    d = driver()
    d.get(BASE + "/")
    d.delete_all_cookies()
    try:
        d.execute_script("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
    except Exception:
        pass
    assert d.find_element(By.ID, "catalog")
    return d

def click_and_wait_nav(element):
    d = driver()
    d.execute_script("window.__marker = 1;")
    element.click()
    WebDriverWait(d, 5).until(lambda x: x.execute_script("return window.__marker === undefined;"))

# ----------------- 15 Scenarios -----------------

def test_shop_catalog_renders_three_products():
    d = fresh()
    assert len(d.find_elements(By.CSS_SELECTOR, ".product-card")) == 3
    assert "Mechanical Keyboard" in d.find_element(By.CSS_SELECTOR, "#product-1 .product-name").text

def test_shop_cart_initially_empty():
    d = fresh()
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "0"
    assert d.find_element(By.ID, "empty-cart-msg").is_displayed()
    assert not d.find_element(By.ID, "checkout-btn").is_enabled()

def test_shop_add_single_item_to_cart():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "1"
    assert d.find_element(By.CSS_SELECTOR, "#cart-item-1 .item-qty").text.strip() == "1"
    assert d.find_element(By.ID, "subtotal").text.strip() == "100"

def test_shop_add_multiple_quantity():
    d = fresh()
    inp = d.find_element(By.ID, "qty-2")
    inp.clear(); inp.send_keys("3")
    click_and_wait_nav(d.find_element(By.ID, "add-btn-2"))
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "3"
    assert d.find_element(By.ID, "subtotal").text.strip() == "150"

def test_shop_add_different_products():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    click_and_wait_nav(d.find_element(By.ID, "add-btn-3"))
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "2"
    assert d.find_element(By.ID, "subtotal").text.strip() == "130"

def test_shop_tax_calculation_at_eight_percent():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    assert d.find_element(By.ID, "tax").text.strip() == "8.0"
    assert d.find_element(By.ID, "grand-total").text.strip() == "108.0"

def test_shop_remove_item_from_cart():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    click_and_wait_nav(d.find_element(By.ID, "add-btn-2"))
    click_and_wait_nav(d.find_element(By.ID, "remove-btn-1"))
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "1"
    assert d.find_element(By.ID, "subtotal").text.strip() == "50"

def test_shop_apply_valid_coupon_save10():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    inp = d.find_element(By.ID, "coupon-input")
    inp.clear(); inp.send_keys("SAVE10")
    click_and_wait_nav(d.find_element(By.ID, "apply-coupon-btn"))
    assert d.find_element(By.ID, "discount").text.strip() == "10.0"
    assert d.find_element(By.ID, "grand-total").text.strip() == "97.2"

def test_shop_apply_valid_coupon_save20():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    inp = d.find_element(By.ID, "coupon-input")
    inp.clear(); inp.send_keys("save20")
    click_and_wait_nav(d.find_element(By.ID, "apply-coupon-btn"))
    assert d.find_element(By.ID, "discount").text.strip() == "20.0"
    assert d.find_element(By.ID, "grand-total").text.strip() == "86.4"

def test_shop_apply_invalid_coupon_rejected():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    inp = d.find_element(By.ID, "coupon-input")
    inp.clear(); inp.send_keys("BOGUS")
    click_and_wait_nav(d.find_element(By.ID, "apply-coupon-btn"))
    assert "Invalid coupon code" in d.find_element(By.ID, "shop-flash").text
    assert len(d.find_elements(By.ID, "discount")) == 0

def test_shop_coupon_button_disabled_when_empty():
    d = fresh()
    assert not d.find_element(By.ID, "apply-coupon-btn").is_enabled()

def test_shop_coupon_button_enabled_after_typing():
    d = fresh()
    d.find_element(By.ID, "coupon-input").send_keys("A")
    assert d.find_element(By.ID, "apply-coupon-btn").is_enabled()

def test_shop_quantity_exceeding_stock_rejected():
    d = fresh()
    inp = d.find_element(By.ID, "qty-1")
    inp.clear(); inp.send_keys("6")
    d.execute_script("arguments[0].dispatchEvent(new Event('input'));", inp)
    assert not d.find_element(By.ID, "add-btn-1").is_enabled()
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "0"

def test_shop_checkout_success():
    d = fresh()
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    click_and_wait_nav(d.find_element(By.ID, "checkout-btn"))
    assert d.find_element(By.ID, "order-success").is_displayed()
    assert d.find_element(By.ID, "cart-item-count").text.strip() == "0"

def test_shop_checkout_reduces_inventory():
    d = fresh()
    inp = d.find_element(By.ID, "qty-1")
    inp.clear(); inp.send_keys("2")
    click_and_wait_nav(d.find_element(By.ID, "add-btn-1"))
    click_and_wait_nav(d.find_element(By.ID, "checkout-btn"))
    assert d.find_element(By.CSS_SELECTOR, "#product-1 .product-stock").text.strip() == "3"

def _all():
    return {k: v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)}

if __name__ == "__main__":
    tests = _all()
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
        if _driver is not None:
            try: _driver.quit()
            except Exception: pass
    sys.exit(1 if failed else 0)
