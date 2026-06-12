"""
Billing API Endpoints — Plans, subscriptions, invoices, payment methods, webhooks.

From spec section 8.2:
- GET    /api/v1/billing/plan — Current plan
- POST   /api/v1/billing/upgrade — Change plan
- POST   /api/v1/billing/downgrade — Cancel/downgrade
- GET    /api/v1/billing/invoices — Invoice history
- POST   /api/v1/billing/payment-method — Update payment method
- POST   /api/v1/billing/webhook/stripe — Stripe webhook (public)
- POST   /api/v1/billing/webhook/paystack — Paystack webhook (public)
- GET    /api/v1/billing/plans — List available plans
- POST   /api/v1/billing/check-feature — Check plan feature access
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from structlog import get_logger

from app.core.dependencies import CurrentUser, get_current_user, rate_limit
from app.core.exceptions import ValidationError
from app.services.billing import BillingService

logger = get_logger(__name__)

router = APIRouter()
billing_service = BillingService()


# ─── Plans ─────────────────────────────────────────────────────────────────────


@router.get("/plans")
async def list_plans(
    current_user: CurrentUser | None = None,
) -> list[dict[str, Any]]:
    """List all available plans with features and pricing."""
    return await billing_service.list_plans()


@router.get("/plan")
async def get_current_plan(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the current user's plan and subscription status."""
    return await billing_service.get_plan(user_id=current_user.id)


# ─── Upgrade / Downgrade ──────────────────────────────────────────────────────


@router.post("/upgrade")
async def upgrade_plan(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Upgrade or change the current user's plan.

    Body:
        plan_slug (str, required): Target plan slug ('pro', 'business')
        billing_cycle (str, default='monthly'): 'monthly' or 'yearly'
        payment_method (str, optional): 'stripe' or 'paystack'
        payment_method_id (str, optional): Payment source ID from provider
    """
    plan_slug = body.get("plan_slug")
    if not plan_slug:
        raise ValidationError(message="plan_slug is required")

    billing_cycle = body.get("billing_cycle", "monthly")
    payment_method = body.get("payment_method")
    payment_method_id = body.get("payment_method_id")

    return await billing_service.upgrade_plan(
        user_id=current_user.id,
        plan_slug=plan_slug,
        billing_cycle=billing_cycle,
        payment_method=payment_method,
        payment_method_id=payment_method_id,
    )


@router.post("/downgrade")
async def downgrade_plan(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Schedule downgrade to free plan at the end of the current period."""
    return await billing_service.downgrade_plan(user_id=current_user.id)


@router.post("/cancel")
async def cancel_subscription(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancel subscription at the end of the current period."""
    return await billing_service.cancel_subscription(user_id=current_user.id)


# ─── Invoices ──────────────────────────────────────────────────────────────────


@router.get("/invoices")
async def get_invoices(
    limit: int = Query(20, ge=1, le=100, description="Maximum invoices to return"),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get invoice history for the current user."""
    return await billing_service.get_invoices(
        user_id=current_user.id,
        limit=limit,
    )


# ─── Payment Method ────────────────────────────────────────────────────────────


@router.post("/payment-method")
async def update_payment_method(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update the payment method on file.

    Body:
        payment_method_id (str, required): Payment method ID from provider
        provider (str, default='stripe'): 'stripe' or 'paystack'
    """
    payment_method_id = body.get("payment_method_id")
    if not payment_method_id:
        raise ValidationError(message="payment_method_id is required")

    provider = body.get("provider", "stripe")

    return await billing_service.update_payment_method(
        user_id=current_user.id,
        payment_method_id=payment_method_id,
        provider=provider,
    )


# ─── Feature Access Check ─────────────────────────────────────────────────────


@router.post("/check-feature")
async def check_feature_access(
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Check if the current user's plan allows access to a feature.

    Body:
        feature_key (str, required): Feature key to check
            (e.g., 'max_agents', 'max_integrations', 'private_marketplace')

    Used by other services (agents, integrations, brain) to enforce plan limits.
    """
    feature_key = body.get("feature_key")
    if not feature_key:
        raise ValidationError(message="feature_key is required")

    return await billing_service.check_plan_feature_access(
        user_id=current_user.id,
        feature_key=feature_key,
    )


# ─── Usage Stats ──────────────────────────────────────────────────────────────


@router.get("/usage")
async def get_usage_stats(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the current user's usage statistics against plan limits.

    Returns counts for agents, integrations, memory nodes, and their limits.
    """
    usage: dict[str, Any] = {
        "agents": {},
        "integrations": {},
        "memory_nodes": {},
        "team_members": {},
    }

    # Fetch each feature check
    for feature_key in ("max_agents", "max_integrations", "max_memory_nodes", "max_team_members"):
        key_name = feature_key.replace("max_", "")
        result = await billing_service.check_plan_feature_access(
            user_id=current_user.id,
            feature_key=feature_key,
        )
        usage[key_name] = {
            "limit": result["limit"],
            "current": result["current"],
            "allowed": result["allowed"],
        }

    return usage


# ─── Webhooks (Public, no auth) ────────────────────────────────────────────────


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, Any]:
    """Handle incoming Stripe webhook events.

    This endpoint is public (no auth) — security is provided by
    Stripe's webhook signature verification.
    """
    payload = await request.body()
    sig_header = stripe_signature or ""

    return await billing_service.handle_stripe_webhook(
        payload=payload,
        sig_header=sig_header,
    )


@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str | None = Header(default=None, alias="x-paystack-signature"),
) -> dict[str, Any]:
    """Handle incoming Paystack webhook events.

    This endpoint is public (no auth) — security is provided by
    Paystack's HMAC-SHA512 webhook signature verification.
    """
    payload = await request.body()

    return await billing_service.handle_paystack_webhook(
        payload=payload,
    )
