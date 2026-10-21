"""ShopCart - E-commerce shopping cart web app used as the second SUT for cross-application validation."""
import os
import threading
from flask import Flask, jsonify, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = "shopcart-not-a-secret"
_lock = threading.Lock()

INITIAL_CATALOG = [
    {"id": 1, "name": "Mechanical Keyboard", "price": 100, "stock": 5},
    {"id": 2, "name": "Wireless Mouse", "price": 50, "stock": 10},
    {"id": 3, "name": "USB-C Hub", "price": 30, "stock": 8},
]

STATE = {
    "catalog": [dict(p) for p in INITIAL_CATALOG],
    "cart": {},  # product_id -> quantity
    "coupon": None,
    "discount_rate": 0.0,
    "order_placed": False
}

SHOP_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>ShopCart</title></head>
<body>
<h1>Tech Shop</h1>
{% for m in messages %}<div id="shop-flash" class="flash">{{ m }}</div>{% endfor %}
{% if order_placed %}<div id="order-success" class="success">Order placed successfully!</div>{% endif %}

<div id="catalog">
  <h2>Catalog</h2>
  {% for p in catalog %}
  <div id="product-{{ p.id }}" class="product-card">
    <span class="product-name">{{ p.name }}</span> - $<span class="product-price">{{ p.price }}</span>
    (In stock: <span class="product-stock">{{ p.stock }}</span>)
    <form method="post" action="/add-to-cart/{{ p.id }}">
      <input type="number" id="qty-{{ p.id }}" name="quantity" value="1" min="1" max="{{ p.stock }}">
      <button id="add-btn-{{ p.id }}" type="submit">Add to Cart</button>
    </form>
  </div>
  {% endfor %}
</div>

<div id="cart-section">
  <h2>Your Cart (<span id="cart-item-count">{{ total_items }}</span> items)</h2>
  {% if cart_items %}
  <ul id="cart-list">
    {% for item in cart_items %}
    <li id="cart-item-{{ item.id }}">
      <span class="item-name">{{ item.name }}</span> x <span class="item-qty">{{ item.qty }}</span>
      = $<span class="item-total">{{ item.total }}</span>
      <form method="post" action="/remove-cart/{{ item.id }}">
        <button id="remove-btn-{{ item.id }}" type="submit">Remove</button>
      </form>
    </li>
    {% endfor %}
  </ul>
  {% else %}
  <p id="empty-cart-msg">Your cart is empty.</p>
  {% endif %}

  <div id="summary">
    <p>Subtotal: $<span id="subtotal">{{ subtotal }}</span></p>
    {% if discount > 0 %}<p>Discount: -$<span id="discount">{{ discount }}</span></p>{% endif %}
    <p>Tax (8%): $<span id="tax">{{ tax }}</span></p>
    <p><strong>Total: $<span id="grand-total">{{ grand_total }}</span></strong></p>
  </div>

  <form id="coupon-form" method="post" action="/apply-coupon">
    <input id="coupon-input" name="coupon" placeholder="Coupon code">
    <button id="apply-coupon-btn" type="submit">Apply Coupon</button>
  </form>

  <form id="checkout-form" method="post" action="/checkout">
    <button id="checkout-btn" type="submit" {% if total_items == 0 %}disabled{% endif %}>Proceed to Checkout</button>
  </form>
</div>

<script src="/static/shop.js"></script>
</body></html>"""

@app.route("/health")
def health():
    return "ok"

@app.route("/__reset", methods=["POST"])
def reset():
    with _lock:
        STATE["catalog"] = [dict(p) for p in INITIAL_CATALOG]
        STATE["cart"] = {}
        STATE["coupon"] = None
        STATE["discount_rate"] = 0.0
        STATE["order_placed"] = False
        session.clear()
    return jsonify({"status": "reset"})

def _compute_totals():
    items = []
    subtotal = 0
    total_qty = 0
    for pid, qty in STATE["cart"].items():
        prod = next((p for p in STATE["catalog"] if p["id"] == pid), None)
        if prod:
            tot = prod["price"] * qty
            subtotal += tot
            total_qty += qty
            items.append({"id": pid, "name": prod["name"], "price": prod["price"], "qty": qty, "total": tot})
    discount = round(subtotal * STATE["discount_rate"], 2)
    taxable = max(0, subtotal - discount)
    tax = round(taxable * 0.08, 2)
    grand_total = round(taxable + tax, 2)
    return items, total_qty, subtotal, discount, tax, grand_total

@app.route("/")
def index():
    with _lock:
        items, total_qty, subtotal, discount, tax, grand_total = _compute_totals()
        return render_template_string(
            SHOP_TEMPLATE,
            catalog=STATE["catalog"],
            cart_items=items,
            total_items=total_qty,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            grand_total=grand_total,
            order_placed=STATE["order_placed"],
            messages=session.pop("messages", [])
        )

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    with _lock:
        prod = next((p for p in STATE["catalog"] if p["id"] == product_id), None)
        if not prod:
            session["messages"] = ["Product not found"]
            return redirect("/")
        try:
            qty = int(request.form.get("quantity", 1))
        except ValueError:
            session["messages"] = ["Invalid quantity"]
            return redirect("/")
        if qty <= 0:
            session["messages"] = ["Quantity must be at least 1"]
            return redirect("/")
        curr = STATE["cart"].get(product_id, 0)
        if curr + qty > prod["stock"]:
            session["messages"] = ["Not enough stock"]
            return redirect("/")
        STATE["cart"][product_id] = curr + qty
    return redirect("/")

@app.route("/remove-cart/<int:product_id>", methods=["POST"])
def remove_cart(product_id):
    with _lock:
        if product_id in STATE["cart"]:
            del STATE["cart"][product_id]
    return redirect("/")

@app.route("/apply-coupon", methods=["POST"])
def apply_coupon():
    code = (request.form.get("coupon") or "").strip().upper()
    with _lock:
        if code == "SAVE10":
            STATE["coupon"] = "SAVE10"
            STATE["discount_rate"] = 0.10
            session["messages"] = ["Coupon SAVE10 applied (10% off)"]
        elif code == "SAVE20":
            STATE["coupon"] = "SAVE20"
            STATE["discount_rate"] = 0.20
            session["messages"] = ["Coupon SAVE20 applied (20% off)"]
        else:
            session["messages"] = ["Invalid coupon code"]
    return redirect("/")

@app.route("/checkout", methods=["POST"])
def checkout():
    with _lock:
        if not STATE["cart"]:
            session["messages"] = ["Cart is empty"]
            return redirect("/")
        for pid, qty in STATE["cart"].items():
            prod = next(p for p in STATE["catalog"] if p["id"] == pid)
            prod["stock"] -= qty
        STATE["cart"] = {}
        STATE["order_placed"] = True
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=False)
