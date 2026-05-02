import math

import numpy as np
import pandas as pd

from halal_agent.market_data import (
    atr,
    bollinger,
    ema,
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_doji,
    is_hammer,
    is_shooting_star,
    rsi,
    snapshot_from_ohlcv,
)


def test_ema_matches_pandas():
    s = pd.Series(np.arange(1, 30, dtype=float))
    out = ema(s, span=5)
    assert math.isclose(out.iloc[-1], s.ewm(span=5, adjust=False).mean().iloc[-1])


def test_rsi_in_range():
    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(loc=100, scale=2, size=100).cumsum())
    out = rsi(s, period=14).dropna()
    assert (out >= 0).all() and (out <= 100).all()


def test_bollinger_envelopes_price_series():
    s = pd.Series(np.linspace(100, 110, 30))
    lower, middle, upper = bollinger(s, period=20, num_std=2.0)
    # Last bar: lower <= middle <= upper, all finite.
    assert lower.iloc[-1] <= middle.iloc[-1] <= upper.iloc[-1]
    assert np.isfinite(lower.iloc[-1])


def test_atr_positive_for_volatile_series():
    df = pd.DataFrame(
        {
            "high": np.linspace(105, 115, 30),
            "low": np.linspace(95, 105, 30),
            "close": np.linspace(100, 110, 30),
        }
    )
    out = atr(df, period=14)
    assert (out.dropna() > 0).all()


def test_bullish_engulfing_pattern():
    # Prev red: open=100, close=95. Curr green: open=94, close=102.
    assert is_bullish_engulfing(100.0, 95.0, 94.0, 102.0)
    # Not engulfing — current close doesn't exceed prev open.
    assert not is_bullish_engulfing(100.0, 95.0, 94.0, 99.0)


def test_bearish_engulfing_pattern():
    # Prev green: open=95, close=100. Curr red: open=101, close=93.
    assert is_bearish_engulfing(95.0, 100.0, 101.0, 93.0)
    assert not is_bearish_engulfing(95.0, 100.0, 96.0, 95.5)


def test_hammer_pattern():
    # Long lower wick, small body near top.
    assert is_hammer(o=100.0, h=101.0, low=90.0, c=100.5)
    # Symmetric candle — not a hammer.
    assert not is_hammer(o=100.0, h=105.0, low=95.0, c=104.0)


def test_shooting_star_pattern():
    # Long upper wick, small body near bottom.
    assert is_shooting_star(o=100.0, h=110.0, low=99.0, c=100.5)
    # Hammer-like, opposite shape — not a shooting star.
    assert not is_shooting_star(o=100.0, h=101.0, low=90.0, c=100.5)


def test_doji_pattern():
    assert is_doji(o=100.0, h=101.0, low=99.0, c=100.05)
    # Big-bodied candle is not a doji.
    assert not is_doji(o=100.0, h=110.0, low=95.0, c=109.0)


def _make_ohlcv(prices: list[float], volumes: list[float] | None = None) -> list[list[float]]:
    vols = volumes or [100.0] * len(prices)
    return [
        [i * 1000, p, p * 1.01, p * 0.99, p, v]
        for i, (p, v) in enumerate(zip(prices, vols, strict=True))
    ]


def test_snapshot_basic_fields():
    prices = list(np.linspace(100, 120, 60))
    snap = snapshot_from_ohlcv("BTC", _make_ohlcv(prices))
    assert snap.symbol == "BTC"
    assert snap.last_price == prices[-1]
    assert snap.ema_9 > 0
    assert snap.ema_21 > 0
    assert snap.ema_50 > 0
    assert snap.bb_lower < snap.bb_upper
    assert snap.atr_14 >= 0
    assert -100 < snap.pct_change_24h < 100


def test_snapshot_detects_bullish_trend():
    """Steadily rising prices → trend_up True, EMA stack ordered, RSI elevated."""
    prices = list(np.linspace(100, 200, 80))
    snap = snapshot_from_ohlcv("ETH", _make_ohlcv(prices))
    assert snap.ema_9 > snap.ema_21 > snap.ema_50
    assert snap.trend_up
    assert not snap.trend_down


def test_snapshot_detects_volume_spike():
    prices = list(np.linspace(100, 110, 60))
    volumes = [100.0] * 59 + [500.0]  # last bar is 5x normal volume
    snap = snapshot_from_ohlcv("ETH", _make_ohlcv(prices, volumes))
    assert snap.high_volume
    assert snap.volume_z > 1.0
