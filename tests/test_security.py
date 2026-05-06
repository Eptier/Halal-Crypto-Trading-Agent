"""Security and API key tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from silent_money_machine.core.security import generate_api_key


@pytest.mark.asyncio
async def test_missing_api_key_returns_403(client: AsyncClient) -> None:
    resp = await client.get("/content-agency/clients")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invalid_api_key_returns_403(client: AsyncClient) -> None:
    resp = await client.get(
        "/content-agency/clients", headers={"X-API-Key": "wrong-key"}
    )
    assert resp.status_code == 403


def test_generate_api_key_format() -> None:
    key = generate_api_key()
    assert key.startswith("smm_")
    assert len(key) > 20


def test_generate_api_key_unique() -> None:
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100
