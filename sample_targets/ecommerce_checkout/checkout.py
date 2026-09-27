"""
E-Commerce Checkout Module
Orchestrates the checkout pipeline: cart → discount → tax → summary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .cart import Cart
from .discount import calculate_discount
from .tax import calculate_sales_tax


@dataclass
class CheckoutSummary:
    """Immutable value object representing a completed checkout calculation."""
    subtotal: float
    discount_amount: float
    taxable_subtotal: float
    tax_amount: float
    final_total: float
    coupon_code: Optional[str] = None
    voucher_code: Optional[str] = None

    def __str__(self) -> str:
        lines = [
            f"  Subtotal:          ${self.subtotal:>8.2f}",
            f"  Discount:         -${self.discount_amount:>8.2f}",
            f"  Taxable subtotal:  ${self.taxable_subtotal:>8.2f}",
            f"  Tax (8%):          ${self.tax_amount:>8.2f}",
            f"  ─────────────────────────────",
            f"  Total:             ${self.final_total:>8.2f}",
        ]
        return "\n".join(lines)


class CheckoutService:
    """Processes a cart and optional promotions into a CheckoutSummary."""

    def process_checkout(
        self,
        cart: Cart,
        coupon_code: Optional[str] = None,
        voucher_code: Optional[str] = None,
    ) -> CheckoutSummary:
        """
        Run the full checkout calculation pipeline.

        Steps:
          1. Compute cart subtotal.
          2. Apply discount (coupon + voucher).
          3. Compute taxable subtotal (subtotal − discount).
          4. Compute sales tax on taxable subtotal.
          5. Compute final total.

        Args:
            cart:         Populated Cart object.
            coupon_code:  Optional coupon code string.
            voucher_code: Optional voucher code string.

        Returns:
            CheckoutSummary with all computed values.

        Raises:
            ValueError: If the cart is empty.
            ValueError: Propagated from calculate_sales_tax when the
                        discount exceeds the subtotal (the planted bug).
        """
        if not cart.items:
            raise ValueError("Cannot checkout with an empty cart.")

        subtotal = cart.subtotal()
        discount_amount = calculate_discount(subtotal, coupon_code, voucher_code)

        # This line will produce a NEGATIVE value when the bug is active,
        # which is then passed to calculate_sales_tax() and triggers ValueError.
        taxable_subtotal = round(subtotal - discount_amount, 2)

        tax_amount = calculate_sales_tax(taxable_subtotal)
        final_total = round(taxable_subtotal + tax_amount, 2)

        return CheckoutSummary(
            subtotal=subtotal,
            discount_amount=discount_amount,
            taxable_subtotal=taxable_subtotal,
            tax_amount=tax_amount,
            final_total=final_total,
            coupon_code=coupon_code,
            voucher_code=voucher_code,
        )
