"""
Test Suite for the E-Commerce Checkout Pipeline.

Pre-fix (bug active) expected results:
  test_standard_checkout_without_discount        → PASS
  test_standard_percentage_discount              → PASS
  test_stacked_discount_exceeds_subtotal         → FAIL (ValueError from tax module)
  test_large_voucher_zero_balance_edge_case      → FAIL (ValueError from tax module)

Post-fix (discount clamped) expected results:
  All 4 tests → PASS
"""
import pytest
from .cart import Cart, CartItem
from .checkout import CheckoutService
from .discount import calculate_discount


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_cart(*items: tuple) -> Cart:
    """Create a Cart from (item_id, name, price, quantity) tuples."""
    cart = Cart()
    for item_id, name, price, qty in items:
        cart.add_item(CartItem(item_id=item_id, name=name, price=price, quantity=qty))
    return cart


# ---------------------------------------------------------------------------
# Test 1: Standard checkout, no promotions — should always PASS
# ---------------------------------------------------------------------------

def test_standard_checkout_without_discount():
    """A plain checkout with no coupon or voucher produces the correct totals."""
    cart = make_cart(("item-001", "Wireless Headphones", 79.99, 1))
    service = CheckoutService()

    summary = service.process_checkout(cart)

    assert summary.subtotal == 79.99
    assert summary.discount_amount == 0.0
    assert summary.taxable_subtotal == 79.99
    assert summary.tax_amount == round(79.99 * 0.08, 2)
    assert summary.final_total == round(79.99 * 1.08, 2)


# ---------------------------------------------------------------------------
# Test 2: Small percentage discount — discount < subtotal — should always PASS
# ---------------------------------------------------------------------------

def test_standard_percentage_discount():
    """A 20% coupon on a $100 cart produces a $20 discount and valid tax."""
    cart = make_cart(("item-002", "Mechanical Keyboard", 100.00, 1))
    service = CheckoutService()

    summary = service.process_checkout(cart, coupon_code="SAVE20")

    assert summary.subtotal == 100.00
    assert summary.discount_amount == 20.00
    assert summary.taxable_subtotal == 80.00
    assert summary.tax_amount == round(80.00 * 0.08, 2)
    assert summary.final_total == round(80.00 * 1.08, 2)


# ---------------------------------------------------------------------------
# Test 3: Stacked coupon + voucher exceeds subtotal — FAILS pre-fix
# ---------------------------------------------------------------------------

def test_stacked_discount_exceeds_subtotal():
    """
    A 20% coupon + $50 GIFT voucher on a $60 cart produces:
      coupon discount = $12.00
      voucher discount = $50.00
      total discount = $62.00 > subtotal $60.00
    Pre-fix: calculate_sales_tax receives -$2.00 → ValueError.
    Post-fix: discount is clamped to $60.00 → taxable subtotal = $0.00.
    """
    cart = make_cart(("item-003", "USB-C Hub", 60.00, 1))
    service = CheckoutService()

    summary = service.process_checkout(cart, coupon_code="SAVE20", voucher_code="GIFT50")

    # These assertions are only reachable post-fix.
    assert summary.subtotal == 60.00
    assert summary.discount_amount == 60.00   # clamped from 62.00
    assert summary.taxable_subtotal == 0.00
    assert summary.tax_amount == 0.00
    assert summary.final_total == 0.00


# ---------------------------------------------------------------------------
# Test 4: Voucher alone exceeds subtotal — FAILS pre-fix
# ---------------------------------------------------------------------------

def test_large_voucher_zero_balance_edge_case():
    """
    A single $50 GIFT voucher on a $30 item:
      voucher discount = $50.00 > subtotal $30.00
    Pre-fix: taxable subtotal = -$20.00 → ValueError.
    Post-fix: discount clamped to $30.00, total = $0.00.
    """
    cart = make_cart(("item-004", "Phone Case", 30.00, 1))
    service = CheckoutService()

    summary = service.process_checkout(cart, voucher_code="GIFT50")

    assert summary.subtotal == 30.00
    assert summary.discount_amount == 30.00   # clamped from 50.00
    assert summary.taxable_subtotal == 0.00
    assert summary.tax_amount == 0.00
    assert summary.final_total == 0.00
