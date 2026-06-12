-- ============================================================================
-- ANANSI Platform — PostgreSQL Functions & Stored Procedures
-- Migration: 003_functions
-- ============================================================================

-- ============================================================================
-- FUNCTION: update_memory_node_links_count (Trigger Function)
-- Updates the links_count and is_orphan columns on memory_nodes when
-- a memory_link is inserted, updated, or deleted.
-- NOTE: This is already defined in 001_initial_schema.sql as a trigger.
-- This is the standalone version for use in non-trigger contexts.
-- ============================================================================

CREATE OR REPLACE FUNCTION update_memory_node_links_count(p_node_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE memory_nodes
    SET
        links_count = (
            SELECT COUNT(*)
            FROM memory_links
            WHERE source_id = p_node_id OR target_id = p_node_id
        ),
        is_orphan = (
            SELECT COUNT(*) <= 1
            FROM memory_links
            WHERE source_id = p_node_id OR target_id = p_node_id
        )
    WHERE id = p_node_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: update_user_brain_stats
-- Updates the memory_count and link_count columns on a user's row based on
-- actual counts in memory_nodes and memory_links tables.
-- ============================================================================

CREATE OR REPLACE FUNCTION update_user_brain_stats(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET
        memory_count = (
            SELECT COUNT(*)
            FROM memory_nodes
            WHERE user_id = p_user_id
        ),
        link_count = (
            SELECT COUNT(*)
            FROM memory_links
            WHERE user_id = p_user_id
        ),
        brain_age_days = (
            SELECT COALESCE(
                EXTRACT(DAY FROM (NOW() - MIN(created_at)))::INTEGER,
                0
            )
            FROM memory_nodes
            WHERE user_id = p_user_id
        )
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: search_memory_nodes
-- Full-text search across memory node titles and content, combined with
-- tag filtering and pagination. Returns relevance-ranked results.
-- ============================================================================

CREATE OR REPLACE FUNCTION search_memory_nodes(
    p_query_text TEXT,
    p_user_id UUID,
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0,
    p_tags TEXT[] DEFAULT NULL,
    p_node_type VARCHAR(50) DEFAULT NULL,
    p_min_confidence FLOAT DEFAULT NULL,
    p_para_category VARCHAR(20) DEFAULT NULL
)
RETURNS TABLE(
    id UUID,
    title TEXT,
    content TEXT,
    node_type VARCHAR(50),
    tags TEXT[],
    layers JSONB,
    metadata JSONB,
    source VARCHAR(20),
    confidence FLOAT,
    review_status VARCHAR(20),
    links_count INTEGER,
    para_category VARCHAR(20),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    relevance FLOAT
) AS $$
DECLARE
    search_tsquery tsquery;
BEGIN
    -- Convert query text to tsquery (strip special chars, add prefix matching)
    search_tsquery := plainto_tsquery('english', p_query_text);

    RETURN QUERY
    SELECT
        mn.id,
        mn.title,
        mn.content,
        mn.type AS node_type,
        mn.tags,
        mn.layers,
        mn.metadata,
        mn.source,
        mn.confidence,
        mn.review_status,
        mn.links_count,
        mn.para_category,
        mn.created_at,
        mn.updated_at,
        -- Calculate relevance score as combination of:
        -- 1. Text search rank (primary, weight 0.6)
        -- 2. Confidence (weight 0.2)
        -- 3. Recency (weight 0.1)
        -- 4. Link count (weight 0.1)
        COALESCE(
            ts_rank(to_tsvector('english', mn.title || ' ' || mn.content), search_tsquery) * 0.6
            + mn.confidence * 0.2
            + LEAST(EXTRACT(EPOCH FROM (mn.updated_at - '2025-01-01'::timestamp)) / 31536000.0, 1.0) * 0.1
            + LEAST(mn.links_count::FLOAT / 100.0, 1.0) * 0.1
        , 0.0) AS relevance
    FROM memory_nodes mn
    WHERE
        mn.user_id = p_user_id
        AND (
            p_query_text = ''
            OR search_tsquery IS NULL
            OR to_tsvector('english', mn.title || ' ' || mn.content) @@ search_tsquery
        )
        -- Tag filtering: all specified tags must be present
        AND (p_tags IS NULL OR mn.tags @> p_tags)
        -- Type filtering
        AND (p_node_type IS NULL OR mn.type = p_node_type)
        -- Confidence threshold
        AND (p_min_confidence IS NULL OR mn.confidence >= p_min_confidence)
        -- PARA category filtering
        AND (p_para_category IS NULL OR mn.para_category = p_para_category)
    ORDER BY relevance DESC, mn.updated_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: get_review_queue
-- Returns memory nodes due for spaced repetition review for a user.
-- Orders by priority: overdue first, then due soon, then by confidence (lowest first).
-- ============================================================================

CREATE OR REPLACE FUNCTION get_review_queue(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    id UUID,
    title TEXT,
    content TEXT,
    node_type VARCHAR(50),
    tags TEXT[],
    layers JSONB,
    metadata JSONB,
    confidence FLOAT,
    review_interval INTEGER,
    next_review_at TIMESTAMPTZ,
    last_reviewed_at TIMESTAMPTZ,
    access_count INTEGER,
    links_count INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    priority_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mn.id,
        mn.title,
        mn.content,
        mn.type,
        mn.tags,
        mn.layers,
        mn.metadata,
        mn.confidence,
        mn.review_interval,
        mn.next_review_at,
        mn.last_reviewed_at,
        mn.access_count,
        mn.links_count,
        mn.created_at,
        mn.updated_at,
        -- Priority score: overdue items get boosted by how overdue they are
        -- Items with low confidence get priority
        CASE
            WHEN mn.next_review_at < NOW() THEN
                EXTRACT(EPOCH FROM (NOW() - mn.next_review_at)) / 86400.0 * 2.0
                + (1.0 - mn.confidence) * 5.0
            ELSE
                (1.0 - mn.confidence) * 3.0
                + (1.0 - LEAST(mn.access_count::FLOAT / 20.0, 1.0)) * 2.0
        END AS priority_score
    FROM memory_nodes mn
    WHERE
        mn.user_id = p_user_id
        AND mn.review_status IN ('due', 'overdue')
        AND (mn.next_review_at IS NOT NULL AND mn.next_review_at <= NOW() + INTERVAL '1 day')
    ORDER BY
        -- Overdue items first
        CASE WHEN mn.next_review_at < NOW() THEN 0 ELSE 1 END,
        priority_score DESC,
        mn.next_review_at ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: get_graph_data
-- Returns graph data (nodes + edges) for the Second Brain visualization.
-- Supports max_depth parameter for expansive queries from a starting node.
-- If p_start_node_id is NULL, returns all nodes with their connections.
-- ============================================================================

CREATE OR REPLACE FUNCTION get_graph_data(
    p_user_id UUID,
    p_max_depth INTEGER DEFAULT 2,
    p_start_node_id UUID DEFAULT NULL,
    p_tags TEXT[] DEFAULT NULL,
    p_node_type VARCHAR(50) DEFAULT NULL,
    p_limit INTEGER DEFAULT 500
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    node_ids UUID[];
    current_level UUID[];
    next_level UUID[];
    depth INTEGER := 0;
    visited_ids UUID[] := ARRAY[]::UUID[];
BEGIN
    -- Determine starting nodes
    IF p_start_node_id IS NOT NULL THEN
        -- Verify the start node belongs to the user
        IF NOT EXISTS (
            SELECT 1 FROM memory_nodes
            WHERE id = p_start_node_id AND user_id = p_user_id
        ) THEN
            RETURN '{"nodes": [], "edges": [], "error": "Node not found"}'::jsonb;
        END IF;
        current_level := ARRAY[p_start_node_id];
    ELSE
        -- Start with all user's nodes (limited)
        SELECT array_agg(id) INTO current_level
        FROM (
            SELECT id FROM memory_nodes
            WHERE user_id = p_user_id
            AND (p_tags IS NULL OR tags @> p_tags)
            AND (p_node_type IS NULL OR type = p_node_type)
            ORDER BY links_count DESC, created_at DESC
            LIMIT p_limit
        ) sub;
    END IF;

    -- BFS traversal to collect nodes up to max_depth
    visited_ids := current_level;

    WHILE depth < p_max_depth AND current_level IS NOT NULL AND array_length(current_level, 1) > 0 LOOP
        -- Find all linked nodes (both directions) at this level
        SELECT array_agg(DISTINCT linked_id) INTO next_level
        FROM (
            SELECT
                CASE
                    WHEN ml.source_id = ANY(current_level) THEN ml.target_id
                    ELSE ml.source_id
                END AS linked_id
            FROM memory_links ml
            WHERE ml.user_id = p_user_id
              AND (ml.source_id = ANY(current_level) OR ml.target_id = ANY(current_level))
              AND NOT (
                CASE
                    WHEN ml.source_id = ANY(current_level) THEN ml.target_id
                    ELSE ml.source_id
                END = ANY(visited_ids)
              )
            LIMIT p_limit * 2  -- Safety limit per level
        ) sub;

        -- Merge into visited
        IF next_level IS NOT NULL THEN
            visited_ids := visited_ids || next_level;
        END IF;

        current_level := next_level;
        depth := depth + 1;
    END LOOP;

    -- Build JSON result
    SELECT jsonb_build_object(
        'nodes', COALESCE(
            (SELECT jsonb_agg(jsonb_build_object(
                'id', mn.id,
                'title', mn.title,
                'type', mn.type,
                'tags', mn.tags,
                'confidence', mn.confidence,
                'links_count', mn.links_count,
                'para_category', mn.para_category,
                'review_status', mn.review_status,
                'source', mn.source,
                'created_at', mn.created_at,
                'embedding_available', mn.embedding IS NOT NULL
            ))
            FROM memory_nodes mn
            WHERE mn.id = ANY(visited_ids)
            ORDER BY mn.links_count DESC),
            '[]'::jsonb
        ),
        'edges', COALESCE(
            (SELECT jsonb_agg(jsonb_build_object(
                'id', ml.id,
                'source_id', ml.source_id,
                'target_id', ml.target_id,
                'link_type', ml.link_type,
                'label', ml.label,
                'strength', ml.strength,
                'confidence', ml.confidence,
                'is_auto_generated', ml.is_auto_generated
            ))
            FROM memory_links ml
            WHERE ml.user_id = p_user_id
              AND ml.source_id = ANY(visited_ids)
              AND ml.target_id = ANY(visited_ids)),
            '[]'::jsonb
        ),
        'stats', jsonb_build_object(
            'total_nodes', array_length(visited_ids, 1),
            'total_edges', (SELECT COUNT(*) FROM memory_links ml
                           WHERE ml.user_id = p_user_id
                             AND ml.source_id = ANY(visited_ids)
                             AND ml.target_id = ANY(visited_ids)),
            'depth_reached', depth
        )
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: get_brain_stats
-- Returns aggregated statistics about a user's Second Brain.
-- ============================================================================

CREATE OR REPLACE FUNCTION get_brain_stats(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_nodes', COUNT(*),
        'total_links', (SELECT COUNT(*) FROM memory_links WHERE user_id = p_user_id),
        'nodes_by_type', (
            SELECT jsonb_object_agg(type, cnt)
            FROM (
                SELECT type, COUNT(*) AS cnt
                FROM memory_nodes
                WHERE user_id = p_user_id
                GROUP BY type
            ) sub
        ),
        'nodes_by_source', (
            SELECT jsonb_object_agg(source, cnt)
            FROM (
                SELECT source, COUNT(*) AS cnt
                FROM memory_nodes
                WHERE user_id = p_user_id
                GROUP BY source
            ) sub
        ),
        'nodes_by_status', (
            SELECT jsonb_object_agg(review_status, cnt)
            FROM (
                SELECT review_status, COUNT(*) AS cnt
                FROM memory_nodes
                WHERE user_id = p_user_id
                GROUP BY review_status
            ) sub
        ),
        'orphan_count', COUNT(*) FILTER (WHERE is_orphan = true),
        'avg_confidence', COALESCE(AVG(confidence), 0.0),
        'avg_links_per_node', CASE WHEN COUNT(*) > 0
            THEN (SELECT COUNT(*)::FLOAT / GREATEST(COUNT(*), 1) FROM memory_links WHERE user_id = p_user_id)
            ELSE 0.0 END,
        'largest_cluster', (
            SELECT COALESCE(MAX(cnt), 0)
            FROM (
                -- Simple heuristic: count nodes sharing the most common tag
                SELECT COUNT(*) AS cnt
                FROM memory_nodes, unnest(tags) AS tag
                WHERE user_id = p_user_id
                GROUP BY tag
                ORDER BY cnt DESC
                LIMIT 1
            ) sub
        ),
        'top_tags', (
            SELECT jsonb_agg(jsonb_build_object('tag', tag, 'count', cnt))
            FROM (
                SELECT unnest(tags) AS tag, COUNT(*) AS cnt
                FROM memory_nodes
                WHERE user_id = p_user_id AND tags IS NOT NULL
                GROUP BY tag
                ORDER BY cnt DESC
                LIMIT 20
            ) sub
        ),
        'top_linked_nodes', (
            SELECT jsonb_agg(jsonb_build_object('id', id, 'title', title, 'links', links_count))
            FROM (
                SELECT id, title, links_count
                FROM memory_nodes
                WHERE user_id = p_user_id
                ORDER BY links_count DESC
                LIMIT 10
            ) sub
        ),
        'growth_this_week', (
            SELECT COUNT(*)
            FROM memory_nodes
            WHERE user_id = p_user_id
              AND created_at >= DATE_TRUNC('week', NOW())
        ),
        'links_this_week', (
            SELECT COUNT(*)
            FROM memory_links
            WHERE user_id = p_user_id
              AND created_at >= DATE_TRUNC('week', NOW())
        ),
        'reviews_due', (
            SELECT COUNT(*)
            FROM memory_nodes
            WHERE user_id = p_user_id
              AND review_status IN ('due', 'overdue')
              AND next_review_at <= NOW() + INTERVAL '1 day'
        ),
        'brain_age_days', (
            SELECT COALESCE(EXTRACT(DAY FROM (NOW() - MIN(created_at)))::INTEGER, 0)
            FROM memory_nodes
            WHERE user_id = p_user_id
        )
    ) INTO result
    FROM memory_nodes
    WHERE user_id = p_user_id;

    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: create_bidirectional_link
-- Creates a bidirectional link with proper constraint checking.
-- Returns the created link's ID or NULL if duplicate.
-- ============================================================================

CREATE OR REPLACE FUNCTION create_bidirectional_link(
    p_user_id UUID,
    p_source_id UUID,
    p_target_id UUID,
    p_link_type VARCHAR(50) DEFAULT 'related_to',
    p_label TEXT DEFAULT NULL,
    p_context TEXT DEFAULT NULL,
    p_strength FLOAT DEFAULT 0.5,
    p_confidence FLOAT DEFAULT 0.7,
    p_is_auto_generated BOOLEAN DEFAULT false
)
RETURNS UUID AS $$
DECLARE
    v_link_id UUID;
BEGIN
    -- Prevent self-links
    IF p_source_id = p_target_id THEN
        RAISE EXCEPTION 'Cannot create a link from a node to itself';
    END IF;

    -- Check both nodes exist and belong to user
    IF NOT EXISTS (
        SELECT 1 FROM memory_nodes
        WHERE id IN (p_source_id, p_target_id)
        AND user_id = p_user_id
        HAVING COUNT(*) = 2
    ) THEN
        RAISE EXCEPTION 'Both nodes must exist and belong to the user';
    END IF;

    -- Normalize direction: always use the lower UUID as source for consistency
    -- This prevents duplicate mirrored links
    -- Actually, we enforce this at the application level via UNIQUE(source_id, target_id, link_type)
    -- Insert the link (will fail with unique violation if duplicate)
    INSERT INTO memory_links (
        user_id, source_id, target_id, link_type,
        label, context, strength, confidence, is_auto_generated
    ) VALUES (
        p_user_id, p_source_id, p_target_id, p_link_type,
        p_label, p_context, p_strength, p_confidence, p_is_auto_generated
    )
    RETURNING id INTO v_link_id;

    -- Trigger on memory_links will handle updating links_count and is_orphan
    RETURN v_link_id;

EXCEPTION
    WHEN unique_violation THEN
        -- Link already exists, return existing link ID
        SELECT id INTO v_link_id
        FROM memory_links
        WHERE source_id = p_source_id
          AND target_id = p_target_id
          AND link_type = p_link_type;
        RETURN v_link_id;
END;
$$ LANGUAGE plpgsql;
