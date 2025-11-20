"""
Authentication API endpoints
Handles user registration, login, logout, password reset, and email verification
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt,
    create_access_token, create_refresh_token
)
from backend.services import AuthService
from backend.models import User, Session
from backend.extensions import db, limiter
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)


def get_client_ip():
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr


def get_user_agent():
    """Get user agent from request"""
    return request.headers.get('User-Agent', 'Unknown')


@auth_bp.route('/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """
    Register a new user

    POST /api/auth/register

    Request Body:
    {
        "email": "user@example.com",
        "username": "username",
        "password": "SecurePass123!",
        "full_name": "John Doe",  # optional
        "first_name": "John",      # optional
        "last_name": "Doe"         # optional
    }

    Response:
    {
        "success": true,
        "message": "Registration successful. Please check your email to verify your account.",
        "user": {...}
    }
    """
    try:
        data = request.get_json()

        # Required fields
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not email or not username or not password:
            return jsonify({
                'success': False,
                'error': 'Email, username, and password are required'
            }), 400

        # Optional fields
        full_name = data.get('full_name')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        # Register user
        user, error = AuthService.register_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name
        )

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Registration successful. Please check your email to verify your account.',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Registration failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """
    Login user and create session

    POST /api/auth/login

    Request Body:
    {
        "email": "user@example.com",  # or username
        "password": "SecurePass123!"
    }

    Response:
    {
        "success": true,
        "message": "Login successful",
        "user": {...},
        "access_token": "...",
        "refresh_token": "..."
    }
    """
    try:
        data = request.get_json()

        email_or_username = data.get('email') or data.get('username')
        password = data.get('password')

        if not email_or_username or not password:
            return jsonify({
                'success': False,
                'error': 'Email/username and password are required'
            }), 400

        # Authenticate user
        user, access_token, refresh_token, error = AuthService.login_user(
            email_or_username=email_or_username,
            password=password,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 401

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Login failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user and revoke session

    POST /api/auth/logout
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Logout successful"
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

        # Get session token from JWT
        jwt = get_jwt()
        session_token = jwt.get('jti')  # JWT ID

        # Logout user
        AuthService.logout_user(
            user=user,
            session_token=session_token,
            ip_address=get_client_ip()
        )

        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Logout failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token

    POST /api/auth/refresh
    Headers: Authorization: Bearer <refresh_token>

    Response:
    {
        "success": true,
        "access_token": "...",
        "refresh_token": "..."
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

        # Get old refresh token
        jwt = get_jwt()
        old_refresh_token = jwt.get('jti')

        # Refresh tokens
        access_token, refresh_token, error = AuthService.refresh_access_token(
            user=user,
            old_refresh_token=old_refresh_token
        )

        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 401

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Token refresh failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/verify-email', methods=['POST'])
def verify_email():
    """
    Verify user email with token

    POST /api/auth/verify-email

    Request Body:
    {
        "token": "verification_token"
    }

    Response:
    {
        "success": true,
        "message": "Email verified successfully"
    }
    """
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({
                'success': False,
                'error': 'Verification token is required'
            }), 400

        # Verify email
        success, error = AuthService.verify_email(token)

        if not success:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Email verified successfully. You can now log in.'
        }), 200

    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Email verification failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/resend-verification', methods=['POST'])
@limiter.limit("3 per minute")
def resend_verification():
    """
    Resend email verification

    POST /api/auth/resend-verification

    Request Body:
    {
        "email": "user@example.com"
    }

    Response:
    {
        "success": true,
        "message": "Verification email sent"
    }
    """
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400

        user = User.find_by_email(email)

        if not user:
            # Don't reveal if email exists
            return jsonify({
                'success': True,
                'message': 'If that email is registered, a verification email has been sent.'
            }), 200

        if user.email_verified:
            return jsonify({
                'success': False,
                'error': 'Email already verified'
            }), 400

        # Send verification email
        AuthService.send_verification_email(user)

        return jsonify({
            'success': True,
            'message': 'Verification email sent'
        }), 200

    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to send verification email',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    """
    Request password reset

    POST /api/auth/forgot-password

    Request Body:
    {
        "email": "user@example.com"
    }

    Response:
    {
        "success": true,
        "message": "If that email is registered, a password reset link has been sent."
    }
    """
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400

        # Request password reset
        AuthService.request_password_reset(
            email=email,
            ip_address=get_client_ip()
        )

        # Always return success to not reveal if email exists
        return jsonify({
            'success': True,
            'message': 'If that email is registered, a password reset link has been sent.'
        }), 200

    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Password reset request failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    """
    Reset password using token

    POST /api/auth/reset-password

    Request Body:
    {
        "token": "reset_token",
        "password": "NewSecurePass123!"
    }

    Response:
    {
        "success": true,
        "message": "Password reset successful. You can now log in with your new password."
    }
    """
    try:
        data = request.get_json()
        token = data.get('token')
        password = data.get('password')

        if not token or not password:
            return jsonify({
                'success': False,
                'error': 'Token and new password are required'
            }), 400

        # Reset password
        success, error = AuthService.reset_password(token, password)

        if not success:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Password reset successful. You can now log in with your new password.'
        }), 200

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Password reset failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password (requires old password)

    POST /api/auth/change-password
    Headers: Authorization: Bearer <access_token>

    Request Body:
    {
        "old_password": "OldPass123!",
        "new_password": "NewSecurePass123!"
    }

    Response:
    {
        "success": true,
        "message": "Password changed successfully"
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
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({
                'success': False,
                'error': 'Old password and new password are required'
            }), 400

        # Change password
        success, error = AuthService.change_password(user, old_password, new_password)

        if not success:
            return jsonify({
                'success': False,
                'error': error
            }), 400

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Password change failed',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user

    GET /api/auth/me
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
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

        return jsonify({
            'success': True,
            'user': user.to_dict(include_sensitive=True)
        }), 200

    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user',
            'message': str(e)
        }), 500


@auth_bp.route('/auth/check', methods=['GET'])
@jwt_required()
def check_auth():
    """
    Check if current token is valid

    GET /api/auth/check
    Headers: Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "authenticated": true,
        "user_id": 1
    }
    """
    try:
        user_id = get_jwt_identity()

        return jsonify({
            'success': True,
            'authenticated': True,
            'user_id': user_id
        }), 200

    except Exception as e:
        logger.error(f"Auth check error: {str(e)}")
        return jsonify({
            'success': False,
            'authenticated': False
        }), 401
