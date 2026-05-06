"""FastAPI routes for the Content Agency service."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import get_session
from silent_money_machine.core.security import RequireAPIKey
from silent_money_machine.services.content_agency.service import (
    batch_generate_for_all_clients,
    create_client,
    generate_content_for_client,
    get_client,
    list_active_clients,
    list_content,
)

router = APIRouter(prefix="/content-agency", tags=["Content Agency"])

DB = Annotated[AsyncSession, Depends(get_session)]


class ClientCreate(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    niche: str = ""
    plan: str = "basic"
    delivery_method: str = "email"
    webhook_url: str = ""
    content_frequency: str = "weekly"


class ContentRequest(BaseModel):
    content_type: str = "blog"
    topic: str = ""
    keywords: str = ""


@router.post("/clients", summary="Onboard a new content client")
async def onboard_client(
    body: ClientCreate, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    client = await create_client(session, body.model_dump())
    return {"id": client.id, "email": client.email, "status": "created"}


@router.get("/clients", summary="List active clients")
async def list_clients(session: DB, _key: RequireAPIKey) -> list[dict[str, Any]]:
    clients = await list_active_clients(session)
    return [
        {"id": c.id, "name": c.name, "email": c.email, "niche": c.niche, "plan": c.plan}
        for c in clients
    ]


@router.post("/clients/{client_id}/generate", summary="Generate content for a client")
async def generate_for_client(
    client_id: int,
    body: ContentRequest,
    session: DB,
    _key: RequireAPIKey,
) -> dict[str, Any]:
    client = await get_client(session, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    piece = await generate_content_for_client(
        session, client, body.content_type, body.topic, body.keywords
    )
    return {
        "id": piece.id,
        "title": piece.title,
        "content_type": piece.content_type,
        "tokens_used": piece.tokens_used,
        "cost_usd": piece.cost_usd,
        "status": piece.status,
    }


@router.post("/generate-all", summary="Batch-generate content for all active clients")
async def batch_generate(session: DB, _key: RequireAPIKey) -> dict[str, Any]:
    pieces = await batch_generate_for_all_clients(session)
    return {"generated": len(pieces), "pieces": [p.id for p in pieces]}


@router.get("/content", summary="List generated content")
async def get_content(
    session: DB,
    _key: RequireAPIKey,
    client_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    pieces = await list_content(session, client_id, limit)
    return [
        {
            "id": p.id,
            "client_id": p.client_id,
            "title": p.title,
            "content_type": p.content_type,
            "status": p.status,
            "tokens_used": p.tokens_used,
        }
        for p in pieces
    ]
