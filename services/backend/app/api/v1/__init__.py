"""
Anansi API v1 — Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.agents import router as agents_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.billing import router as billing_router
from app.api.v1.whatsapp import router as whatsapp_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.brain import router as brain_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
router.include_router(agents_router, prefix="/agents", tags=["Agents"])
router.include_router(marketplace_router, prefix="/marketplace", tags=["Marketplace"])
router.include_router(billing_router, prefix="/billing", tags=["Billing"])
router.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])
router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
router.include_router(brain_router, prefix="/brain", tags=["Brain"])

__all__ = ["router"]
