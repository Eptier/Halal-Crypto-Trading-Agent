"""CCXT-based exchange adapter (spot only, halal-enforced)."""

from __future__ import annotations

import logging
from typing import Any

import ccxt.async_support as ccxt

from .config import Settings
from .halal import assert_halal_pair

logger = logging.getLogger(__name__)


class ExchangeAdapter:
    """Thin wrapper around CCXT that enforces:

    - Spot markets only (no margin / no futures).
    - Halal whitelist on every order.
    - Read-only methods always available; write methods only when api keys set.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        klass = getattr(ccxt, settings.exchange, None)
        if klass is None:
            raise ValueError(f"Unknown exchange: {settings.exchange}")

        config: dict[str, Any] = {"options": {"defaultType": "spot"}, "enableRateLimit": True}
        if settings.is_live:
            if not settings.exchange_api_key or not settings.exchange_api_secret:
                raise RuntimeError(
                    "Live mode requires EXCHANGE_API_KEY and EXCHANGE_API_SECRET."
                )
            config["apiKey"] = settings.exchange_api_key.get_secret_value()
            config["secret"] = settings.exchange_api_secret.get_secret_value()
        self._client: ccxt.Exchange = klass(config)

    async def load_markets(self) -> None:
        await self._client.load_markets()

    async def close(self) -> None:
        await self._client.close()

    # -- Read methods (always allowed) --------------------------------------

    async def fetch_ticker(self, pair: str) -> dict[str, Any]:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        return await self._client.fetch_ticker(pair)

    async def fetch_ohlcv(
        self,
        pair: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[list[float]]:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        return await self._client.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)

    async def fetch_balance(self) -> dict[str, Any]:
        return await self._client.fetch_balance()

    # -- Write methods (LIVE only, halal-checked) ---------------------------

    async def create_market_buy(self, pair: str, quote_amount: float) -> dict[str, Any]:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        if not self.settings.is_live:
            raise RuntimeError("create_market_buy called outside live mode")
        # Use createOrder with createMarketBuyOrderRequiresPrice handling for binance
        params = {"quoteOrderQty": quote_amount}
        return await self._client.create_order(pair, "market", "buy", quote_amount, None, params)

    async def create_market_sell(self, pair: str, base_amount: float) -> dict[str, Any]:
        assert_halal_pair(pair, quote=self.settings.quote_currency)
        if not self.settings.is_live:
            raise RuntimeError("create_market_sell called outside live mode")
        return await self._client.create_order(pair, "market", "sell", base_amount)
