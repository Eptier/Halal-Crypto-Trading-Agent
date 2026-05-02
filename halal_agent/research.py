"""Research agent: forms a directional thesis (BUY / HOLD / SELL) per asset.

Two backends:
  * `LLMResearchAgent` — uses OpenAI when an API key is configured. Feeds
    technical snapshot + recent price action into a structured prompt and
    parses a JSON response.
  * `RuleBasedResearchAgent` — deterministic fallback. Uses RSI/MACD/EMA
    crossover heuristics. Always available, no external dependency.

The research agent only *proposes* trades; the strategy + risk manager
decide whether to act. This separation keeps the LLM out of the
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


@dataclass
class Thesis:
    symbol: str
    action: Action
    confidence: float  # 0..1
    rationale: str


class ResearchAgent(Protocol):
    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis: ...


class RuleBasedResearchAgent:
    """Deterministic, dependency-free research heuristic.

    Logic:
      * BUY  if oversold (RSI<30) AND uptrend (EMA20>EMA50) AND MACD>signal
      * SELL if overbought (RSI>70) OR (EMA20<EMA50 AND MACD<signal)
      * HOLD otherwise
    Confidence scales with how decisively the conditions are met.
    """

    async def evaluate(self, snapshot: TechnicalSnapshot) -> Thesis:
        s = snapshot
        macd_bull = s.macd > s.macd_signal
        macd_bear = s.macd < s.macd_signal

        if s.oversold and s.trend_up and macd_bull:
            confidence = min(1.0, (30 - s.rsi_14) / 30 + 0.5)
            return Thesis(
                s.symbol,
                "BUY",
                confidence,
                f"RSI={s.rsi_14:.1f} oversold; EMA20>EMA50; MACD bullish.",
            )
        if s.overbought or (not s.trend_up and macd_bear):
            confidence = 0.6 if s.overbought else 0.5
            return Thesis(
                s.symbol,
                "SELL",
                confidence,
                f"RSI={s.rsi_14:.1f}; trend_up={s.trend_up}; MACD bearish.",
            )
        return Thesis(
            s.symbol,
            "HOLD",
            0.3,
            f"No clear signal (RSI={s.rsi_14:.1f}, trend_up={s.trend_up}).",
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
            "You are a conservative crypto trading analyst. Given the technical "
            "snapshot below, output a JSON object with keys "
            '"action" (one of "BUY","HOLD","SELL"), '
            '"confidence" (0..1), and "rationale" (one sentence).\n\n'
            "Be conservative — prefer HOLD over BUY/SELL when signals conflict.\n\n"
            f"Snapshot: {json.dumps(asdict(snapshot))}\n"
        )
        assert self._client is not None
        resp = await self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
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
