"""Centralised application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 4096

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_basic: str = ""
    stripe_price_pro: str = ""

    # --- Email ---
    email_provider: str = "resend"
    resend_api_key: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./silent_money_machine.db"

    # --- Security ---
    api_secret_key: str = "change-me-in-production"
    api_key_header: str = "X-API-Key"

    # --- App ---
    app_name: str = "Silent Money Machine"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- Scheduler ---
    scheduler_enabled: bool = True
    content_generation_hour: int = 6
    outreach_hour: int = 9
    product_generation_hour: int = 3

    # --- Outreach ---
    daily_outreach_limit: int = 50
    follow_up_days: str = "3,7,14"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def follow_up_day_list(self) -> list[int]:
        return [int(d.strip()) for d in self.follow_up_days.split(",") if d.strip()]


settings = Settings()
