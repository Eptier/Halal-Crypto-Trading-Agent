"""Market-data helpers: OHLCV fetch + technical indicators + candle patterns.

All indicators are implemented inline (no TA-Lib / pandas-ta dependency) so
the project remains pure-Python and trivial to install. Indicator choices and
formulas follow the standard textbook definitions (Wilder, Murphy, Bulkowski).

The :class:`TechnicalSnapshot` returned by :func:`snapshot_from_ohlcv` is a
plain, JSON-friendly value object that the research agent and the smarter
exit logic both consume. The snapshot does *not* make any trade decisions on
its own — it only describes the current market state.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
import pandas as pd


@dataclass
class TechnicalSnapshot:
    symbol: str
    last_price: float

    # Momentum / oscillators
    rsi_14: float
    macd: float
    macd_signal: float
    macd_hist: float

    # Trend / moving averages
    ema_9: float
    ema_21: float
    ema_50: float

    # Volatility / bands
    bb_lower: float
    bb_middle: float
    bb_upper: float
    bb_pct: float           # 0..1 position of price between lower and upper band
    atr_14: float
    atr_pct: float          # ATR as % of last_price (volatility normalised)

    # Volume
    volume_z: float         # z-score of last bar's volume vs 20-bar mean/std

    # Recent crossovers (look-back of 3 bars)
    macd_bull_cross: bool
    macd_bear_cross: bool

    # Candle patterns on the most recent CLOSED candle
    bullish_engulfing: bool
    bearish_engulfing: bool
    hammer: bool
    shooting_star: bool
    doji: bool

    # Convenience scalars
    pct_change_24h: float

    # ------------------------------------------------------------------
    # Derived properties used by the research agent / exit logic.
    # ------------------------------------------------------------------

    @property
    def trend_up(self) -> bool:
        """Bullish EMA stack: short-term > medium > long, price above short EMA."""
        return (
            self.ema_9 > self.ema_21 > self.ema_50
            and self.last_price > self.ema_9
        )

    @property
    def trend_down(self) -> bool:
        return (
            self.ema_9 < self.ema_21 < self.ema_50
            and self.last_price < self.ema_9
        )

    @property
    def oversold(self) -> bool:
        return self.rsi_14 < 30

    @property
    def overbought(self) -> bool:
        return self.rsi_14 > 70

    @property
    def near_lower_band(self) -> bool:
        """Price is close to the lower Bollinger Band — possible mean-reversion buy."""
        return self.bb_pct <= 0.2

    @property
    def near_upper_band(self) -> bool:
        """Price is close to the upper Bollinger Band — possible mean-reversion sell."""
        return self.bb_pct >= 0.8

    @property
    def high_volume(self) -> bool:
        """Volume spike (above the recent mean) - confirms breakouts/reversals."""
        return self.volume_z >= 1.0

    @property
    def bullish_reversal_candle(self) -> bool:
        return self.bullish_engulfing or self.hammer

    @property
    def bearish_reversal_candle(self) -> bool:
        return self.bearish_engulfing or self.shooting_star


# ---------------------------------------------------------------------------
# Indicator primitives.
# ---------------------------------------------------------------------------


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    return middle - num_std * std, middle, middle + num_std * std


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Welles Wilder Average True Range using the EMA smoothing variant."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ---------------------------------------------------------------------------
# Candle pattern detection. Inputs are the last 2 candles (previous + current).
# ---------------------------------------------------------------------------


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _range(h: float, low: float) -> float:
    return max(h - low, 1e-12)


def is_bullish_engulfing(o1: float, c1: float, o2: float, c2: float) -> bool:
    """Previous red candle's body fully engulfed by current green candle's body."""
    prev_red = c1 < o1
    curr_green = c2 > o2
    body_engulf = (o2 <= c1) and (c2 >= o1)
    return prev_red and curr_green and body_engulf


def is_bearish_engulfing(o1: float, c1: float, o2: float, c2: float) -> bool:
    prev_green = c1 > o1
    curr_red = c2 < o2
    body_engulf = (o2 >= c1) and (c2 <= o1)
    return prev_green and curr_red and body_engulf


def is_hammer(o: float, h: float, low: float, c: float) -> bool:
    """Small body at top of range, long lower wick, tiny upper wick.

    Classical hammer: lower shadow at least 2x the body, upper shadow no more
    than ~30 percent of the lower shadow. Body must be small relative to total range.
    """
    body = _body(o, c)
    rng = _range(h, low)
    if body / rng > 0.35:
        return False
    body_top = max(o, c)
    body_bottom = min(o, c)
    lower_wick = body_bottom - low
    upper_wick = h - body_top
    if lower_wick < 2 * body:
        return False
    return upper_wick <= max(body, lower_wick * 0.3)


def is_shooting_star(o: float, h: float, low: float, c: float) -> bool:
    """Small body at bottom of range, long upper wick, tiny lower wick.

    Mirror of :func:`is_hammer`.
    """
    body = _body(o, c)
    rng = _range(h, low)
    if body / rng > 0.35:
        return False
    body_top = max(o, c)
    body_bottom = min(o, c)
    upper_wick = h - body_top
    lower_wick = body_bottom - low
    if upper_wick < 2 * body:
        return False
    return lower_wick <= max(body, upper_wick * 0.3)


def is_doji(o: float, h: float, low: float, c: float) -> bool:
    """Body is < 10% of total range — indecision."""
    body = _body(o, c)
    rng = _range(h, low)
    return body / rng < 0.10


# ---------------------------------------------------------------------------
# Snapshot builder.
# ---------------------------------------------------------------------------


MIN_CANDLES = 60  # need >= 50 for EMA-50 + a bit of warm-up for BB / RSI


def snapshot_from_ohlcv(symbol: str, ohlcv: list[list[float]]) -> TechnicalSnapshot:
    """Build a :class:`TechnicalSnapshot` from a CCXT-style OHLCV list.

    OHLCV row format: ``[timestamp_ms, open, high, low, close, volume]``.
    Requires at least :data:`MIN_CANDLES` candles for indicator stability.
    """
    if len(ohlcv) < MIN_CANDLES:
        raise ValueError(
            f"Need at least {MIN_CANDLES} candles for indicators, got {len(ohlcv)}"
        )
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "vol"])
    closes = df["close"].astype(float)
    volumes = df["vol"].astype(float)

    # Momentum
    rsi_series = rsi(closes, 14)
    macd_line, macd_signal, macd_hist = macd(closes)

    # Trend
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    # Volatility / bands
    bb_low, bb_mid, bb_high = bollinger(closes, 20, 2.0)
    atr_series = atr(df, 14)

    # Volume z-score (last bar vs 20-bar mean / std)
    vol_mean = volumes.rolling(20).mean()
    vol_std = volumes.rolling(20).std(ddof=0)
    last_vol_mean = float(vol_mean.iloc[-1])
    last_vol_std = float(vol_std.iloc[-1])
    last_vol = float(volumes.iloc[-1])
    volume_z = (last_vol - last_vol_mean) / last_vol_std if last_vol_std > 0 else 0.0

    # MACD crosses within the last 3 bars (any sign change)
    hist_recent = macd_hist.iloc[-4:].astype(float).tolist()
    macd_bull_cross = any(prev <= 0 < cur for prev, cur in pairwise(hist_recent))
    macd_bear_cross = any(prev >= 0 > cur for prev, cur in pairwise(hist_recent))

    # Candle patterns on the last fully-formed candle (using last two rows).
    o1 = float(df["open"].iloc[-2])
    c1 = float(df["close"].iloc[-2])
    o2 = float(df["open"].iloc[-1])
    h2 = float(df["high"].iloc[-1])
    l2 = float(df["low"].iloc[-1])
    c2 = float(df["close"].iloc[-1])

    last = float(closes.iloc[-1])
    bb_lower = float(bb_low.iloc[-1])
    bb_upper = float(bb_high.iloc[-1])
    bb_middle = float(bb_mid.iloc[-1])
    bb_width = max(bb_upper - bb_lower, 1e-12)
    bb_pct = float(np.clip((last - bb_lower) / bb_width, 0.0, 1.0))

    atr_val = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else 0.0
    atr_pct = (atr_val / last * 100.0) if last > 0 else 0.0

    first_24h = float(closes.iloc[-min(24, len(closes))])
    pct_24h = (last - first_24h) / first_24h * 100.0 if first_24h else 0.0

    return TechnicalSnapshot(
        symbol=symbol,
        last_price=last,
        rsi_14=float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0,
        macd=float(macd_line.iloc[-1]),
        macd_signal=float(macd_signal.iloc[-1]),
        macd_hist=float(macd_hist.iloc[-1]),
        ema_9=float(ema9.iloc[-1]),
        ema_21=float(ema21.iloc[-1]),
        ema_50=float(ema50.iloc[-1]),
        bb_lower=bb_lower,
        bb_middle=bb_middle,
        bb_upper=bb_upper,
        bb_pct=bb_pct,
        atr_14=atr_val,
        atr_pct=atr_pct,
        volume_z=float(volume_z),
        macd_bull_cross=macd_bull_cross,
        macd_bear_cross=macd_bear_cross,
        bullish_engulfing=is_bullish_engulfing(o1, c1, o2, c2),
        bearish_engulfing=is_bearish_engulfing(o1, c1, o2, c2),
        hammer=is_hammer(o2, h2, l2, c2),
        shooting_star=is_shooting_star(o2, h2, l2, c2),
        doji=is_doji(o2, h2, l2, c2),
        pct_change_24h=pct_24h,
    )
