from pathlib import Path
from typing import Any

import pytest

from halal_agent.config import Settings
from halal_agent.executor import LiveExecutor, PaperExecutor
from halal_agent.halal import HalalViolation
from halal_agent.ledger import Ledger


@pytest.fixture
async def ledger(tmp_path: Path):
    db = tmp_path / "test.db"
    ledger = Ledger(db)
    await ledger.init()
    return ledger


def _settings(mode: str = "paper") -> Settings:
    return Settings(
        trading_mode=mode,
        paper_starting_equity=1000.0,
        quote_currency="USDT",
        exchange_api_key="test_key" if mode == "live" else None,
        exchange_api_secret="test_secret" if mode == "live" else None,
    )


class FakeExchange:
    """Minimal fake CCXT-style exchange for LiveExecutor tests.

    Records buy/sell calls and returns a configurable order dict.
    """

    def __init__(self, *, fill_price: float, slippage: float = 0.0) -> None:
        self.fill_price = fill_price
        self.slippage = slippage
        self.buy_calls: list[tuple[str, float]] = []
        self.sell_calls: list[tuple[str, float]] = []

    async def create_market_buy(self, pair: str, quote_amount: float) -> dict[str, Any]:
        self.buy_calls.append((pair, quote_amount))
        price = self.fill_price * (1 + self.slippage)
        filled = quote_amount / price
        return {"filled": filled, "cost": quote_amount, "average": price}

    async def create_market_sell(self, pair: str, base_amount: float) -> dict[str, Any]:
        self.sell_calls.append((pair, base_amount))
        price = self.fill_price * (1 - self.slippage)
        return {"filled": base_amount, "cost": base_amount * price, "average": price}


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


# ---------------------------------------------------------------------------
# LiveExecutor — verify that ledger.positions is maintained on buy & sell so
# the agent can enforce stop-loss / take-profit / max-open-positions.
# Regression test for the bug where LiveExecutor only wrote to the trades
# table, leaving positions empty.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_buy_persists_position_to_ledger(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=20_000.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]

    fill = await lx.buy("BTC/USDT", quote_amount=200.0, last_price=20_000.0)
    assert fill.side == "buy"
    assert fill.is_paper is False
    assert fx.buy_calls == [("BTC/USDT", 200.0)]

    pos = await ledger.get_position("BTC/USDT")
    assert pos is not None
    base, avg = pos
    assert base == pytest.approx(0.01)
    assert avg == pytest.approx(20_000.0)


@pytest.mark.asyncio
async def test_live_buy_averages_existing_position(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=10_000.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]

    await lx.buy("BTC/USDT", quote_amount=100.0, last_price=10_000.0)  # 0.01 BTC @ 10k
    fx.fill_price = 20_000.0
    await lx.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)  # 0.005 BTC @ 20k

    pos = await ledger.get_position("BTC/USDT")
    assert pos is not None
    base, avg = pos
    assert base == pytest.approx(0.015)
    # weighted avg: (0.01 * 10000 + 0.005 * 20000) / 0.015 = 13333.33
    assert avg == pytest.approx(13_333.333, rel=1e-4)


@pytest.mark.asyncio
async def test_live_sell_full_deletes_position(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=20_000.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]

    await lx.buy("BTC/USDT", quote_amount=200.0, last_price=20_000.0)  # 0.01 BTC
    assert await ledger.get_position("BTC/USDT") is not None

    await lx.sell("BTC/USDT", base_amount=0.01, last_price=21_000.0)
    assert fx.sell_calls == [("BTC/USDT", 0.01)]
    assert await ledger.get_position("BTC/USDT") is None


@pytest.mark.asyncio
async def test_live_sell_partial_keeps_remainder(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=20_000.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]

    await lx.buy("BTC/USDT", quote_amount=200.0, last_price=20_000.0)  # 0.01 BTC
    await lx.sell("BTC/USDT", base_amount=0.004, last_price=21_000.0)

    pos = await ledger.get_position("BTC/USDT")
    assert pos is not None
    base, avg = pos
    assert base == pytest.approx(0.006)
    # avg entry should be unchanged after a partial sell
    assert avg == pytest.approx(20_000.0)


@pytest.mark.asyncio
async def test_live_buy_refuses_haram(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=50.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]
    with pytest.raises(HalalViolation):
        await lx.buy("AAVE/USDT", quote_amount=100.0, last_price=50.0)
    # Halal check must fire BEFORE hitting the exchange.
    assert fx.buy_calls == []


@pytest.mark.asyncio
async def test_live_sell_refuses_haram(ledger):
    s = _settings("live")
    fx = FakeExchange(fill_price=50.0)
    lx = LiveExecutor(s, fx, ledger)  # type: ignore[arg-type]
    with pytest.raises(HalalViolation):
        await lx.sell("AAVE/USDT", base_amount=1.0, last_price=50.0)
    assert fx.sell_calls == []
