"""
Dashboard API endpoints
Handles dashboard CRUD, sharing, public access, and management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import Dashboard, User, AuditLog, DashboardShare, Role, DashboardComponent, DashboardDataSource, OracleConnection, DashboardVersion, DashboardTemplate
from backend.services import DashboardService, SimpleOracleConnector
from backend.extensions import db, limiter
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Create blueprint
dashboards_bp = Blueprint('dashboards', __name__)


def get_current_user():
    """Get current authenticated user (None if anonymous)"""
    try:
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
    except:
        pass
    return None


# ==========================================
# Dashboard CRUD Endpoints
# ==========================================

@dashboards_bp.route('/dashboards', methods=['GET'])
def list_dashboards():
    """
    List dashboards with search and filters

    GET /api/dashboards

    Query Parameters:
    - query: Search query (title/description)
    - category: Filter by category
    - tags: Filter by tags (comma-separated)
    - access_level: Filter by access level
    - is_published: Filter by published status (true/false)
    - owner_id: Filter by owner
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - sort_by: Sort field (default: updated_at)
    - sort_order: Sort order (asc/desc, default: desc)

    Response:
    {
        "success": true,
        "dashboards": [...],
        "pagination": {...}
    }
    """
    try:
        # Get current user (may be None for anonymous)
        user = get_current_user()

        # Get query parameters
        query = request.args.get('query')
        category = request.args.get('category')
        tags_str = request.args.get('tags')
        tags = tags_str.split(',') if tags_str else None
        access_level = request.args.get('access_level')
        is_published_str = request.args.get('is_published')
        is_published = is_published_str.lower() == 'true' if is_published_str else None
        owner_id = request.args.get('owner_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        sort_by = request.args.get('sort_by', 'updated_at')
        sort_order = request.args.get('sort_order', 'desc')

        # Search dashboards
        dashboards, pagination = DashboardService.search_dashboards(
            user=user,
            query=query,
            category=category,
            tags=tags,
            access_level=access_level,
            is_published=is_published,
            owner_id=owner_id,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return jsonify({
            'success': True,
            'dashboards': [d.to_dict(include_owner=True) for d in dashboards],
            'pagination': pagination
        }), 200

    except Exception as e:
        logger.error(f"List dashboards error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list dashboards',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>', methods=['GET'])
def get_dashboard(dashboard_id):
    """
    Get dashboard by ID

    GET /api/dashboards/<dashboard_id>

    Query Parameters:
    - include_components: Include components (default: false)

    Response:
    {
        "success": true,
        "dashboard": {...}
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        # Increment view count
        dashboard.increment_view_count()
        db.session.commit()

        # Include components if requested
        include_components = request.args.get('include_components', 'false').lower() == 'true'

        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict(include_components=include_components, include_owner=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/slug/<slug>', methods=['GET'])
def get_dashboard_by_slug(slug):
    """
    Get dashboard by slug

    GET /api/dashboards/slug/<slug>

    Query Parameters:
    - include_components: Include components (default: false)

    Response:
    {
        "success": true,
        "dashboard": {...}
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.filter_by(slug=slug).first()

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        # Increment view count
        dashboard.increment_view_count()
        db.session.commit()

        # Include components if requested
        include_components = request.args.get('include_components', 'false').lower() == 'true'

        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict(include_components=include_components, include_owner=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard by slug error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards', methods=['POST'])
@jwt_required()
def create_dashboard():
    """
    Create new dashboard

    POST /api/dashboards
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "My Dashboard",
        "description": "Optional description",
        "access_level": "private",  # private, authenticated, public, shared
        "category": "Analytics",
        "tags": ["sales", "analytics"],
        "layout_config": {...},
        "theme": "default",
        "refresh_interval": 60
    }

    Response:
    {
        "success": true,
        "message": "Dashboard created successfully",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.get_json()

        # Required fields
        title = data.get('title')

        if not title:
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400

        # Optional fields
        description = data.get('description')
        access_level = data.get('access_level', 'private')
        category = data.get('category')
        tags = data.get('tags')
        layout_config = data.get('layout_config')
        theme = data.get('theme', 'default')
        refresh_interval = data.get('refresh_interval')
        allow_embedding = data.get('allow_embedding', False)
        allow_export = data.get('allow_export', True)
        allow_filters = data.get('allow_filters', True)

        # Create dashboard
        dashboard, error = DashboardService.create_dashboard(
            owner=user,
            title=title,
            description=description,
            access_level=access_level,
            category=category,
            tags=tags,
            layout_config=layout_config,
            theme=theme,
            refresh_interval=refresh_interval,
            allow_embedding=allow_embedding,
            allow_export=allow_export,
            allow_filters=allow_filters
        )

        if error:
            return jsonify({
                'success': False,
                'error': 'Failed to create dashboard',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Dashboard created successfully',
            'dashboard': dashboard.to_dict(include_owner=True)
        }), 201

    except Exception as e:
        logger.error(f"Create dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>', methods=['PUT'])
@jwt_required()
def update_dashboard(dashboard_id):
    """
    Update dashboard

    PUT /api/dashboards/<dashboard_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "Updated Title",
        "description": "Updated description",
        "layout_config": {...},
        "theme": "dark",
        "tags": ["updated", "tags"]
    }

    Response:
    {
        "success": true,
        "message": "Dashboard updated successfully",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()

        # Update dashboard
        success, error = DashboardService.update_dashboard(dashboard, user, **data)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update dashboard',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Dashboard updated successfully',
            'dashboard': dashboard.to_dict(include_owner=True)
        }), 200

    except Exception as e:
        logger.error(f"Update dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard(dashboard_id):
    """
    Delete dashboard

    DELETE /api/dashboards/<dashboard_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Dashboard deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_delete_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to delete this dashboard'
            }), 403

        # Delete dashboard
        success, error = DashboardService.delete_dashboard(dashboard, user)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to delete dashboard',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Dashboard deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Delete dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/clone', methods=['POST'])
@jwt_required()
def clone_dashboard(dashboard_id):
    """
    Clone dashboard

    POST /api/dashboards/<dashboard_id>/clone
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "Optional new title"
    }

    Response:
    {
        "success": true,
        "message": "Dashboard cloned successfully",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check view permission (need to view to clone)
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to clone this dashboard'
            }), 403

        data = request.get_json() or {}
        new_title = data.get('title')

        # Clone dashboard
        cloned, error = DashboardService.clone_dashboard(dashboard, user, new_title)

        if error:
            return jsonify({
                'success': False,
                'error': 'Failed to clone dashboard',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Dashboard cloned successfully',
            'dashboard': cloned.to_dict(include_owner=True)
        }), 201

    except Exception as e:
        logger.error(f"Clone dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clone dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/publish', methods=['POST'])
@jwt_required()
def publish_dashboard(dashboard_id):
    """
    Publish dashboard

    POST /api/dashboards/<dashboard_id>/publish
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Dashboard published successfully",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to publish this dashboard'
            }), 403

        # Publish dashboard
        dashboard.publish()
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='publish_dashboard',
            user=user,
            resource_type='dashboard',
            resource_id=dashboard.id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Dashboard published successfully',
            'dashboard': dashboard.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Publish dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to publish dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/unpublish', methods=['POST'])
@jwt_required()
def unpublish_dashboard(dashboard_id):
    """
    Unpublish dashboard

    POST /api/dashboards/<dashboard_id>/unpublish
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Dashboard unpublished successfully",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to unpublish this dashboard'
            }), 403

        # Unpublish dashboard
        dashboard.unpublish()
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='unpublish_dashboard',
            user=user,
            resource_type='dashboard',
            resource_id=dashboard.id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Dashboard unpublished successfully',
            'dashboard': dashboard.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unpublish dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to unpublish dashboard',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Statistics
# ==========================================

@dashboards_bp.route('/dashboards/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Get dashboard statistics for current user

    GET /api/dashboards/stats
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "stats": {
            "total_dashboards": 10,
            "published_dashboards": 5,
            "draft_dashboards": 5,
            "total_views": 1250,
            "dashboards_shared_with_me": 3,
            "most_viewed": {...}
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Count dashboards
        total = Dashboard.query.filter_by(owner_id=user.id).count()
        published = Dashboard.query.filter_by(owner_id=user.id, is_published=True).count()
        drafts = Dashboard.query.filter_by(owner_id=user.id, is_draft=True).count()

        # Total views
        from sqlalchemy import func
        total_views = db.session.query(func.sum(Dashboard.view_count)).filter_by(owner_id=user.id).scalar() or 0

        # Dashboards shared with user
        from backend.models import DashboardShare
        shared_with_me = DashboardShare.query.filter_by(shared_with_user_id=user.id).count()

        # Most viewed dashboard
        most_viewed = Dashboard.query.filter_by(owner_id=user.id).order_by(Dashboard.view_count.desc()).first()

        stats = {
            'total_dashboards': total,
            'published_dashboards': published,
            'draft_dashboards': drafts,
            'total_views': total_views,
            'dashboards_shared_with_me': shared_with_me,
            'most_viewed': most_viewed.to_dict() if most_viewed else None
        }

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard stats error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get dashboard statistics',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Sharing Endpoints
# ==========================================

@dashboards_bp.route('/dashboards/<int:dashboard_id>/share', methods=['POST'])
@jwt_required()
def share_dashboard(dashboard_id):
    """
    Share dashboard with a user or role

    POST /api/dashboards/<dashboard_id>/share
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "user_id": 123,  # OR
        "role_id": 456,
        "permission_level": "view",  # view, edit, admin
        "expires_in_days": 30  # optional
    }

    Response:
    {
        "success": true,
        "message": "Dashboard shared successfully",
        "share": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (only owner or admin can share)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to share this dashboard'
            }), 403

        data = request.get_json()

        # Get share target (user or role)
        shared_with_user_id = data.get('user_id')
        shared_with_role_id = data.get('role_id')
        permission_level = data.get('permission_level', 'view')
        expires_in_days = data.get('expires_in_days')

        if not shared_with_user_id and not shared_with_role_id:
            return jsonify({
                'success': False,
                'error': 'Either user_id or role_id is required'
            }), 400

        if shared_with_user_id and shared_with_role_id:
            return jsonify({
                'success': False,
                'error': 'Cannot share with both user and role simultaneously'
            }), 400

        # Validate permission level
        if permission_level not in ['view', 'edit', 'admin']:
            return jsonify({
                'success': False,
                'error': 'Invalid permission_level. Must be: view, edit, or admin'
            }), 400

        # Get target user or role
        shared_with_user = None
        shared_with_role = None

        if shared_with_user_id:
            shared_with_user = User.query.get(shared_with_user_id)
            if not shared_with_user:
                return jsonify({
                    'success': False,
                    'error': 'Target user not found'
                }), 404

            # Cannot share with yourself
            if shared_with_user.id == user.id:
                return jsonify({
                    'success': False,
                    'error': 'Cannot share dashboard with yourself'
                }), 400

        if shared_with_role_id:
            shared_with_role = Role.query.get(shared_with_role_id)
            if not shared_with_role:
                return jsonify({
                    'success': False,
                    'error': 'Target role not found'
                }), 404

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Share dashboard
        share, error = DashboardService.share_dashboard(
            dashboard=dashboard,
            user=user,
            shared_with_user=shared_with_user,
            shared_with_role=shared_with_role,
            permission_level=permission_level,
            expires_at=expires_at
        )

        if error:
            return jsonify({
                'success': False,
                'error': 'Failed to share dashboard',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Dashboard shared successfully',
            'share': share.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Share dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to share dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/shares', methods=['GET'])
@jwt_required()
def list_dashboard_shares(dashboard_id):
    """
    List all shares for a dashboard

    GET /api/dashboards/<dashboard_id>/shares
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "shares": [...]
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (only owner or admin can view shares)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view shares for this dashboard'
            }), 403

        # Get all shares
        shares = DashboardShare.query.filter_by(dashboard_id=dashboard_id).all()

        return jsonify({
            'success': True,
            'shares': [share.to_dict(include_user=True, include_role=True) for share in shares]
        }), 200

    except Exception as e:
        logger.error(f"List dashboard shares error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list dashboard shares',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/shares/<int:share_id>', methods=['PUT'])
@jwt_required()
def update_dashboard_share(dashboard_id, share_id):
    """
    Update share permissions

    PUT /api/dashboards/<dashboard_id>/shares/<share_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "permission_level": "edit",
        "expires_in_days": 60
    }

    Response:
    {
        "success": true,
        "message": "Share updated successfully",
        "share": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        share = DashboardShare.query.filter_by(id=share_id, dashboard_id=dashboard_id).first()

        if not share:
            return jsonify({
                'success': False,
                'error': 'Share not found'
            }), 404

        # Check permission (only owner or admin can update shares)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to update shares for this dashboard'
            }), 403

        data = request.get_json()

        # Update permission level
        if 'permission_level' in data:
            permission_level = data['permission_level']
            if permission_level not in ['view', 'edit', 'admin']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid permission_level. Must be: view, edit, or admin'
                }), 400
            share.permission_level = permission_level

        # Update expiration
        if 'expires_in_days' in data:
            expires_in_days = data['expires_in_days']
            if expires_in_days is None:
                share.expires_at = None
            else:
                share.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='update_dashboard_share',
            user=user,
            resource_type='dashboard_share',
            resource_id=share.id,
            details={'dashboard_id': dashboard_id},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Share updated successfully',
            'share': share.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update dashboard share error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update share',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/shares/<int:share_id>', methods=['DELETE'])
@jwt_required()
def remove_dashboard_share(dashboard_id, share_id):
    """
    Remove share (revoke access)

    DELETE /api/dashboards/<dashboard_id>/shares/<share_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Share removed successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        share = DashboardShare.query.filter_by(id=share_id, dashboard_id=dashboard_id).first()

        if not share:
            return jsonify({
                'success': False,
                'error': 'Share not found'
            }), 404

        # Check permission (only owner or admin can remove shares)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to remove shares for this dashboard'
            }), 403

        # Remove share
        success, error = DashboardService.unshare_dashboard(dashboard, user, share)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to remove share',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Share removed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Remove dashboard share error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to remove share',
            'message': str(e)
        }), 500


# ==========================================
# Public Dashboard Access
# ==========================================

@dashboards_bp.route('/dashboards/<int:dashboard_id>/public-link', methods=['POST'])
@jwt_required()
def generate_public_link(dashboard_id):
    """
    Generate public access link for dashboard

    POST /api/dashboards/<dashboard_id>/public-link
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "password": "optional_password",
        "expires_in_days": 30  # optional
    }

    Response:
    {
        "success": true,
        "message": "Public link generated successfully",
        "public_token": "abc123...",
        "public_url": "/public/dashboards/abc123",
        "expires_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (only owner or admin can generate public links)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to generate public links for this dashboard'
            }), 403

        data = request.get_json() or {}

        password = data.get('password')
        expires_in_days = data.get('expires_in_days')

        # Generate public link
        success, error = DashboardService.generate_public_link(
            dashboard=dashboard,
            user=user,
            password=password,
            expires_in_days=expires_in_days
        )

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to generate public link',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Public link generated successfully',
            'public_token': dashboard.public_token,
            'public_url': f'/public/dashboards/{dashboard.public_token}',
            'expires_at': dashboard.public_link_expires_at.isoformat() if dashboard.public_link_expires_at else None
        }), 201

    except Exception as e:
        logger.error(f"Generate public link error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate public link',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/public-link', methods=['DELETE'])
@jwt_required()
def revoke_public_link(dashboard_id):
    """
    Revoke public access link

    DELETE /api/dashboards/<dashboard_id>/public-link
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Public link revoked successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (only owner or admin can revoke public links)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to revoke public links for this dashboard'
            }), 403

        # Revoke public link
        success, error = DashboardService.revoke_public_link(dashboard, user)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to revoke public link',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Public link revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"Revoke public link error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to revoke public link',
            'message': str(e)
        }), 500


@dashboards_bp.route('/public/dashboards/<token>', methods=['GET'])
@limiter.limit("50 per minute")
def access_public_dashboard(token):
    """
    Access public dashboard by token (no authentication required)

    GET /api/public/dashboards/<token>

    Query Parameters:
    - password: Optional password if dashboard is password-protected
    - include_components: Include components (default: true)

    Response:
    {
        "success": true,
        "dashboard": {...},
        "requires_password": false
    }
    """
    try:
        dashboard = Dashboard.query.filter_by(public_token=token).first()

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found',
                'message': 'Invalid or expired public link'
            }), 404

        # Check if public access is enabled
        if dashboard.access_level != 'public' or not dashboard.is_published:
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'This dashboard is not publicly accessible'
            }), 403

        # Check if public link has expired
        if dashboard.public_link_expires_at and dashboard.public_link_expires_at < datetime.utcnow():
            return jsonify({
                'success': False,
                'error': 'Link expired',
                'message': 'This public link has expired'
            }), 410

        # Check password if required
        password = request.args.get('password')

        if dashboard.public_password_hash:
            if not password:
                return jsonify({
                    'success': False,
                    'error': 'Password required',
                    'message': 'This dashboard requires a password',
                    'requires_password': True
                }), 401

            if not dashboard.verify_public_password(password):
                return jsonify({
                    'success': False,
                    'error': 'Invalid password',
                    'message': 'The password you provided is incorrect',
                    'requires_password': True
                }), 401

        # Increment view count
        dashboard.increment_view_count()
        db.session.commit()

        # Include components by default for public access
        include_components = request.args.get('include_components', 'true').lower() == 'true'

        return jsonify({
            'success': True,
            'dashboard': dashboard.to_dict(include_components=include_components, include_owner=True),
            'requires_password': False
        }), 200

    except Exception as e:
        logger.error(f"Access public dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to access dashboard',
            'message': str(e)
        }), 500


@dashboards_bp.route('/public/dashboards/<token>/verify-password', methods=['POST'])
@limiter.limit("10 per minute")
def verify_public_dashboard_password(token):
    """
    Verify password for password-protected public dashboard

    POST /api/public/dashboards/<token>/verify-password

    Request Body:
    {
        "password": "the_password"
    }

    Response:
    {
        "success": true,
        "message": "Password verified",
        "valid": true
    }
    """
    try:
        dashboard = Dashboard.query.filter_by(public_token=token).first()

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        if not dashboard.public_password_hash:
            return jsonify({
                'success': True,
                'message': 'No password required',
                'valid': True
            }), 200

        data = request.get_json()
        password = data.get('password')

        if not password:
            return jsonify({
                'success': False,
                'error': 'Password is required'
            }), 400

        valid = dashboard.verify_public_password(password)

        return jsonify({
            'success': True,
            'message': 'Password verified' if valid else 'Invalid password',
            'valid': valid
        }), 200

    except Exception as e:
        logger.error(f"Verify public dashboard password error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to verify password',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Component Management
# ==========================================

@dashboards_bp.route('/dashboards/<int:dashboard_id>/components', methods=['GET'])
def list_dashboard_components(dashboard_id):
    """
    List all components for a dashboard

    GET /api/dashboards/<dashboard_id>/components

    Response:
    {
        "success": true,
        "components": [...]
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        # Get all components ordered by position
        components = DashboardComponent.query.filter_by(
            dashboard_id=dashboard_id
        ).order_by(DashboardComponent.order_index).all()

        return jsonify({
            'success': True,
            'components': [comp.to_dict(include_data_source=True) for comp in components]
        }), 200

    except Exception as e:
        logger.error(f"List dashboard components error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list components',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components', methods=['POST'])
@jwt_required()
def add_dashboard_component(dashboard_id):
    """
    Add a new component to dashboard

    POST /api/dashboards/<dashboard_id>/components
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "component_type": "chart",  # chart, table, metric, text, filter, image, etc.
        "title": "Sales Chart",
        "grid_position": {
            "x": 0,
            "y": 0,
            "w": 6,
            "h": 4,
            "minW": 2,
            "minH": 2
        },
        "config": {
            "chart_type": "bar",
            "colors": ["#3b82f6"],
            ...
        },
        "data_source_id": 123,  # optional
        "refresh_interval": 60,  # optional
        "order_index": 0  # optional
    }

    Response:
    {
        "success": true,
        "message": "Component added successfully",
        "component": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()

        # Required fields
        component_type = data.get('component_type')
        title = data.get('title')

        if not component_type:
            return jsonify({
                'success': False,
                'error': 'component_type is required'
            }), 400

        # Validate component type
        valid_types = ['chart', 'table', 'metric', 'text', 'filter', 'image', 'iframe', 'map', 'gauge', 'progress']
        if component_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'Invalid component_type. Must be one of: {", ".join(valid_types)}'
            }), 400

        # Optional fields
        description = data.get('description')
        grid_position = data.get('grid_position', {})
        config = data.get('config', {})
        data_source_id = data.get('data_source_id')
        refresh_interval = data.get('refresh_interval')
        order_index = data.get('order_index')
        is_visible = data.get('is_visible', True)

        # Validate data source if provided
        if data_source_id:
            data_source = DashboardDataSource.query.get(data_source_id)
            if not data_source:
                return jsonify({
                    'success': False,
                    'error': 'Data source not found'
                }), 404
            if data_source.dashboard_id != dashboard_id:
                return jsonify({
                    'success': False,
                    'error': 'Data source does not belong to this dashboard'
                }), 400

        # Get next order index if not provided
        if order_index is None:
            max_order = db.session.query(db.func.max(DashboardComponent.order_index)).filter_by(
                dashboard_id=dashboard_id
            ).scalar() or -1
            order_index = max_order + 1

        # Create component
        component = DashboardComponent(
            dashboard_id=dashboard_id,
            component_type=component_type,
            title=title,
            description=description,
            grid_position=grid_position,
            config=config,
            data_source_id=data_source_id,
            refresh_interval=refresh_interval,
            order_index=order_index,
            is_visible=is_visible
        )

        db.session.add(component)
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='add_dashboard_component',
            user=user,
            resource_type='dashboard_component',
            resource_id=component.id,
            details={'dashboard_id': dashboard_id, 'component_type': component_type},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Component added successfully',
            'component': component.to_dict(include_data_source=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Add dashboard component error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to add component',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components/<int:component_id>', methods=['GET'])
def get_dashboard_component(dashboard_id, component_id):
    """
    Get a specific component

    GET /api/dashboards/<dashboard_id>/components/<component_id>

    Response:
    {
        "success": true,
        "component": {...}
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        component = DashboardComponent.query.filter_by(
            id=component_id,
            dashboard_id=dashboard_id
        ).first()

        if not component:
            return jsonify({
                'success': False,
                'error': 'Component not found'
            }), 404

        return jsonify({
            'success': True,
            'component': component.to_dict(include_data_source=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard component error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get component',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components/<int:component_id>', methods=['PUT'])
@jwt_required()
def update_dashboard_component(dashboard_id, component_id):
    """
    Update component

    PUT /api/dashboards/<dashboard_id>/components/<component_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "Updated Title",
        "grid_position": {...},
        "config": {...},
        "is_visible": false
    }

    Response:
    {
        "success": true,
        "message": "Component updated successfully",
        "component": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        component = DashboardComponent.query.filter_by(
            id=component_id,
            dashboard_id=dashboard_id
        ).first()

        if not component:
            return jsonify({
                'success': False,
                'error': 'Component not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()

        # Update fields
        if 'title' in data:
            component.title = data['title']
        if 'description' in data:
            component.description = data['description']
        if 'grid_position' in data:
            component.grid_position = data['grid_position']
        if 'config' in data:
            component.config = data['config']
        if 'data_source_id' in data:
            data_source_id = data['data_source_id']
            if data_source_id:
                data_source = DashboardDataSource.query.get(data_source_id)
                if not data_source or data_source.dashboard_id != dashboard_id:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid data source'
                    }), 400
            component.data_source_id = data_source_id
        if 'refresh_interval' in data:
            component.refresh_interval = data['refresh_interval']
        if 'is_visible' in data:
            component.is_visible = data['is_visible']

        component.updated_at = datetime.utcnow()
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='update_dashboard_component',
            user=user,
            resource_type='dashboard_component',
            resource_id=component.id,
            details={'dashboard_id': dashboard_id},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Component updated successfully',
            'component': component.to_dict(include_data_source=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update dashboard component error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update component',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components/<int:component_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard_component(dashboard_id, component_id):
    """
    Delete component

    DELETE /api/dashboards/<dashboard_id>/components/<component_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Component deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        component = DashboardComponent.query.filter_by(
            id=component_id,
            dashboard_id=dashboard_id
        ).first()

        if not component:
            return jsonify({
                'success': False,
                'error': 'Component not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        # Log action before deletion
        AuditLog.log_action(
            action='delete_dashboard_component',
            user=user,
            resource_type='dashboard_component',
            resource_id=component.id,
            details={'dashboard_id': dashboard_id, 'component_type': component.component_type},
            ip_address=request.remote_addr
        )

        db.session.delete(component)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Component deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete dashboard component error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete component',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components/reorder', methods=['POST'])
@jwt_required()
def reorder_dashboard_components(dashboard_id):
    """
    Reorder/rearrange components

    POST /api/dashboards/<dashboard_id>/components/reorder
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "component_orders": [
            {"id": 1, "order_index": 0},
            {"id": 2, "order_index": 1},
            {"id": 3, "order_index": 2}
        ]
    }

    Response:
    {
        "success": true,
        "message": "Components reordered successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()
        component_orders = data.get('component_orders', [])

        if not component_orders:
            return jsonify({
                'success': False,
                'error': 'component_orders is required'
            }), 400

        # Update order for each component
        for order_item in component_orders:
            component_id = order_item.get('id')
            order_index = order_item.get('order_index')

            if component_id is None or order_index is None:
                continue

            component = DashboardComponent.query.filter_by(
                id=component_id,
                dashboard_id=dashboard_id
            ).first()

            if component:
                component.order_index = order_index

        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='reorder_dashboard_components',
            user=user,
            resource_type='dashboard',
            resource_id=dashboard_id,
            details={'component_count': len(component_orders)},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Components reordered successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Reorder dashboard components error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to reorder components',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/components/<int:component_id>/duplicate', methods=['POST'])
@jwt_required()
def duplicate_dashboard_component(dashboard_id, component_id):
    """
    Duplicate a component

    POST /api/dashboards/<dashboard_id>/components/<component_id>/duplicate
    Headers: Authorization: Bearer <access_token>

    Request Body (optional):
    {
        "title": "Copy of Chart"  # optional override
    }

    Response:
    {
        "success": true,
        "message": "Component duplicated successfully",
        "component": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        component = DashboardComponent.query.filter_by(
            id=component_id,
            dashboard_id=dashboard_id
        ).first()

        if not component:
            return jsonify({
                'success': False,
                'error': 'Component not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json() or {}

        # Get next order index
        max_order = db.session.query(db.func.max(DashboardComponent.order_index)).filter_by(
            dashboard_id=dashboard_id
        ).scalar() or -1

        # Create duplicate
        new_title = data.get('title', f"{component.title} (Copy)")

        # Offset grid position slightly to avoid overlap
        new_grid_position = component.grid_position.copy() if component.grid_position else {}
        if 'x' in new_grid_position:
            new_grid_position['x'] = new_grid_position['x'] + 1
        if 'y' in new_grid_position:
            new_grid_position['y'] = new_grid_position['y'] + 1

        duplicate = DashboardComponent(
            dashboard_id=dashboard_id,
            component_type=component.component_type,
            title=new_title,
            description=component.description,
            grid_position=new_grid_position,
            config=component.config.copy() if component.config else {},
            data_source_id=component.data_source_id,
            refresh_interval=component.refresh_interval,
            order_index=max_order + 1,
            is_visible=component.is_visible
        )

        db.session.add(duplicate)
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='duplicate_dashboard_component',
            user=user,
            resource_type='dashboard_component',
            resource_id=duplicate.id,
            details={'dashboard_id': dashboard_id, 'source_component_id': component_id},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Component duplicated successfully',
            'component': duplicate.to_dict(include_data_source=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Duplicate dashboard component error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to duplicate component',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Data Source Integration
# ==========================================

@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources', methods=['GET'])
def list_dashboard_data_sources(dashboard_id):
    """
    List all data sources for a dashboard

    GET /api/dashboards/<dashboard_id>/data-sources

    Response:
    {
        "success": true,
        "data_sources": [...]
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        # Get all data sources
        data_sources = DashboardDataSource.query.filter_by(
            dashboard_id=dashboard_id
        ).all()

        return jsonify({
            'success': True,
            'data_sources': [ds.to_dict(include_connection=True) for ds in data_sources]
        }), 200

    except Exception as e:
        logger.error(f"List dashboard data sources error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list data sources',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources', methods=['POST'])
@jwt_required()
def create_dashboard_data_source(dashboard_id):
    """
    Create a new data source for dashboard

    POST /api/dashboards/<dashboard_id>/data-sources
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "name": "Sales Data",
        "source_type": "sql_query",  # sql_query, saved_query, rest_api, static_data, csv_upload
        "connection_id": 123,  # Required for sql_query
        "query_text": "SELECT * FROM sales",  # Required for sql_query
        "saved_query_id": 456,  # Required for saved_query
        "api_url": "https://api.example.com/data",  # Required for rest_api
        "api_method": "GET",  # For rest_api
        "api_headers": {...},  # For rest_api
        "static_data": {...},  # Required for static_data
        "cache_enabled": true,
        "cache_duration": 300,  # seconds
        "refresh_on_load": true
    }

    Response:
    {
        "success": true,
        "message": "Data source created successfully",
        "data_source": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()

        # Required fields
        name = data.get('name')
        source_type = data.get('source_type')

        if not name:
            return jsonify({
                'success': False,
                'error': 'name is required'
            }), 400

        if not source_type:
            return jsonify({
                'success': False,
                'error': 'source_type is required'
            }), 400

        # Validate source type
        valid_types = ['sql_query', 'saved_query', 'rest_api', 'static_data', 'csv_upload']
        if source_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'Invalid source_type. Must be one of: {", ".join(valid_types)}'
            }), 400

        # Type-specific validation
        connection_id = data.get('connection_id')
        query_text = data.get('query_text')
        saved_query_id = data.get('saved_query_id')
        api_url = data.get('api_url')
        api_method = data.get('api_method', 'GET')
        api_headers = data.get('api_headers')
        api_body = data.get('api_body')
        static_data = data.get('static_data')
        csv_data = data.get('csv_data')

        if source_type == 'sql_query':
            if not connection_id:
                return jsonify({
                    'success': False,
                    'error': 'connection_id is required for sql_query type'
                }), 400
            if not query_text:
                return jsonify({
                    'success': False,
                    'error': 'query_text is required for sql_query type'
                }), 400

            # Validate connection exists and user has access
            connection = OracleConnection.query.get(connection_id)
            if not connection:
                return jsonify({
                    'success': False,
                    'error': 'Connection not found'
                }), 404

            # Check connection access (owner or shared)
            if connection.owner_id != user.id:
                # TODO: Add share checking logic if connections can be shared
                return jsonify({
                    'success': False,
                    'error': 'You do not have access to this connection'
                }), 403

        elif source_type == 'saved_query':
            if not saved_query_id:
                return jsonify({
                    'success': False,
                    'error': 'saved_query_id is required for saved_query type'
                }), 400
            # TODO: Validate saved query exists and user has access

        elif source_type == 'rest_api':
            if not api_url:
                return jsonify({
                    'success': False,
                    'error': 'api_url is required for rest_api type'
                }), 400

        elif source_type == 'static_data':
            if not static_data:
                return jsonify({
                    'success': False,
                    'error': 'static_data is required for static_data type'
                }), 400

        elif source_type == 'csv_upload':
            if not csv_data:
                return jsonify({
                    'success': False,
                    'error': 'csv_data is required for csv_upload type'
                }), 400

        # Optional fields
        description = data.get('description')
        cache_enabled = data.get('cache_enabled', True)
        cache_duration = data.get('cache_duration', 300)
        refresh_on_load = data.get('refresh_on_load', True)

        # Create data source
        data_source = DashboardDataSource(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            source_type=source_type,
            connection_id=connection_id,
            query_text=query_text,
            saved_query_id=saved_query_id,
            api_url=api_url,
            api_method=api_method,
            api_headers=api_headers,
            api_body=api_body,
            static_data=static_data,
            csv_data=csv_data,
            cache_enabled=cache_enabled,
            cache_duration=cache_duration,
            refresh_on_load=refresh_on_load
        )

        db.session.add(data_source)
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='create_dashboard_data_source',
            user=user,
            resource_type='dashboard_data_source',
            resource_id=data_source.id,
            details={'dashboard_id': dashboard_id, 'source_type': source_type},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Data source created successfully',
            'data_source': data_source.to_dict(include_connection=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>', methods=['GET'])
def get_dashboard_data_source(dashboard_id, source_id):
    """
    Get a specific data source

    GET /api/dashboards/<dashboard_id>/data-sources/<source_id>

    Response:
    {
        "success": true,
        "data_source": {...}
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        return jsonify({
            'success': True,
            'data_source': data_source.to_dict(include_connection=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>', methods=['PUT'])
@jwt_required()
def update_dashboard_data_source(dashboard_id, source_id):
    """
    Update data source

    PUT /api/dashboards/<dashboard_id>/data-sources/<source_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "name": "Updated Name",
        "query_text": "SELECT * FROM updated_table",
        "cache_duration": 600
    }

    Response:
    {
        "success": true,
        "message": "Data source updated successfully",
        "data_source": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        data = request.get_json()

        # Update fields
        if 'name' in data:
            data_source.name = data['name']
        if 'description' in data:
            data_source.description = data['description']
        if 'query_text' in data:
            data_source.query_text = data['query_text']
            # Clear cached data when query changes
            data_source.cached_data = None
            data_source.cached_at = None
        if 'api_url' in data:
            data_source.api_url = data['api_url']
            data_source.cached_data = None
            data_source.cached_at = None
        if 'api_method' in data:
            data_source.api_method = data['api_method']
        if 'api_headers' in data:
            data_source.api_headers = data['api_headers']
        if 'api_body' in data:
            data_source.api_body = data['api_body']
        if 'static_data' in data:
            data_source.static_data = data['static_data']
            data_source.cached_data = None
        if 'cache_enabled' in data:
            data_source.cache_enabled = data['cache_enabled']
        if 'cache_duration' in data:
            data_source.cache_duration = data['cache_duration']
        if 'refresh_on_load' in data:
            data_source.refresh_on_load = data['refresh_on_load']

        data_source.updated_at = datetime.utcnow()
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='update_dashboard_data_source',
            user=user,
            resource_type='dashboard_data_source',
            resource_id=data_source.id,
            details={'dashboard_id': dashboard_id},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Data source updated successfully',
            'data_source': data_source.to_dict(include_connection=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard_data_source(dashboard_id, source_id):
    """
    Delete data source

    DELETE /api/dashboards/<dashboard_id>/data-sources/<source_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Data source deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to edit this dashboard'
            }), 403

        # Check if data source is in use
        components_using = DashboardComponent.query.filter_by(data_source_id=source_id).count()
        if components_using > 0:
            return jsonify({
                'success': False,
                'error': 'Cannot delete data source',
                'message': f'This data source is currently used by {components_using} component(s). Remove it from components first.'
            }), 400

        # Log action before deletion
        AuditLog.log_action(
            action='delete_dashboard_data_source',
            user=user,
            resource_type='dashboard_data_source',
            resource_id=data_source.id,
            details={'dashboard_id': dashboard_id, 'source_type': data_source.source_type},
            ip_address=request.remote_addr
        )

        db.session.delete(data_source)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Data source deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>/test', methods=['POST'])
@jwt_required()
def test_dashboard_data_source(dashboard_id, source_id):
    """
    Test data source connection/query

    POST /api/dashboards/<dashboard_id>/data-sources/<source_id>/test
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Data source test successful",
        "test_results": {
            "connection_ok": true,
            "row_count": 100,
            "columns": ["col1", "col2"],
            "execution_time": 0.523
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        # Check permission
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        import time
        start_time = time.time()

        test_results = {
            'connection_ok': False,
            'row_count': 0,
            'columns': [],
            'execution_time': 0,
            'error': None
        }

        try:
            if data_source.source_type == 'sql_query':
                # Test Oracle connection and query
                connection = OracleConnection.query.get(data_source.connection_id)
                if not connection:
                    raise Exception('Connection not found')

                connector = SimpleOracleConnector(
                    host=connection.host,
                    port=connection.port,
                    service_name=connection.service_name,
                    username=connection.username,
                    password=connection.get_decrypted_password()
                )

                # Execute query with ROWNUM limit for testing
                test_query = f"SELECT * FROM ({data_source.query_text}) WHERE ROWNUM <= 10"
                results = connector.execute_query(test_query)

                test_results['connection_ok'] = True
                test_results['row_count'] = len(results)
                test_results['columns'] = list(results[0].keys()) if results else []

            elif data_source.source_type == 'static_data':
                # Validate static data structure
                if data_source.static_data:
                    if isinstance(data_source.static_data, list):
                        test_results['connection_ok'] = True
                        test_results['row_count'] = len(data_source.static_data)
                        if data_source.static_data:
                            test_results['columns'] = list(data_source.static_data[0].keys())
                    else:
                        raise Exception('static_data must be a list of objects')

            elif data_source.source_type == 'rest_api':
                # Test REST API
                import requests
                response = requests.request(
                    method=data_source.api_method,
                    url=data_source.api_url,
                    headers=data_source.api_headers or {},
                    json=data_source.api_body if data_source.api_method != 'GET' else None,
                    timeout=10
                )
                response.raise_for_status()

                data = response.json()
                test_results['connection_ok'] = True
                test_results['row_count'] = len(data) if isinstance(data, list) else 1
                if isinstance(data, list) and data:
                    test_results['columns'] = list(data[0].keys())
                elif isinstance(data, dict):
                    test_results['columns'] = list(data.keys())

            else:
                test_results['error'] = f'Testing not implemented for source_type: {data_source.source_type}'

        except Exception as test_error:
            test_results['error'] = str(test_error)

        test_results['execution_time'] = round(time.time() - start_time, 3)

        # Log action
        AuditLog.log_action(
            action='test_dashboard_data_source',
            user=user,
            resource_type='dashboard_data_source',
            resource_id=data_source.id,
            details={
                'dashboard_id': dashboard_id,
                'success': test_results['connection_ok'],
                'execution_time': test_results['execution_time']
            },
            ip_address=request.remote_addr
        )

        if test_results['error']:
            return jsonify({
                'success': False,
                'error': 'Data source test failed',
                'message': test_results['error'],
                'test_results': test_results
            }), 400

        return jsonify({
            'success': True,
            'message': 'Data source test successful',
            'test_results': test_results
        }), 200

    except Exception as e:
        logger.error(f"Test dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to test data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>/execute', methods=['POST'])
def execute_dashboard_data_source(dashboard_id, source_id):
    """
    Execute data source and fetch data

    POST /api/dashboards/<dashboard_id>/data-sources/<source_id>/execute

    Query Parameters:
    - force_refresh: Force refresh even if cached (default: false)

    Response:
    {
        "success": true,
        "data": [...],
        "metadata": {
            "row_count": 100,
            "columns": ["col1", "col2"],
            "cached": false,
            "execution_time": 0.523,
            "fetched_at": "2024-01-01T00:00:00Z"
        }
    }
    """
    try:
        user = get_current_user()

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check cache
        if not force_refresh and data_source.cache_enabled and data_source.cached_data:
            if data_source.cached_at:
                cache_age = (datetime.utcnow() - data_source.cached_at).total_seconds()
                if cache_age < data_source.cache_duration:
                    # Return cached data
                    return jsonify({
                        'success': True,
                        'data': data_source.cached_data,
                        'metadata': {
                            'row_count': len(data_source.cached_data),
                            'columns': list(data_source.cached_data[0].keys()) if data_source.cached_data else [],
                            'cached': True,
                            'cache_age': round(cache_age, 2),
                            'fetched_at': data_source.cached_at.isoformat()
                        }
                    }), 200

        # Execute data source
        import time
        start_time = time.time()
        results = []

        try:
            if data_source.source_type == 'sql_query':
                connection = OracleConnection.query.get(data_source.connection_id)
                if not connection:
                    raise Exception('Connection not found')

                connector = SimpleOracleConnector(
                    host=connection.host,
                    port=connection.port,
                    service_name=connection.service_name,
                    username=connection.username,
                    password=connection.get_decrypted_password()
                )

                results = connector.execute_query(data_source.query_text)

            elif data_source.source_type == 'static_data':
                results = data_source.static_data or []

            elif data_source.source_type == 'rest_api':
                import requests
                response = requests.request(
                    method=data_source.api_method,
                    url=data_source.api_url,
                    headers=data_source.api_headers or {},
                    json=data_source.api_body if data_source.api_method != 'GET' else None,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()
                results = data if isinstance(data, list) else [data]

            elif data_source.source_type == 'csv_upload':
                results = data_source.csv_data or []

            else:
                raise Exception(f'Execution not implemented for source_type: {data_source.source_type}')

            # Update cache
            if data_source.cache_enabled:
                data_source.cached_data = results
                data_source.cached_at = datetime.utcnow()
                db.session.commit()

            execution_time = round(time.time() - start_time, 3)

            return jsonify({
                'success': True,
                'data': results,
                'metadata': {
                    'row_count': len(results),
                    'columns': list(results[0].keys()) if results else [],
                    'cached': False,
                    'execution_time': execution_time,
                    'fetched_at': datetime.utcnow().isoformat()
                }
            }), 200

        except Exception as exec_error:
            logger.error(f"Execute data source error: {str(exec_error)}")
            return jsonify({
                'success': False,
                'error': 'Data source execution failed',
                'message': str(exec_error)
            }), 400

    except Exception as e:
        logger.error(f"Execute dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to execute data source',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/data-sources/<int:source_id>/refresh', methods=['POST'])
@jwt_required()
def refresh_dashboard_data_source(dashboard_id, source_id):
    """
    Refresh cached data for data source

    POST /api/dashboards/<dashboard_id>/data-sources/<source_id>/refresh
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Data source refreshed successfully",
        "metadata": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check access (can view is enough to refresh)
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        data_source = DashboardDataSource.query.filter_by(
            id=source_id,
            dashboard_id=dashboard_id
        ).first()

        if not data_source:
            return jsonify({
                'success': False,
                'error': 'Data source not found'
            }), 404

        # Clear cache
        data_source.cached_data = None
        data_source.cached_at = None
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='refresh_dashboard_data_source',
            user=user,
            resource_type='dashboard_data_source',
            resource_id=data_source.id,
            details={'dashboard_id': dashboard_id},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Data source cache cleared. Data will be refreshed on next fetch.',
            'metadata': {
                'cache_cleared': True
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Refresh dashboard data source error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to refresh data source',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Version Control
# ==========================================

@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions', methods=['GET'])
@jwt_required()
def list_dashboard_versions(dashboard_id):
    """
    List all versions for a dashboard

    GET /api/dashboards/<dashboard_id>/versions
    Headers: Authorization: Bearer <access_token>

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)

    Response:
    {
        "success": true,
        "versions": [...],
        "pagination": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (need to view to see versions)
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        # Get versions
        versions_query = DashboardVersion.query.filter_by(
            dashboard_id=dashboard_id
        ).order_by(DashboardVersion.created_at.desc())

        pagination_obj = versions_query.paginate(page=page, per_page=per_page, error_out=False)

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': pagination_obj.total,
            'pages': pagination_obj.pages,
            'has_next': pagination_obj.has_next,
            'has_prev': pagination_obj.has_prev
        }

        return jsonify({
            'success': True,
            'versions': [v.to_dict(include_user=True) for v in pagination_obj.items],
            'pagination': pagination
        }), 200

    except Exception as e:
        logger.error(f"List dashboard versions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list versions',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions', methods=['POST'])
@jwt_required()
def create_dashboard_version(dashboard_id):
    """
    Create a new version snapshot

    POST /api/dashboards/<dashboard_id>/versions
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "change_summary": "Added new sales chart",  # optional
        "is_major_version": false  # optional, default false
    }

    Response:
    {
        "success": true,
        "message": "Version created successfully",
        "version": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (need edit permission to create versions)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to create versions for this dashboard'
            }), 403

        data = request.get_json() or {}

        change_summary = data.get('change_summary')
        is_major = data.get('is_major_version', False)

        # Create version
        version, error = DashboardService.create_version(
            dashboard=dashboard,
            user=user,
            change_summary=change_summary,
            is_major=is_major
        )

        if error:
            return jsonify({
                'success': False,
                'error': 'Failed to create version',
                'message': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Version created successfully',
            'version': version.to_dict(include_user=True)
        }), 201

    except Exception as e:
        logger.error(f"Create dashboard version error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create version',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions/<int:version_id>', methods=['GET'])
@jwt_required()
def get_dashboard_version(dashboard_id, version_id):
    """
    Get a specific version

    GET /api/dashboards/<dashboard_id>/versions/<version_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "version": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        version = DashboardVersion.query.filter_by(
            id=version_id,
            dashboard_id=dashboard_id
        ).first()

        if not version:
            return jsonify({
                'success': False,
                'error': 'Version not found'
            }), 404

        return jsonify({
            'success': True,
            'version': version.to_dict(include_user=True, include_snapshots=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard version error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get version',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions/<int:version_id>/restore', methods=['POST'])
@jwt_required()
def restore_dashboard_version(dashboard_id, version_id):
    """
    Restore dashboard to a specific version

    POST /api/dashboards/<dashboard_id>/versions/<version_id>/restore
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "create_backup": true  # optional, create backup of current state before restore
    }

    Response:
    {
        "success": true,
        "message": "Dashboard restored successfully",
        "dashboard": {...},
        "backup_version": {...}  # if create_backup was true
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (need edit permission to restore)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to restore versions for this dashboard'
            }), 403

        version = DashboardVersion.query.filter_by(
            id=version_id,
            dashboard_id=dashboard_id
        ).first()

        if not version:
            return jsonify({
                'success': False,
                'error': 'Version not found'
            }), 404

        data = request.get_json() or {}
        create_backup = data.get('create_backup', True)

        # Create backup of current state before restore
        backup_version = None
        if create_backup:
            backup_version, error = DashboardService.create_version(
                dashboard=dashboard,
                user=user,
                change_summary=f"Backup before restoring to version {version.version_number}",
                is_major=False
            )

            if error:
                return jsonify({
                    'success': False,
                    'error': 'Failed to create backup',
                    'message': error
                }), 400

        # Restore from version
        if not version.dashboard_snapshot or not version.components_snapshot:
            return jsonify({
                'success': False,
                'error': 'Version snapshot is incomplete',
                'message': 'Cannot restore from this version'
            }), 400

        try:
            # Restore dashboard properties
            snapshot = version.dashboard_snapshot
            dashboard.title = snapshot.get('title', dashboard.title)
            dashboard.description = snapshot.get('description', dashboard.description)
            dashboard.layout_config = snapshot.get('layout_config')
            dashboard.theme = snapshot.get('theme', dashboard.theme)
            dashboard.refresh_interval = snapshot.get('refresh_interval')
            dashboard.allow_embedding = snapshot.get('allow_embedding', False)
            dashboard.allow_export = snapshot.get('allow_export', True)
            dashboard.allow_filters = snapshot.get('allow_filters', True)

            # Delete existing components
            DashboardComponent.query.filter_by(dashboard_id=dashboard_id).delete()

            # Restore components from snapshot
            for comp_snapshot in version.components_snapshot:
                component = DashboardComponent(
                    dashboard_id=dashboard_id,
                    component_type=comp_snapshot['component_type'],
                    title=comp_snapshot.get('title'),
                    description=comp_snapshot.get('description'),
                    grid_position=comp_snapshot.get('grid_position'),
                    config=comp_snapshot.get('config'),
                    data_source_id=comp_snapshot.get('data_source_id'),
                    refresh_interval=comp_snapshot.get('refresh_interval'),
                    order_index=comp_snapshot.get('order_index', 0),
                    is_visible=comp_snapshot.get('is_visible', True)
                )
                db.session.add(component)

            dashboard.updated_at = datetime.utcnow()
            db.session.commit()

            # Log action
            AuditLog.log_action(
                action='restore_dashboard_version',
                user=user,
                resource_type='dashboard',
                resource_id=dashboard_id,
                details={
                    'version_id': version_id,
                    'version_number': version.version_number,
                    'backup_created': create_backup
                },
                ip_address=request.remote_addr
            )

            response_data = {
                'success': True,
                'message': f'Dashboard restored to version {version.version_number}',
                'dashboard': dashboard.to_dict()
            }

            if backup_version:
                response_data['backup_version'] = backup_version.to_dict()

            return jsonify(response_data), 200

        except Exception as restore_error:
            db.session.rollback()
            logger.error(f"Restore failed: {str(restore_error)}")
            return jsonify({
                'success': False,
                'error': 'Failed to restore version',
                'message': str(restore_error)
            }), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Restore dashboard version error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to restore version',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions/<int:version_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard_version(dashboard_id, version_id):
    """
    Delete a version

    DELETE /api/dashboards/<dashboard_id>/versions/<version_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Version deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (need edit permission to delete versions)
        if not DashboardService.can_edit_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to delete versions for this dashboard'
            }), 403

        version = DashboardVersion.query.filter_by(
            id=version_id,
            dashboard_id=dashboard_id
        ).first()

        if not version:
            return jsonify({
                'success': False,
                'error': 'Version not found'
            }), 404

        # Log action before deletion
        AuditLog.log_action(
            action='delete_dashboard_version',
            user=user,
            resource_type='dashboard_version',
            resource_id=version_id,
            details={
                'dashboard_id': dashboard_id,
                'version_number': version.version_number
            },
            ip_address=request.remote_addr
        )

        db.session.delete(version)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Version deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete dashboard version error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete version',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/versions/compare', methods=['POST'])
@jwt_required()
def compare_dashboard_versions(dashboard_id):
    """
    Compare two versions or current state with a version

    POST /api/dashboards/<dashboard_id>/versions/compare
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "version_a_id": 123,  # optional, if null compares with current state
        "version_b_id": 456   # required
    }

    Response:
    {
        "success": true,
        "comparison": {
            "dashboard_changes": {...},
            "components_added": [...],
            "components_removed": [...],
            "components_modified": [...]
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        data = request.get_json()
        version_a_id = data.get('version_a_id')
        version_b_id = data.get('version_b_id')

        if not version_b_id:
            return jsonify({
                'success': False,
                'error': 'version_b_id is required'
            }), 400

        # Get version B (required)
        version_b = DashboardVersion.query.filter_by(
            id=version_b_id,
            dashboard_id=dashboard_id
        ).first()

        if not version_b:
            return jsonify({
                'success': False,
                'error': 'Version B not found'
            }), 404

        # Get version A or use current state
        if version_a_id:
            version_a = DashboardVersion.query.filter_by(
                id=version_a_id,
                dashboard_id=dashboard_id
            ).first()

            if not version_a:
                return jsonify({
                    'success': False,
                    'error': 'Version A not found'
                }), 404

            snapshot_a = version_a.dashboard_snapshot
            components_a = version_a.components_snapshot
        else:
            # Use current state
            snapshot_a = dashboard.to_dict()
            components_a = [comp.to_dict() for comp in dashboard.components]

        snapshot_b = version_b.dashboard_snapshot
        components_b = version_b.components_snapshot

        # Compare dashboard properties
        dashboard_changes = {}
        for key in ['title', 'description', 'theme', 'layout_config', 'refresh_interval']:
            val_a = snapshot_a.get(key)
            val_b = snapshot_b.get(key)
            if val_a != val_b:
                dashboard_changes[key] = {
                    'old': val_b,
                    'new': val_a
                }

        # Compare components
        components_a_dict = {c.get('id') or c.get('title'): c for c in components_a}
        components_b_dict = {c.get('id') or c.get('title'): c for c in components_b}

        components_added = []
        components_removed = []
        components_modified = []

        # Find added and modified
        for key, comp_a in components_a_dict.items():
            if key not in components_b_dict:
                components_added.append(comp_a)
            else:
                comp_b = components_b_dict[key]
                changes = {}
                for field in ['title', 'component_type', 'grid_position', 'config']:
                    if comp_a.get(field) != comp_b.get(field):
                        changes[field] = {
                            'old': comp_b.get(field),
                            'new': comp_a.get(field)
                        }
                if changes:
                    components_modified.append({
                        'component': comp_a,
                        'changes': changes
                    })

        # Find removed
        for key, comp_b in components_b_dict.items():
            if key not in components_a_dict:
                components_removed.append(comp_b)

        return jsonify({
            'success': True,
            'comparison': {
                'dashboard_changes': dashboard_changes,
                'components_added': components_added,
                'components_removed': components_removed,
                'components_modified': components_modified,
                'summary': {
                    'dashboard_changed': len(dashboard_changes) > 0,
                    'components_added_count': len(components_added),
                    'components_removed_count': len(components_removed),
                    'components_modified_count': len(components_modified)
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Compare dashboard versions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to compare versions',
            'message': str(e)
        }), 500


# ==========================================
# Dashboard Templates
# ==========================================

@dashboards_bp.route('/templates', methods=['GET'])
@limiter.limit("100 per minute")
def list_dashboard_templates():
    """
    List available dashboard templates

    GET /api/templates

    Query Parameters:
    - category: Filter by category
    - tags: Filter by tags (comma-separated)
    - is_featured: Filter featured templates (true/false)
    - search: Search in title/description
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    - sort_by: Sort field (default: usage_count)
    - sort_order: Sort order (asc/desc, default: desc)

    Response:
    {
        "success": true,
        "templates": [...],
        "pagination": {...}
    }
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        tags_str = request.args.get('tags')
        tags = tags_str.split(',') if tags_str else None
        is_featured_str = request.args.get('is_featured')
        is_featured = is_featured_str.lower() == 'true' if is_featured_str else None
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        sort_by = request.args.get('sort_by', 'usage_count')
        sort_order = request.args.get('sort_order', 'desc')

        # Build query
        query = DashboardTemplate.query

        # Apply filters
        if category:
            query = query.filter_by(category=category)

        if tags:
            # Filter templates that have any of the specified tags
            for tag in tags:
                query = query.filter(DashboardTemplate.tags.contains([tag]))

        if is_featured is not None:
            query = query.filter_by(is_featured=is_featured)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                db.or_(
                    DashboardTemplate.title.ilike(search_pattern),
                    DashboardTemplate.description.ilike(search_pattern)
                )
            )

        # Apply sorting
        if sort_by == 'usage_count':
            order_col = DashboardTemplate.usage_count
        elif sort_by == 'created_at':
            order_col = DashboardTemplate.created_at
        elif sort_by == 'title':
            order_col = DashboardTemplate.title
        else:
            order_col = DashboardTemplate.usage_count

        if sort_order == 'asc':
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        # Paginate
        pagination_obj = query.paginate(page=page, per_page=per_page, error_out=False)

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': pagination_obj.total,
            'pages': pagination_obj.pages,
            'has_next': pagination_obj.has_next,
            'has_prev': pagination_obj.has_prev
        }

        return jsonify({
            'success': True,
            'templates': [t.to_dict(include_creator=True) for t in pagination_obj.items],
            'pagination': pagination
        }), 200

    except Exception as e:
        logger.error(f"List dashboard templates error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list templates',
            'message': str(e)
        }), 500


@dashboards_bp.route('/templates/<int:template_id>', methods=['GET'])
def get_dashboard_template(template_id):
    """
    Get a specific template

    GET /api/templates/<template_id>

    Response:
    {
        "success": true,
        "template": {...}
    }
    """
    try:
        template = DashboardTemplate.query.get(template_id)

        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404

        return jsonify({
            'success': True,
            'template': template.to_dict(include_creator=True, include_config=True)
        }), 200

    except Exception as e:
        logger.error(f"Get dashboard template error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get template',
            'message': str(e)
        }), 500


@dashboards_bp.route('/templates', methods=['POST'])
@jwt_required()
def create_dashboard_template():
    """
    Create a new template

    POST /api/templates
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "Sales Dashboard Template",
        "description": "Template for sales analytics",
        "category": "Analytics",
        "tags": ["sales", "analytics"],
        "template_config": {...},  # Dashboard configuration
        "components_config": [...],  # Components configuration
        "preview_image_url": "https://...",  # optional
        "is_featured": false  # optional, admin only
    }

    Response:
    {
        "success": true,
        "message": "Template created successfully",
        "template": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.get_json()

        # Required fields
        title = data.get('title')
        template_config = data.get('template_config')
        components_config = data.get('components_config')

        if not title:
            return jsonify({
                'success': False,
                'error': 'title is required'
            }), 400

        if not template_config:
            return jsonify({
                'success': False,
                'error': 'template_config is required'
            }), 400

        if not components_config:
            return jsonify({
                'success': False,
                'error': 'components_config is required'
            }), 400

        # Optional fields
        description = data.get('description')
        category = data.get('category')
        tags = data.get('tags')
        preview_image_url = data.get('preview_image_url')
        is_featured = data.get('is_featured', False)

        # Only admins can set featured flag
        if is_featured and not user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Only administrators can create featured templates'
            }), 403

        # Create template
        template = DashboardTemplate(
            title=title,
            description=description,
            category=category,
            tags=tags,
            template_config=template_config,
            components_config=components_config,
            preview_image_url=preview_image_url,
            is_featured=is_featured,
            created_by_id=user.id
        )

        db.session.add(template)
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='create_dashboard_template',
            user=user,
            resource_type='dashboard_template',
            resource_id=template.id,
            details={'title': title, 'category': category},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Template created successfully',
            'template': template.to_dict(include_creator=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create dashboard template error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create template',
            'message': str(e)
        }), 500


@dashboards_bp.route('/dashboards/<int:dashboard_id>/create-template', methods=['POST'])
@jwt_required()
def create_template_from_dashboard(dashboard_id):
    """
    Create a template from an existing dashboard

    POST /api/dashboards/<dashboard_id>/create-template
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "My Template",
        "description": "Template description",
        "category": "Analytics",
        "tags": ["sales"],
        "include_data_sources": false  # optional, default false
    }

    Response:
    {
        "success": true,
        "message": "Template created from dashboard",
        "template": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        dashboard = Dashboard.query.get(dashboard_id)

        if not dashboard:
            return jsonify({
                'success': False,
                'error': 'Dashboard not found'
            }), 404

        # Check permission (need to view to create template)
        if not DashboardService.can_view_dashboard(dashboard, user):
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to view this dashboard'
            }), 403

        data = request.get_json()

        title = data.get('title')
        description = data.get('description')
        category = data.get('category')
        tags = data.get('tags')
        include_data_sources = data.get('include_data_sources', False)

        if not title:
            return jsonify({
                'success': False,
                'error': 'title is required'
            }), 400

        # Create template config from dashboard
        template_config = {
            'theme': dashboard.theme,
            'layout_config': dashboard.layout_config,
            'refresh_interval': dashboard.refresh_interval,
            'allow_embedding': dashboard.allow_embedding,
            'allow_export': dashboard.allow_export,
            'allow_filters': dashboard.allow_filters
        }

        # Create components config
        components_config = []
        for component in dashboard.components:
            comp_config = {
                'component_type': component.component_type,
                'title': component.title,
                'description': component.description,
                'grid_position': component.grid_position,
                'config': component.config,
                'refresh_interval': component.refresh_interval,
                'order_index': component.order_index,
                'is_visible': component.is_visible
            }

            # Optionally include data source info
            if include_data_sources and component.data_source:
                comp_config['data_source'] = {
                    'name': component.data_source.name,
                    'source_type': component.data_source.source_type,
                    'query_text': component.data_source.query_text if component.data_source.source_type == 'sql_query' else None,
                    'api_url': component.data_source.api_url if component.data_source.source_type == 'rest_api' else None,
                    'static_data': component.data_source.static_data if component.data_source.source_type == 'static_data' else None
                }

            components_config.append(comp_config)

        # Create template
        template = DashboardTemplate(
            title=title,
            description=description or dashboard.description,
            category=category or dashboard.category,
            tags=tags or dashboard.tags,
            template_config=template_config,
            components_config=components_config,
            created_by_id=user.id,
            is_featured=False
        )

        db.session.add(template)
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='create_template_from_dashboard',
            user=user,
            resource_type='dashboard_template',
            resource_id=template.id,
            details={'dashboard_id': dashboard_id, 'title': title},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Template created from dashboard',
            'template': template.to_dict(include_creator=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create template from dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create template',
            'message': str(e)
        }), 500


@dashboards_bp.route('/templates/<int:template_id>/use', methods=['POST'])
@jwt_required()
def create_dashboard_from_template(template_id):
    """
    Create a new dashboard from a template

    POST /api/templates/<template_id>/use
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "My Dashboard",  # optional, defaults to template title
        "description": "My dashboard description"  # optional
    }

    Response:
    {
        "success": true,
        "message": "Dashboard created from template",
        "dashboard": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        template = DashboardTemplate.query.get(template_id)

        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404

        data = request.get_json() or {}

        title = data.get('title', template.title)
        description = data.get('description', template.description)

        # Create dashboard from template
        template_config = template.template_config or {}

        dashboard, error = DashboardService.create_dashboard(
            owner=user,
            title=title,
            description=description,
            category=template.category,
            tags=template.tags,
            layout_config=template_config.get('layout_config'),
            theme=template_config.get('theme', 'default'),
            refresh_interval=template_config.get('refresh_interval'),
            allow_embedding=template_config.get('allow_embedding', False),
            allow_export=template_config.get('allow_export', True),
            allow_filters=template_config.get('allow_filters', True)
        )

        if error:
            return jsonify({
                'success': False,
                'error': 'Failed to create dashboard from template',
                'message': error
            }), 400

        # Create components from template
        for comp_config in (template.components_config or []):
            # Create data source if provided
            data_source_id = None
            if comp_config.get('data_source'):
                ds_config = comp_config['data_source']
                data_source = DashboardDataSource(
                    dashboard_id=dashboard.id,
                    name=ds_config.get('name', 'Data Source'),
                    source_type=ds_config.get('source_type', 'static_data'),
                    query_text=ds_config.get('query_text'),
                    api_url=ds_config.get('api_url'),
                    static_data=ds_config.get('static_data'),
                    cache_enabled=True,
                    cache_duration=300
                )
                db.session.add(data_source)
                db.session.flush()
                data_source_id = data_source.id

            # Create component
            component = DashboardComponent(
                dashboard_id=dashboard.id,
                component_type=comp_config['component_type'],
                title=comp_config.get('title'),
                description=comp_config.get('description'),
                grid_position=comp_config.get('grid_position'),
                config=comp_config.get('config'),
                data_source_id=data_source_id,
                refresh_interval=comp_config.get('refresh_interval'),
                order_index=comp_config.get('order_index', 0),
                is_visible=comp_config.get('is_visible', True)
            )
            db.session.add(component)

        # Increment template usage count
        template.increment_usage()

        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='create_dashboard_from_template',
            user=user,
            resource_type='dashboard',
            resource_id=dashboard.id,
            details={'template_id': template_id, 'template_title': template.title},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Dashboard created from template',
            'dashboard': dashboard.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create dashboard from template error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create dashboard from template',
            'message': str(e)
        }), 500


@dashboards_bp.route('/templates/<int:template_id>', methods=['PUT'])
@jwt_required()
def update_dashboard_template(template_id):
    """
    Update a template

    PUT /api/templates/<template_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "title": "Updated Title",
        "description": "Updated description",
        "category": "Updated Category",
        "tags": ["updated", "tags"],
        "is_featured": true  # admin only
    }

    Response:
    {
        "success": true,
        "message": "Template updated successfully",
        "template": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        template = DashboardTemplate.query.get(template_id)

        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404

        # Check permission (only creator or admin can update)
        if template.created_by_id != user.id and not user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to update this template'
            }), 403

        data = request.get_json()

        # Update fields
        if 'title' in data:
            template.title = data['title']
        if 'description' in data:
            template.description = data['description']
        if 'category' in data:
            template.category = data['category']
        if 'tags' in data:
            template.tags = data['tags']
        if 'template_config' in data:
            template.template_config = data['template_config']
        if 'components_config' in data:
            template.components_config = data['components_config']
        if 'preview_image_url' in data:
            template.preview_image_url = data['preview_image_url']

        # Only admins can change featured status
        if 'is_featured' in data:
            if not user.is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Only administrators can change featured status'
                }), 403
            template.is_featured = data['is_featured']

        template.updated_at = datetime.utcnow()
        db.session.commit()

        # Log action
        AuditLog.log_action(
            action='update_dashboard_template',
            user=user,
            resource_type='dashboard_template',
            resource_id=template.id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Template updated successfully',
            'template': template.to_dict(include_creator=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update dashboard template error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update template',
            'message': str(e)
        }), 500


@dashboards_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
def delete_dashboard_template(template_id):
    """
    Delete a template

    DELETE /api/templates/<template_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Template deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        template = DashboardTemplate.query.get(template_id)

        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404

        # Check permission (only creator or admin can delete)
        if template.created_by_id != user.id and not user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'message': 'You do not have permission to delete this template'
            }), 403

        # Log action before deletion
        AuditLog.log_action(
            action='delete_dashboard_template',
            user=user,
            resource_type='dashboard_template',
            resource_id=template.id,
            details={'title': template.title},
            ip_address=request.remote_addr
        )

        db.session.delete(template)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Template deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete dashboard template error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete template',
            'message': str(e)
        }), 500
