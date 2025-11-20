-- Phase 5: Dashboard Builder Models Migration
-- This migration adds all dashboard-related tables
-- Run this on your PostgreSQL/MySQL database (or it will be created automatically via SQLAlchemy)

-- Dashboard main table
CREATE TABLE IF NOT EXISTS dashboards (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),
    tags JSON,

    -- Access control
    access_level VARCHAR(20) DEFAULT 'private', -- private, authenticated, public, shared
    public_token VARCHAR(64) UNIQUE,
    public_password_hash VARCHAR(255),
    public_link_expires_at TIMESTAMP,

    -- Layout and configuration
    layout_config JSON,
    theme VARCHAR(50) DEFAULT 'default',
    refresh_interval INTEGER,

    -- Settings
    allow_embedding BOOLEAN DEFAULT FALSE,
    allow_export BOOLEAN DEFAULT TRUE,
    allow_filters BOOLEAN DEFAULT TRUE,

    -- State
    is_draft BOOLEAN DEFAULT TRUE,
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,

    -- Stats
    view_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_dashboards_owner (owner_id),
    INDEX idx_dashboards_slug (slug),
    INDEX idx_dashboards_access_level (access_level),
    INDEX idx_dashboards_published (is_published),
    INDEX idx_dashboards_category (category),
    INDEX idx_dashboards_created (created_at DESC)
);

-- Dashboard components (widgets)
CREATE TABLE IF NOT EXISTS dashboard_components (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    component_type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    description TEXT,

    -- Layout
    grid_position JSON,
    order_index INTEGER DEFAULT 0,

    -- Configuration
    config JSON,
    data_source_id INTEGER REFERENCES dashboard_data_sources(id) ON DELETE SET NULL,
    refresh_interval INTEGER,

    -- State
    is_visible BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_components_dashboard (dashboard_id),
    INDEX idx_components_type (component_type),
    INDEX idx_components_order (order_index)
);

-- Dashboard data sources
CREATE TABLE IF NOT EXISTS dashboard_data_sources (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Source configuration
    source_type VARCHAR(50) NOT NULL, -- sql_query, saved_query, rest_api, static_data, csv_upload
    connection_id INTEGER REFERENCES oracle_connections(id) ON DELETE SET NULL,
    saved_query_id INTEGER REFERENCES saved_queries(id) ON DELETE SET NULL,
    query_text TEXT,
    api_url VARCHAR(500),
    api_method VARCHAR(10) DEFAULT 'GET',
    api_headers JSON,
    api_body JSON,
    static_data JSON,
    csv_data JSON,

    -- Caching
    cache_enabled BOOLEAN DEFAULT TRUE,
    cache_duration INTEGER DEFAULT 300,
    cached_data JSON,
    cached_at TIMESTAMP,

    -- Settings
    refresh_on_load BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_datasources_dashboard (dashboard_id),
    INDEX idx_datasources_type (source_type),
    INDEX idx_datasources_connection (connection_id)
);

-- Dashboard sharing
CREATE TABLE IF NOT EXISTS dashboard_shares (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    shared_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shared_with_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    shared_with_role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,

    -- Permissions
    permission_level VARCHAR(20) DEFAULT 'view', -- view, edit, admin
    expires_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_shares_dashboard (dashboard_id),
    INDEX idx_shares_user (shared_with_user_id),
    INDEX idx_shares_role (shared_with_role_id),

    -- Constraints
    CHECK (shared_with_user_id IS NOT NULL OR shared_with_role_id IS NOT NULL)
);

-- Dashboard versions
CREATE TABLE IF NOT EXISTS dashboard_versions (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,

    -- Snapshots
    dashboard_snapshot JSON NOT NULL,
    components_snapshot JSON NOT NULL,

    -- Metadata
    change_summary TEXT,
    is_major_version BOOLEAN DEFAULT FALSE,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_versions_dashboard (dashboard_id),
    INDEX idx_versions_number (dashboard_id, version_number),
    INDEX idx_versions_created (created_at DESC),

    -- Unique constraint
    UNIQUE (dashboard_id, version_number)
);

-- Dashboard templates
CREATE TABLE IF NOT EXISTS dashboard_templates (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags JSON,

    -- Configuration
    template_config JSON NOT NULL,
    components_config JSON NOT NULL,

    -- Display
    preview_image_url VARCHAR(500),
    is_featured BOOLEAN DEFAULT FALSE,

    -- Stats
    usage_count INTEGER DEFAULT 0,

    -- Creator
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_templates_category (category),
    INDEX idx_templates_featured (is_featured),
    INDEX idx_templates_usage (usage_count DESC),
    INDEX idx_templates_created (created_at DESC)
);

-- Add foreign key constraint for components after data_sources table exists
ALTER TABLE dashboard_components
ADD CONSTRAINT fk_component_data_source
FOREIGN KEY (data_source_id)
REFERENCES dashboard_data_sources(id)
ON DELETE SET NULL;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_dashboards_public_token ON dashboards(public_token) WHERE public_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dashboards_tags ON dashboards USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_templates_tags ON dashboard_templates USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_dashboards_updated ON dashboards(updated_at DESC);

-- Add comments for documentation
COMMENT ON TABLE dashboards IS 'Main dashboard table for storing user dashboards';
COMMENT ON TABLE dashboard_components IS 'Dashboard widgets/components with grid positioning';
COMMENT ON TABLE dashboard_data_sources IS 'Data source configurations for dashboard components';
COMMENT ON TABLE dashboard_shares IS 'Dashboard sharing permissions for users and roles';
COMMENT ON TABLE dashboard_versions IS 'Version history snapshots for dashboards';
COMMENT ON TABLE dashboard_templates IS 'Reusable dashboard templates';
