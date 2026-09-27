"""
E-Commerce Discount Module
Calculates the combined discount amount from coupon codes and flat vouchers.

NOTE: This module contains a deliberately planted bug.
      The calculate_discount function does NOT clamp the total discount
      to the cart subtotal. When combined discounts exceed the subtotal,
      a negative value is returned, causing downstream failures in
      tax calculation (ValueError: taxable subtotal cannot be negative).
"""
from __future__ import annotations
from typing import Optional

# Coupon registry: code → percentage discount (0.0–1.0)
COUPON_REGISTRY: dict[str, float] = {
    "SAVE10": 0.10,   # 10% off
    "SAVE20": 0.20,   # 20% off
    "VIP50":  0.50,   # 50% off (VIP customers)
}

# Voucher registry: code → flat dollar discount
VOUCHER_REGISTRY: dict[str, float] = {
    "GIFT50":   50.00,   # $50 flat discount
    "BONUS100": 100.00,  # $100 flat discount
}


def calculate_discount(
    subtotal: float,
    coupon_code: Optional[str] = None,
    voucher_code: Optional[str] = None,
) -> float:
    """
    Calculate the total discount to apply to the order.

    Args:
        subtotal:     The cart subtotal before any discounts.
        coupon_code:  Optional percentage-based coupon code.
        voucher_code: Optional flat-value voucher code.

    Returns:
        The combined discount amount in dollars.

    BUG: The returned discount is NOT clamped to the subtotal.
         If coupon + voucher exceed the subtotal, the caller receives a
         discount larger than the order value, producing a negative
         taxable subtotal downstream.
    """
    total_discount: float = 0.0

    if coupon_code and coupon_code in COUPON_REGISTRY:
        percentage = COUPON_REGISTRY[coupon_code]
        total_discount += subtotal * percentage

    if voucher_code and voucher_code in VOUCHER_REGISTRY:
        flat_amount = VOUCHER_REGISTRY[voucher_code]
        total_discount += flat_amount

    # ⚠ ROOT CAUSE DEFECT: Missing floor clamp.
    # Correct logic should be: min(total_discount, subtotal)
    return round(total_discount, 2)
