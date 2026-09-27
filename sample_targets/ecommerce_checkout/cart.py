"""
E-Commerce Cart Module
Provides CartItem and Cart data models for the checkout pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class CartItem:
    """Represents a single line item in the shopping cart."""
    item_id: str
    name: str
    price: float
    quantity: int

    @property
    def total(self) -> float:
        """Line-item total (price × quantity)."""
        return round(self.price * self.quantity, 2)


class Cart:
    """Shopping cart that holds a collection of CartItems."""

    def __init__(self) -> None:
        self.items: List[CartItem] = []

    def add_item(self, item: CartItem) -> None:
        """Add a CartItem to the cart."""
        if item.quantity <= 0:
            raise ValueError(f"Quantity for item '{item.name}' must be positive.")
        if item.price < 0:
            raise ValueError(f"Price for item '{item.name}' cannot be negative.")
        self.items.append(item)

    def subtotal(self) -> float:
        """Sum of all line-item totals."""
        return round(sum(item.total for item in self.items), 2)

    def item_count(self) -> int:
        """Total number of individual units in the cart."""
        return sum(item.quantity for item in self.items)

    def __repr__(self) -> str:
        return f"Cart(items={len(self.items)}, subtotal={self.subtotal()})"
