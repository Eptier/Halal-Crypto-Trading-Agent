"""Content Agency API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_client(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/content-agency/clients",
        json={
            "name": "Test Corp",
            "email": "test@example.com",
            "niche": "technology",
            "plan": "basic",
        },
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_clients(client: AsyncClient, api_headers: dict[str, str]) -> None:
    await client.post(
        "/content-agency/clients",
        json={"name": "A", "email": "a@example.com", "niche": "tech"},
        headers=api_headers,
    )
    resp = await client.get("/content-agency/clients", headers=api_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_content_empty(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/content-agency/content", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_auth_required(client: AsyncClient) -> None:
    resp = await client.get("/content-agency/clients")
    assert resp.status_code == 403
