"""FastAPI routes for the AI Micro-SaaS API (public-facing, keyed by subscriber API key)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from silent_money_machine.core.database import get_session
from silent_money_machine.core.security import RequireAPIKey
from silent_money_machine.services.saas_api.service import (
    check_and_increment_usage,
    create_subscription,
    get_subscription_by_key,
    list_subscriptions,
)
from silent_money_machine.services.saas_api.tools import TOOL_REGISTRY

router = APIRouter(prefix="/saas", tags=["AI Micro-SaaS API"])

DB = Annotated[AsyncSession, Depends(get_session)]


class SubscriptionCreate(BaseModel):
    email: EmailStr
    name: str = ""
    plan: str = "basic"


class ToolRequest(BaseModel):
    tool: str
    params: dict[str, str] = {}


# ── Admin endpoints (protected by master API key) ──


@router.post("/subscriptions", summary="Create a SaaS subscription (admin)")
async def create_sub(
    body: SubscriptionCreate, session: DB, _key: RequireAPIKey
) -> dict[str, Any]:
    sub = await create_subscription(session, body.email, body.name, body.plan)
    return {
        "id": sub.id,
        "email": sub.email,
        "api_key": sub.api_key,
        "plan": sub.plan,
        "monthly_quota": sub.monthly_quota,
    }


@router.get("/subscriptions", summary="List all subscriptions (admin)")
async def list_subs(session: DB, _key: RequireAPIKey) -> list[dict[str, Any]]:
    subs = await list_subscriptions(session)
    return [
        {
            "id": s.id,
            "email": s.email,
            "plan": s.plan,
            "used": s.used_this_month,
            "quota": s.monthly_quota,
            "status": s.status,
        }
        for s in subs
    ]


# ── Public tool endpoints (authenticated by subscriber API key) ──


@router.get("/tools", summary="List available AI tools")
async def list_tools() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": info["description"], "params": info["params"]}
        for name, info in TOOL_REGISTRY.items()
    ]


@router.post("/tools/run", summary="Run an AI tool (subscriber API key required)")
async def run_tool(
    body: ToolRequest,
    session: DB,
    x_subscriber_key: str = Header(..., alias="X-Subscriber-Key"),
) -> dict[str, Any]:
    sub = await get_subscription_by_key(session, x_subscriber_key)
    if not sub or sub.status != "active":
        raise HTTPException(status_code=403, detail="Invalid or inactive subscription key")

    if body.tool not in TOOL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool '{body.tool}'. Available: {list(TOOL_REGISTRY.keys())}",
        )

    within_quota = await check_and_increment_usage(session, sub)
    if not within_quota:
        raise HTTPException(status_code=429, detail="Monthly usage quota exceeded")

    handler = TOOL_REGISTRY[body.tool]["handler"]
    result = await handler(body.params)

    return {
        "tool": body.tool,
        "result": result,
        "usage": {"used": sub.used_this_month, "quota": sub.monthly_quota},
    }
