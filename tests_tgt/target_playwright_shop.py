"""Target Playwright tests for ShopCart SUT (Framework Ft = Playwright/Python).
15 end-to-end shopping cart and checkout scenarios.
"""
import argparse, os, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
_pw = None; _browser = None; _context = None; _page = None

def get_page():
    global _pw, _browser, _context, _page
    if _pw is None:
        _pw = sync_playwright().start()
        _browser = _pw.chromium.launch(headless=os.environ.get("HEADLESS", "1") != "0")
        _context = _browser.new_context()
        _page = _context.new_page()
        _page.set_default_timeout(3000)
    return _page

def reset_server():
    urllib.request.urlopen(urllib.request.Request(BASE + "/__reset", method="POST", data=b""), timeout=5).read()

def fresh():
    reset_server()
    p = get_page()
    _context.clear_cookies()
    try:
        p.evaluate("try { localStorage.clear(); sessionStorage.clear(); } catch(e){}")
    except Exception:
        pass
    p.goto(BASE + "/")
    p.locator("#catalog").wait_for(state="attached")
    return p

def click_nav(locator):
    p = get_page()
    with p.expect_navigation():
        locator.click()

# ----------------- 15 Scenarios -----------------

def test_shop_catalog_renders_three_products():
    p = fresh()
    assert len(p.locator(".product-card").all()) == 3
    assert "Mechanical Keyboard" in p.locator("#product-1 .product-name").inner_text()

def test_shop_cart_initially_empty():
    p = fresh()
    assert p.locator("#cart-item-count").inner_text().strip() == "0"
    assert p.locator("#empty-cart-msg").is_visible()
    assert p.locator("#checkout-btn").is_disabled()

def test_shop_add_single_item_to_cart():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))
    assert p.locator("#cart-item-count").inner_text().strip() == "1"
    assert p.locator("#cart-item-1 .item-qty").inner_text().strip() == "1"
    assert p.locator("#subtotal").inner_text().strip() == "100"

def test_shop_add_multiple_quantity():
    p = fresh()
    p.locator("#qty-2").fill("3")
    click_nav(p.locator("#add-btn-2"))
    assert p.locator("#cart-item-count").inner_text().strip() == "3"
    assert p.locator("#subtotal").inner_text().strip() == "150"

def test_shop_add_different_products():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))
    click_nav(p.locator("#add-btn-3"))
    assert p.locator("#cart-item-count").inner_text().strip() == "2"
    assert p.locator("#subtotal").inner_text().strip() == "130"

def test_shop_tax_calculation_at_eight_percent():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))  # $100
    assert p.locator("#tax").inner_text().strip() == "8.0"
    assert p.locator("#grand-total").inner_text().strip() == "108.0"

def test_shop_remove_item_from_cart():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))
    click_nav(p.locator("#add-btn-2"))
    click_nav(p.locator("#remove-btn-1"))
    assert p.locator("#cart-item-count").inner_text().strip() == "1"
    assert p.locator("#subtotal").inner_text().strip() == "50"

def test_shop_apply_valid_coupon_save10():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))  # $100
    p.locator("#coupon-input").fill("SAVE10")
    click_nav(p.locator("#apply-coupon-btn"))
    assert p.locator("#discount").inner_text().strip() == "10.0"
    assert p.locator("#grand-total").inner_text().strip() == "97.2"

def test_shop_apply_valid_coupon_save20():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))  # $100
    p.locator("#coupon-input").fill("save20")  # case-insensitive
    click_nav(p.locator("#apply-coupon-btn"))
    assert p.locator("#discount").inner_text().strip() == "20.0"
    assert p.locator("#grand-total").inner_text().strip() == "86.4"

def test_shop_apply_invalid_coupon_rejected():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))
    p.locator("#coupon-input").fill("BOGUS")
    click_nav(p.locator("#apply-coupon-btn"))
    assert "Invalid coupon code" in p.locator("#shop-flash").inner_text()
    assert not p.locator("#discount").is_visible()

def test_shop_coupon_button_disabled_when_empty():
    p = fresh()
    assert p.locator("#apply-coupon-btn").is_disabled()

def test_shop_coupon_button_enabled_after_typing():
    p = fresh()
    p.locator("#coupon-input").fill("A")
    assert p.locator("#apply-coupon-btn").is_enabled()

def test_shop_quantity_exceeding_stock_rejected():
    p = fresh()
    p.locator("#qty-1").fill("6")  # stock is 5
    p.locator("#qty-1").dispatch_event("input")
    assert p.locator("#add-btn-1").is_disabled()
    assert p.locator("#cart-item-count").inner_text().strip() == "0"

def test_shop_checkout_success():
    p = fresh()
    click_nav(p.locator("#add-btn-1"))
    click_nav(p.locator("#checkout-btn"))
    assert p.locator("#order-success").is_visible()
    assert p.locator("#cart-item-count").inner_text().strip() == "0"

def test_shop_checkout_reduces_inventory():
    p = fresh()
    p.locator("#qty-1").fill("2")
    click_nav(p.locator("#add-btn-1"))
    click_nav(p.locator("#checkout-btn"))
    # In stock should now be 3 (5 - 2)
    assert p.locator("#product-1 .product-stock").inner_text().strip() == "3"

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
        if _browser is not None:
            try: _browser.close()
            except Exception: pass
        if _pw is not None:
            try: _pw.stop()
            except Exception: pass
    sys.exit(1 if failed else 0)
