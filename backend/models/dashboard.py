"""
Dashboard models for Phase 5: Dashboard Builder
Comprehensive APEX-like dashboard system with components, sharing, versioning
"""

from datetime import datetime
from backend.extensions import db
import secrets
import json


class Dashboard(db.Model):
    """
    Main Dashboard model
    Supports public, authenticated, and private access levels
    """

    __tablename__ = 'dashboards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Basic information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    slug = db.Column(db.String(200), unique=True, nullable=True, index=True)

    # Access control
    access_level = db.Column(db.String(20), default='private', nullable=False, index=True)
    # Options: 'private' (owner only), 'authenticated' (logged-in users), 'public' (anyone), 'shared' (specific users/roles)

    is_published = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_template = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Public sharing
    public_token = db.Column(db.String(64), unique=True, nullable=True, index=True)  # For public access without auth
    public_password_hash = db.Column(db.String(255), nullable=True)  # Optional password protection
    public_expiry = db.Column(db.DateTime, nullable=True)  # Optional expiration for public links

    # Layout configuration
    layout_config = db.Column(db.JSON, nullable=True)  # Grid layout: {rows, cols, breakpoints, etc}
    theme = db.Column(db.String(50), default='default', nullable=False)  # Theme name
    custom_css = db.Column(db.Text, nullable=True)  # Custom CSS for dashboard

    # Settings
    refresh_interval = db.Column(db.Integer, nullable=True)  # Auto-refresh in seconds (null = no auto-refresh)
    allow_embedding = db.Column(db.Boolean, default=False, nullable=False)  # Allow iframe embedding
    allow_export = db.Column(db.Boolean, default=True, nullable=False)  # Allow data export
    allow_filters = db.Column(db.Boolean, default=True, nullable=False)  # Enable global filters

    # Metadata
    tags = db.Column(db.JSON, nullable=True)  # Tags for organization ["analytics", "sales", etc.]
    category = db.Column(db.String(100), nullable=True, index=True)  # Category for grouping
    view_count = db.Column(db.Integer, default=0, nullable=False)  # Track popularity

    # Version control
    version = db.Column(db.Integer, default=1, nullable=False)  # Current version number
    is_draft = db.Column(db.Boolean, default=True, nullable=False)  # Draft vs published

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    last_viewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    owner = db.relationship('User', back_populates='owned_dashboards', foreign_keys=[owner_id])
    components = db.relationship('DashboardComponent', back_populates='dashboard', cascade='all, delete-orphan', lazy='dynamic')
    data_sources = db.relationship('DashboardDataSource', back_populates='dashboard', cascade='all, delete-orphan', lazy='dynamic')
    shares = db.relationship('DashboardShare', back_populates='dashboard', cascade='all, delete-orphan', lazy='dynamic')
    versions = db.relationship('DashboardVersion', back_populates='dashboard', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Dashboard {self.title}>'

    def generate_public_token(self):
        """Generate unique public access token"""
        self.public_token = secrets.token_urlsafe(32)
        return self.public_token

    def set_public_password(self, password):
        """Set password for public access"""
        from werkzeug.security import generate_password_hash
        self.public_password_hash = generate_password_hash(password)

    def check_public_password(self, password):
        """Verify public access password"""
        if not self.public_password_hash:
            return True  # No password required
        from werkzeug.security import check_password_hash
        return check_password_hash(self.public_password_hash, password)

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.last_viewed_at = datetime.utcnow()

    def publish(self):
        """Publish dashboard"""
        self.is_published = True
        self.is_draft = False
        self.published_at = datetime.utcnow()

    def unpublish(self):
        """Unpublish dashboard"""
        self.is_published = False

    def to_dict(self, include_components=False, include_owner=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'owner_id': self.owner_id,
            'title': self.title,
            'description': self.description,
            'slug': self.slug,
            'access_level': self.access_level,
            'is_published': self.is_published,
            'is_template': self.is_template,
            'public_token': self.public_token if self.access_level == 'public' else None,
            'has_password': bool(self.public_password_hash),
            'public_expiry': self.public_expiry.isoformat() if self.public_expiry else None,
            'layout_config': self.layout_config,
            'theme': self.theme,
            'custom_css': self.custom_css,
            'refresh_interval': self.refresh_interval,
            'allow_embedding': self.allow_embedding,
            'allow_export': self.allow_export,
            'allow_filters': self.allow_filters,
            'tags': self.tags or [],
            'category': self.category,
            'view_count': self.view_count,
            'version': self.version,
            'is_draft': self.is_draft,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'last_viewed_at': self.last_viewed_at.isoformat() if self.last_viewed_at else None
        }

        if include_components:
            data['components'] = [comp.to_dict() for comp in self.components]

        if include_owner and self.owner:
            data['owner'] = {
                'id': self.owner.id,
                'username': self.owner.username,
                'full_name': self.owner.full_name
            }

        return data


class DashboardComponent(db.Model):
    """
    Dashboard components (widgets, charts, tables, etc.)
    Each component is positioned on the dashboard grid
    """

    __tablename__ = 'dashboard_components'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False, index=True)

    # Component type
    component_type = db.Column(db.String(50), nullable=False, index=True)
    # Types: 'chart', 'table', 'metric', 'text', 'filter', 'image', 'iframe', 'sql_editor', etc.

    # Basic information
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Layout positioning (grid system)
    grid_position = db.Column(db.JSON, nullable=False)
    # Format: {x: 0, y: 0, w: 6, h: 4, minW: 2, minH: 2, maxW: 12, maxH: null}

    # Component configuration
    config = db.Column(db.JSON, nullable=True)
    # Format: {chartType: 'bar', colors: [...], options: {...}, etc.}

    # Data source
    data_source_id = db.Column(db.Integer, db.ForeignKey('dashboard_data_sources.id', ondelete='SET NULL'), nullable=True)
    query_override = db.Column(db.Text, nullable=True)  # Override data source query

    # Styling
    style = db.Column(db.JSON, nullable=True)  # Custom styles {backgroundColor, borderColor, etc.}

    # Display settings
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)  # Z-index/layer order

    # Interactivity
    is_interactive = db.Column(db.Boolean, default=True, nullable=False)
    refresh_on_filter = db.Column(db.Boolean, default=True, nullable=False)  # Respond to global filters

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    dashboard = db.relationship('Dashboard', back_populates='components')
    data_source = db.relationship('DashboardDataSource', foreign_keys=[data_source_id])

    def __repr__(self):
        return f'<DashboardComponent {self.component_type} on Dashboard {self.dashboard_id}>'

    def to_dict(self, include_data_source=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'dashboard_id': self.dashboard_id,
            'component_type': self.component_type,
            'title': self.title,
            'description': self.description,
            'grid_position': self.grid_position,
            'config': self.config or {},
            'data_source_id': self.data_source_id,
            'query_override': self.query_override,
            'style': self.style or {},
            'is_visible': self.is_visible,
            'display_order': self.display_order,
            'is_interactive': self.is_interactive,
            'refresh_on_filter': self.refresh_on_filter,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_data_source and self.data_source:
            data['data_source'] = self.data_source.to_dict()

        return data


class DashboardDataSource(db.Model):
    """
    Data sources for dashboard components
    Connects dashboards to Oracle queries or other data
    """

    __tablename__ = 'dashboard_data_sources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False, index=True)

    # Data source information
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source_type = db.Column(db.String(50), nullable=False, index=True)
    # Types: 'sql_query', 'saved_query', 'rest_api', 'static_data', 'csv_upload'

    # Connection
    connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id', ondelete='SET NULL'), nullable=True)
    saved_query_id = db.Column(db.Integer, db.ForeignKey('saved_queries.id', ondelete='SET NULL'), nullable=True)

    # Query/Data
    query_text = db.Column(db.Text, nullable=True)  # SQL query
    static_data = db.Column(db.JSON, nullable=True)  # Static JSON data
    api_endpoint = db.Column(db.String(500), nullable=True)  # REST API URL
    api_method = db.Column(db.String(10), default='GET', nullable=True)  # GET, POST, etc.
    api_headers = db.Column(db.JSON, nullable=True)  # API headers

    # Parameters
    parameters = db.Column(db.JSON, nullable=True)  # Query parameters {param1: 'value1', etc.}
    default_filters = db.Column(db.JSON, nullable=True)  # Default filter values

    # Caching
    cache_enabled = db.Column(db.Boolean, default=True, nullable=False)
    cache_duration = db.Column(db.Integer, default=300, nullable=False)  # Cache TTL in seconds
    last_cached_at = db.Column(db.DateTime, nullable=True)

    # Refresh settings
    auto_refresh = db.Column(db.Boolean, default=False, nullable=False)
    refresh_interval = db.Column(db.Integer, nullable=True)  # Auto-refresh in seconds

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    dashboard = db.relationship('Dashboard', back_populates='data_sources')
    connection = db.relationship('OracleConnection', foreign_keys=[connection_id])
    saved_query = db.relationship('SavedQuery', foreign_keys=[saved_query_id])

    def __repr__(self):
        return f'<DashboardDataSource {self.name}>'

    def is_cache_valid(self):
        """Check if cached data is still valid"""
        if not self.cache_enabled or not self.last_cached_at:
            return False

        elapsed = (datetime.utcnow() - self.last_cached_at).total_seconds()
        return elapsed < self.cache_duration

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'dashboard_id': self.dashboard_id,
            'name': self.name,
            'description': self.description,
            'source_type': self.source_type,
            'connection_id': self.connection_id,
            'saved_query_id': self.saved_query_id,
            'query_text': self.query_text,
            'static_data': self.static_data,
            'api_endpoint': self.api_endpoint,
            'api_method': self.api_method,
            'api_headers': self.api_headers,
            'parameters': self.parameters or {},
            'default_filters': self.default_filters or {},
            'cache_enabled': self.cache_enabled,
            'cache_duration': self.cache_duration,
            'last_cached_at': self.last_cached_at.isoformat() if self.last_cached_at else None,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DashboardShare(db.Model):
    """
    Dashboard sharing permissions
    Allows dashboards to be shared with specific users or roles
    """

    __tablename__ = 'dashboard_shares'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False, index=True)

    # Who it's shared with
    shared_with_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    shared_with_role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=True, index=True)

    # Permissions
    permission_level = db.Column(db.String(20), nullable=False, default='view')
    # Options: 'view' (read-only), 'edit' (can modify), 'admin' (full control)

    # Share metadata
    shared_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    share_token = db.Column(db.String(64), unique=True, nullable=True, index=True)  # Optional token for link sharing

    # Expiration
    expires_at = db.Column(db.DateTime, nullable=True)

    # Email notification
    notify_on_share = db.Column(db.Boolean, default=True, nullable=False)
    notified_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    dashboard = db.relationship('Dashboard', back_populates='shares')
    shared_with_user = db.relationship('User', foreign_keys=[shared_with_user_id], backref='shared_dashboards')
    shared_with_role = db.relationship('Role', foreign_keys=[shared_with_role_id])
    shared_by_user = db.relationship('User', foreign_keys=[shared_by_user_id])

    def __repr__(self):
        if self.shared_with_user_id:
            return f'<DashboardShare Dashboard {self.dashboard_id} with User {self.shared_with_user_id}>'
        else:
            return f'<DashboardShare Dashboard {self.dashboard_id} with Role {self.shared_with_role_id}>'

    def is_expired(self):
        """Check if share has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def generate_share_token(self):
        """Generate unique share token"""
        self.share_token = secrets.token_urlsafe(32)
        return self.share_token

    def to_dict(self):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'dashboard_id': self.dashboard_id,
            'shared_with_user_id': self.shared_with_user_id,
            'shared_with_role_id': self.shared_with_role_id,
            'permission_level': self.permission_level,
            'shared_by_user_id': self.shared_by_user_id,
            'share_token': self.share_token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'notify_on_share': self.notify_on_share,
            'notified_at': self.notified_at.isoformat() if self.notified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_expired': self.is_expired()
        }

        # Include user/role info if available
        if self.shared_with_user:
            data['shared_with_user'] = {
                'id': self.shared_with_user.id,
                'username': self.shared_with_user.username,
                'email': self.shared_with_user.email
            }

        if self.shared_with_role:
            data['shared_with_role'] = {
                'id': self.shared_with_role.id,
                'role_name': self.shared_with_role.role_name
            }

        if self.shared_by_user:
            data['shared_by_user'] = {
                'id': self.shared_by_user.id,
                'username': self.shared_by_user.username
            }

        return data


class DashboardVersion(db.Model):
    """
    Dashboard version history
    Stores snapshots of dashboard configurations for rollback
    """

    __tablename__ = 'dashboard_versions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False, index=True)

    # Version information
    version_number = db.Column(db.Integer, nullable=False)
    version_name = db.Column(db.String(100), nullable=True)  # Optional name like "v1.0", "Beta", etc.
    change_summary = db.Column(db.Text, nullable=True)  # What changed in this version

    # Snapshot of dashboard state
    dashboard_snapshot = db.Column(db.JSON, nullable=False)  # Full dashboard configuration
    components_snapshot = db.Column(db.JSON, nullable=False)  # All components at this version

    # Version metadata
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_major_version = db.Column(db.Boolean, default=False, nullable=False)  # Major vs minor version

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    dashboard = db.relationship('Dashboard', back_populates='versions')
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f'<DashboardVersion {self.version_number} of Dashboard {self.dashboard_id}>'

    def to_dict(self, include_snapshots=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'dashboard_id': self.dashboard_id,
            'version_number': self.version_number,
            'version_name': self.version_name,
            'change_summary': self.change_summary,
            'created_by_user_id': self.created_by_user_id,
            'is_major_version': self.is_major_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_snapshots:
            data['dashboard_snapshot'] = self.dashboard_snapshot
            data['components_snapshot'] = self.components_snapshot

        if self.created_by_user:
            data['created_by_user'] = {
                'id': self.created_by_user.id,
                'username': self.created_by_user.username
            }

        return data


class DashboardTemplate(db.Model):
    """
    Reusable dashboard templates
    Pre-built dashboard layouts that can be cloned
    """

    __tablename__ = 'dashboard_templates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Template information
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True, index=True)  # "Analytics", "Sales", "Operations", etc.

    # Template configuration
    template_config = db.Column(db.JSON, nullable=False)  # Dashboard configuration
    components_config = db.Column(db.JSON, nullable=False)  # Component configurations

    # Preview
    preview_image_url = db.Column(db.String(500), nullable=True)
    thumbnail_url = db.Column(db.String(500), nullable=True)

    # Metadata
    is_system_template = db.Column(db.Boolean, default=False, nullable=False)  # System vs user-created
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    tags = db.Column(db.JSON, nullable=True)  # Tags for searching

    # Usage tracking
    usage_count = db.Column(db.Integer, default=0, nullable=False)  # How many times used
    rating = db.Column(db.Float, nullable=True)  # Average rating

    # Availability
    is_public = db.Column(db.Boolean, default=False, nullable=False)  # Public template gallery
    is_featured = db.Column(db.Boolean, default=False, nullable=False)  # Featured template

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])

    def __repr__(self):
        return f'<DashboardTemplate {self.name}>'

    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1

    def to_dict(self, include_config=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'preview_image_url': self.preview_image_url,
            'thumbnail_url': self.thumbnail_url,
            'is_system_template': self.is_system_template,
            'created_by_user_id': self.created_by_user_id,
            'tags': self.tags or [],
            'usage_count': self.usage_count,
            'rating': self.rating,
            'is_public': self.is_public,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_config:
            data['template_config'] = self.template_config
            data['components_config'] = self.components_config

        if self.created_by_user:
            data['created_by_user'] = {
                'id': self.created_by_user.id,
                'username': self.created_by_user.username
            }

        return data
