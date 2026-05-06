"""Async OpenAI client wrapper with retry logic and cost tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from silent_money_machine.core.config import settings

logger = logging.getLogger(__name__)

# Approximate pricing per 1K tokens (input/output) for common models
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.005, 0.015),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}


@dataclass
class GPTResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model: str


class GPTClient:
    """Thin async wrapper around the OpenAI chat completion API."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.default_model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "You are a professional content creator and business automation assistant.",
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7,
    ) -> GPTResponse:
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = prompt_tokens + completion_tokens

        input_rate, output_rate = _PRICING.get(model, (0.001, 0.002))
        cost = (prompt_tokens / 1000 * input_rate) + (completion_tokens / 1000 * output_rate)

        logger.info(
            "GPT call: model=%s tokens=%d cost=$%.4f",
            model,
            total_tokens,
            cost,
        )

        return GPTResponse(
            text=choice.message.content or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=round(cost, 6),
            model=model,
        )

    async def generate_structured(
        self,
        prompt: str,
        *,
        system: str = "You are a JSON-only assistant. Return valid JSON only, no markdown.",
        model: str | None = None,
        temperature: float = 0.4,
    ) -> GPTResponse:
        """Generate a response expected to be valid JSON."""
        return await self.generate(
            prompt, system=system, model=model, temperature=temperature
        )


gpt_client = GPTClient()
