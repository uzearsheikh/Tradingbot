"""
Order placement logic.
Translates validated user parameters into Binance API calls and
formats the responses for display.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .logging_config import get_logger

logger = get_logger("orders")


def _fmt(value: Any, decimals: int = 8) -> str:
    """Format a number nicely for display, stripping trailing zeros."""
    try:
        return f"{Decimal(str(value)):.{decimals}f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _build_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> dict:
    """
    Build the raw parameter dict for the Binance /fapi/v1/order endpoint.
    """
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": str(quantity),
        "newOrderRespType": "RESULT",  # returns fills/avgPrice
    }

    if reduce_only:
        params["reduceOnly"] = "true"

    if order_type == "LIMIT":
        if price is None:
            raise ValueError("price is required for LIMIT orders.")
        params["price"] = str(price)
        params["timeInForce"] = time_in_force

    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("stop_price is required for STOP_MARKET orders.")
        params["stopPrice"] = str(stop_price)

    return params


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> Dict:
    """
    Place an order and return the API response dict.

    Raises:
        BinanceAPIError: propagated from the client on API errors.
        ValueError: on invalid parameter combinations.
    """
    params = _build_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        reduce_only=reduce_only,
    )
    logger.debug("Order params: %s", params)
    response = client.place_order(**params)
    return response


def format_order_summary(params: dict) -> str:
    """Return a human-readable summary of the order *request*."""
    lines = [
        "┌─── Order Request ───────────────────────────────",
        f"│  Symbol     : {params.get('symbol')}",
        f"│  Side       : {params.get('side')}",
        f"│  Type       : {params.get('order_type')}",
        f"│  Quantity   : {params.get('quantity')}",
    ]
    if params.get("price"):
        lines.append(f"│  Price      : {params['price']}")
    if params.get("stop_price"):
        lines.append(f"│  Stop Price : {params['stop_price']}")
    lines.append("└────────────────────────────────────────────────")
    return "\n".join(lines)


def format_order_response(response: dict) -> str:
    """Return a human-readable summary of the API *response*."""
    order_id = response.get("orderId", "N/A")
    status = response.get("status", "N/A")
    exec_qty = _fmt(response.get("executedQty", 0))
    avg_price = _fmt(response.get("avgPrice", 0))
    cum_quote = _fmt(response.get("cumQuote", 0))
    client_order_id = response.get("clientOrderId", "N/A")
    update_time = response.get("updateTime", "N/A")

    lines = [
        "┌─── Order Response ──────────────────────────────",
        f"│  Order ID       : {order_id}",
        f"│  Client OID     : {client_order_id}",
        f"│  Status         : {status}",
        f"│  Executed Qty   : {exec_qty}",
        f"│  Avg Fill Price : {avg_price}",
        f"│  Cum Quote      : {cum_quote}",
        f"│  Updated At     : {update_time}",
        "└────────────────────────────────────────────────",
    ]
    return "\n".join(lines)
