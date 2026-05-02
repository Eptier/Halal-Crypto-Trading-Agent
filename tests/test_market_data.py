import math

import numpy as np
import pandas as pd

from halal_agent.market_data import ema, rsi, snapshot_from_ohlcv


def test_ema_matches_pandas():
    s = pd.Series(np.arange(1, 30, dtype=float))
    out = ema(s, span=5)
    assert math.isclose(out.iloc[-1], s.ewm(span=5, adjust=False).mean().iloc[-1])


def test_rsi_in_range():
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(loc=100, scale=2, size=100).cumsum())
    out = rsi(s, period=14).dropna()
    assert (out >= 0).all() and (out <= 100).all()


def _make_ohlcv(prices: list[float]) -> list[list[float]]:
    return [[i * 1000, p, p * 1.01, p * 0.99, p, 100.0] for i, p in enumerate(prices)]


def test_snapshot_basic_fields():
    prices = list(np.linspace(100, 120, 60))
    snap = snapshot_from_ohlcv("BTC", _make_ohlcv(prices))
    assert snap.symbol == "BTC"
    assert snap.last_price == prices[-1]
    assert snap.ema_20 > 0
    assert snap.ema_50 > 0
    assert -100 < snap.pct_change_24h < 100
