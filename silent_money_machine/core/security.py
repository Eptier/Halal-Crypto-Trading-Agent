"""API key authentication and security utilities."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from silent_money_machine.core.config import settings

api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> str:
    """Validate the incoming API key against the configured secret."""
    if not api_key or api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key.",
        )
    return api_key


RequireAPIKey = Annotated[str, Depends(verify_api_key)]


def generate_api_key(prefix: str = "smm") -> str:
    """Generate a random API key for SaaS subscribers."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"
