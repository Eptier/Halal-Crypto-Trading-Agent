"""FastAPI routes for the Digital Product Factory."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import get_session
from silent_money_machine.core.security import RequireAPIKey
from silent_money_machine.services.product_factory.service import (
    create_ebook,
    create_email_sequence_product,
    create_lead_magnet_product,
    get_product,
    list_products,
    publish_product,
)

router = APIRouter(prefix="/products", tags=["Digital Product Factory"])

DB = Annotated[AsyncSession, Depends(get_session)]


class EbookRequest(BaseModel):
    topic: str
    audience: str
    niche: str
    chapters: int = 8
    price: str = "19.99"


class LeadMagnetRequest(BaseModel):
    topic: str
    format: str = "checklist"
    niche: str = ""
    audience: str = ""
    price: str = "0.00"


class EmailSequenceRequest(BaseModel):
    goal: str
    niche: str
    audience: str
    product_name: str
    length: int = 5
    price: str = "29.99"


@router.post("/ebook", summary="Generate a complete ebook")
async def create_ebook_endpoint(
    body: EbookRequest, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    product = await create_ebook(
        session, body.topic, body.audience, body.niche, body.chapters, body.price
    )
    return {
        "id": product.id,
        "title": product.title,
        "type": product.product_type,
        "price": product.price_usd,
        "status": product.status,
    }


@router.post("/lead-magnet", summary="Generate a lead magnet")
async def create_lead_magnet_endpoint(
    body: LeadMagnetRequest, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    product = await create_lead_magnet_product(
        session, body.topic, body.format, body.niche, body.audience, body.price
    )
    return {"id": product.id, "title": product.title, "status": product.status}


@router.post("/email-sequence", summary="Generate an email sequence product")
async def create_email_seq_endpoint(
    body: EmailSequenceRequest, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    product = await create_email_sequence_product(
        session, body.goal, body.niche, body.audience, body.product_name, body.length, body.price
    )
    return {"id": product.id, "title": product.title, "status": product.status}


@router.get("/", summary="List digital products")
async def list_products_endpoint(
    session: DB,
    _key: RequireAPIKey,
    product_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    products = await list_products(session, product_type, status, limit)
    return [
        {
            "id": p.id,
            "title": p.title,
            "type": p.product_type,
            "niche": p.niche,
            "price": p.price_usd,
            "sales": p.sales_count,
            "revenue": p.revenue_usd,
            "status": p.status,
        }
        for p in products
    ]


@router.get("/{product_id}", summary="Get a product with full content")
async def get_product_endpoint(
    product_id: int, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    product = await get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "title": product.title,
        "type": product.product_type,
        "description": product.description,
        "content": product.content,
        "price": product.price_usd,
        "status": product.status,
    }


@router.post("/{product_id}/publish", summary="Publish a product")
async def publish_product_endpoint(
    product_id: int, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    product = await publish_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": product.id, "title": product.title, "status": product.status}
