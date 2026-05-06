"""FastAPI routes for billing and Stripe integration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from silent_money_machine.billing.stripe_client import (
    create_checkout_session,
    create_customer,
    create_one_time_payment,
    handle_webhook_event,
    list_invoices,
)
from silent_money_machine.core.security import RequireAPIKey

router = APIRouter(prefix="/billing", tags=["Billing & Payments"])


class CustomerCreate(BaseModel):
    email: EmailStr
    name: str = ""


class CheckoutRequest(BaseModel):
    customer_id: str
    price_id: str
    success_url: str = "https://yourdomain.com/success"
    cancel_url: str = "https://yourdomain.com/cancel"


class PaymentRequest(BaseModel):
    amount_cents: int
    currency: str = "usd"
    description: str = ""
    customer_id: str | None = None


@router.post("/customers", summary="Create a Stripe customer")
async def create_stripe_customer(
    body: CustomerCreate, _key: RequireAPIKey
) -> dict[str, str]:
    customer_id = await create_customer(body.email, body.name)
    return {"customer_id": customer_id}


@router.post("/checkout", summary="Create a checkout session")
async def create_checkout(
    body: CheckoutRequest, _key: RequireAPIKey
) -> dict[str, str]:
    return await create_checkout_session(
        body.customer_id, body.price_id, body.success_url, body.cancel_url
    )


@router.post("/pay", summary="Create a one-time payment")
async def create_payment(
    body: PaymentRequest, _key: RequireAPIKey
) -> dict[str, str]:
    return await create_one_time_payment(
        body.amount_cents, body.currency, body.description, body.customer_id
    )


@router.get("/invoices/{customer_id}", summary="List invoices for a customer")
async def get_invoices(
    customer_id: str, _key: RequireAPIKey, limit: int = 10
) -> list[dict[str, Any]]:
    return await list_invoices(customer_id, limit)


@router.post("/webhook", summary="Stripe webhook handler")
async def stripe_webhook(request: Request) -> dict[str, str]:
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        event = handle_webhook_event(payload, sig)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "received", "type": event["type"]}
