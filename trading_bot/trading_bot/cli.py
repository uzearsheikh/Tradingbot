#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples:
    python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.001
    python cli.py place --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.001 --price 50000
    python cli.py place --symbol ETHUSDT --side BUY  --type STOP_MARKET --quantity 0.01 --stop-price 2000
    python cli.py account
    python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order, format_order_summary, format_order_response
from bot.validators import validate_all

# ── Logging ─────────────────────────────────────────────────────────────────
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("cli")

# ── Colour helpers (graceful degradation on Windows) ────────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = ""


def _ok(msg: str) -> None:
    print(f"{GREEN}✔  {msg}{RESET}")


def _err(msg: str) -> None:
    print(f"{RED}✘  {msg}{RESET}", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"{CYAN}{msg}{RESET}")


# ── Client factory ───────────────────────────────────────────────────────────
def _make_client() -> BinanceFuturesClient:
    """
    Create the Binance client from environment variables.
    Exits with a clear message if credentials are missing.
    """
    api_key    = os.getenv("BINANCE_TESTNET_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "").strip()

    if not api_key or not api_secret:
        _err(
            "API credentials not found.\n"
            "  Please set the following environment variables:\n"
            "    export BINANCE_TESTNET_API_KEY=<your_key>\n"
            "    export BINANCE_TESTNET_API_SECRET=<your_secret>"
        )
        sys.exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


# ── Sub-command handlers ─────────────────────────────────────────────────────
def cmd_place(args: argparse.Namespace) -> int:
    """Handle the `place` sub-command."""
    # ── Validate input ──────────────────────────────────────────────────────
    try:
        cleaned = validate_all(
            symbol     = args.symbol,
            side       = args.side,
            order_type = args.type,
            quantity   = args.quantity,
            price      = args.price,
            stop_price = args.stop_price,
        )
    except ValueError as exc:
        _err(f"Validation error: {exc}")
        logger.warning("Input validation failed: %s", exc)
        return 1

    _info(format_order_summary(cleaned))

    # ── Confirm (interactive mode) ──────────────────────────────────────────
    if not args.yes:
        try:
            answer = input(f"{YELLOW}Proceed with this order? [y/N] {RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            _info("Aborted.")
            return 0
        if answer not in ("y", "yes"):
            _info("Order cancelled by user.")
            return 0

    # ── Place order ─────────────────────────────────────────────────────────
    client = _make_client()
    try:
        response = place_order(
            client     = client,
            symbol     = cleaned["symbol"],
            side       = cleaned["side"],
            order_type = cleaned["order_type"],
            quantity   = cleaned["quantity"],
            price      = cleaned["price"],
            stop_price = cleaned["stop_price"],
        )
    except BinanceAPIError as exc:
        _err(f"Binance API error {exc.code}: {exc.message}")
        logger.error("Order failed — code=%s msg=%s", exc.code, exc.message)
        return 1
    except Exception as exc:
        _err(f"Unexpected error: {exc}")
        logger.exception("Unexpected error during order placement")
        return 1

    print(format_order_response(response))
    _ok("Order placed successfully!")
    return 0


def cmd_account(args: argparse.Namespace) -> int:
    """Handle the `account` sub-command."""
    client = _make_client()
    try:
        account = client.get_account()
    except BinanceAPIError as exc:
        _err(f"Binance API error {exc.code}: {exc.message}")
        return 1
    except Exception as exc:
        _err(f"Unexpected error: {exc}")
        logger.exception("Unexpected error fetching account")
        return 1

    assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    _info(f"\n{BOLD}Account Summary{RESET}")
    _info(f"  Total Wallet Balance : {account.get('totalWalletBalance', 'N/A')} USDT")
    _info(f"  Available Balance    : {account.get('availableBalance', 'N/A')} USDT")
    _info(f"  Total Unrealised PnL : {account.get('totalUnrealizedProfit', 'N/A')} USDT")
    if assets:
        _info("\n  Non-zero assets:")
        for a in assets:
            _info(f"    {a['asset']:8s}  wallet={a['walletBalance']}  unrealised={a.get('unrealizedProfit','0')}")
    _ok("Account fetched successfully.")
    return 0


def cmd_open_orders(args: argparse.Namespace) -> int:
    """Handle the `open-orders` sub-command."""
    client = _make_client()
    symbol = args.symbol.strip().upper() if args.symbol else None
    try:
        orders = client.get_open_orders(symbol=symbol)
    except BinanceAPIError as exc:
        _err(f"Binance API error {exc.code}: {exc.message}")
        return 1
    except Exception as exc:
        _err(f"Unexpected error: {exc}")
        logger.exception("Unexpected error fetching open orders")
        return 1

    if not orders:
        _info("No open orders found.")
        return 0

    _info(f"\n{BOLD}Open Orders ({len(orders)}){RESET}")
    for o in orders:
        _info(
            f"  [{o.get('orderId')}]  {o.get('symbol')}  "
            f"{o.get('side')} {o.get('type')}  "
            f"qty={o.get('origQty')}  price={o.get('price')}  "
            f"status={o.get('status')}"
        )
    _ok(f"Listed {len(orders)} open order(s).")
    return 0


# ── Argument parser ──────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Market buy
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 -y

  # Limit sell
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 90000

  # Stop-market (bonus order type)
  python cli.py place --symbol ETHUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 2000 -y

  # Account summary
  python cli.py account

  # Open orders for a symbol
  python cli.py open-orders --symbol BTCUSDT
        """,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO).",
    )

    sub = parser.add_subparsers(title="commands", dest="command")
    sub.required = True

    # ── place ───────────────────────────────────────────────────────────────
    p_place = sub.add_parser("place", help="Place a new futures order.")
    p_place.add_argument("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
    p_place.add_argument("--side",       required=True,  choices=["BUY", "SELL"], help="BUY or SELL")
    p_place.add_argument("--type",       required=True,  choices=["MARKET", "LIMIT", "STOP_MARKET"],
                         help="Order type")
    p_place.add_argument("--quantity",   required=True,  type=str, help="Order quantity (base asset)")
    p_place.add_argument("--price",      default=None,   type=str,
                         help="Limit price (required for LIMIT orders)")
    p_place.add_argument("--stop-price", dest="stop_price", default=None, type=str,
                         help="Stop price (required for STOP_MARKET orders)")
    p_place.add_argument("-y", "--yes",  action="store_true",
                         help="Skip confirmation prompt")
    p_place.set_defaults(func=cmd_place)

    # ── account ─────────────────────────────────────────────────────────────
    p_account = sub.add_parser("account", help="Show account balance summary.")
    p_account.set_defaults(func=cmd_account)

    # ── open-orders ──────────────────────────────────────────────────────────
    p_oo = sub.add_parser("open-orders", help="List open orders.")
    p_oo.add_argument("--symbol", default=None, help="Filter by symbol (optional)")
    p_oo.set_defaults(func=cmd_open_orders)

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Allow overriding log level from flag
    setup_logging(log_level=args.log_level)

    logger.info("Command: %s  args: %s", args.command, vars(args))
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
