"""SQLAlchemy model imports for Anansi platform.

All models are imported here for easy access via:
    from app.models import User, MemoryNode, ...

Also provides the Base and mixins.
"""

from .base import Base, UUIDMixin, TimestampMixin

# Auth
from .user import User, OAuthAccount, Session

# Billing
from .billing import Plan, Subscription

# Second Brain
from .brain import MemoryNode, MemoryLink, DailyNote, MemoryReview

# Conversations
from .conversation import Conversation, Message

# Agents
from .agent import Agent, AgentVersion, AgentRun

# Integrations
from .integration import Connector, Integration

# Marketplace
from .marketplace import MarketplaceListing, MarketplaceReview, MarketplaceInstall

# Teams
from .team import Team, TeamMember

# WhatsApp
from .whatsapp import WhatsAppConnection

# Notifications
from .notification import Notification


# Convenience list of all models for Alembic or migration tools
all_models: list = [
    User,
    OAuthAccount,
    Session,
    Plan,
    Subscription,
    MemoryNode,
    MemoryLink,
    DailyNote,
    MemoryReview,
    Conversation,
    Message,
    Agent,
    AgentVersion,
    AgentRun,
    Connector,
    Integration,
    MarketplaceListing,
    MarketplaceReview,
    MarketplaceInstall,
    Team,
    TeamMember,
    WhatsAppConnection,
    Notification,
]
