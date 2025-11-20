"""
Dashboard API endpoints
Handles dashboard CRUD, sharing, public access, and management
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import Dashboard, User, AuditLog, DashboardShare, Role
from backend.services import DashboardService
from backend.extensions import db
import logging
from datetime import datetime, timedelta

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
