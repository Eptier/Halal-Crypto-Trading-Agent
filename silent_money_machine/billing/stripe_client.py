"""Stripe integration for payments, subscriptions, and invoicing."""

from __future__ import annotations

import logging
from typing import Any

import stripe

from silent_money_machine.core.config import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key


async def create_customer(email: str, name: str = "", metadata: dict[str, str] | None = None) -> str:
    """Create a Stripe customer and return the customer ID."""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {},
        )
        logger.info("Created Stripe customer: %s", customer.id)
        return customer.id
    except stripe.StripeError as exc:
        logger.error("Stripe customer creation failed: %s", exc)
        raise


async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str = "https://yourdomain.com/success",
    cancel_url: str = "https://yourdomain.com/cancel",
) -> dict[str, str]:
    """Create a Stripe Checkout session for subscription."""
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"session_id": session.id, "url": session.url or ""}
    except stripe.StripeError as exc:
        logger.error("Stripe checkout creation failed: %s", exc)
        raise


async def create_one_time_payment(
    amount_cents: int,
    currency: str = "usd",
    description: str = "",
    customer_id: str | None = None,
) -> dict[str, str]:
    """Create a one-time payment intent."""
    try:
        kwargs: dict[str, object] = {
            "amount": amount_cents,
            "currency": currency,
            "description": description,
        }
        if customer_id:
            kwargs["customer"] = customer_id
        intent = stripe.PaymentIntent.create(**kwargs)  # type: ignore[arg-type]
        return {
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret or "",
            "status": intent.status,
        }
    except stripe.StripeError as exc:
        logger.error("Stripe payment intent failed: %s", exc)
        raise


async def list_invoices(customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """List recent invoices for a customer."""
    try:
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
        return [
            {
                "id": inv.id,
                "amount_due": inv.amount_due,
                "status": inv.status,
                "created": inv.created,
                "hosted_invoice_url": inv.hosted_invoice_url,
            }
            for inv in invoices.data
        ]
    except stripe.StripeError as exc:
        logger.error("Stripe invoice list failed: %s", exc)
        raise


def handle_webhook_event(payload: bytes, sig_header: str) -> dict[str, Any]:
    """Verify and parse a Stripe webhook event."""
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return {"type": event.type, "data": event.data.object}
    except (stripe.SignatureVerificationError, ValueError) as exc:
        logger.error("Stripe webhook verification failed: %s", exc)
        raise
