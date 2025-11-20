"""
Admin Panel API endpoints
Handles administrative tasks like user management, statistics, and audit logs
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import User, Role, Permission, Session, AuditLog
from backend.extensions import db
from backend.services import AuthService
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__)


def require_admin():
    """Decorator to require admin permission"""
    def decorator(f):
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404

            # Check if user has manage_users permission
            if not user.has_permission('manage_users'):
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions',
                    'required_permission': 'manage_users'
                }), 403

            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# ==========================================
# User Management Endpoints
# ==========================================

@admin_bp.route('/admin/users', methods=['GET'])
@require_admin()
def list_users():
    """
    List all users with search and filtering

    GET /api/admin/users

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - search: Search by email, username, or name
    - email_verified: Filter by email verification status (true/false)
    - account_locked: Filter by account lock status (true/false)
    - role: Filter by role name
    - sort_by: Sort field (created_at, last_login, email, username)
    - sort_order: Sort order (asc/desc, default: desc)

    Response:
    {
        "success": true,
        "users": [...],
        "pagination": {...}
    }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search')
        email_verified = request.args.get('email_verified')
        account_locked = request.args.get('account_locked')
        role_filter = request.args.get('role')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        # Build query
        query = User.query

        # Search filter
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    User.email.ilike(search_pattern),
                    User.username.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            )

        # Email verified filter
        if email_verified is not None:
            verified = email_verified.lower() == 'true'
            query = query.filter_by(email_verified=verified)

        # Account locked filter
        if account_locked is not None:
            locked = account_locked.lower() == 'true'
            query = query.filter_by(account_locked=locked)

        # Role filter
        if role_filter:
            role = Role.query.filter_by(role_name=role_filter).first()
            if role:
                query = query.join(User.user_roles).filter_by(role_id=role.id)

        # Sorting
        if sort_by in ['created_at', 'last_login', 'email', 'username']:
            sort_column = getattr(User, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(User.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        users = [user.to_dict(include_sensitive=True) for user in pagination.items]

        return jsonify({
            'success': True,
            'users': users,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list users',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>', methods=['GET'])
@require_admin()
def get_user(target_user_id):
    """
    Get user details

    GET /api/admin/users/<user_id>

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            ...
            "roles": [...],
            "permissions": [...],
            "recent_activity": [...]
        }
    }
    """
    try:
        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Get user data with roles and permissions
        user_data = user.to_dict(include_sensitive=True)
        user_data['roles'] = [role.to_dict() for role in user.get_roles()]
        user_data['permissions'] = [perm.to_dict() for perm in user.get_all_permissions()]

        # Get recent activity
        recent_activity = AuditLog.query.filter_by(user_id=user.id).order_by(
            AuditLog.created_at.desc()
        ).limit(10).all()
        user_data['recent_activity'] = [log.to_dict() for log in recent_activity]

        # Get active sessions count
        active_sessions_count = Session.query.filter_by(
            user_id=user.id,
            revoked=False
        ).count()
        user_data['active_sessions_count'] = active_sessions_count

        return jsonify({
            'success': True,
            'user': user_data
        }), 200

    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>', methods=['PUT'])
@require_admin()
def update_user(target_user_id):
    """
    Update user

    PUT /api/admin/users/<user_id>

    Request Body:
    {
        "email": "newemail@example.com",
        "username": "newusername",
        "full_name": "New Name",
        "first_name": "New",
        "last_name": "Name"
    }

    Response:
    {
        "success": true,
        "message": "User updated successfully",
        "user": {...}
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.get_json()

        # Store old values for audit
        old_values = {
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        # Update email
        if 'email' in data and data['email'] != user.email:
            # Check if email already exists
            existing_user = User.find_by_email(data['email'])
            if existing_user and existing_user.id != user.id:
                return jsonify({
                    'success': False,
                    'error': 'Email already in use'
                }), 400

            user.email = data['email']
            # Admin can manually verify email or require re-verification
            # For now, keep verification status unchanged

        # Update username
        if 'username' in data and data['username'] != user.username:
            # Check if username already exists
            existing_user = User.find_by_username(data['username'])
            if existing_user and existing_user.id != user.id:
                return jsonify({
                    'success': False,
                    'error': 'Username already in use'
                }), 400

            user.username = data['username']

        # Update names
        if 'full_name' in data:
            user.full_name = data['full_name']

        if 'first_name' in data:
            user.first_name = data['first_name']

        if 'last_name' in data:
            user.last_name = data['last_name']

        # Store new values for audit
        new_values = {
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        db.session.commit()

        # Log the update
        AuditLog.log_action(
            action='admin_update_user',
            user=admin,
            resource_type='user',
            resource_id=user.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update user',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>', methods=['DELETE'])
@require_admin()
def delete_user(target_user_id):
    """
    Delete user

    DELETE /api/admin/users/<user_id>

    Response:
    {
        "success": true,
        "message": "User deleted successfully"
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        # Prevent admin from deleting themselves
        if admin_id == target_user_id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 403

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Store user data for audit
        user_data = user.to_dict(include_sensitive=True)

        # Delete user (cascades to related records)
        db.session.delete(user)
        db.session.commit()

        # Log the deletion
        AuditLog.log_action(
            action='admin_delete_user',
            user=admin,
            resource_type='user',
            resource_id=target_user_id,
            old_values=user_data,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete user',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>/lock', methods=['POST'])
@require_admin()
def lock_user(target_user_id):
    """
    Lock user account

    POST /api/admin/users/<user_id>/lock

    Response:
    {
        "success": true,
        "message": "User account locked successfully"
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        # Prevent admin from locking themselves
        if admin_id == target_user_id:
            return jsonify({
                'success': False,
                'error': 'Cannot lock your own account'
            }), 403

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if user.account_locked:
            return jsonify({
                'success': False,
                'error': 'Account is already locked'
            }), 400

        # Lock account
        user.account_locked = True
        user.account_locked_at = datetime.utcnow()
        db.session.commit()

        # Revoke all active sessions
        active_sessions = Session.query.filter_by(
            user_id=user.id,
            revoked=False
        ).all()

        for session in active_sessions:
            session.revoke()

        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='admin_lock_user',
            user=admin,
            resource_type='user',
            resource_id=user.id,
            new_values={'account_locked': True},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'User account locked successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Lock user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to lock user',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>/unlock', methods=['POST'])
@require_admin()
def unlock_user(target_user_id):
    """
    Unlock user account

    POST /api/admin/users/<user_id>/unlock

    Response:
    {
        "success": true,
        "message": "User account unlocked successfully"
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if not user.account_locked:
            return jsonify({
                'success': False,
                'error': 'Account is not locked'
            }), 400

        # Unlock account and reset failed login attempts
        user.account_locked = False
        user.account_locked_at = None
        user.failed_login_attempts = 0
        user.last_failed_login = None
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='admin_unlock_user',
            user=admin,
            resource_type='user',
            resource_id=user.id,
            new_values={'account_locked': False},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'User account unlocked successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Unlock user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to unlock user',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>/verify-email', methods=['POST'])
@require_admin()
def verify_email(target_user_id):
    """
    Manually verify user email

    POST /api/admin/users/<user_id>/verify-email

    Response:
    {
        "success": true,
        "message": "Email verified successfully"
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        if user.email_verified:
            return jsonify({
                'success': False,
                'error': 'Email is already verified'
            }), 400

        # Verify email
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_expires = None
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='admin_verify_email',
            user=admin,
            resource_type='user',
            resource_id=user.id,
            new_values={'email_verified': True},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Email verified successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Verify email error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to verify email',
            'message': str(e)
        }), 500


@admin_bp.route('/admin/users/<int:target_user_id>/reset-password', methods=['POST'])
@require_admin()
def force_password_reset(target_user_id):
    """
    Force password reset (send reset email)

    POST /api/admin/users/<user_id>/reset-password

    Response:
    {
        "success": true,
        "message": "Password reset email sent successfully"
    }
    """
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Request password reset
        AuthService.request_password_reset(
            email=user.email,
            ip_address=request.remote_addr
        )

        # Log the action
        AuditLog.log_action(
            action='admin_force_password_reset',
            user=admin,
            resource_type='user',
            resource_id=user.id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Password reset email sent successfully'
        }), 200

    except Exception as e:
        logger.error(f"Force password reset error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send password reset email',
            'message': str(e)
        }), 500


# ==========================================
# Statistics Endpoints
# ==========================================

@admin_bp.route('/admin/stats', methods=['GET'])
@require_admin()
def get_statistics():
    """
    Get user statistics

    GET /api/admin/stats

    Response:
    {
        "success": true,
        "stats": {
            "total_users": 150,
            "verified_users": 120,
            "locked_users": 5,
            "new_users_today": 3,
            "new_users_this_week": 15,
            "new_users_this_month": 45,
            "active_sessions": 75,
            "total_logins_today": 230,
            "failed_logins_today": 12
        }
    }
    """
    try:
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Total users
        total_users = User.query.count()

        # Verified users
        verified_users = User.query.filter_by(email_verified=True).count()

        # Locked users
        locked_users = User.query.filter_by(account_locked=True).count()

        # New users today
        new_users_today = User.query.filter(User.created_at >= today).count()

        # New users this week
        new_users_this_week = User.query.filter(User.created_at >= week_ago).count()

        # New users this month
        new_users_this_month = User.query.filter(User.created_at >= month_ago).count()

        # Active sessions
        active_sessions = Session.query.filter_by(revoked=False).count()

        # Total logins today
        total_logins_today = AuditLog.query.filter(
            AuditLog.action == 'login',
            AuditLog.created_at >= today
        ).count()

        # Failed logins today
        failed_logins_today = AuditLog.query.filter(
            AuditLog.action == 'failed_login',
            AuditLog.created_at >= today
        ).count()

        stats = {
            'total_users': total_users,
            'verified_users': verified_users,
            'locked_users': locked_users,
            'new_users_today': new_users_today,
            'new_users_this_week': new_users_this_week,
            'new_users_this_month': new_users_this_month,
            'active_sessions': active_sessions,
            'total_logins_today': total_logins_today,
            'failed_logins_today': failed_logins_today
        }

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get statistics',
            'message': str(e)
        }), 500


# ==========================================
# Audit Log Endpoints
# ==========================================

@admin_bp.route('/admin/audit-logs', methods=['GET'])
@require_admin()
def get_audit_logs():
    """
    Get audit logs with filtering

    GET /api/admin/audit-logs

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - user_id: Filter by user ID
    - action: Filter by action type
    - resource_type: Filter by resource type
    - start_date: Filter by start date (ISO format)
    - end_date: Filter by end date (ISO format)

    Response:
    {
        "success": true,
        "audit_logs": [...],
        "pagination": {...}
    }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Build query
        query = AuditLog.query

        # User filter
        if user_id:
            query = query.filter_by(user_id=user_id)

        # Action filter
        if action:
            query = query.filter_by(action=action)

        # Resource type filter
        if resource_type:
            query = query.filter_by(resource_type=resource_type)

        # Date range filter
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(AuditLog.created_at >= start)
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(AuditLog.created_at <= end)
            except ValueError:
                pass

        # Order by most recent first
        query = query.order_by(AuditLog.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Include user info in audit logs
        audit_logs = []
        for log in pagination.items:
            log_dict = log.to_dict()
            if log.user:
                log_dict['user'] = {
                    'id': log.user.id,
                    'email': log.user.email,
                    'username': log.user.username
                }
            audit_logs.append(log_dict)

        return jsonify({
            'success': True,
            'audit_logs': audit_logs,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        logger.error(f"Get audit logs error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get audit logs',
            'message': str(e)
        }), 500
