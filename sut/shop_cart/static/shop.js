// Client-side dynamic interaction and live cart validation
document.addEventListener("DOMContentLoaded", function() {
    var couponInput = document.getElementById("coupon-input");
    var applyBtn = document.getElementById("apply-coupon-btn");
    var checkoutBtn = document.getElementById("checkout-btn");

    if (couponInput && applyBtn) {
        applyBtn.disabled = couponInput.value.trim().length === 0;
        couponInput.addEventListener("input", function() {
            applyBtn.disabled = couponInput.value.trim().length === 0;
        });
    }

    // Live quantity boundary validation
    var qtyInputs = document.querySelectorAll('input[type="number"][name="quantity"]');
    qtyInputs.forEach(function(inp) {
        inp.addEventListener("input", function() {
            var val = parseInt(inp.value, 10);
            var max = parseInt(inp.getAttribute("max"), 10);
            var min = parseInt(inp.getAttribute("min"), 10) || 1;
            var form = inp.closest("form");
            var btn = form ? form.querySelector('button[type="submit"]') : null;
            if (btn) {
                btn.disabled = (isNaN(val) || val < min || val > max);
            }
        });
    });
});
