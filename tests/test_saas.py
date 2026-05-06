"""SaaS API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tools(client: AsyncClient) -> None:
    resp = await client.get("/saas/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) >= 4
    names = [t["name"] for t in tools]
    assert "resume_writer" in names
    assert "blog_writer" in names


@pytest.mark.asyncio
async def test_create_subscription(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/saas/subscriptions",
        json={"email": "sub@example.com", "name": "Subscriber", "plan": "basic"},
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "basic"
    assert "api_key" in data
    assert data["monthly_quota"] == 1000


@pytest.mark.asyncio
async def test_run_tool_invalid_key(client: AsyncClient) -> None:
    resp = await client.post(
        "/saas/tools/run",
        json={"tool": "resume_writer", "params": {}},
        headers={"X-Subscriber-Key": "invalid-key"},
    )
    assert resp.status_code == 403
