"""
Input validation for trading bot CLI parameters.
All validation raises ValueError with a human-readable message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

# Minimum notional / quantity guard-rails (conservative defaults)
MIN_QUANTITY = Decimal("0.001")
MAX_QUANTITY = Decimal("1_000_000")
MIN_PRICE = Decimal("0.01")
MAX_PRICE = Decimal("10_000_000")


def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol after basic sanity checks."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    if not symbol.isalnum():
        raise ValueError(f"Symbol '{symbol}' must be alphanumeric (e.g. BTCUSDT).")
    if len(symbol) < 5 or len(symbol) > 12:
        raise ValueError(
            f"Symbol '{symbol}' length ({len(symbol)}) looks wrong. "
            "Expected something like BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return uppercased side or raise."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate quantity. Returns Decimal."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    if qty < MIN_QUANTITY:
        raise ValueError(f"Quantity {qty} is below the minimum allowed ({MIN_QUANTITY}).")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity {qty} exceeds the maximum allowed ({MAX_QUANTITY}).")
    return qty


def validate_price(price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Validate price.
    - LIMIT / STOP_MARKET orders require a positive price.
    - MARKET orders must NOT supply a price.
    Returns Decimal or None.
    """
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        if price is not None:
            raise ValueError("Price must not be provided for MARKET orders.")
        return None

    # LIMIT / STOP_MARKET
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")

    if p <= 0:
        raise ValueError(f"Price must be positive, got {p}.")
    if p < MIN_PRICE:
        raise ValueError(f"Price {p} is below the minimum allowed ({MIN_PRICE}).")
    if p > MAX_PRICE:
        raise ValueError(f"Price {p} exceeds the maximum allowed ({MAX_PRICE}).")

    return p


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[Decimal]:
    """Validate stop_price for STOP_MARKET orders."""
    order_type = order_type.strip().upper()
    if order_type != "STOP_MARKET":
        return None
    if stop_price is None:
        raise ValueError("stop_price is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"stop_price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"stop_price must be positive, got {sp}.")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Run all validators and return a cleaned dict ready for the API layer.
    Raises ValueError describing the first problem found.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)

    result = {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
        "price": clean_price,
        "stop_price": clean_stop,
    }
    return result
