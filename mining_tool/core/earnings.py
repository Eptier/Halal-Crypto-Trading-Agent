"""Earnings calculator and tracker for mining operations."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

EARNINGS_LOG = Path.home() / ".crypto_miner" / "earnings.json"
PRICE_CACHE_DURATION = 300  # 5 minutes


class EarningsTracker:
    """Track and estimate mining earnings."""

    def __init__(self):
        self._price_cache: dict[str, tuple[float, float]] = {}  # coin -> (price, timestamp)
        self._load_history()

    def _load_history(self) -> None:
        """Load earnings history from disk."""
        self.history: list[dict] = []
        if EARNINGS_LOG.exists():
            try:
                with open(EARNINGS_LOG) as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.history = []

    def _save_history(self) -> None:
        """Save earnings history to disk."""
        EARNINGS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(EARNINGS_LOG, "w") as f:
            json.dump(self.history, f, indent=2)

    def get_xmr_price(self) -> float:
        """Get current XMR price in USD."""
        cached = self._price_cache.get("xmr")
        if cached and (time.time() - cached[1]) < PRICE_CACHE_DURATION:
            return cached[0]

        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "monero", "vs_currencies": "usd"},
                timeout=10,
            )
            response.raise_for_status()
            price = response.json()["monero"]["usd"]
            self._price_cache["xmr"] = (price, time.time())
            return price
        except (requests.RequestException, KeyError):
            return self._price_cache.get("xmr", (0.0, 0))[0]

    def estimate_daily_earnings(self, hashrate_hs: float) -> dict:
        """Estimate daily earnings based on current hashrate.

        Uses simplified calculation based on network stats.
        For Monero (RandomX), rough estimate: 1 KH/s ~ 0.00006 XMR/day
        (varies significantly based on network difficulty)
        """
        if hashrate_hs <= 0:
            return {
                "xmr_per_day": 0,
                "usd_per_day": 0,
                "xmr_per_month": 0,
                "usd_per_month": 0,
            }

        xmr_per_khs_per_day = 0.00006
        hashrate_khs = hashrate_hs / 1000
        xmr_per_day = hashrate_khs * xmr_per_khs_per_day

        xmr_price = self.get_xmr_price()
        usd_per_day = xmr_per_day * xmr_price

        return {
            "xmr_per_day": round(xmr_per_day, 8),
            "usd_per_day": round(usd_per_day, 4),
            "xmr_per_month": round(xmr_per_day * 30, 8),
            "usd_per_month": round(usd_per_day * 30, 4),
            "xmr_price_usd": xmr_price,
            "hashrate_hs": hashrate_hs,
        }

    def record_earning(self, amount_xmr: float, source: str = "mining") -> None:
        """Record an earning event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "amount_xmr": amount_xmr,
            "usd_value": amount_xmr * self.get_xmr_price(),
            "source": source,
        }
        self.history.append(entry)
        self._save_history()

    def get_total_earnings(self, days: int | None = None) -> dict:
        """Get total earnings, optionally filtered by recent days."""
        entries = self.history
        if days is not None:
            cutoff = datetime.now() - timedelta(days=days)
            entries = [
                e
                for e in entries
                if datetime.fromisoformat(e["timestamp"]) > cutoff
            ]

        total_xmr = sum(e["amount_xmr"] for e in entries)
        xmr_price = self.get_xmr_price()

        return {
            "total_xmr": round(total_xmr, 8),
            "total_usd": round(total_xmr * xmr_price, 4),
            "entries_count": len(entries),
            "period_days": days or "all time",
        }

    def get_profitability_report(
        self, hashrate_hs: float, power_watts: float, electricity_cost_kwh: float = 0.10
    ) -> dict:
        """Generate a profitability report."""
        earnings = self.estimate_daily_earnings(hashrate_hs)

        power_kwh_per_day = (power_watts * 24) / 1000
        electricity_cost_per_day = power_kwh_per_day * electricity_cost_kwh

        profit_per_day = earnings["usd_per_day"] - electricity_cost_per_day

        return {
            "earnings": earnings,
            "electricity": {
                "power_watts": power_watts,
                "kwh_per_day": round(power_kwh_per_day, 2),
                "cost_per_day_usd": round(electricity_cost_per_day, 4),
                "cost_per_month_usd": round(electricity_cost_per_day * 30, 2),
            },
            "profit": {
                "per_day_usd": round(profit_per_day, 4),
                "per_month_usd": round(profit_per_day * 30, 2),
                "profitable": profit_per_day > 0,
            },
        }
