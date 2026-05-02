"""Research agent: forms a directional thesis (BUY / HOLD / SELL) per asset.

Two backends:
  * :class:`RuleBasedResearchAgent` — deterministic, no external dependency.
    Uses **multi-indicator confluence scoring** (RSI / EMA stack / MACD /
    Bollinger Bands / candle patterns / volume confirmation). The bot only
    proposes a high-confidence trade when several signals agree, instead of
    firing on a single threshold.
  * :class:`LLMResearchAgent` — uses OpenAI when an API key is configured.
    Feeds the full snapshot (including candle patterns and band position)
    into a structured prompt and parses a JSON response. Falls back to the
    rule-based agent on any error.

The research agent only *proposes* trades; the strategy + risk manager
decide whether to act on them. This separation keeps the LLM out of the
risk-control loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Literal, Protocol

from .config import Settings
from .market_data import TechnicalSnapshot

logger = logging.getLogger(__name__)

Action = Literal["BUY", "HOLD", "SELL"]

# Score thresholds tuned for the rule-based agent. Buying needs more
# conviction than selling because we are in a long-only spot strategy:
# being wrong on entry burns capital and time, being slow on exit usually
# only gives back a portion of unrealised profit.
BUY_SCORE_THRESHOLD = 6
SELL_SCORE_THRESHOLD = 5
MAX_SCORE = 12  # used to normalise score → confidence


@dataclass
class Thesis:
    symbol: str
    action: Action
    confidence: float  # 0..1
    rationale: str


class ResearchAgent(Protocol):
    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis: ...


# ---------------------------------------------------------------------------
# Rule-based agent — confluence scoring.
# ---------------------------------------------------------------------------


def _score_buy(s: TechnicalSnapshot) -> tuple[int, list[str]]:
    """Return (score, reasons) for a hypothetical BUY at this snapshot."""
    score = 0
    reasons: list[str] = []

    # Momentum
    if s.oversold:
        score += 2
        reasons.append(f"RSI={s.rsi_14:.0f} oversold")
    elif s.rsi_14 < 45:
        score += 1
        reasons.append(f"RSI={s.rsi_14:.0f} weak/lower-half")

    # Mean reversion (Bollinger lower band)
    if s.near_lower_band:
        score += 2
        reasons.append("near lower BB")

    # Trend alignment
    if s.trend_up:
        score += 2
        reasons.append("EMA stack bullish (9>21>50)")
    elif s.ema_21 > s.ema_50:
        score += 1
        reasons.append("medium-term uptrend (EMA21>EMA50)")

    # MACD
    if s.macd_bull_cross:
        score += 2
        reasons.append("MACD bullish cross (recent)")
    elif s.macd_hist > 0:
        score += 1
        reasons.append("MACD positive")

    # Candle reversal
    if s.bullish_reversal_candle:
        score += 2
        reasons.append("bullish reversal candle")

    # Volume confirmation (only awarded if at least one other signal fired)
    if s.high_volume and score > 0:
        score += 1
        reasons.append(f"volume spike (z={s.volume_z:.1f})")

    return score, reasons


def _score_sell(s: TechnicalSnapshot) -> tuple[int, list[str]]:
    """Return (score, reasons) for a hypothetical SELL/exit at this snapshot."""
    score = 0
    reasons: list[str] = []

    # Momentum
    if s.overbought:
        score += 2
        reasons.append(f"RSI={s.rsi_14:.0f} overbought")
    elif s.rsi_14 > 60:
        score += 1
        reasons.append(f"RSI={s.rsi_14:.0f} elevated")

    # Mean reversion (Bollinger upper band)
    if s.near_upper_band:
        score += 2
        reasons.append("near upper BB")

    # Trend breakdown
    if s.trend_down:
        score += 2
        reasons.append("EMA stack bearish (9<21<50)")
    elif s.ema_21 < s.ema_50:
        score += 1
        reasons.append("medium-term downtrend (EMA21<EMA50)")

    # MACD
    if s.macd_bear_cross:
        score += 2
        reasons.append("MACD bearish cross (recent)")
    elif s.macd_hist < 0:
        score += 1
        reasons.append("MACD negative")

    # Candle reversal
    if s.bearish_reversal_candle:
        score += 2
        reasons.append("bearish reversal candle")

    if s.high_volume and score > 0:
        score += 1
        reasons.append(f"volume spike (z={s.volume_z:.1f})")

    return score, reasons


class RuleBasedResearchAgent:
    """Deterministic confluence-scoring research heuristic.

    For each snapshot we compute a *buy score* and a *sell score* by summing
    independent signal weights (see :func:`_score_buy` / :func:`_score_sell`).
    The action with the higher score is preferred, but only emitted if it
    clears its threshold.

    Confidence is the score normalised by :data:`MAX_SCORE` so it lives in
    ``[0, 1]`` and can be compared across pairs and used by the risk manager
    to scale the position size.
    """

    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis:
        s = snapshot
        buy_score, buy_reasons = _score_buy(s)
        sell_score, sell_reasons = _score_sell(s)

        if buy_score >= BUY_SCORE_THRESHOLD and buy_score >= sell_score:
            return Thesis(
                s.symbol,
                "BUY",
                min(1.0, buy_score / MAX_SCORE),
                f"BUY (score={buy_score}): " + "; ".join(buy_reasons),
            )
        if sell_score >= SELL_SCORE_THRESHOLD and sell_score > buy_score:
            return Thesis(
                s.symbol,
                "SELL",
                min(1.0, sell_score / MAX_SCORE),
                f"SELL (score={sell_score}): " + "; ".join(sell_reasons),
            )
        # Insufficient confluence — emit HOLD so the agent falls back to its
        # deterministic % stop-loss / take-profit safety net for any held
        # position.
        return Thesis(
            s.symbol,
            "HOLD",
            0.3,
            (
                f"HOLD (buy={buy_score}<{BUY_SCORE_THRESHOLD}, "
                f"sell={sell_score}<{SELL_SCORE_THRESHOLD}, RSI={s.rsi_14:.0f})"
            ),
        )


# ---------------------------------------------------------------------------
# LLM-backed agent.
# ---------------------------------------------------------------------------


_LLM_SYSTEM_PROMPT = (
    "You are a conservative crypto trading analyst. You read a technical "
    "snapshot (price, RSI, EMA stack, MACD, Bollinger band position, ATR, "
    "volume z-score, and candle pattern flags) and emit a directional "
    "thesis as a JSON object.\n\n"
    "Rules:\n"
    "  - Output keys: action ('BUY'|'HOLD'|'SELL'), confidence (0..1), "
    "rationale (one sentence).\n"
    "  - Prefer HOLD when signals conflict.\n"
    "  - BUY only when momentum, trend, and at least one confirmation "
    "(candle pattern or volume spike) align.\n"
    "  - SELL when there is a clear bearish confluence — overbought + "
    "bearish reversal candle, MACD bearish cross with downtrend, etc.\n"
    "  - Never use leverage, margin, futures, or options. Spot only.\n"
)


class LLMResearchAgent:
    """OpenAI-backed research agent. Falls back to rules if a call fails."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fallback = RuleBasedResearchAgent()
        self._client = None
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
            except ImportError:
                logger.warning("openai package not installed; using rule-based research")

    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis:
        if self._client is None:
            return await self._fallback.evaluate(snapshot)
        try:
            return await self._call_llm(snapshot)
        except Exception as exc:
            logger.warning("LLM research failed, falling back: %s", exc)
            return await self._fallback.evaluate(snapshot)

    async def _call_llm(self, snapshot: TechnicalSnapshot) -> Thesis:
        prompt = (
            "Analyse the following snapshot and emit a JSON object as "
            "specified.\n\n"
            f"Snapshot: {json.dumps(asdict(snapshot))}"
        )
        assert self._client is not None
        resp = await self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        action = data.get("action", "HOLD").upper()
        if action not in ("BUY", "HOLD", "SELL"):
            action = "HOLD"
        return Thesis(
            symbol=snapshot.symbol,
            action=action,
            confidence=float(data.get("confidence", 0.3)),
            rationale=str(data.get("rationale", "(no rationale)")),
        )


def build_research_agent(settings: Settings) -> ResearchAgent:
    if settings.openai_api_key:
        return LLMResearchAgent(settings)
    return RuleBasedResearchAgent()
