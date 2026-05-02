from pathlib import Path

import pytest

from halal_agent.config import Settings
from halal_agent.executor import PaperExecutor
from halal_agent.halal import HalalViolation
from halal_agent.ledger import Ledger


@pytest.fixture
async def ledger(tmp_path: Path):
    db = tmp_path / "test.db"
    ledger = Ledger(db)
    await ledger.init()
    return ledger


def _settings() -> Settings:
    return Settings(trading_mode="paper", paper_starting_equity=1000.0, quote_currency="USDT")


@pytest.mark.asyncio
async def test_paper_buy_then_sell(ledger):
    s = _settings()
    px = PaperExecutor(s, ledger, starting_equity=s.paper_starting_equity)
    fill = await px.buy("BTC/USDT", quote_amount=200.0, last_price=20_000.0)
    assert fill.side == "buy"
    assert fill.is_paper
    assert px.cash == pytest.approx(800.0)
    assert px.positions["BTC/USDT"].base_amount == pytest.approx(0.01)

    sell = await px.sell("BTC/USDT", base_amount=0.01, last_price=21_000.0)
    assert sell.side == "sell"
    assert "BTC/USDT" not in px.positions
    assert px.cash == pytest.approx(800.0 + 210.0)


@pytest.mark.asyncio
async def test_paper_buy_refuses_haram(ledger):
    px = PaperExecutor(_settings(), ledger, 1000.0)
    with pytest.raises(HalalViolation):
        await px.buy("AAVE/USDT", 100.0, 50.0)


@pytest.mark.asyncio
async def test_paper_buy_refuses_oversize(ledger):
    px = PaperExecutor(_settings(), ledger, 100.0)
    with pytest.raises(RuntimeError):
        await px.buy("BTC/USDT", quote_amount=200.0, last_price=20_000.0)


@pytest.mark.asyncio
async def test_paper_sell_refuses_no_position(ledger):
    px = PaperExecutor(_settings(), ledger, 1000.0)
    with pytest.raises(RuntimeError):
        await px.sell("BTC/USDT", base_amount=0.01, last_price=20_000.0)


@pytest.mark.asyncio
async def test_paper_average_entry_price(ledger):
    px = PaperExecutor(_settings(), ledger, 1000.0)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=10_000.0)  # 0.01 BTC
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)  # 0.005 BTC
    pos = px.positions["BTC/USDT"]
    assert pos.base_amount == pytest.approx(0.015)
    # weighted avg: (0.01 * 10000 + 0.005 * 20000) / 0.015 = 13333.33
    assert pos.avg_entry_price == pytest.approx(13_333.333, rel=1e-4)
