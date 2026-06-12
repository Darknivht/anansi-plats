-- ============================================================================
-- ANANSI Platform — Initial Database Schema
-- PostgreSQL 16 + pgvector + Neo4j-compatible relational layer
-- Migration: 001_initial_schema
-- ============================================================================

-- Enable pgvector extension for embedding similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS & AUTH
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    display_name VARCHAR(100),
    avatar_url TEXT,
    timezone VARCHAR(50) DEFAULT 'Africa/Lagos',
    language VARCHAR(10) DEFAULT 'en',
    theme VARCHAR(10) DEFAULT 'dark',
    onboarding_step INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    is_verified BOOLEAN DEFAULT false NOT NULL,
    two_factor_enabled BOOLEAN DEFAULT false NOT NULL,
    two_factor_secret VARCHAR(255),
    brain_age_days INTEGER DEFAULT 0 NOT NULL,
    memory_count INTEGER DEFAULT 0 NOT NULL,
    link_count INTEGER DEFAULT 0 NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    avatar_url TEXT,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(provider, provider_account_id)
);

CREATE INDEX idx_oauth_accounts_user ON oauth_accounts(user_id);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(500) NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(45),
    is_valid BOOLEAN DEFAULT true NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(refresh_token);
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE is_valid = true;

-- ============================================================================
-- PLANS & SUBSCRIPTIONS
-- ============================================================================

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    price_monthly_cents INTEGER NOT NULL CHECK (price_monthly_cents >= 0),
    price_yearly_cents INTEGER NOT NULL CHECK (price_yearly_cents >= 0),
    max_agents INTEGER,
    max_integrations INTEGER,
    max_team_members INTEGER,
    max_memory_nodes INTEGER,
    max_graph_depth INTEGER,
    max_reviews_per_day INTEGER,
    daily_notes_history_days INTEGER,
    progressive_summarization_layers INTEGER DEFAULT 1,
    auto_linking_level VARCHAR(20) DEFAULT 'basic',
    export_formats TEXT[] DEFAULT ARRAY['json'],
    memory_analytics VARCHAR(20) DEFAULT 'weekly',
    features JSONB,
    is_active BOOLEAN DEFAULT true NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id),
    status VARCHAR(20) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'past_due', 'cancelled', 'expired', 'trialing')),
    billing_cycle VARCHAR(10) DEFAULT 'monthly' NOT NULL CHECK (billing_cycle IN ('monthly', 'yearly')),
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    paystack_subscription_code VARCHAR(255),
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

-- ============================================================================
-- SECOND BRAIN — MEMORY SYSTEM
-- ============================================================================

CREATE TABLE memory_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'fact', 'preference', 'pattern', 'relation', 'daily_note', 'agent_output',
        'conversation_summary', 'inferred', 'archived', 'ephemeral'
    )),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    layers JSONB,
    embedding vector(1536),
    tags TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    review_interval INTEGER DEFAULT 86400 NOT NULL,
    next_review_at TIMESTAMPTZ DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0 NOT NULL,
    source VARCHAR(20) DEFAULT 'explicit' NOT NULL CHECK (source IN ('explicit', 'inferred', 'learned', 'imported')),
    confidence FLOAT DEFAULT 0.7 NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    review_status VARCHAR(20) DEFAULT 'current' NOT NULL CHECK (review_status IN ('current', 'due', 'overdue', 'archived')),
    is_orphan BOOLEAN DEFAULT false NOT NULL,
    links_count INTEGER DEFAULT 0 NOT NULL,
    para_category VARCHAR(20) CHECK (para_category IN ('project', 'area', 'resource', 'archive')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_memory_nodes_user ON memory_nodes(user_id);
CREATE INDEX idx_memory_nodes_type ON memory_nodes(user_id, type);
CREATE INDEX idx_memory_nodes_embedding ON memory_nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_nodes_tags ON memory_nodes USING gin(tags);
CREATE INDEX idx_memory_nodes_review ON memory_nodes(user_id, next_review_at) WHERE next_review_at IS NOT NULL;
CREATE INDEX idx_memory_nodes_created ON memory_nodes(user_id, created_at DESC);
CREATE INDEX idx_memory_nodes_source ON memory_nodes(user_id, source);
CREATE INDEX idx_memory_nodes_para ON memory_nodes(user_id, para_category) WHERE para_category IS NOT NULL;
CREATE INDEX idx_memory_nodes_review_status ON memory_nodes(user_id, review_status) WHERE review_status IN ('due', 'overdue');
CREATE INDEX idx_memory_nodes_orphan ON memory_nodes(user_id) WHERE is_orphan = true;
CREATE INDEX idx_memory_nodes_search ON memory_nodes USING gin(to_tsvector('english', title || ' ' || content));

-- Bidirectional memory links
CREATE TABLE memory_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    link_type VARCHAR(50) NOT NULL CHECK (link_type IN (
        'related_to', 'categorized_as', 'causes', 'contradicts',
        'mentioned_in', 'supports', 'follows_from', 'user_defined'
    )),
    label TEXT,
    context TEXT,
    strength FLOAT DEFAULT 0.5 NOT NULL CHECK (strength >= 0 AND strength <= 1),
    confidence FLOAT DEFAULT 0.7 NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    is_auto_generated BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(source_id, target_id, link_type)
);

CREATE INDEX idx_memory_links_source ON memory_links(source_id);
CREATE INDEX idx_memory_links_target ON memory_links(target_id);
CREATE INDEX idx_memory_links_user ON memory_links(user_id);
CREATE INDEX idx_memory_links_type ON memory_links(link_type);

-- Daily Notes
CREATE TABLE daily_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note_date DATE NOT NULL,
    highlights TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    decisions JSONB DEFAULT '[]'::jsonb NOT NULL,
    connections_made JSONB DEFAULT '[]'::jsonb NOT NULL,
    metrics JSONB DEFAULT '{}'::jsonb NOT NULL,
    ai_reflection TEXT,
    is_finalized BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(user_id, note_date)
);

CREATE INDEX idx_daily_notes_user ON daily_notes(user_id, note_date DESC);

-- Spaced Repetition Review Log
CREATE TABLE memory_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    rating VARCHAR(10) NOT NULL CHECK (rating IN ('easy', 'medium', 'hard', 'forgot')),
    response_time_ms INTEGER,
    interval_before INTEGER,
    interval_after INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_memory_reviews_node ON memory_reviews(node_id, created_at DESC);
CREATE INDEX idx_memory_reviews_user ON memory_reviews(user_id, created_at DESC);

-- ============================================================================
-- CONVERSATIONS & MESSAGES
-- ============================================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel VARCHAR(20) DEFAULT 'web' NOT NULL CHECK (channel IN ('web', 'whatsapp', 'api', 'voice')),
    title VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    message_count INTEGER DEFAULT 0 NOT NULL,
    is_archived BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_conversations_user ON conversations(user_id, updated_at DESC);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    referenced_memory_nodes UUID[] DEFAULT ARRAY[]::UUID[] NOT NULL,
    tokens_used INTEGER,
    model_used VARCHAR(100),
    latency_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_role ON messages(conversation_id, role);
CREATE INDEX idx_messages_memory_refs ON messages USING gin(referenced_memory_nodes);

-- ============================================================================
-- AGENTS
-- ============================================================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'archived')),
    is_published BOOLEAN DEFAULT false NOT NULL,
    marketplace_price_cents INTEGER,
    total_runs INTEGER DEFAULT 0 NOT NULL,
    successful_runs INTEGER DEFAULT 0 NOT NULL,
    success_rate FLOAT DEFAULT 0 NOT NULL,
    avg_duration_ms INTEGER DEFAULT 0 NOT NULL,
    memory_nodes_created INTEGER DEFAULT 0 NOT NULL,
    memory_links_created INTEGER DEFAULT 0 NOT NULL,
    category VARCHAR(50),
    tags TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_agents_user ON agents(user_id);
CREATE INDEX idx_agents_status ON agents(user_id, status);
CREATE INDEX idx_agents_tags ON agents USING gin(tags);

CREATE TABLE agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    definition JSONB NOT NULL,
    change_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_agent_versions_agent ON agent_versions(agent_id, version DESC);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) CHECK (trigger_type IN ('manual', 'schedule', 'webhook', 'event')),
    trigger_detail VARCHAR(255),
    status VARCHAR(20) DEFAULT 'running' NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    error_details JSONB,
    steps JSONB DEFAULT '[]'::jsonb NOT NULL,
    memory_nodes_created INTEGER DEFAULT 0 NOT NULL,
    memory_links_created INTEGER DEFAULT 0 NOT NULL,
    model_used VARCHAR(100),
    tokens_used INTEGER DEFAULT 0 NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    cost_cents INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_id, started_at DESC);
CREATE INDEX idx_agent_runs_user ON agent_runs(user_id, started_at DESC);
CREATE INDEX idx_agent_runs_status ON agent_runs(agent_id, status);
CREATE INDEX idx_agent_runs_created ON agent_runs(created_at DESC);

-- ============================================================================
-- INTEGRATIONS & CONNECTORS
-- ============================================================================

CREATE TABLE connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_url TEXT,
    auth_type VARCHAR(50) CHECK (auth_type IN ('oauth2', 'apikey', 'basic')),
    auth_url_template TEXT,
    token_url TEXT,
    scopes_available TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    is_builtin BOOLEAN DEFAULT true NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    category VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connector_type VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'error', 'disconnected', 'pending')),
    auth_data JSONB,
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    last_sync_at TIMESTAMPTZ,
    error_message TEXT,
    rate_limit_remaining INTEGER,
    rate_limit_reset_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_integrations_user ON integrations(user_id);
CREATE INDEX idx_integrations_connector ON integrations(connector_type);
CREATE INDEX idx_integrations_status ON integrations(user_id, status);

-- ============================================================================
-- MARKETPLACE
-- ============================================================================

CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price_cents INTEGER DEFAULT 0 NOT NULL CHECK (price_cents >= 0),
    category VARCHAR(50),
    tags TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    screenshots TEXT[] DEFAULT ARRAY[]::TEXT[] NOT NULL,
    rating_avg FLOAT DEFAULT 0 NOT NULL CHECK (rating_avg >= 0 AND rating_avg <= 5),
    rating_count INTEGER DEFAULT 0 NOT NULL,
    install_count INTEGER DEFAULT 0 NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' NOT NULL CHECK (status IN ('draft', 'published', 'unpublished', 'rejected')),
    rejection_reason TEXT,
    is_featured BOOLEAN DEFAULT false NOT NULL,
    memory_nodes_per_run INTEGER DEFAULT 0,
    memory_links_per_run INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_marketplace_listings_user ON marketplace_listings(user_id);
CREATE INDEX idx_marketplace_listings_status ON marketplace_listings(status);
CREATE INDEX idx_marketplace_listings_category ON marketplace_listings(category) WHERE status = 'published';
CREATE INDEX idx_marketplace_listings_rating ON marketplace_listings(rating_avg DESC) WHERE status = 'published';
CREATE INDEX idx_marketplace_listings_featured ON marketplace_listings(is_featured) WHERE is_featured = true;
CREATE INDEX idx_marketplace_listings_tags ON marketplace_listings USING gin(tags);

CREATE TABLE marketplace_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(listing_id, user_id)
);

CREATE INDEX idx_marketplace_reviews_listing ON marketplace_reviews(listing_id, created_at DESC);

CREATE TABLE marketplace_installs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_marketplace_installs_listing ON marketplace_installs(listing_id);
CREATE INDEX idx_marketplace_installs_user ON marketplace_installs(user_id);

-- ============================================================================
-- TEAMS
-- ============================================================================

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    avatar_url TEXT,
    settings JSONB DEFAULT '{}'::jsonb NOT NULL,
    member_count INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_teams_owner ON teams(owner_id);

CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(team_id, user_id)
);

CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);

-- ============================================================================
-- WHATSAPP
-- ============================================================================

CREATE TABLE whatsapp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    phone_number VARCHAR(20) NOT NULL,
    waba_id VARCHAR(100),
    phone_number_id VARCHAR(100),
    business_account_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL CHECK (status IN ('pending', 'active', 'disconnected', 'expired')),
    verification_code VARCHAR(10),
    verified_at TIMESTAMPTZ,
    settings JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_whatsapp_connections_user ON whatsapp_connections(user_id);
CREATE INDEX idx_whatsapp_connections_phone ON whatsapp_connections(phone_number);

-- ============================================================================
-- NOTIFICATIONS
-- ============================================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'agent_completed', 'agent_failed', 'ai_suggestion', 'integration_alert',
        'brain_review_due', 'brain_insight', 'brain_link_suggestion',
        'billing_alert', 'team_invite', 'marketplace_update',
        'morning_briefing', 'system'
    )),
    title VARCHAR(255) NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}'::jsonb NOT NULL,
    related_memory_node UUID REFERENCES memory_nodes(id) ON DELETE SET NULL,
    related_entity_type VARCHAR(50),
    related_entity_id UUID,
    is_read BOOLEAN DEFAULT false NOT NULL,
    is_archived BOOLEAN DEFAULT false NOT NULL,
    channel VARCHAR(20) DEFAULT 'in_app' NOT NULL CHECK (channel IN ('in_app', 'whatsapp', 'email', 'push')),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_read ON notifications(user_id) WHERE is_read = false AND is_archived = false;
CREATE INDEX idx_notifications_type ON notifications(user_id, type);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);

-- ============================================================================
-- TRIGGER FUNCTION: Auto-update updated_at on any row change
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables that have updated_at
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'updated_at'
          AND table_schema = 'public'
          AND table_name NOT LIKE 'pg_%'
    LOOP
        EXECUTE format(
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            tbl
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER FUNCTION: Auto-count links for memory nodes
-- ============================================================================

CREATE OR REPLACE FUNCTION update_memory_node_links_count()
RETURNS TRIGGER AS $$
DECLARE
    affected_source UUID;
    affected_target UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        affected_source = NEW.source_id;
        affected_target = NEW.target_id;
    ELSIF TG_OP = 'DELETE' THEN
        affected_source = OLD.source_id;
        affected_target = OLD.target_id;
    END IF;

    -- Update source node link count
    IF affected_source IS NOT NULL THEN
        UPDATE memory_nodes
        SET links_count = (
            SELECT COUNT(*) FROM memory_links
            WHERE source_id = affected_source OR target_id = affected_source
        )
        WHERE id = affected_source;
    END IF;

    -- Update target node link count
    IF affected_target IS NOT NULL THEN
        UPDATE memory_nodes
        SET links_count = (
            SELECT COUNT(*) FROM memory_links
            WHERE source_id = affected_target OR target_id = affected_target
        )
        WHERE id = affected_target;
    END IF;

    -- Update orphan status for both nodes
    IF affected_source IS NOT NULL THEN
        UPDATE memory_nodes
        SET is_orphan = (links_count <= 1)
        WHERE id = affected_source;
    END IF;
    IF affected_target IS NOT NULL THEN
        UPDATE memory_nodes
        SET is_orphan = (links_count <= 1)
        WHERE id = affected_target;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_memory_links_aiud
    AFTER INSERT OR UPDATE OR DELETE ON memory_links
    FOR EACH ROW
    EXECUTE FUNCTION update_memory_node_links_count();
