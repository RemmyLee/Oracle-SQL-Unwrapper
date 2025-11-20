"""
Dashboard Service
Business logic for dashboard operations, access control, and management
"""

from backend.models import (
    Dashboard, DashboardComponent, DashboardDataSource,
    DashboardShare, DashboardVersion, DashboardTemplate,
    User, Role, AuditLog
)
from backend.extensions import db, cache
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
import re
import secrets


class DashboardService:
    """Service for dashboard operations"""

    # ==========================================
    # Dashboard CRUD Operations
    # ==========================================

    @staticmethod
    def create_dashboard(owner, title, description=None, access_level='private', **kwargs):
        """
        Create a new dashboard

        Args:
            owner: User object (owner)
            title: Dashboard title
            description: Optional description
            access_level: 'private', 'authenticated', 'public', 'shared'
            **kwargs: Additional dashboard fields

        Returns:
            tuple: (dashboard, error_message)
        """
        try:
            # Generate slug from title
            slug = DashboardService.generate_slug(title)

            # Create dashboard
            dashboard = Dashboard(
                owner_id=owner.id,
                title=title,
                description=description,
                slug=slug,
                access_level=access_level,
                **kwargs
            )

            db.session.add(dashboard)
            db.session.commit()

            # Log creation
            AuditLog.log_action(
                action='create',
                user=owner,
                resource_type='dashboard',
                resource_id=dashboard.id,
                new_values=dashboard.to_dict()
            )

            return dashboard, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_dashboard(dashboard, user, **updates):
        """
        Update dashboard

        Args:
            dashboard: Dashboard object
            user: User performing update
            **updates: Fields to update

        Returns:
            tuple: (success, error_message)
        """
        try:
            # Store old values for audit
            old_values = dashboard.to_dict()

            # Update allowed fields
            allowed_fields = [
                'title', 'description', 'slug', 'access_level', 'is_published',
                'is_template', 'layout_config', 'theme', 'custom_css',
                'refresh_interval', 'allow_embedding', 'allow_export',
                'allow_filters', 'tags', 'category'
            ]

            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(dashboard, field, value)

            # Update slug if title changed
            if 'title' in updates and 'slug' not in updates:
                dashboard.slug = DashboardService.generate_slug(updates['title'])

            dashboard.updated_at = datetime.utcnow()
            db.session.commit()

            # Log update
            AuditLog.log_action(
                action='update',
                user=user,
                resource_type='dashboard',
                resource_id=dashboard.id,
                old_values=old_values,
                new_values=dashboard.to_dict()
            )

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete_dashboard(dashboard, user):
        """
        Delete dashboard

        Args:
            dashboard: Dashboard object
            user: User performing deletion

        Returns:
            tuple: (success, error_message)
        """
        try:
            dashboard_data = dashboard.to_dict()
            dashboard_id = dashboard.id

            db.session.delete(dashboard)
            db.session.commit()

            # Log deletion
            AuditLog.log_action(
                action='delete',
                user=user,
                resource_type='dashboard',
                resource_id=dashboard_id,
                old_values=dashboard_data
            )

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def clone_dashboard(dashboard, user, new_title=None):
        """
        Clone a dashboard

        Args:
            dashboard: Dashboard to clone
            user: User creating clone
            new_title: Optional new title

        Returns:
            tuple: (cloned_dashboard, error_message)
        """
        try:
            # Create new dashboard
            title = new_title or f"{dashboard.title} (Copy)"
            cloned = Dashboard(
                owner_id=user.id,
                title=title,
                description=dashboard.description,
                slug=DashboardService.generate_slug(title),
                access_level='private',  # Clones start as private
                layout_config=dashboard.layout_config,
                theme=dashboard.theme,
                custom_css=dashboard.custom_css,
                refresh_interval=dashboard.refresh_interval,
                allow_embedding=dashboard.allow_embedding,
                allow_export=dashboard.allow_export,
                allow_filters=dashboard.allow_filters,
                tags=dashboard.tags,
                category=dashboard.category
            )

            db.session.add(cloned)
            db.session.flush()  # Get ID for components

            # Clone components
            for component in dashboard.components:
                cloned_component = DashboardComponent(
                    dashboard_id=cloned.id,
                    component_type=component.component_type,
                    title=component.title,
                    description=component.description,
                    grid_position=component.grid_position,
                    config=component.config,
                    data_source_id=component.data_source_id,
                    query_override=component.query_override,
                    style=component.style,
                    is_visible=component.is_visible,
                    display_order=component.display_order,
                    is_interactive=component.is_interactive,
                    refresh_on_filter=component.refresh_on_filter
                )
                db.session.add(cloned_component)

            # Clone data sources
            for ds in dashboard.data_sources:
                cloned_ds = DashboardDataSource(
                    dashboard_id=cloned.id,
                    name=ds.name,
                    description=ds.description,
                    source_type=ds.source_type,
                    connection_id=ds.connection_id,
                    saved_query_id=ds.saved_query_id,
                    query_text=ds.query_text,
                    static_data=ds.static_data,
                    api_endpoint=ds.api_endpoint,
                    api_method=ds.api_method,
                    api_headers=ds.api_headers,
                    parameters=ds.parameters,
                    default_filters=ds.default_filters,
                    cache_enabled=ds.cache_enabled,
                    cache_duration=ds.cache_duration,
                    auto_refresh=ds.auto_refresh,
                    refresh_interval=ds.refresh_interval
                )
                db.session.add(cloned_ds)

            db.session.commit()

            # Log cloning
            AuditLog.log_action(
                action='clone',
                user=user,
                resource_type='dashboard',
                resource_id=cloned.id,
                new_values={'cloned_from': dashboard.id, 'title': title}
            )

            return cloned, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    # ==========================================
    # Access Control
    # ==========================================

    @staticmethod
    def can_view_dashboard(dashboard, user=None):
        """
        Check if user can view dashboard

        Args:
            dashboard: Dashboard object
            user: User object (None for anonymous)

        Returns:
            bool: True if user can view
        """
        # Public dashboards
        if dashboard.access_level == 'public' and dashboard.is_published:
            return True

        # Authenticated dashboards
        if dashboard.access_level == 'authenticated' and user and dashboard.is_published:
            return True

        # Owner
        if user and dashboard.owner_id == user.id:
            return True

        # Shared with user
        if user:
            share = DashboardShare.query.filter_by(
                dashboard_id=dashboard.id,
                shared_with_user_id=user.id
            ).first()
            if share and not share.is_expired():
                return True

            # Shared with role
            user_roles = user.get_roles()
            for role in user_roles:
                share = DashboardShare.query.filter_by(
                    dashboard_id=dashboard.id,
                    shared_with_role_id=role.id
                ).first()
                if share and not share.is_expired():
                    return True

        return False

    @staticmethod
    def can_edit_dashboard(dashboard, user):
        """
        Check if user can edit dashboard

        Args:
            dashboard: Dashboard object
            user: User object

        Returns:
            bool: True if user can edit
        """
        if not user:
            return False

        # Owner
        if dashboard.owner_id == user.id:
            return True

        # Shared with edit permission
        share = DashboardShare.query.filter_by(
            dashboard_id=dashboard.id,
            shared_with_user_id=user.id
        ).filter(
            DashboardShare.permission_level.in_(['edit', 'admin'])
        ).first()

        if share and not share.is_expired():
            return True

        # Shared with role (edit permission)
        user_roles = user.get_roles()
        for role in user_roles:
            share = DashboardShare.query.filter_by(
                dashboard_id=dashboard.id,
                shared_with_role_id=role.id
            ).filter(
                DashboardShare.permission_level.in_(['edit', 'admin'])
            ).first()
            if share and not share.is_expired():
                return True

        return False

    @staticmethod
    def can_delete_dashboard(dashboard, user):
        """
        Check if user can delete dashboard

        Args:
            dashboard: Dashboard object
            user: User object

        Returns:
            bool: True if user can delete
        """
        if not user:
            return False

        # Owner
        if dashboard.owner_id == user.id:
            return True

        # Shared with admin permission
        share = DashboardShare.query.filter_by(
            dashboard_id=dashboard.id,
            shared_with_user_id=user.id,
            permission_level='admin'
        ).first()

        return share and not share.is_expired()

    # ==========================================
    # Sharing & Permissions
    # ==========================================

    @staticmethod
    def share_dashboard(dashboard, user, shared_with_user=None, shared_with_role=None,
                       permission_level='view', expires_at=None, notify=True):
        """
        Share dashboard with user or role

        Args:
            dashboard: Dashboard object
            user: User sharing (must have permission)
            shared_with_user: User to share with (optional)
            shared_with_role: Role to share with (optional)
            permission_level: 'view', 'edit', 'admin'
            expires_at: Optional expiration datetime
            notify: Send email notification

        Returns:
            tuple: (share, error_message)
        """
        try:
            # Validate
            if not shared_with_user and not shared_with_role:
                return None, 'Must specify user or role to share with'

            if shared_with_user and shared_with_role:
                return None, 'Cannot share with both user and role simultaneously'

            # Check if already shared
            existing = DashboardShare.query.filter_by(
                dashboard_id=dashboard.id,
                shared_with_user_id=shared_with_user.id if shared_with_user else None,
                shared_with_role_id=shared_with_role.id if shared_with_role else None
            ).first()

            if existing:
                return None, 'Dashboard already shared with this user/role'

            # Create share
            share = DashboardShare(
                dashboard_id=dashboard.id,
                shared_with_user_id=shared_with_user.id if shared_with_user else None,
                shared_with_role_id=shared_with_role.id if shared_with_role else None,
                permission_level=permission_level,
                shared_by_user_id=user.id,
                expires_at=expires_at,
                notify_on_share=notify
            )

            db.session.add(share)
            db.session.commit()

            # TODO: Send email notification if notify=True

            # Log sharing
            AuditLog.log_action(
                action='share_dashboard',
                user=user,
                resource_type='dashboard_share',
                resource_id=share.id,
                new_values=share.to_dict()
            )

            return share, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def unshare_dashboard(share, user):
        """
        Remove dashboard share

        Args:
            share: DashboardShare object
            user: User removing share

        Returns:
            tuple: (success, error_message)
        """
        try:
            share_data = share.to_dict()
            share_id = share.id

            db.session.delete(share)
            db.session.commit()

            # Log unsharing
            AuditLog.log_action(
                action='unshare_dashboard',
                user=user,
                resource_type='dashboard_share',
                resource_id=share_id,
                old_values=share_data
            )

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    # ==========================================
    # Public Access
    # ==========================================

    @staticmethod
    def generate_public_link(dashboard, user, password=None, expires_in_days=None):
        """
        Generate public access link for dashboard

        Args:
            dashboard: Dashboard object
            user: User generating link
            password: Optional password protection
            expires_in_days: Optional expiration in days

        Returns:
            tuple: (public_token, error_message)
        """
        try:
            # Generate token
            dashboard.generate_public_token()

            # Set password if provided
            if password:
                dashboard.set_public_password(password)

            # Set expiration
            if expires_in_days:
                dashboard.public_expiry = datetime.utcnow() + timedelta(days=expires_in_days)

            # Ensure dashboard is public
            dashboard.access_level = 'public'
            db.session.commit()

            # Log action
            AuditLog.log_action(
                action='generate_public_link',
                user=user,
                resource_type='dashboard',
                resource_id=dashboard.id,
                new_values={'public_token': dashboard.public_token, 'has_password': bool(password)}
            )

            return dashboard.public_token, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def revoke_public_link(dashboard, user):
        """
        Revoke public access link

        Args:
            dashboard: Dashboard object
            user: User revoking link

        Returns:
            tuple: (success, error_message)
        """
        try:
            old_token = dashboard.public_token

            dashboard.public_token = None
            dashboard.public_password_hash = None
            dashboard.public_expiry = None

            # Change access level if it was public
            if dashboard.access_level == 'public':
                dashboard.access_level = 'private'

            db.session.commit()

            # Log action
            AuditLog.log_action(
                action='revoke_public_link',
                user=user,
                resource_type='dashboard',
                resource_id=dashboard.id,
                old_values={'public_token': old_token}
            )

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    # ==========================================
    # Version Control
    # ==========================================

    @staticmethod
    def create_version(dashboard, user, change_summary=None, version_name=None, is_major=False):
        """
        Create dashboard version snapshot

        Args:
            dashboard: Dashboard object
            user: User creating version
            change_summary: Description of changes
            version_name: Optional version name
            is_major: Major version flag

        Returns:
            tuple: (version, error_message)
        """
        try:
            # Get current version number
            latest_version = DashboardVersion.query.filter_by(
                dashboard_id=dashboard.id
            ).order_by(DashboardVersion.version_number.desc()).first()

            version_number = (latest_version.version_number + 1) if latest_version else 1

            # Create snapshots
            dashboard_snapshot = dashboard.to_dict(include_components=False)
            components_snapshot = [comp.to_dict() for comp in dashboard.components]

            # Create version
            version = DashboardVersion(
                dashboard_id=dashboard.id,
                version_number=version_number,
                version_name=version_name,
                change_summary=change_summary,
                dashboard_snapshot=dashboard_snapshot,
                components_snapshot=components_snapshot,
                created_by_user_id=user.id,
                is_major_version=is_major
            )

            db.session.add(version)

            # Update dashboard version number
            dashboard.version = version_number
            db.session.commit()

            # Log action
            AuditLog.log_action(
                action='create_version',
                user=user,
                resource_type='dashboard_version',
                resource_id=version.id,
                new_values={'version_number': version_number, 'is_major': is_major}
            )

            return version, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    # ==========================================
    # Utility Methods
    # ==========================================

    @staticmethod
    def generate_slug(title):
        """
        Generate URL-friendly slug from title

        Args:
            title: Dashboard title

        Returns:
            str: URL-friendly slug
        """
        # Convert to lowercase
        slug = title.lower()

        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while Dashboard.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    @staticmethod
    def search_dashboards(user=None, query=None, category=None, tags=None,
                         access_level=None, is_published=None, owner_id=None,
                         page=1, per_page=50, sort_by='updated_at', sort_order='desc'):
        """
        Search dashboards with filters

        Args:
            user: Current user (for access control)
            query: Search query (title/description)
            category: Filter by category
            tags: Filter by tags (list)
            access_level: Filter by access level
            is_published: Filter by published status
            owner_id: Filter by owner
            page: Page number
            per_page: Items per page
            sort_by: Sort field
            sort_order: 'asc' or 'desc'

        Returns:
            tuple: (dashboards, pagination_info)
        """
        # Build query
        q = Dashboard.query

        # Access control filter
        if user:
            # User can see: own dashboards, public, authenticated, shared
            q = q.filter(
                or_(
                    Dashboard.owner_id == user.id,
                    and_(Dashboard.access_level == 'public', Dashboard.is_published == True),
                    and_(Dashboard.access_level == 'authenticated', Dashboard.is_published == True),
                    Dashboard.id.in_(
                        db.session.query(DashboardShare.dashboard_id).filter(
                            or_(
                                DashboardShare.shared_with_user_id == user.id,
                                DashboardShare.shared_with_role_id.in_([r.id for r in user.get_roles()])
                            )
                        )
                    )
                )
            )
        else:
            # Anonymous: only public published dashboards
            q = q.filter_by(access_level='public', is_published=True)

        # Search query
        if query:
            search_pattern = f'%{query}%'
            q = q.filter(
                or_(
                    Dashboard.title.ilike(search_pattern),
                    Dashboard.description.ilike(search_pattern)
                )
            )

        # Filters
        if category:
            q = q.filter_by(category=category)

        if tags:
            # Filter by tags (PostgreSQL JSON contains, SQLite uses basic check)
            for tag in tags:
                q = q.filter(Dashboard.tags.contains([tag]))

        if access_level:
            q = q.filter_by(access_level=access_level)

        if is_published is not None:
            q = q.filter_by(is_published=is_published)

        if owner_id:
            q = q.filter_by(owner_id=owner_id)

        # Sorting
        if sort_by in ['created_at', 'updated_at', 'title', 'view_count']:
            sort_column = getattr(Dashboard, sort_by)
            if sort_order.lower() == 'asc':
                q = q.order_by(sort_column.asc())
            else:
                q = q.order_by(sort_column.desc())

        # Paginate
        pagination = q.paginate(page=page, per_page=per_page, error_out=False)

        return pagination.items, {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
