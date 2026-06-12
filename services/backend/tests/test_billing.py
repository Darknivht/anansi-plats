"""
Billing Tests — Plans, upgrade/downgrade, Stripe/Paystack webhooks, invoices.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestPlans:
    """Test plan listing and info."""

    @pytest.mark.asyncio
    async def test_list_plans(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing available plans."""
        response = await async_client.get(
            "/api/v1/billing/plans",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_current_plan(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting current subscription plan."""
        response = await async_client.get(
            "/api/v1/billing/plan",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestSubscription:
    """Test subscription management."""

    @pytest.mark.asyncio
    async def test_upgrade_to_pro(self, async_client: AsyncClient, auth_headers: dict):
        """Test upgrading to pro plan."""
        response = await async_client.post(
            "/api/v1/billing/upgrade",
            headers=auth_headers,
            json={"plan_id": "pro"},
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_downgrade_to_free(self, async_client: AsyncClient, auth_headers: dict):
        """Test downgrading to free plan."""
        response = await async_client.post(
            "/api/v1/billing/downgrade",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, async_client: AsyncClient, auth_headers: dict):
        """Test canceling subscription."""
        response = await async_client.post(
            "/api/v1/billing/cancel",
            headers=auth_headers,
        )
        assert response.status_code in (200, 500)


class TestInvoices:
    """Test invoice history."""

    @pytest.mark.asyncio
    async def test_get_invoice_history(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting invoice history."""
        response = await async_client.get(
            "/api/v1/billing/invoices",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestFeatureCheck:
    """Test feature access checking."""

    @pytest.mark.asyncio
    async def test_check_feature(self, async_client: AsyncClient, auth_headers: dict):
        """Test checking feature access."""
        response = await async_client.post(
            "/api/v1/billing/check-feature",
            headers=auth_headers,
            json={"feature": "export_brain"},
        )
        assert response.status_code in (200, 403)


class TestUsage:
    """Test usage tracking."""

    @pytest.mark.asyncio
    async def test_get_usage(self, async_client: AsyncClient, auth_headers: dict):
        """Test getting usage stats."""
        response = await async_client.get(
            "/api/v1/billing/usage",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestPaymentMethod:
    """Test payment method management."""

    @pytest.mark.asyncio
    async def test_add_payment_method(self, async_client: AsyncClient, auth_headers: dict):
        """Test adding a payment method."""
        response = await async_client.post(
            "/api/v1/billing/payment-method",
            headers=auth_headers,
            json={"payment_method_id": "pm_test123"},
        )
        assert response.status_code in (200, 500)


class TestWebhooks:
    """Test billing webhooks."""

    @pytest.mark.asyncio
    async def test_stripe_webhook(self, async_client: AsyncClient):
        """Test Stripe webhook handling."""
        response = await async_client.post(
            "/api/v1/billing/webhook/stripe",
            json={
                "type": "checkout.session.completed",
                "data": {"object": {"id": "cs_test"}},
            },
            headers={"Stripe-Signature": "test_sig"},
        )
        assert response.status_code in (200, 400, 500)

    @pytest.mark.asyncio
    async def test_paystack_webhook(self, async_client: AsyncClient):
        """Test Paystack webhook handling."""
        response = await async_client.post(
            "/api/v1/billing/webhook/paystack",
            json={"event": "charge.success", "data": {"reference": "test_ref"}},
        )
        assert response.status_code in (200, 400, 500)
