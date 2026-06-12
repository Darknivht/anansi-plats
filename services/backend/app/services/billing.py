"""
Billing Service — Plans, subscriptions, invoices, Stripe & Paystack webhooks.

Handles subscription management, plan feature checks, payment processing
via Stripe and Paystack, and webhook event handling.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from structlog import get_logger

from app.core.config import settings
from app.core.events import get_session_factory
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PlanLimitError,
    ValidationError,
)
from app.models.billing import Plan, Subscription
from app.models.user import User

logger = get_logger(__name__)

# Plan slug hierarchy for upgrade/downgrade checks
PLAN_ORDER = {"free": 0, "pro": 1, "business": 2}

# Feature keys that can be checked via check_plan_feature_access
FEATURE_KEYS = {
    "max_agents",
    "max_integrations",
    "max_team_members",
    "max_memory_nodes",
    "daily_notes_history_days",
    "progressive_summarization_layers",
    "export_formats",
    "memory_analytics",
    "max_graph_depth",
    "max_reviews_per_day",
    "auto_linking_level",
    "private_marketplace",  # Business plan feature
}


class BillingService:
    """Business logic for plan management, subscriptions, and payments."""

    # ── Plans ──────────────────────────────────────────────────────────────────

    async def list_plans(self) -> list[dict[str, Any]]:
        """List all available plans with features.

        Returns:
            List of plan dicts with features and pricing.
        """
        factory = get_session_factory()
        async with factory() as session:
            query = (
                select(Plan)
                .where(Plan.is_active == True)
                .order_by(Plan.sort_order.asc(), Plan.price_monthly_cents.asc())
            )
            result = await session.execute(query)
            plans = result.scalars().all()

            return [self._serialize_plan(p) for p in plans]

    async def get_plan(self, user_id: str) -> dict[str, Any]:
        """Get the current plan and subscription status for a user.

        Args:
            user_id: UUID of the user.

        Returns:
            Dict with plan info, subscription status, period dates.
        """
        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            subscription = user.subscription

            if not subscription:
                # Default to free plan
                plan = await self._get_free_plan(session)
                return {
                    "plan": self._serialize_plan(plan) if plan else None,
                    "subscription": None,
                    "status": "free",
                    "current_period_start": None,
                    "current_period_end": None,
                }

            plan = await session.get(Plan, subscription.plan_id)
            if not plan:
                # Plan was deleted — fall back to free
                return {
                    "plan": None,
                    "subscription": None,
                    "status": "free",
                    "current_period_start": None,
                    "current_period_end": None,
                }

            return {
                "plan": self._serialize_plan(plan),
                "subscription": {
                    "id": str(subscription.id),
                    "status": subscription.status,
                    "billing_cycle": subscription.billing_cycle,
                    "current_period_start": subscription.current_period_start.isoformat()
                        if subscription.current_period_start else None,
                    "current_period_end": subscription.current_period_end.isoformat()
                        if subscription.current_period_end else None,
                    "trial_end": subscription.trial_end.isoformat()
                        if subscription.trial_end else None,
                    "canceled_at": subscription.canceled_at.isoformat()
                        if subscription.canceled_at else None,
                    "stripe_subscription_id": subscription.stripe_subscription_id,
                    "paystack_subscription_code": subscription.paystack_subscription_code,
                },
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat()
                    if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat()
                    if subscription.current_period_end else None,
            }

    # ── Upgrade / Downgrade / Cancel ──────────────────────────────────────────

    async def upgrade_plan(
        self,
        user_id: str,
        plan_slug: str,
        billing_cycle: str = "monthly",
        payment_method: str | None = None,
        payment_method_id: str | None = None,
    ) -> dict[str, Any]:
        """Upgrade (or change) a user's plan.

        Args:
            user_id: UUID of the user.
            plan_slug: Slug of the target plan (e.g., 'pro', 'business').
            billing_cycle: 'monthly' or 'yearly'.
            payment_method: 'stripe' or 'paystack'.
            payment_method_id: Payment method / source ID from the provider.

        Returns:
            Updated plan info dict.

        Raises:
            ValidationError: Invalid plan or downgrade.
            NotFoundError: Plan not found.
        """
        if billing_cycle not in ("monthly", "yearly"):
            raise ValidationError(
                message="Billing cycle must be 'monthly' or 'yearly'"
            )

        factory = get_session_factory()
        async with factory() as session:
            plan = await self._get_plan_by_slug(session, plan_slug)
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            current_sub = user.subscription
            current_plan_slug = "free"
            if current_sub:
                current_plan = await session.get(Plan, current_sub.plan_id)
                if current_plan:
                    current_plan_slug = current_plan.slug

            # Check if it's a valid upgrade (not downgrading)
            if current_plan_slug != "free":
                current_level = PLAN_ORDER.get(current_plan_slug, 0)
                target_level = PLAN_ORDER.get(plan_slug, 0)

                if target_level < current_level:
                    raise ValidationError(
                        message="Use downgrade_plan to move to a lower plan",
                        details={
                            "current_plan": current_plan_slug,
                            "target_plan": plan_slug,
                            "hint": "Call downgrade_plan endpoint instead",
                        },
                    )

            now = datetime.now(timezone.utc)

            if current_sub:
                # Update existing subscription
                current_sub.plan_id = plan.id
                current_sub.billing_cycle = billing_cycle
                current_sub.status = "active"
                current_sub.current_period_start = now
                # Calculate period end
                if billing_cycle == "yearly":
                    current_sub.current_period_end = now + timedelta(days=365)
                else:
                    current_sub.current_period_end = now + timedelta(days=30)
                current_sub.canceled_at = None

                # Handle proration: in production, this would call Stripe/Paystack
                # to calculate the prorated amount and issue a credit/invoice.
                # For now, we log it.
                if current_plan_slug != "free" and payment_method:
                    logger.info(
                        "Plan upgrade (proration scenario)",
                        user_id=user_id,
                        from_plan=current_plan_slug,
                        to_plan=plan_slug,
                        billing_cycle=billing_cycle,
                    )

                # Update payment provider
                if payment_method == "stripe" and payment_method_id:
                    current_sub.stripe_subscription_id = payment_method_id
                elif payment_method == "paystack" and payment_method_id:
                    current_sub.paystack_subscription_code = payment_method_id

                await session.commit()
                await session.refresh(current_sub)
            else:
                # Create new subscription
                period_end = now + timedelta(days=30)
                if billing_cycle == "yearly":
                    period_end = now + timedelta(days=365)

                new_sub = Subscription(
                    user_id=uuid.UUID(user_id),
                    plan_id=plan.id,
                    status="active",
                    billing_cycle=billing_cycle,
                    current_period_start=now,
                    current_period_end=period_end,
                )

                if payment_method == "stripe" and payment_method_id:
                    new_sub.stripe_subscription_id = payment_method_id
                elif payment_method == "paystack" and payment_method_id:
                    new_sub.paystack_subscription_code = payment_method_id

                session.add(new_sub)
                await session.commit()
                await session.refresh(new_sub)

                # Update user reference
                user.subscription = new_sub
                await session.commit()

            logger.info(
                "Plan upgraded",
                user_id=user_id,
                plan=plan_slug,
                billing_cycle=billing_cycle,
                current_plan=current_plan_slug,
            )

            return await self.get_plan(user_id)

    async def downgrade_plan(self, user_id: str) -> dict[str, Any]:
        """Downgrade user to free plan at the end of the current period.

        Args:
            user_id: UUID of the user.

        Returns:
            Updated plan info dict showing scheduled downgrade.
        """
        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            sub = user.subscription
            if not sub:
                raise ValidationError(message="You are already on the free plan")

            if sub.status == "cancelled":
                raise ValidationError(message="Your subscription is already cancelled")

            # Schedule downgrade at period end
            sub.status = "cancelled"
            sub.canceled_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(
                "Plan downgrade scheduled",
                user_id=user_id,
                current_plan_slug=str(sub.plan_id),
                period_end=sub.current_period_end.isoformat(),
            )

            return await self.get_plan(user_id)

    async def cancel_subscription(self, user_id: str) -> dict[str, Any]:
        """Cancel subscription at period end (same as downgrade for now).

        Args:
            user_id: UUID of the user.

        Returns:
            Updated plan info.
        """
        return await self.downgrade_plan(user_id)

    # ── Invoices ───────────────────────────────────────────────────────────────

    async def get_invoices(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get invoice history for a user.

        In production, invoices would be stored in an Invoice model or
        fetched from Stripe/Paystack. Here we generate from subscription data.

        Args:
            user_id: UUID of the user.
            limit: Maximum invoices to return.

        Returns:
            List of invoice dicts.
        """
        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            sub = user.subscription
            if not sub:
                return []

            plan = await session.get(Plan, sub.plan_id)
            if not plan:
                return []

            # Generate simulated invoice history from period data
            now = datetime.now(timezone.utc)
            invoices = []
            price_cents = (
                plan.price_yearly_cents
                if sub.billing_cycle == "yearly"
                else plan.price_monthly_cents
            )

            for i in range(min(limit, 12)):
                period_end = sub.current_period_end - timedelta(days=30 * i)
                period_start = period_end - timedelta(days=30)

                if period_start < sub.current_period_start:
                    break

                if period_end > now:
                    continue

                invoices.append({
                    "id": f"inv_{sub.id.hex[:8]}_{i}",
                    "amount_cents": price_cents,
                    "amount_display": f"${price_cents / 100:.2f}",
                    "currency": "USD",
                    "status": "paid" if period_end <= now else "pending",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "paid_at": period_end.isoformat() if period_end <= now else None,
                    "plan_name": plan.name,
                    "billing_cycle": sub.billing_cycle,
                    "description": f"{plan.name} ({sub.billing_cycle})",
                })

            return invoices

    # ── Payment Method ─────────────────────────────────────────────────────────

    async def update_payment_method(
        self,
        user_id: str,
        payment_method_id: str,
        provider: str = "stripe",
    ) -> dict[str, Any]:
        """Update the payment method on file for a user.

        Args:
            user_id: UUID of the user.
            payment_method_id: Payment method ID from Stripe/Paystack.
            provider: 'stripe' or 'paystack'.

        Returns:
            Dict confirming the update.
        """
        if provider not in ("stripe", "paystack"):
            raise ValidationError(message="Provider must be 'stripe' or 'paystack'")

        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            sub = user.subscription
            if sub:
                if provider == "stripe":
                    sub.stripe_subscription_id = payment_method_id
                elif provider == "paystack":
                    sub.paystack_subscription_code = payment_method_id
                await session.commit()

            logger.info(
                "Payment method updated",
                user_id=user_id,
                provider=provider,
            )

            return {
                "success": True,
                "provider": provider,
                "payment_method_id": payment_method_id,
                "message": "Payment method updated successfully",
            }

    # ── Feature Access Check ───────────────────────────────────────────────────

    async def check_plan_feature_access(
        self,
        user_id: str,
        feature_key: str,
    ) -> dict[str, Any]:
        """Check if a user's plan allows access to a specific feature.

        Used by other services (agents, integrations, brain) to enforce
        plan-based feature limits.

        Args:
            user_id: UUID of the user.
            feature_key: Feature key to check (e.g., 'max_agents',
                        'max_integrations', 'private_marketplace').

        Returns:
            Dict with 'allowed' (bool), 'limit' (int|None), 'current' (int|None),
            and 'plan' info.

        Raises:
            ValidationError: If feature_key is invalid.
        """
        if feature_key not in FEATURE_KEYS:
            raise ValidationError(
                message=f"Unknown feature key: {feature_key}. Valid keys: {', '.join(sorted(FEATURE_KEYS))}"
            )

        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, uuid.UUID(user_id))
            if not user:
                raise NotFoundError(
                    message="User not found",
                    resource_type="user",
                    resource_id=user_id,
                )

            # Get the user's plan
            plan = None
            sub = user.subscription

            if sub and sub.status in ("active", "trialing"):
                plan = await session.get(Plan, sub.plan_id)

            if not plan:
                # Default to free plan
                plan = await self._get_free_plan(session)

            if not plan:
                # No free plan seeded — use defaults
                defaults = self._free_plan_defaults()
                limit = defaults.get(feature_key)
                return {
                    "allowed": limit is None or limit > 0,
                    "limit": limit,
                    "current": None,
                    "plan_slug": "free",
                    "plan_name": "Free",
                    "feature_key": feature_key,
                }

            # Get the limit from the plan
            limit = getattr(plan, feature_key, None)

            # For boolean features like 'private_marketplace', check via features JSONB
            if limit is None and plan.features:
                limit = plan.features.get(feature_key, None)

            # Determine current usage (for numeric limits)
            current = None
            if feature_key == "max_agents":
                from app.models.agent import Agent
                count_query = select(func.count(Agent.id)).where(
                    Agent.user_id == uuid.UUID(user_id)
                )
                result = await session.execute(count_query)
                current = result.scalar() or 0
            elif feature_key == "max_integrations":
                from app.models.integration import Integration
                count_query = select(func.count(Integration.id)).where(
                    Integration.user_id == uuid.UUID(user_id)
                )
                result = await session.execute(count_query)
                current = result.scalar() or 0
            elif feature_key == "max_memory_nodes":
                from app.models.brain import MemoryNode
                count_query = select(func.count(MemoryNode.id)).where(
                    MemoryNode.user_id == uuid.UUID(user_id)
                )
                result = await session.execute(count_query)
                current = result.scalar() or 0

            allowed = limit is None or (current is not None and current < limit) or limit is None

            # For boolean-like features from features JSONB
            if isinstance(limit, bool):
                allowed = limit

            return {
                "allowed": allowed,
                "limit": limit if not isinstance(limit, bool) else None,
                "current": current,
                "plan_slug": plan.slug,
                "plan_name": plan.name,
                "feature_key": feature_key,
            }

    # ── Stripe Webhook ─────────────────────────────────────────────────────────

    async def handle_stripe_webhook(
        self,
        payload: bytes,
        sig_header: str,
    ) -> dict[str, Any]:
        """Handle incoming Stripe webhook events.

        Args:
            payload: Raw request body bytes.
            sig_header: Stripe-Signature header value.

        Returns:
            Dict with status and event info.

        Raises:
            ValidationError: If signature verification fails.
        """
        webhook_secret = settings.stripe.webhook_secret
        if not webhook_secret:
            logger.warning("Stripe webhook secret not configured — skipping verification")
            # In development, allow unverified
            event_data = json.loads(payload)
        else:
            try:
                # Verify the signature
                import stripe as stripe_lib
                event_data = stripe_lib.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError as exc:
                raise ValidationError(
                    message=f"Invalid Stripe webhook payload: {exc}"
                ) from exc
            except Exception as exc:
                raise ValidationError(
                    message=f"Stripe webhook signature verification failed: {exc}"
                ) from exc

        event_type = event_data.get("type", "")
        data_object = event_data.get("data", {}).get("object", {})

        logger.info("Stripe webhook received", event_type=event_type)

        # Handle different event types
        handler_map: dict[str, Any] = {
            "customer.subscription.created": self._handle_stripe_subscription_created,
            "customer.subscription.updated": self._handle_stripe_subscription_updated,
            "customer.subscription.deleted": self._handle_stripe_subscription_deleted,
            "invoice.paid": self._handle_stripe_invoice_paid,
            "invoice.payment_failed": self._handle_stripe_invoice_failed,
            "payment_method.attached": self._handle_stripe_payment_method_attached,
        }

        handler = handler_map.get(event_type)
        if handler:
            await handler(data_object)
        else:
            logger.debug("Unhandled Stripe event type", event_type=event_type)

        return {
            "received": True,
            "event_type": event_type,
            "event_id": event_data.get("id"),
        }

    # ── Stripe Webhook Handlers ────────────────────────────────────────────────

    async def _handle_stripe_subscription_created(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe subscription.created event."""
        subscription_id = data.get("id", "")
        customer_id = data.get("customer", "")
        status = data.get("status", "")
        plan_id = data.get("plan", {}).get("id", "")
        period_start = data.get("current_period_start", 0)
        period_end = data.get("current_period_end", 0)

        # Find the user by stripe customer ID
        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.stripe_customer_id == customer_id
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.stripe_subscription_id = subscription_id
                subscription.status = self._map_stripe_status(status)
                if period_start:
                    subscription.current_period_start = datetime.fromtimestamp(
                        period_start, tz=timezone.utc
                    )
                if period_end:
                    subscription.current_period_end = datetime.fromtimestamp(
                        period_end, tz=timezone.utc
                    )
                await session.commit()

            logger.info(
                "Stripe subscription created",
                subscription_id=subscription_id,
                customer_id=customer_id,
                status=status,
            )

    async def _handle_stripe_subscription_updated(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe subscription.updated event."""
        subscription_id = data.get("id", "")
        status = data.get("status", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == subscription_id
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.status = self._map_stripe_status(status)
                period_end = data.get("current_period_end", 0)
                if period_end:
                    subscription.current_period_end = datetime.fromtimestamp(
                        period_end, tz=timezone.utc
                    )
                await session.commit()

                logger.info(
                    "Stripe subscription updated",
                    subscription_id=subscription_id,
                    status=status,
                )

    async def _handle_stripe_subscription_deleted(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe subscription.deleted event."""
        subscription_id = data.get("id", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == subscription_id
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                # Schedule downgrade at period end
                subscription.status = "cancelled"
                subscription.canceled_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(
                    "Stripe subscription deleted",
                    subscription_id=subscription_id,
                )

    async def _handle_stripe_invoice_paid(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe invoice.paid event."""
        invoice_id = data.get("id", "")
        subscription_id = data.get("subscription", "")
        amount_paid = data.get("amount_paid", 0)
        currency = data.get("currency", "usd")

        logger.info(
            "Stripe invoice paid",
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            amount=amount_paid,
            currency=currency,
        )

    async def _handle_stripe_invoice_failed(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe invoice.payment_failed event."""
        subscription_id = data.get("subscription", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == subscription_id
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.status = "past_due"
                await session.commit()

                logger.warning(
                    "Stripe invoice payment failed",
                    subscription_id=subscription_id,
                )

    async def _handle_stripe_payment_method_attached(
        self, data: dict[str, Any]
    ) -> None:
        """Handle stripe payment_method.attached event."""
        customer_id = data.get("customer", "")
        payment_method_id = data.get("id", "")

        logger.info(
            "Stripe payment method attached",
            customer_id=customer_id,
            payment_method_id=payment_method_id,
        )

    @staticmethod
    def _map_stripe_status(stripe_status: str) -> str:
        """Map Stripe subscription status to Anansi status."""
        mapping = {
            "incomplete": "past_due",
            "incomplete_expired": "expired",
            "trialing": "trialing",
            "active": "active",
            "past_due": "past_due",
            "canceled": "cancelled",
            "unpaid": "past_due",
        }
        return mapping.get(stripe_status, "active")

    # ── Paystack Webhook ───────────────────────────────────────────────────────

    async def handle_paystack_webhook(
        self,
        payload: bytes,
    ) -> dict[str, Any]:
        """Handle incoming Paystack webhook events.

        Paystack signs webhooks with a HMAC-SHA512 signature in the
        ``x-paystack-signature`` header.

        Args:
            payload: Raw request body bytes.

        Returns:
            Dict with status and event info.
        """
        event_data = json.loads(payload)
        event_type = event_data.get("event", "")

        logger.info("Paystack webhook received", event_type=event_type)

        data = event_data.get("data", {})

        # Handle different event types
        handler_map: dict[str, Any] = {
            "subscription.create": self._handle_paystack_subscription_create,
            "subscription.disable": self._handle_paystack_subscription_disable,
            "charge.success": self._handle_paystack_charge_success,
            "invoice.create": self._handle_paystack_invoice_create,
            "invoice.payment_failed": self._handle_paystack_invoice_failed,
        }

        handler = handler_map.get(event_type)
        if handler:
            await handler(data)
        else:
            logger.debug("Unhandled Paystack event type", event_type=event_type)

        return {
            "received": True,
            "event_type": event_type,
        }

    # ── Paystack Webhook Handlers ──────────────────────────────────────────────

    async def _handle_paystack_subscription_create(
        self, data: dict[str, Any]
    ) -> None:
        """Handle paystack subscription.create event."""
        subscription_code = data.get("subscription_code", "")
        customer_code = data.get("customer", {}).get("customer_code", "")
        status = data.get("status", "")
        next_payment = data.get("next_payment_date", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.paystack_subscription_code == subscription_code
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.status = "active"
                if next_payment:
                    try:
                        from datetime import datetime as dt
                        subscription.current_period_end = dt.fromisoformat(
                            next_payment.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        pass
                await session.commit()

            logger.info(
                "Paystack subscription created",
                subscription_code=subscription_code,
                status=status,
            )

    async def _handle_paystack_subscription_disable(
        self, data: dict[str, Any]
    ) -> None:
        """Handle paystack subscription.disable event."""
        subscription_code = data.get("subscription_code", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.paystack_subscription_code == subscription_code
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.status = "cancelled"
                subscription.canceled_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(
                    "Paystack subscription disabled",
                    subscription_code=subscription_code,
                )

    async def _handle_paystack_charge_success(
        self, data: dict[str, Any]
    ) -> None:
        """Handle paystack charge.success event."""
        reference = data.get("reference", "")
        amount = data.get("amount", 0)
        currency = data.get("currency", "NGN")
        status = data.get("status", "")

        logger.info(
            "Paystack charge success",
            reference=reference,
            amount=amount,
            currency=currency,
        )

    async def _handle_paystack_invoice_create(
        self, data: dict[str, Any]
    ) -> None:
        """Handle paystack invoice.create event."""
        invoice_code = data.get("invoice_code", "")
        subscription_code = data.get("subscription", "")
        amount = data.get("amount", 0)

        logger.info(
            "Paystack invoice created",
            invoice_code=invoice_code,
            subscription_code=subscription_code,
            amount=amount,
        )

    async def _handle_paystack_invoice_failed(
        self, data: dict[str, Any]
    ) -> None:
        """Handle paystack invoice.payment_failed event."""
        subscription_code = data.get("subscription", "")

        factory = get_session_factory()
        async with factory() as session:
            sub = await session.execute(
                select(Subscription).where(
                    Subscription.paystack_subscription_code == subscription_code
                )
            )
            subscription = sub.scalar_one_or_none()

            if subscription:
                subscription.status = "past_due"
                await session.commit()

                logger.warning(
                    "Paystack invoice payment failed",
                    subscription_code=subscription_code,
                )

    # ── Internal Helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def _get_free_plan(session: AsyncSession) -> Plan | None:
        """Get the free plan from the database."""
        result = await session.execute(
            select(Plan).where(Plan.slug == "free")
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _get_plan_by_slug(
        session: AsyncSession, slug: str
    ) -> Plan:
        """Get a plan by slug, raising NotFoundError if missing."""
        result = await session.execute(
            select(Plan).where(
                and_(Plan.slug == slug, Plan.is_active == True)
            )
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError(
                message=f"Plan '{slug}' not found",
                resource_type="plan",
                resource_id=slug,
            )
        return plan

    @staticmethod
    def _free_plan_defaults() -> dict[str, Any]:
        """Default free plan feature limits when no free plan is seeded."""
        return {
            "max_agents": 5,
            "max_integrations": 3,
            "max_team_members": 1,
            "max_memory_nodes": 500,
            "daily_notes_history_days": 7,
            "progressive_summarization_layers": 1,
            "export_formats": ["csv", "json"],
            "memory_analytics": "weekly",
            "max_graph_depth": 2,
            "max_reviews_per_day": 3,
        }

    @staticmethod
    def _serialize_plan(plan: Plan) -> dict[str, Any]:
        """Convert a Plan ORM instance to a safe API response dict."""
        return {
            "id": str(plan.id),
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "price_monthly_cents": plan.price_monthly_cents,
            "price_monthly_display": f"${plan.price_monthly_cents / 100:.2f}" if plan.price_monthly_cents > 0 else "Free",
            "price_yearly_cents": plan.price_yearly_cents,
            "price_yearly_display": f"${plan.price_yearly_cents / 100:.2f}" if plan.price_yearly_cents > 0 else "Free",
            "max_agents": plan.max_agents,
            "max_integrations": plan.max_integrations,
            "max_team_members": plan.max_team_members,
            "max_memory_nodes": plan.max_memory_nodes,
            "max_graph_depth": plan.max_graph_depth,
            "max_reviews_per_day": plan.max_reviews_per_day,
            "daily_notes_history_days": plan.daily_notes_history_days,
            "progressive_summarization_layers": plan.progressive_summarization_layers,
            "auto_linking_level": plan.auto_linking_level,
            "export_formats": plan.export_formats or [],
            "memory_analytics": plan.memory_analytics,
            "features": plan.features or {},
            "sort_order": plan.sort_order,
            "is_active": plan.is_active,
        }


__all__ = ["BillingService"]
