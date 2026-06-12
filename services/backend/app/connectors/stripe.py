"""
Anansi Stripe Connector — Transactions, invoices, customers, balance (read-only).

Auth: Stripe API key (secret key).
Docs: https://stripe.com/docs/api
"""

from __future__ import annotations

from typing import Any, ClassVar

from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class StripeConnector(BaseConnector):
    """Connect to Stripe — read-only access to transactions, invoices, customers, balance."""

    key: ClassVar[str] = "stripe"
    name: ClassVar[str] = "Stripe"
    description: ClassVar[str] = "View transactions, invoices, customers, and balance (read-only)."
    icon_url: ClassVar[str] = "/icons/stripe.svg"
    category: ClassVar[str] = "finance"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://api.stripe.com/v1"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    async def test_connection(self) -> bool:
        """Verify Stripe connection by fetching the account balance."""
        try:
            client = await self._get_client()
            resp = await client.get("/balance")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Stripe connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Stripe secret key."""
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base_url}/balance", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return {"valid": True, "details": {"available_currencies": list(data.get("available", []))}}
            return {"valid": False, "details": {"error": resp.text}}

    # ── Balance ─────────────────────────────────────────────────────────────

    async def get_balance(self) -> dict[str, Any]:
        """Get current account balance.

        Returns:
            Dict with 'available' and 'pending' balances per currency.
        """
        client = await self._get_client()
        resp = await client.get("/balance")
        resp.raise_for_status()
        return resp.json()

    # ── Transactions ────────────────────────────────────────────────────────

    async def list_balance_transactions(
        self,
        limit: int = 10,
        starting_after: str | None = None,
        payout_id: str | None = None,
        currency: str | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        """List balance transactions (payments, refunds, transfers, etc.).

        Args:
            limit: Max results (1-100).
            starting_after: Pagination cursor.
            payout_id: Filter by payout.
            currency: Filter by currency (e.g. 'usd').
            type: Filter by type.

        Returns:
            Dict with 'data' array of transactions.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if starting_after:
            params["starting_after"] = starting_after
        if payout_id:
            params["payout"] = payout_id
        if currency:
            params["currency"] = currency
        if type:
            params["type"] = type

        client = await self._get_client()
        resp = await client.get("/balance_transactions", params=params)
        resp.raise_for_status()
        return resp.json()

    async def list_charges(
        self,
        limit: int = 10,
        customer: str | None = None,
    ) -> dict[str, Any]:
        """List recent charges (payments).

        Args:
            limit: Max results (1-100).
            customer: Filter by customer ID.

        Returns:
            Dict with 'data' array of charges.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if customer:
            params["customer"] = customer

        client = await self._get_client()
        resp = await client.get("/charges", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Customers ───────────────────────────────────────────────────────────

    async def list_customers(
        self,
        limit: int = 10,
        email: str | None = None,
    ) -> dict[str, Any]:
        """List customers.

        Args:
            limit: Max results (1-100).
            email: Filter by email address.

        Returns:
            Dict with 'data' array of customers.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if email:
            params["email"] = email

        client = await self._get_client()
        resp = await client.get("/customers", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Invoices ────────────────────────────────────────────────────────────

    async def list_invoices(
        self,
        limit: int = 10,
        status: str | None = None,
        customer: str | None = None,
    ) -> dict[str, Any]:
        """List invoices.

        Args:
            limit: Max results (1-100).
            status: 'draft', 'open', 'paid', 'uncollectible', or 'void'.
            customer: Filter by customer ID.

        Returns:
            Dict with 'data' array of invoices.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if status:
            params["status"] = status
        if customer:
            params["customer"] = customer

        client = await self._get_client()
        resp = await client.get("/invoices", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Payouts ─────────────────────────────────────────────────────────────

    async def list_payouts(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List payouts.

        Args:
            limit: Max results.
            status: 'pending', 'paid', 'failed', or 'canceled'.

        Returns:
            Dict with 'data' array.
        """
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if status:
            params["status"] = status

        client = await self._get_client()
        resp = await client.get("/payouts", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Products ────────────────────────────────────────────────────────────

    async def list_products(
        self,
        limit: int = 10,
        active: bool = True,
    ) -> dict[str, Any]:
        """List products.

        Args:
            limit: Max results.
            active: Only active products.

        Returns:
            Dict with 'data' array.
        """
        params: dict[str, Any] = {"limit": min(limit, 100), "active": str(active).lower()}
        client = await self._get_client()
        resp = await client.get("/products", params=params)
        resp.raise_for_status()
        return resp.json()
