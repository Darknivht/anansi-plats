"""
Anansi Paystack Connector — Nigerian payments, transactions, balance.

Auth: Paystack secret key.
Docs: https://paystack.com/docs/api
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from structlog import get_logger

from app.connectors import register_connector
from app.connectors.base import BaseConnector

logger = get_logger(__name__)


@register_connector
class PaystackConnector(BaseConnector):
    """Connect to Paystack — Nigerian payments, transactions, balance."""

    key: ClassVar[str] = "paystack"
    name: ClassVar[str] = "Paystack"
    description: ClassVar[str] = "Nigerian payment processing — transactions, balance, customers."
    icon_url: ClassVar[str] = "/icons/paystack.svg"
    category: ClassVar[str] = "finance"
    auth_type: ClassVar[str] = "apikey"
    api_base_url: ClassVar[str] = "https://api.paystack.co"

    def _inject_auth_headers(self, headers: dict[str, str]) -> None:
        api_key = self._auth_data.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

    async def test_connection(self) -> bool:
        """Verify Paystack connection by fetching balance."""
        try:
            client = await self._get_client()
            resp = await client.get("/balance")
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Paystack connection test failed", error=str(exc))
            return False

    async def validate_api_key(self, api_key: str) -> dict[str, Any]:
        """Validate a Paystack secret key."""
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.api_base_url}/balance", headers=headers)
            if resp.status_code == 200:
                return {"valid": True, "details": {"status": "ok"}}
            return {"valid": False, "details": {"error": resp.text}}

    # ── Balance ─────────────────────────────────────────────────────────────

    async def get_balance(self) -> list[dict[str, Any]]:
        """Get account balance per currency."""
        client = await self._get_client()
        resp = await client.get("/balance")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    # ── Transactions ────────────────────────────────────────────────────────

    async def list_transactions(
        self,
        per_page: int = 50,
        page: int = 1,
        status: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """List transactions.

        Args:
            per_page: Results per page (1-200).
            page: Page number.
            status: 'success', 'failed', 'abandoned'.
            from_date: Start date (ISO 8601).
            to_date: End date (ISO 8601).

        Returns:
            Paginated response with 'data' array.
        """
        params: dict[str, Any] = {"perPage": min(per_page, 200), "page": page}
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        client = await self._get_client()
        resp = await client.get("/transaction", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        """Get a single transaction by ID.

        Args:
            transaction_id: Paystack transaction ID or reference.

        Returns:
            Transaction details.
        """
        client = await self._get_client()
        resp = await client.get(f"/transaction/{transaction_id}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        """Verify a transaction by reference.

        Args:
            reference: Transaction reference.

        Returns:
            Verification result with transaction data.
        """
        client = await self._get_client()
        resp = await client.get(f"/transaction/verify/{reference}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    async def get_transaction_totals(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """Get transaction totals and statistics."""
        params: dict[str, Any] = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        client = await self._get_client()
        resp = await client.get("/transaction/totals", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

    # ── Customers ───────────────────────────────────────────────────────────

    async def list_customers(
        self,
        per_page: int = 50,
        page: int = 1,
    ) -> dict[str, Any]:
        """List customers."""
        params = {"perPage": min(per_page, 200), "page": page}
        client = await self._get_client()
        resp = await client.get("/customer", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Banks ───────────────────────────────────────────────────────────────

    async def list_banks(self, country: str = "nigeria") -> list[dict[str, Any]]:
        """List supported banks for a country."""
        client = await self._get_client()
        resp = await client.get("/bank", params={"country": country})
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
