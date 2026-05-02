"""End-to-end tests for the agent's decision flow, especially the
smarter exit logic: research-driven SELL has priority over the fixed %
stop-loss / take-profit safety net.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from halal_agent.agent import Agent
from halal_agent.config import Settings
from halal_agent.executor import PaperExecutor
from halal_agent.ledger import Ledger
from halal_agent.market_data import TechnicalSnapshot
from halal_agent.research import Thesis
from halal_agent.risk import PortfolioState, RiskManager


def _settings() -> Settings:
    return Settings(
        trading_mode="paper",
        paper_starting_equity=1000.0,
        quote_currency="USDT",
    )


def _snap(**overrides) -> TechnicalSnapshot:
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


class StubResearcher:
    """Returns a pre-canned thesis regardless of snapshot."""

    def __init__(self, thesis: Thesis) -> None:
        self.thesis = thesis
        self.calls: list[str] = []

    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis:
        self.calls.append(snapshot.symbol)
        return self.thesis


@pytest.fixture
async def ledger(tmp_path: Path):
    db = tmp_path / "test.db"
    led = Ledger(db)
    await led.init()
    return led


def _state(equity: float = 1000.0, open_positions: int = 0) -> PortfolioState:
    today = datetime.now(UTC).date()
    return PortfolioState(
        equity=equity,
        open_positions=open_positions,
        realized_pnl_today=0.0,
        starting_equity_today=equity,
        today=today,
    )


def _build_agent(researcher, executor, settings, ledger):
    return Agent(
        settings=settings,
        exchange=None,  # type: ignore[arg-type]  # not used in _evaluate_pair
        executor=executor,
        ledger=ledger,
        researcher=researcher,
        risk=RiskManager(settings),
    )


# ---------------------------------------------------------------------------
# Entry behaviour.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_buys_only_on_high_confidence_research(ledger):
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    researcher = StubResearcher(
        Thesis(symbol="BTC", action="BUY", confidence=0.7, rationale="confluence")
    )
    agent = _build_agent(researcher, px, s, ledger)

    fill = await agent._evaluate_pair(
        "BTC/USDT", _snap(last_price=20_000.0), _state(), prices={}
    )
    assert fill is not None
    assert fill.side == "buy"
    assert "BTC/USDT" in px.positions


@pytest.mark.asyncio
async def test_agent_does_not_pyramid_into_existing_position(ledger):
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    # Open an initial position.
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="BUY", confidence=0.9, rationale="more confluence")
    )
    agent = _build_agent(researcher, px, s, ledger)

    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=20_500.0),
        _state(open_positions=1),
        prices={"BTC/USDT": 20_500.0},
    )
    # Should NOT buy again — already holding.
    assert fill is None
    assert px.positions["BTC/USDT"].base_amount == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# Exit behaviour — the user-requested "indicators first, % only as fallback".
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_exits_on_research_sell_signal(ledger):
    """SELL thesis with confidence >= 0.4 should trigger exit even with no % breach."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="SELL", confidence=0.5, rationale="bearish reversal")
    )
    agent = _build_agent(researcher, px, s, ledger)

    # Price has barely moved (no % stop-loss / take-profit breach).
    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=20_100.0),
        _state(open_positions=1),
        prices={"BTC/USDT": 20_100.0},
    )
    assert fill is not None
    assert fill.side == "sell"
    assert "BTC/USDT" not in px.positions


@pytest.mark.asyncio
async def test_agent_falls_back_to_pct_stop_loss_when_research_holds(ledger):
    """If research is uncertain (HOLD) but price drops past stop-loss → exit on % safety net."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="HOLD", confidence=0.3, rationale="unclear")
    )
    agent = _build_agent(researcher, px, s, ledger)

    # 6% drop — exceeds default 5% stop-loss.
    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=18_800.0),
        _state(open_positions=1, equity=940.0),
        prices={"BTC/USDT": 18_800.0},
    )
    assert fill is not None
    assert fill.side == "sell"
    assert "BTC/USDT" not in px.positions


@pytest.mark.asyncio
async def test_agent_falls_back_to_pct_take_profit_when_research_holds(ledger):
    """If research is uncertain (HOLD) but price rises past take-profit → exit on % safety net."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="HOLD", confidence=0.3, rationale="unclear")
    )
    agent = _build_agent(researcher, px, s, ledger)

    # 11% rise — exceeds default 10% take-profit.
    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=22_200.0),
        _state(open_positions=1, equity=1110.0),
        prices={"BTC/USDT": 22_200.0},
    )
    assert fill is not None
    assert fill.side == "sell"


@pytest.mark.asyncio
async def test_agent_holds_when_research_uncertain_and_no_pct_breach(ledger):
    """Neutral research + price within stop/take band → keep holding."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="HOLD", confidence=0.3, rationale="unclear")
    )
    agent = _build_agent(researcher, px, s, ledger)

    # 2% rise — no breach in either direction.
    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=20_400.0),
        _state(open_positions=1, equity=1020.0),
        prices={"BTC/USDT": 20_400.0},
    )
    assert fill is None
    assert "BTC/USDT" in px.positions


@pytest.mark.asyncio
async def test_research_sell_priority_over_pct_take_profit(ledger):
    """When BOTH would fire, research SELL wins (and we log it as research-driven)."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="SELL", confidence=0.7, rationale="bearish confluence")
    )
    agent = _build_agent(researcher, px, s, ledger)

    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=22_200.0),  # would also trigger TP
        _state(open_positions=1, equity=1110.0),
        prices={"BTC/USDT": 22_200.0},
    )
    assert fill is not None
    assert fill.side == "sell"


@pytest.mark.asyncio
async def test_low_confidence_sell_does_not_exit_alone(ledger):
    """SELL thesis with confidence < 0.4 should NOT exit (avoids whipsaw)."""
    s = _settings()
    px = PaperExecutor(s, ledger, s.paper_starting_equity)
    await px.buy("BTC/USDT", quote_amount=100.0, last_price=20_000.0)

    researcher = StubResearcher(
        Thesis(symbol="BTC", action="SELL", confidence=0.3, rationale="weak signal")
    )
    agent = _build_agent(researcher, px, s, ledger)

    fill = await agent._evaluate_pair(
        "BTC/USDT",
        _snap(last_price=20_100.0),
        _state(open_positions=1, equity=1005.0),
        prices={"BTC/USDT": 20_100.0},
    )
    assert fill is None
    assert "BTC/USDT" in px.positions
