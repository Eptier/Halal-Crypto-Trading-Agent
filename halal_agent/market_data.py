"""Market-data helpers: OHLCV fetch + simple technical indicators.

Indicators are implemented inline (no TA-Lib dependency) so the project
remains pure-Python and trivial to install.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class TechnicalSnapshot:
    symbol: str
    last_price: float
    rsi_14: float
    ema_20: float
    ema_50: float
    macd: float
    macd_signal: float
    pct_change_24h: float

    @property
    def trend_up(self) -> bool:
        return self.ema_20 > self.ema_50 and self.last_price > self.ema_20

    @property
    def oversold(self) -> bool:
        return self.rsi_14 < 30

    @property
    def overbought(self) -> bool:
        return self.rsi_14 > 70


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
) -> tuple[pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line


def snapshot_from_ohlcv(symbol: str, ohlcv: list[list[float]]) -> TechnicalSnapshot:
    """Build a TechnicalSnapshot from a CCXT-style OHLCV list.

    OHLCV row format: [timestamp_ms, open, high, low, close, volume]
    Requires at least ~60 candles for stable indicator output.
    """
    if len(ohlcv) < 30:
        raise ValueError(f"Need at least 30 candles for indicators, got {len(ohlcv)}")
    df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "vol"])
    closes = df["close"].astype(float)
    rsi_series = rsi(closes, 14)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50) if len(closes) >= 50 else ema(closes, len(closes) // 2)
    macd_line, macd_signal = macd(closes)
    last = float(closes.iloc[-1])
    first_24h = float(closes.iloc[-min(24, len(closes))])
    pct_24h = (last - first_24h) / first_24h * 100.0 if first_24h else 0.0
    return TechnicalSnapshot(
        symbol=symbol,
        last_price=last,
        rsi_14=float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0,
        ema_20=float(ema20.iloc[-1]),
        ema_50=float(ema50.iloc[-1]),
        macd=float(macd_line.iloc[-1]),
        macd_signal=float(macd_signal.iloc[-1]),
        pct_change_24h=pct_24h,
    )
