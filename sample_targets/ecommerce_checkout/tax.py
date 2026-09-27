"""
E-Commerce Tax Module
Computes sales tax on a taxable subtotal.
Raises ValueError if a negative subtotal is provided — this is the guard
that surfaces the upstream discount-clamp bug during checkout.
"""
from __future__ import annotations

DEFAULT_TAX_RATE: float = 0.08  # 8% sales tax


def calculate_sales_tax(taxable_amount: float, rate: float = DEFAULT_TAX_RATE) -> float:
    """
    Calculate sales tax for the given taxable amount.

    Args:
        taxable_amount: The dollar amount subject to tax.  Must be >= 0.
        rate:           Tax rate as a decimal fraction (default 8%).

    Returns:
        Tax amount in dollars, rounded to two decimal places.

    Raises:
        ValueError: If taxable_amount is negative.
        ValueError: If rate is outside the range [0, 1].
    """
    if taxable_amount < 0:
        raise ValueError(
            f"Taxable subtotal cannot be negative. Got: {taxable_amount:.2f}. "
            "Check that the applied discount does not exceed the order subtotal."
        )
    if not (0.0 <= rate <= 1.0):
        raise ValueError(f"Tax rate must be between 0 and 1. Got: {rate}")

    return round(taxable_amount * rate, 2)
