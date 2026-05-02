"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global agent configuration. Values are read from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    trading_mode: Literal["paper", "live"] = "paper"
    exchange: str = "binance"
    quote_currency: str = "USDT"
    paper_starting_equity: float = 1000.0

    exchange_api_key: SecretStr | None = None
    exchange_api_secret: SecretStr | None = None

    max_position_pct: float = Field(0.20, ge=0.01, le=0.50)
    max_open_positions: int = Field(3, ge=1, le=10)
    max_daily_loss_pct: float = Field(0.05, ge=0.005, le=0.20)
    stop_loss_pct: float = Field(0.05, ge=0.005, le=0.50)
    take_profit_pct: float = Field(0.10, ge=0.005, le=1.00)
    min_trade_quote: float = Field(10.0, ge=1.0)

    research_interval_seconds: int = Field(300, ge=30)
    trading_interval_seconds: int = Field(60, ge=5)

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"

    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765

    database_url: str = "sqlite+aiosqlite:///data/agent.db"
    log_level: str = "INFO"

    repo_root: Path = Path(__file__).resolve().parent.parent

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    @property
    def db_path(self) -> Path:
        prefix = "sqlite+aiosqlite:///"
        url = self.database_url
        if url.startswith(prefix):
            return self.repo_root / url[len(prefix) :]
        return Path(url)


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
