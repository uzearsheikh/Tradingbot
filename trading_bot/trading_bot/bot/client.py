"""
Low-level Binance Futures Testnet REST client.
Handles request signing, rate-limit headers, and error normalisation.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error payload."""

    def __init__(self, code: int, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{code}] {message}")


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures Testnet REST API.

    Only the endpoints needed by the trading bot are exposed.
    Signing follows the HMAC-SHA256 scheme documented by Binance.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must both be non-empty strings.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceFuturesClient initialised — base_url=%s", self._base_url)

    # ── internal helpers ────────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        """Append a HMAC-SHA256 signature to *params* (mutates and returns it)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        sig = hmac.new(self._api_secret, query_string.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request and return the parsed JSON body.

        Raises:
            BinanceAPIError: API returned a non-2xx status or error JSON.
            requests.exceptions.ConnectionError / Timeout: network issues.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{path}"
        logger.debug("→ %s %s  params=%s", method.upper(), url, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method.upper() == "GET":
                resp = self._session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "POST":
                resp = self._session.post(url, data=params, timeout=DEFAULT_TIMEOUT)
            elif method.upper() == "DELETE":
                resp = self._session.delete(url, params=params, timeout=DEFAULT_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.Timeout:
            logger.error("Request timed out: %s %s", method.upper(), url)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error: %s", exc)
            raise

        logger.debug("← HTTP %s  body=%s", resp.status_code, resp.text[:500])

        # Binance always returns JSON (even for errors)
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %s): %s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
            return resp.text

        if not resp.ok or (isinstance(data, dict) and "code" in data and data["code"] != 200):
            code = data.get("code", resp.status_code)
            msg = data.get("msg", resp.reason)
            logger.error("API error code=%s msg=%s", code, msg)
            raise BinanceAPIError(code=int(code), message=msg, status_code=resp.status_code)

        return data

    # ── public endpoints ────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Test connectivity. Returns True on success."""
        self._request("GET", "/fapi/v1/ping")
        logger.info("Ping OK")
        return True

    def get_exchange_info(self) -> Dict:
        """Return exchange trading rules and symbol info."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict:
        """Return current account information (signed)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **kwargs) -> Dict:
        """
        Place a new futures order.

        Accepted kwargs mirror the Binance /fapi/v1/order endpoint parameters:
            symbol, side, type, quantity, price, timeInForce,
            stopPrice, reduceOnly, newOrderRespType, etc.
        """
        logger.info(
            "Placing order — symbol=%s side=%s type=%s qty=%s price=%s",
            kwargs.get("symbol"),
            kwargs.get("side"),
            kwargs.get("type"),
            kwargs.get("quantity"),
            kwargs.get("price", "N/A"),
        )
        result = self._request("POST", "/fapi/v1/order", params=kwargs, signed=True)
        logger.info("Order placed — orderId=%s status=%s", result.get("orderId"), result.get("status"))
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an open order by symbol + orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        result = self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
        logger.info("Order cancelled — orderId=%s", order_id)
        return result

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
