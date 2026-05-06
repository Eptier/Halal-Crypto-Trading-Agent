"""Outreach Engine API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_leads_empty(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/outreach/leads", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_bulk_add_leads(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/outreach/leads/bulk",
        json={
            "leads": [
                {"name": "Alice", "email": "alice@corp.com", "company": "Corp A"},
                {"name": "Bob", "email": "bob@corp.com", "company": "Corp B"},
            ]
        },
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] == 2
