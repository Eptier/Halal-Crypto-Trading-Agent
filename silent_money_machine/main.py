"""FastAPI application — Silent Money Machine entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from silent_money_machine.billing.router import router as billing_router
from silent_money_machine.core.config import settings
from silent_money_machine.core.database import init_db
from silent_money_machine.dashboard.router import router as dashboard_router
from silent_money_machine.scheduler.runner import shutdown_scheduler, start_scheduler
from silent_money_machine.services.content_agency.router import router as content_router
from silent_money_machine.services.outreach.router import router as outreach_router
from silent_money_machine.services.product_factory.router import router as product_router
from silent_money_machine.services.saas_api.router import router as saas_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    await init_db()
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered backend automation system for generating passive income "
        "through GPT and silent automation. Halal compliant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all route modules ──
app.include_router(content_router)
app.include_router(product_router)
app.include_router(saas_router)
app.include_router(outreach_router)
app.include_router(billing_router)
app.include_router(dashboard_router)


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "healthy"}
