"""Dashboard & Analytics API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_overview(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/dashboard/overview", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "clients" in data
    assert "products" in data
    assert "saas_subscribers" in data
    assert "leads" in data


@pytest.mark.asyncio
async def test_revenue_summary(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/dashboard/revenue", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "total_usd" in data


@pytest.mark.asyncio
async def test_record_and_get_revenue(client: AsyncClient, api_headers: dict[str, str]) -> None:
    await client.post(
        "/dashboard/revenue",
        json={"stream": "content_agency", "amount_usd": "500.00", "transactions": 2},
        headers=api_headers,
    )
    await client.post(
        "/dashboard/revenue",
        json={"stream": "saas_api", "amount_usd": "300.00"},
        headers=api_headers,
    )
    resp = await client.get("/dashboard/revenue", headers=api_headers)
    data = resp.json()
    assert float(data["total_usd"]) == 800.0


@pytest.mark.asyncio
async def test_scheduler_history(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/dashboard/scheduler", headers=api_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
