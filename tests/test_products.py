"""Digital Product Factory API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/products/", headers=api_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, api_headers: dict[str, str]) -> None:
    resp = await client.get("/products/999", headers=api_headers)
    assert resp.status_code == 404
