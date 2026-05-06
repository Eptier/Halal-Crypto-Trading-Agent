"""FastAPI routes for the Outreach Engine."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import get_session
from silent_money_machine.core.security import RequireAPIKey
from silent_money_machine.services.outreach.service import (
    add_and_score_lead,
    add_lead,
    list_leads,
    run_daily_outreach,
    send_cold_outreach,
    send_follow_up,
)

router = APIRouter(prefix="/outreach", tags=["Outreach Engine"])

DB = Annotated[AsyncSession, Depends(get_session)]


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    industry: str = ""
    company_size: str = "unknown"
    source: str = "manual"


class LeadBulkCreate(BaseModel):
    leads: list[LeadCreate]


@router.post("/leads", summary="Add a single lead with auto-scoring")
async def add_single_lead(
    body: LeadCreate, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    lead = await add_and_score_lead(
        session,
        name=body.name,
        email=body.email,
        company=body.company,
        industry=body.industry,
        company_size=body.company_size,
        source=body.source,
    )
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "score": lead.score,
        "stage": lead.outreach_stage,
    }


@router.post("/leads/bulk", summary="Bulk-add leads")
async def add_bulk_leads(
    body: LeadBulkCreate, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    results = []
    for lead_data in body.leads:
        lead = await add_lead(session, lead_data.model_dump())
        results.append({"id": lead.id, "email": lead.email})
    return {"added": len(results), "leads": results}


@router.get("/leads", summary="List leads")
async def get_leads(
    session: DB,
    _key: RequireAPIKey,
    stage: str | None = None,
    min_score: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    leads = await list_leads(session, stage, min_score, limit)
    return [
        {
            "id": ld.id,
            "name": ld.name,
            "email": ld.email,
            "company": ld.company,
            "score": ld.score,
            "stage": ld.outreach_stage,
            "last_contacted": ld.last_contacted_at,
        }
        for ld in leads
    ]


@router.post("/leads/{lead_id}/contact", summary="Send cold email to a lead")
async def contact_lead(
    lead_id: int, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    from silent_money_machine.core.database import Lead

    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    email_data = await send_cold_outreach(session, lead)
    return {"lead_id": lead.id, "email": email_data, "stage": lead.outreach_stage}


@router.post("/leads/{lead_id}/follow-up", summary="Send follow-up to a lead")
async def follow_up_lead(
    lead_id: int,
    session: DB,
    _key: RequireAPIKey,
    attempt: int = 1,
) -> dict[str, Any]:
    from silent_money_machine.core.database import Lead

    lead = await session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    email_data = await send_follow_up(session, lead, attempt)
    return {"lead_id": lead.id, "email": email_data, "stage": lead.outreach_stage}


@router.post("/run-daily", summary="Trigger daily outreach cycle")
async def trigger_daily_outreach(session: DB, _key: RequireAPIKey) -> dict[str, Any]:
    stats = await run_daily_outreach(session)
    return {"status": "completed", "stats": stats}
