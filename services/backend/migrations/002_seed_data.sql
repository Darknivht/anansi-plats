-- ============================================================================
-- ANANSI Platform — Seed Data
-- Migration: 002_seed_data
-- ============================================================================

-- ============================================================================
-- DEFAULT PLANS
-- ============================================================================

INSERT INTO plans (name, slug, description, price_monthly_cents, price_yearly_cents,
                   max_agents, max_integrations, max_team_members, max_memory_nodes,
                   max_graph_depth, max_reviews_per_day, daily_notes_history_days,
                   progressive_summarization_layers, auto_linking_level,
                   export_formats, memory_analytics, features, sort_order)
VALUES
(
    'Free',
    'free',
    'Perfect for getting started with your Personal AI and Second Brain.',
    0, 0,
    3,           -- max_agents
    3,           -- max_integrations
    1,           -- max_team_members
    1000,        -- max_memory_nodes
    2,           -- max_graph_depth
    5,           -- max_reviews_per_day
    7,           -- daily_notes_history_days
    1,           -- progressive_summarization_layers
    'basic',     -- auto_linking_level
    ARRAY['json'],  -- export_formats
    'weekly',    -- memory_analytics
    '{
        "ai_chat": true,
        "morning_briefing": true,
        "agent_builder": true,
        "basic_connectors": true,
        "marketplace_browse": true,
        "whatsapp_channel": true,
        "community_support": true,
        "memory_graph_view": true,
        "email_support": false,
        "priority_support": false,
        "custom_branding": false,
        "team_management": false,
        "advanced_analytics": false,
        "api_access": false
    }'::jsonb,
    0
),
(
    'Pro',
    'pro',
    'For professionals who want their AI to truly manage their digital life.',
    1900,  -- $19/mo
    19000, -- $190/yr (2 months free)
    10,          -- max_agents
    20,          -- max_integrations
    5,           -- max_team_members
    10000,       -- max_memory_nodes
    5,           -- max_graph_depth
    25,          -- max_reviews_per_day
    90,          -- daily_notes_history_days
    4,           -- progressive_summarization_layers (all 4)
    'advanced',  -- auto_linking_level
    ARRAY['json', 'obsidian'],  -- export_formats
    'daily',     -- memory_analytics
    '{
        "ai_chat": true,
        "morning_briefing": true,
        "agent_builder": true,
        "all_connectors": true,
        "marketplace_browse": true,
        "marketplace_publish": true,
        "whatsapp_channel": true,
        "priority_email_support": true,
        "custom_agent_templates": true,
        "advanced_memory_analytics": true,
        "memory_graph_view": true,
        "brain_export_obsidian": true,
        "email_support": true,
        "priority_support": false,
        "custom_branding": false,
        "team_management": true,
        "advanced_analytics": true,
        "api_access": true,
        "custom_auto_link_rules": false
    }'::jsonb,
    1
),
(
    'Business',
    'business',
    'For teams and businesses who need unlimited everything and white-glove support.',
    9900,  -- $99/mo
    99000, -- $990/yr (2 months free)
    NULL,        -- max_agents (unlimited)
    NULL,        -- max_integrations (unlimited)
    NULL,        -- max_team_members (unlimited)
    NULL,        -- max_memory_nodes (unlimited)
    NULL,        -- max_graph_depth (unlimited)
    NULL,        -- max_reviews_per_day (unlimited)
    NULL,        -- daily_notes_history_days (unlimited)
    4,           -- progressive_summarization_layers (all 4)
    'full',      -- auto_linking_level (full + custom rules)
    ARRAY['json', 'obsidian', 'csv', 'markdown'],  -- export_formats
    'real_time',  -- memory_analytics
    '{
        "ai_chat": true,
        "morning_briefing": true,
        "agent_builder": true,
        "all_connectors": true,
        "marketplace_browse": true,
        "marketplace_publish": true,
        "whatsapp_channel": true,
        "priority_support": true,
        "custom_agent_templates": true,
        "advanced_memory_analytics": true,
        "memory_graph_view": true,
        "brain_export_obsidian": true,
        "email_support": true,
        "priority_support": true,
        "dedicated_support": true,
        "custom_branding": true,
        "team_management": true,
        "advanced_analytics": true,
        "api_access": true,
        "custom_auto_link_rules": true,
        "private_marketplace": true,
        "sso": true,
        "audit_logs": true,
        "custom_integrations": true
    }'::jsonb,
    2
);

-- ============================================================================
-- DEFAULT CONNECTORS
-- ============================================================================

INSERT INTO connectors (key, name, description, icon_url, auth_type, auth_url_template, scopes_available, is_builtin, is_active, category)
VALUES
(
    'gmail',
    'Gmail',
    'Send, receive, and search emails through Google Gmail API.',
    '/icons/connectors/gmail.svg',
    'oauth2',
    'https://accounts.google.com/o/oauth2/v2/auth',
    ARRAY[
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ],
    true, true,
    'communications'
),
(
    'google_calendar',
    'Google Calendar',
    'Read and create calendar events. Get daily agenda and reminders.',
    '/icons/connectors/google-calendar.svg',
    'oauth2',
    'https://accounts.google.com/o/oauth2/v2/auth',
    ARRAY[
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
    ],
    true, true,
    'productivity'
),
(
    'google_drive',
    'Google Drive',
    'Read, search, and organize files in Google Drive.',
    '/icons/connectors/google-drive.svg',
    'oauth2',
    'https://accounts.google.com/o/oauth2/v2/auth',
    ARRAY[
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ],
    true, true,
    'storage'
),
(
    'whatsapp',
    'WhatsApp Business',
    'Send and receive WhatsApp messages via Cloud API.',
    '/icons/connectors/whatsapp.svg',
    'apikey',
    NULL,
    ARRAY['whatsapp_business_messaging', 'whatsapp_business_profile'],
    true, true,
    'communications'
),
(
    'telegram',
    'Telegram',
    'Send and receive Telegram messages. Bot integration.',
    '/icons/connectors/telegram.svg',
    'apikey',
    NULL,
    ARRAY['send_messages', 'read_messages', 'manage_bot'],
    true, true,
    'communications'
),
(
    'slack',
    'Slack',
    'Post messages, search channels, and receive notifications.',
    '/icons/connectors/slack.svg',
    'oauth2',
    'https://slack.com/oauth/v2/authorize',
    ARRAY[
        'channels:read',
        'channels:history',
        'chat:write',
        'users:read'
    ],
    true, true,
    'communications'
),
(
    'notion',
    'Notion',
    'Read, create, and update Notion pages and databases.',
    '/icons/connectors/notion.svg',
    'oauth2',
    'https://api.notion.com/v1/oauth/authorize',
    ARRAY['read', 'write', 'insert'],
    true, true,
    'productivity'
),
(
    'github',
    'GitHub',
    'Manage repositories, issues, PRs, and code reviews.',
    '/icons/connectors/github.svg',
    'oauth2',
    'https://github.com/login/oauth/authorize',
    ARRAY[
        'repo',
        'issues:read',
        'issues:write',
        'pull_requests:read',
        'pull_requests:write'
    ],
    true, true,
    'devops'
),
(
    'linear',
    'Linear',
    'Manage issues, projects, and cycles in Linear.',
    '/icons/connectors/linear.svg',
    'oauth2',
    'https://linear.app/oauth/authorize',
    ARRAY['read', 'write', 'issues:create', 'issues:read'],
    true, true,
    'productivity'
),
(
    'stripe',
    'Stripe',
    'View transactions, manage invoices, and handle payments.',
    '/icons/connectors/stripe.svg',
    'oauth2',
    'https://connect.stripe.com/oauth/authorize',
    ARRAY[
        'charge:read',
        'customer:read',
        'invoice:read',
        'balance:read'
    ],
    true, true,
    'finance'
),
(
    'paystack',
    'Paystack',
    'Nigerian payment processing. View transactions and handle payouts.',
    '/icons/connectors/paystack.svg',
    'apikey',
    NULL,
    ARRAY['transaction:read', 'customer:read', 'balance:read'],
    true, true,
    'finance'
),
(
    'google_keep',
    'Google Keep',
    'Sync notes between Google Keep and your Second Brain.',
    '/icons/connectors/google-keep.svg',
    'oauth2',
    'https://accounts.google.com/o/oauth2/v2/auth',
    ARRAY['https://www.googleapis.com/auth/keep.readonly', 'https://www.googleapis.com/auth/keep'],
    true, true,
    'productivity'
),
(
    'twitter',
    'Twitter / X',
    'Read tweets, post updates, and monitor mentions.',
    '/icons/connectors/twitter.svg',
    'oauth2',
    'https://twitter.com/i/oauth2/authorize',
    ARRAY['tweet.read', 'tweet.write', 'users.read', 'follows.read'],
    true, true,
    'social_media'
),
(
    'outlook',
    'Outlook / Office 365',
    'Send, receive, and manage emails via Microsoft Graph.',
    '/icons/connectors/outlook.svg',
    'oauth2',
    'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    ARRAY[
        'Mail.Read',
        'Mail.ReadWrite',
        'Mail.Send',
        'User.Read'
    ],
    true, true,
    'communications'
),
(
    'discord',
    'Discord',
    'Send messages, monitor channels, and manage Discord bots.',
    '/icons/connectors/discord.svg',
    'oauth2',
    'https://discord.com/api/oauth2/authorize',
    ARRAY['bot', 'messages.read', 'guilds.read'],
    true, true,
    'communications'
);
