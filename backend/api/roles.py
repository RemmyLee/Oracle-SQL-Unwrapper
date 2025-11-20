"""
RBAC (Role-Based Access Control) API endpoints
Handles roles, permissions, and user role assignments
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import User, Role, Permission, UserRole, RolePermission, AuditLog
from backend.extensions import db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create blueprint
roles_bp = Blueprint('roles', __name__)


def require_permission(permission_name):
    """Decorator to require specific permission"""
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

            # Check if user has permission
            if not user.has_permission(permission_name):
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions',
                    'required_permission': permission_name
                }), 403

            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


# ==========================================
# Role Management Endpoints
# ==========================================

@roles_bp.route('/roles', methods=['GET'])
@jwt_required()
def list_roles():
    """
    List all roles

    GET /api/roles

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - include_permissions: Include permissions in response (default: false)

    Response:
    {
        "success": true,
        "roles": [...]
    }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        include_permissions = request.args.get('include_permissions', 'false').lower() == 'true'

        # Query roles
        query = Role.query.order_by(Role.role_name)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        roles = [role.to_dict(include_permissions=include_permissions) for role in pagination.items]

        return jsonify({
            'success': True,
            'roles': roles,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        logger.error(f"List roles error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list roles',
            'message': str(e)
        }), 500


@roles_bp.route('/roles', methods=['POST'])
@require_permission('manage_roles')
def create_role():
    """
    Create new role

    POST /api/roles
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "role_name": "Editor",
        "description": "Can edit content",
        "is_system": false
    }

    Response:
    {
        "success": true,
        "message": "Role created successfully",
        "role": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()

        role_name = data.get('role_name')
        description = data.get('description')
        is_system = data.get('is_system', False)

        if not role_name:
            return jsonify({
                'success': False,
                'error': 'Role name is required'
            }), 400

        # Check if role already exists
        existing_role = Role.query.filter_by(role_name=role_name).first()
        if existing_role:
            return jsonify({
                'success': False,
                'error': 'Role already exists'
            }), 400

        # Create role
        role = Role(
            role_name=role_name,
            description=description,
            is_system=is_system
        )

        db.session.add(role)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='create',
            user=user,
            resource_type='role',
            resource_id=role.id,
            new_values=role.to_dict(),
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Role created successfully',
            'role': role.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create role',
            'message': str(e)
        }), 500


@roles_bp.route('/roles/<int:role_id>', methods=['GET'])
@jwt_required()
def get_role(role_id):
    """
    Get role details

    GET /api/roles/<role_id>

    Response:
    {
        "success": true,
        "role": {
            "id": 1,
            "role_name": "Admin",
            "description": "Administrator",
            "permissions": [...]
        }
    }
    """
    try:
        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        return jsonify({
            'success': True,
            'role': role.to_dict(include_permissions=True)
        }), 200

    except Exception as e:
        logger.error(f"Get role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get role',
            'message': str(e)
        }), 500


@roles_bp.route('/roles/<int:role_id>', methods=['PUT'])
@require_permission('manage_roles')
def update_role(role_id):
    """
    Update role

    PUT /api/roles/<role_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "role_name": "Editor",
        "description": "Can edit content"
    }

    Response:
    {
        "success": true,
        "message": "Role updated successfully",
        "role": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Prevent updating system roles
        if role.is_system:
            return jsonify({
                'success': False,
                'error': 'Cannot modify system roles'
            }), 403

        data = request.get_json()

        # Store old values for audit
        old_values = role.to_dict()

        # Update fields
        if 'role_name' in data:
            # Check if new name already exists
            existing_role = Role.query.filter_by(role_name=data['role_name']).first()
            if existing_role and existing_role.id != role.id:
                return jsonify({
                    'success': False,
                    'error': 'Role name already in use'
                }), 400

            role.role_name = data['role_name']

        if 'description' in data:
            role.description = data['description']

        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='update',
            user=user,
            resource_type='role',
            resource_id=role.id,
            old_values=old_values,
            new_values=role.to_dict(),
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Role updated successfully',
            'role': role.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update role',
            'message': str(e)
        }), 500


@roles_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@require_permission('manage_roles')
def delete_role(role_id):
    """
    Delete role

    DELETE /api/roles/<role_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Role deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Prevent deleting system roles
        if role.is_system:
            return jsonify({
                'success': False,
                'error': 'Cannot delete system roles'
            }), 403

        # Store role data for audit
        role_data = role.to_dict()

        db.session.delete(role)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='delete',
            user=user,
            resource_type='role',
            resource_id=role_id,
            old_values=role_data,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Role deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete role',
            'message': str(e)
        }), 500


# ==========================================
# Permission Management Endpoints
# ==========================================

@roles_bp.route('/permissions', methods=['GET'])
@jwt_required()
def list_permissions():
    """
    List all permissions

    GET /api/permissions

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50)
    - category: Filter by category

    Response:
    {
        "success": true,
        "permissions": [...]
    }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        category = request.args.get('category')

        # Query permissions
        query = Permission.query

        if category:
            query = query.filter_by(category=category)

        query = query.order_by(Permission.category, Permission.permission_name)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        permissions = [perm.to_dict() for perm in pagination.items]

        return jsonify({
            'success': True,
            'permissions': permissions,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        logger.error(f"List permissions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list permissions',
            'message': str(e)
        }), 500


@roles_bp.route('/permissions', methods=['POST'])
@require_permission('manage_permissions')
def create_permission():
    """
    Create new permission

    POST /api/permissions
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "permission_name": "edit_dashboards",
        "description": "Can edit dashboards",
        "category": "dashboards"
    }

    Response:
    {
        "success": true,
        "message": "Permission created successfully",
        "permission": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        data = request.get_json()

        permission_name = data.get('permission_name')
        description = data.get('description')
        category = data.get('category')

        if not permission_name:
            return jsonify({
                'success': False,
                'error': 'Permission name is required'
            }), 400

        # Check if permission already exists
        existing_perm = Permission.query.filter_by(permission_name=permission_name).first()
        if existing_perm:
            return jsonify({
                'success': False,
                'error': 'Permission already exists'
            }), 400

        # Create permission
        permission = Permission(
            permission_name=permission_name,
            description=description,
            category=category
        )

        db.session.add(permission)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='create',
            user=user,
            resource_type='permission',
            resource_id=permission.id,
            new_values=permission.to_dict(),
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Permission created successfully',
            'permission': permission.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create permission',
            'message': str(e)
        }), 500


@roles_bp.route('/permissions/<int:permission_id>', methods=['GET'])
@jwt_required()
def get_permission(permission_id):
    """
    Get permission details

    GET /api/permissions/<permission_id>

    Response:
    {
        "success": true,
        "permission": {...}
    }
    """
    try:
        permission = Permission.query.get(permission_id)

        if not permission:
            return jsonify({
                'success': False,
                'error': 'Permission not found'
            }), 404

        return jsonify({
            'success': True,
            'permission': permission.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Get permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get permission',
            'message': str(e)
        }), 500


@roles_bp.route('/permissions/<int:permission_id>', methods=['PUT'])
@require_permission('manage_permissions')
def update_permission(permission_id):
    """
    Update permission

    PUT /api/permissions/<permission_id>
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "permission_name": "edit_dashboards",
        "description": "Can edit dashboards",
        "category": "dashboards"
    }

    Response:
    {
        "success": true,
        "message": "Permission updated successfully",
        "permission": {...}
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        permission = Permission.query.get(permission_id)

        if not permission:
            return jsonify({
                'success': False,
                'error': 'Permission not found'
            }), 404

        data = request.get_json()

        # Store old values for audit
        old_values = permission.to_dict()

        # Update fields
        if 'permission_name' in data:
            # Check if new name already exists
            existing_perm = Permission.query.filter_by(permission_name=data['permission_name']).first()
            if existing_perm and existing_perm.id != permission.id:
                return jsonify({
                    'success': False,
                    'error': 'Permission name already in use'
                }), 400

            permission.permission_name = data['permission_name']

        if 'description' in data:
            permission.description = data['description']

        if 'category' in data:
            permission.category = data['category']

        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='update',
            user=user,
            resource_type='permission',
            resource_id=permission.id,
            old_values=old_values,
            new_values=permission.to_dict(),
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Permission updated successfully',
            'permission': permission.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update permission',
            'message': str(e)
        }), 500


@roles_bp.route('/permissions/<int:permission_id>', methods=['DELETE'])
@require_permission('manage_permissions')
def delete_permission(permission_id):
    """
    Delete permission

    DELETE /api/permissions/<permission_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Permission deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        permission = Permission.query.get(permission_id)

        if not permission:
            return jsonify({
                'success': False,
                'error': 'Permission not found'
            }), 404

        # Store permission data for audit
        perm_data = permission.to_dict()

        db.session.delete(permission)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='delete',
            user=user,
            resource_type='permission',
            resource_id=permission_id,
            old_values=perm_data,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Permission deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete permission',
            'message': str(e)
        }), 500


# ==========================================
# User Role Assignment Endpoints
# ==========================================

@roles_bp.route('/users/<int:target_user_id>/roles', methods=['GET'])
@jwt_required()
def get_user_roles(target_user_id):
    """
    Get user's roles

    GET /api/users/<user_id>/roles

    Response:
    {
        "success": true,
        "roles": [...]
    }
    """
    try:
        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        roles = user.get_roles()

        return jsonify({
            'success': True,
            'roles': [role.to_dict() for role in roles]
        }), 200

    except Exception as e:
        logger.error(f"Get user roles error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user roles',
            'message': str(e)
        }), 500


@roles_bp.route('/users/<int:target_user_id>/roles', methods=['POST'])
@require_permission('manage_users')
def assign_role_to_user(target_user_id):
    """
    Assign role to user

    POST /api/users/<user_id>/roles
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "role_id": 1,
        "expires_at": "2025-12-31T23:59:59Z"  # optional
    }

    Response:
    {
        "success": true,
        "message": "Role assigned successfully"
    }
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        data = request.get_json()
        role_id = data.get('role_id')
        expires_at = data.get('expires_at')

        if not role_id:
            return jsonify({
                'success': False,
                'error': 'Role ID is required'
            }), 400

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Check if user already has role
        existing = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': 'User already has this role'
            }), 400

        # Parse expiration date if provided
        expiration_date = None
        if expires_at:
            try:
                expiration_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid expiration date format'
                }), 400

        # Assign role
        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_by=current_user_id,
            expires_at=expiration_date
        )

        db.session.add(user_role)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='assign_role',
            user=current_user,
            resource_type='user_role',
            resource_id=user.id,
            new_values={
                'user_id': user.id,
                'role_id': role.id,
                'role_name': role.role_name,
                'expires_at': expires_at
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Role assigned successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Assign role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to assign role',
            'message': str(e)
        }), 500


@roles_bp.route('/users/<int:target_user_id>/roles/<int:role_id>', methods=['DELETE'])
@require_permission('manage_users')
def remove_role_from_user(target_user_id, role_id):
    """
    Remove role from user

    DELETE /api/users/<user_id>/roles/<role_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Role removed successfully"
    }
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        user = User.query.get(target_user_id)

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Find user role
        user_role = UserRole.query.filter_by(
            user_id=user.id,
            role_id=role.id
        ).first()

        if not user_role:
            return jsonify({
                'success': False,
                'error': 'User does not have this role'
            }), 404

        db.session.delete(user_role)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='remove_role',
            user=current_user,
            resource_type='user_role',
            resource_id=user.id,
            old_values={
                'user_id': user.id,
                'role_id': role.id,
                'role_name': role.role_name
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Role removed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Remove role error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to remove role',
            'message': str(e)
        }), 500


# ==========================================
# Role Permission Assignment Endpoints
# ==========================================

@roles_bp.route('/roles/<int:role_id>/permissions', methods=['GET'])
@jwt_required()
def get_role_permissions(role_id):
    """
    Get role's permissions

    GET /api/roles/<role_id>/permissions

    Response:
    {
        "success": true,
        "permissions": [...]
    }
    """
    try:
        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        permissions = role.get_permissions()

        return jsonify({
            'success': True,
            'permissions': [perm.to_dict() for perm in permissions]
        }), 200

    except Exception as e:
        logger.error(f"Get role permissions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get role permissions',
            'message': str(e)
        }), 500


@roles_bp.route('/roles/<int:role_id>/permissions', methods=['POST'])
@require_permission('manage_roles')
def assign_permission_to_role(role_id):
    """
    Assign permission to role

    POST /api/roles/<role_id>/permissions
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "permission_id": 1
    }

    Response:
    {
        "success": true,
        "message": "Permission assigned successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Prevent modifying system roles
        if role.is_system:
            return jsonify({
                'success': False,
                'error': 'Cannot modify system roles'
            }), 403

        data = request.get_json()
        permission_id = data.get('permission_id')

        if not permission_id:
            return jsonify({
                'success': False,
                'error': 'Permission ID is required'
            }), 400

        permission = Permission.query.get(permission_id)

        if not permission:
            return jsonify({
                'success': False,
                'error': 'Permission not found'
            }), 404

        # Check if role already has permission
        existing = RolePermission.query.filter_by(
            role_id=role.id,
            permission_id=permission.id
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': 'Role already has this permission'
            }), 400

        # Assign permission
        role_permission = RolePermission(
            role_id=role.id,
            permission_id=permission.id
        )

        db.session.add(role_permission)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='assign_permission',
            user=user,
            resource_type='role_permission',
            resource_id=role.id,
            new_values={
                'role_id': role.id,
                'role_name': role.role_name,
                'permission_id': permission.id,
                'permission_name': permission.permission_name
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Permission assigned successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Assign permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to assign permission',
            'message': str(e)
        }), 500


@roles_bp.route('/roles/<int:role_id>/permissions/<int:permission_id>', methods=['DELETE'])
@require_permission('manage_roles')
def remove_permission_from_role(role_id, permission_id):
    """
    Remove permission from role

    DELETE /api/roles/<role_id>/permissions/<permission_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Permission removed successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        role = Role.query.get(role_id)

        if not role:
            return jsonify({
                'success': False,
                'error': 'Role not found'
            }), 404

        # Prevent modifying system roles
        if role.is_system:
            return jsonify({
                'success': False,
                'error': 'Cannot modify system roles'
            }), 403

        permission = Permission.query.get(permission_id)

        if not permission:
            return jsonify({
                'success': False,
                'error': 'Permission not found'
            }), 404

        # Find role permission
        role_permission = RolePermission.query.filter_by(
            role_id=role.id,
            permission_id=permission.id
        ).first()

        if not role_permission:
            return jsonify({
                'success': False,
                'error': 'Role does not have this permission'
            }), 404

        db.session.delete(role_permission)
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='remove_permission',
            user=user,
            resource_type='role_permission',
            resource_id=role.id,
            old_values={
                'role_id': role.id,
                'role_name': role.role_name,
                'permission_id': permission.id,
                'permission_name': permission.permission_name
            },
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Permission removed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Remove permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to remove permission',
            'message': str(e)
        }), 500


# ==========================================
# Permission Checking Endpoints
# ==========================================

@roles_bp.route('/users/me/permissions', methods=['GET'])
@jwt_required()
def get_my_permissions():
    """
    Get current user's effective permissions

    GET /api/users/me/permissions

    Response:
    {
        "success": true,
        "permissions": [
            {
                "id": 1,
                "permission_name": "view_dashboards",
                "description": "Can view dashboards",
                "category": "dashboards"
            }
        ]
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

        permissions = user.get_all_permissions()

        return jsonify({
            'success': True,
            'permissions': [perm.to_dict() for perm in permissions]
        }), 200

    except Exception as e:
        logger.error(f"Get my permissions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get permissions',
            'message': str(e)
        }), 500


@roles_bp.route('/users/me/check-permission', methods=['POST'])
@jwt_required()
def check_my_permission():
    """
    Check if current user has specific permission

    POST /api/users/me/check-permission

    Request Body:
    {
        "permission": "view_dashboards"
    }

    Response:
    {
        "success": true,
        "has_permission": true
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
        permission_name = data.get('permission')

        if not permission_name:
            return jsonify({
                'success': False,
                'error': 'Permission name is required'
            }), 400

        has_permission = user.has_permission(permission_name)

        return jsonify({
            'success': True,
            'has_permission': has_permission
        }), 200

    except Exception as e:
        logger.error(f"Check permission error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to check permission',
            'message': str(e)
        }), 500
