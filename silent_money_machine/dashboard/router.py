"""FastAPI routes for the monitoring & analytics dashboard."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import get_session
from silent_money_machine.core.security import RequireAPIKey
from silent_money_machine.dashboard.metrics import (
    get_overview,
    get_revenue_summary,
    get_scheduler_history,
    record_revenue,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

DB = Annotated[AsyncSession, Depends(get_session)]


@router.get("/overview", summary="System overview — all key metrics")
async def dashboard_overview(session: DB, _key: RequireAPIKey) -> dict[str, Any]:
    return await get_overview(session)


@router.get("/revenue", summary="Revenue summary by month")
async def revenue_summary(
    session: DB, _key: RequireAPIKey, month: str | None = None
) -> dict[str, Any]:
    return await get_revenue_summary(session, month)


class RevenueEntry(BaseModel):
    stream: str
    amount_usd: str
    transactions: int = 1
    month: str | None = None


@router.post("/revenue", summary="Record a revenue entry")
async def add_revenue(
    body: RevenueEntry, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    rec = await record_revenue(session, body.stream, body.amount_usd, body.transactions, body.month)
    return {
        "id": rec.id,
        "month": rec.month,
        "stream": rec.stream,
        "amount_usd": rec.amount_usd,
        "transactions": rec.transactions,
    }


@router.get("/scheduler", summary="Scheduler job history")
async def scheduler_history(
    session: DB, _key: RequireAPIKey, limit: int = 20
) -> list[dict[str, Any]]:
    return await get_scheduler_history(session, limit)
