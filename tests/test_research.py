import pytest

from halal_agent.market_data import TechnicalSnapshot
from halal_agent.research import RuleBasedResearchAgent


def _snap(**overrides) -> TechnicalSnapshot:
    """Build a neutral snapshot; override fields per test."""
    base = dict(
        symbol="BTC",
        last_price=100.0,
        rsi_14=50.0,
        macd=0.0,
        macd_signal=0.0,
        macd_hist=0.0,
        ema_9=100.0,
        ema_21=100.0,
        ema_50=100.0,
        bb_lower=95.0,
        bb_middle=100.0,
        bb_upper=105.0,
        bb_pct=0.5,
        atr_14=1.0,
        atr_pct=1.0,
        volume_z=0.0,
        macd_bull_cross=False,
        macd_bear_cross=False,
        bullish_engulfing=False,
        bearish_engulfing=False,
        hammer=False,
        shooting_star=False,
        doji=False,
        pct_change_24h=0.0,
    )
    base.update(overrides)
    return TechnicalSnapshot(**base)


@pytest.mark.asyncio
async def test_buy_signal_requires_confluence():
    """Confluence: oversold + uptrend + MACD bull cross + bullish engulfing → BUY."""
    snap = _snap(
        rsi_14=25.0,           # oversold (+2)
        ema_9=101.0,
        ema_21=100.0,
        ema_50=98.0,           # bullish stack (+2)
        last_price=101.5,
        macd=0.5,
        macd_signal=0.2,
        macd_hist=0.3,
        macd_bull_cross=True,  # +2
        bullish_engulfing=True,  # +2
        bb_pct=0.15,           # near lower band (+2)
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "BUY"
    assert t.confidence > 0.5


@pytest.mark.asyncio
async def test_buy_refused_on_single_signal():
    """RSI oversold alone is NOT enough (would have fired in old strategy)."""
    snap = _snap(rsi_14=25.0)
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "HOLD"


@pytest.mark.asyncio
async def test_sell_signal_on_bearish_confluence():
    """Overbought + bearish reversal candle + MACD bear cross + downtrend → SELL."""
    snap = _snap(
        rsi_14=78.0,             # overbought (+2)
        ema_9=98.0,
        ema_21=99.0,
        ema_50=100.0,
        last_price=97.5,         # bearish stack (+2)
        macd=-0.5,
        macd_signal=-0.2,
        macd_hist=-0.3,
        macd_bear_cross=True,    # +2
        bearish_engulfing=True,  # +2
        bb_pct=0.85,             # near upper band (+2)
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "SELL"
    assert t.confidence > 0.5


@pytest.mark.asyncio
async def test_hold_on_neutral_market():
    """Mid-range RSI, flat EMAs, neutral MACD → HOLD with low confidence."""
    snap = _snap()
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "HOLD"
    assert t.confidence < 0.5


@pytest.mark.asyncio
async def test_volume_spike_does_not_buy_alone():
    """Volume spike with no other bullish signals shouldn't trigger BUY."""
    snap = _snap(volume_z=3.0)
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "HOLD"


@pytest.mark.asyncio
async def test_conflicting_signals_default_to_hold():
    """Bullish trend + bearish reversal candle → conflicting → HOLD."""
    snap = _snap(
        ema_9=101.0,
        ema_21=100.0,
        ema_50=98.0,             # bullish trend
        last_price=101.5,
        bearish_engulfing=True,  # but bearish candle
        rsi_14=55.0,             # neutral momentum
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    # Buy score: 2 (trend) = 2 < 6 → not BUY
    # Sell score: 2 (engulfing) = 2 < 5 → not SELL
    assert t.action == "HOLD"
