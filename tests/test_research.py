import pytest

from halal_agent.market_data import TechnicalSnapshot
from halal_agent.research import RuleBasedResearchAgent


@pytest.mark.asyncio
async def test_rule_based_buy_signal():
    snap = TechnicalSnapshot(
        symbol="BTC",
        last_price=100.0,
        rsi_14=25.0,
        ema_20=98.0,
        ema_50=95.0,
        macd=0.5,
        macd_signal=0.2,
        pct_change_24h=-3.0,
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "BUY"


@pytest.mark.asyncio
async def test_rule_based_sell_on_overbought():
    snap = TechnicalSnapshot(
        symbol="BTC",
        last_price=100.0,
        rsi_14=80.0,
        ema_20=98.0,
        ema_50=95.0,
        macd=0.1,
        macd_signal=0.05,
        pct_change_24h=5.0,
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "SELL"


@pytest.mark.asyncio
async def test_rule_based_hold_on_neutral():
    snap = TechnicalSnapshot(
        symbol="BTC",
        last_price=100.0,
        rsi_14=50.0,
        ema_20=99.0,
        ema_50=99.5,
        macd=0.0,
        macd_signal=0.0,
        pct_change_24h=0.0,
    )
    t = await RuleBasedResearchAgent().evaluate(snap)
    assert t.action == "HOLD"
