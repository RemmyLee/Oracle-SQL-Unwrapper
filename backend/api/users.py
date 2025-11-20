"""
User Profile Management API endpoints
Handles user profile, avatar, sessions, and activity
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from backend.models import User, Session, AuditLog
from backend.extensions import db
from werkzeug.utils import secure_filename
import logging
import os

logger = logging.getLogger(__name__)

# Create blueprint
users_bp = Blueprint('users', __name__)

# Allowed file extensions for avatars
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@users_bp.route('/users/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile

    GET /api/users/profile
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "username": "username",
            "full_name": "John Doe",
            "avatar_url": "/uploads/avatars/1.jpg",
            "email_verified": true,
            "created_at": "2025-01-15T10:30:00Z",
            "last_login": "2025-01-20T08:15:00Z"
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

        return jsonify({
            'success': True,
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get profile',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update current user profile

    PUT /api/users/profile
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "full_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "email": "newemail@example.com"  # Will require re-verification
    }

    Response:
    {
        "success": true,
        "message": "Profile updated successfully",
        "user": {...}
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

        # Store old values for audit
        old_values = {
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        }

        # Update allowed fields
        if 'full_name' in data:
            user.full_name = data['full_name']

        if 'first_name' in data:
            user.first_name = data['first_name']

        if 'last_name' in data:
            user.last_name = data['last_name']

        # Email change requires re-verification
        if 'email' in data and data['email'] != user.email:
            # Check if email already exists
            existing_user = User.find_by_email(data['email'])
            if existing_user and existing_user.id != user.id:
                return jsonify({
                    'success': False,
                    'error': 'Email already in use'
                }), 400

            user.email = data['email']
            user.email_verified = False

            # Generate new verification token
            from backend.services import AuthService
            user.generate_email_verification_token()
            db.session.commit()

            # Send verification email
            AuthService.send_verification_email(user)

        # Store new values for audit
        new_values = {
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        }

        db.session.commit()

        # Log the update
        AuditLog.log_action(
            action='update',
            user=user,
            resource_type='user_profile',
            resource_id=user.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update profile error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update profile',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """
    Upload user avatar

    POST /api/users/profile/avatar
    Headers: Authorization: Bearer <access_token>
    Content-Type: multipart/form-data

    Form Data:
    - avatar: file (png, jpg, jpeg, gif - max 5MB)

    Response:
    {
        "success": true,
        "message": "Avatar uploaded successfully",
        "avatar_url": "/uploads/avatars/1.jpg"
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

        # Check if file is present
        if 'avatar' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['avatar']

        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_AVATAR_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size is {MAX_AVATAR_SIZE / (1024*1024)}MB'
            }), 400

        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif'
            }), 400

        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)

        # Generate secure filename
        extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{user.id}.{extension}"
        filepath = os.path.join(upload_dir, filename)

        # Delete old avatar if exists
        if user.avatar_url:
            old_filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                user.avatar_url.lstrip('/')
            )
            if os.path.exists(old_filepath):
                os.remove(old_filepath)

        # Save file
        file.save(filepath)

        # Update user avatar_url
        user.avatar_url = f"/uploads/avatars/{filename}"
        db.session.commit()

        # Log the upload
        AuditLog.log_action(
            action='update',
            user=user,
            resource_type='user_avatar',
            resource_id=user.id,
            new_values={'avatar_url': user.avatar_url},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Avatar uploaded successfully',
            'avatar_url': user.avatar_url
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Upload avatar error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload avatar',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/avatar', methods=['DELETE'])
@jwt_required()
def delete_avatar():
    """
    Delete user avatar

    DELETE /api/users/profile/avatar
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Avatar deleted successfully"
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

        if not user.avatar_url:
            return jsonify({
                'success': False,
                'error': 'No avatar to delete'
            }), 400

        # Delete file from filesystem
        filepath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            user.avatar_url.lstrip('/')
        )
        if os.path.exists(filepath):
            os.remove(filepath)

        # Update user
        old_avatar = user.avatar_url
        user.avatar_url = None
        db.session.commit()

        # Log the deletion
        AuditLog.log_action(
            action='delete',
            user=user,
            resource_type='user_avatar',
            resource_id=user.id,
            old_values={'avatar_url': old_avatar},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Avatar deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete avatar error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete avatar',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    """
    Get user's active sessions

    GET /api/users/profile/sessions
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "sessions": [
            {
                "id": 1,
                "device_type": "desktop",
                "browser": "Chrome",
                "operating_system": "Windows",
                "ip_address": "192.168.1.1",
                "created_at": "2025-01-20T10:00:00Z",
                "last_activity": "2025-01-20T15:30:00Z",
                "is_current": true
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

        # Get current session token
        jwt = get_jwt()
        current_session_token = jwt.get('jti')

        # Get all active sessions
        sessions = Session.query.filter_by(
            user_id=user.id,
            revoked=False
        ).order_by(Session.last_activity.desc()).all()

        sessions_data = []
        for session in sessions:
            session_dict = session.to_dict()
            session_dict['is_current'] = (session.session_token == current_session_token)
            sessions_data.append(session_dict)

        return jsonify({
            'success': True,
            'sessions': sessions_data
        }), 200

    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get sessions',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/sessions/<int:session_id>', methods=['DELETE'])
@jwt_required()
def revoke_session(session_id):
    """
    Revoke a specific session

    DELETE /api/users/profile/sessions/<session_id>
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Session revoked successfully"
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

        # Get the session
        session = Session.query.filter_by(
            id=session_id,
            user_id=user.id
        ).first()

        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Revoke the session
        session.revoke()
        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='revoke_session',
            user=user,
            resource_type='session',
            resource_id=session.id,
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'Session revoked successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Revoke session error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to revoke session',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/sessions', methods=['DELETE'])
@jwt_required()
def revoke_all_sessions():
    """
    Revoke all sessions except current one

    DELETE /api/users/profile/sessions
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "All other sessions revoked successfully",
        "revoked_count": 3
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

        # Get current session token
        jwt = get_jwt()
        current_session_token = jwt.get('jti')

        # Get all other active sessions
        other_sessions = Session.query.filter(
            Session.user_id == user.id,
            Session.revoked == False,
            Session.session_token != current_session_token
        ).all()

        revoked_count = len(other_sessions)

        # Revoke all other sessions
        for session in other_sessions:
            session.revoke()

        db.session.commit()

        # Log the action
        AuditLog.log_action(
            action='revoke_all_sessions',
            user=user,
            resource_type='session',
            new_values={'revoked_count': revoked_count},
            ip_address=request.remote_addr
        )

        return jsonify({
            'success': True,
            'message': 'All other sessions revoked successfully',
            'revoked_count': revoked_count
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Revoke all sessions error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to revoke sessions',
            'message': str(e)
        }), 500


@users_bp.route('/users/profile/activity', methods=['GET'])
@jwt_required()
def get_activity():
    """
    Get user activity log

    GET /api/users/profile/activity
    Headers: Authorization: Bearer <access_token>

    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    - action: Filter by action type (login, update, delete, etc.)

    Response:
    {
        "success": true,
        "activity": [
            {
                "id": 1,
                "action": "login",
                "resource_type": "session",
                "ip_address": "192.168.1.1",
                "created_at": "2025-01-20T10:00:00Z",
                "details": {...}
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 50,
            "total": 150,
            "pages": 3
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

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        action_filter = request.args.get('action')

        # Build query
        query = AuditLog.query.filter_by(user_id=user.id)

        if action_filter:
            query = query.filter_by(action=action_filter)

        # Order by most recent first
        query = query.order_by(AuditLog.created_at.desc())

        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        activity = [log.to_dict() for log in pagination.items]

        return jsonify({
            'success': True,
            'activity': activity,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200

    except Exception as e:
        logger.error(f"Get activity error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get activity',
            'message': str(e)
        }), 500
