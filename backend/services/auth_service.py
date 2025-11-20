"""
Authentication Service
Handles all authentication-related business logic
"""

from datetime import datetime, timedelta
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from backend.extensions import db, mail
from backend.models import User, Session, AuditLog
from flask_mail import Message
import re


class AuthService:
    """
    Authentication service for user management

    Handles:
    - User registration
    - Login/logout
    - Email verification
    - Password reset
    - Token generation
    - Session management
    """

    @staticmethod
    def validate_password(password):
        """
        Validate password strength based on configured requirements

        Returns:
            tuple: (is_valid, error_message)
        """
        min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        require_uppercase = current_app.config.get('PASSWORD_REQUIRE_UPPERCASE', True)
        require_lowercase = current_app.config.get('PASSWORD_REQUIRE_LOWERCASE', True)
        require_digits = current_app.config.get('PASSWORD_REQUIRE_DIGITS', True)
        require_special = current_app.config.get('PASSWORD_REQUIRE_SPECIAL', True)

        if len(password) < min_length:
            return False, f'Password must be at least {min_length} characters long'

        if require_uppercase and not re.search(r'[A-Z]', password):
            return False, 'Password must contain at least one uppercase letter'

        if require_lowercase and not re.search(r'[a-z]', password):
            return False, 'Password must contain at least one lowercase letter'

        if require_digits and not re.search(r'\d', password):
            return False, 'Password must contain at least one digit'

        if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, 'Password must contain at least one special character'

        return True, None

    @staticmethod
    def validate_email(email):
        """
        Validate email format

        Returns:
            tuple: (is_valid, error_message)
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_regex, email):
            return False, 'Invalid email format'

        return True, None

    @staticmethod
    def register_user(email, username, password, full_name=None, **kwargs):
        """
        Register a new user

        Args:
            email: User email
            username: Username
            password: Password
            full_name: Full name (optional)
            **kwargs: Additional user fields

        Returns:
            tuple: (user, error_message)
        """
        # Validate email
        is_valid, error = AuthService.validate_email(email)
        if not is_valid:
            return None, error

        # Validate password
        is_valid, error = AuthService.validate_password(password)
        if not is_valid:
            return None, error

        # Check if email already exists
        if User.find_by_email(email):
            return None, 'Email already registered'

        # Check if username already exists
        if User.find_by_username(username):
            return None, 'Username already taken'

        # Create user
        user = User(
            email=email.lower(),
            username=username,
            full_name=full_name
        )

        # Set password
        user.set_password(password)

        # Set additional fields
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        # Generate email verification token if required
        if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True):
            user.generate_email_verification_token()

        # Add to database
        db.session.add(user)
        db.session.commit()

        # Send verification email
        if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True):
            AuthService.send_verification_email(user)

        # Log registration
        AuditLog.log_action(
            action='register',
            user=user,
            details={'email': email, 'username': username}
        )
        db.session.commit()

        return user, None

    @staticmethod
    def login_user(email_or_username, password, ip_address=None, user_agent=None):
        """
        Authenticate user and create session

        Args:
            email_or_username: Email or username
            password: Password
            ip_address: Client IP address
            user_agent: User agent string

        Returns:
            tuple: (user, access_token, refresh_token, error_message)
        """
        # Find user by email or username
        user = User.find_by_email(email_or_username)
        if not user:
            user = User.find_by_username(email_or_username)

        if not user:
            return None, None, None, 'Invalid email/username or password'

        # Check if account is active
        if not user.is_active:
            return None, None, None, 'Account is deactivated'

        # Check if account is locked
        if user.account_locked:
            return None, None, None, 'Account is locked due to too many failed login attempts'

        # Verify password
        if not user.check_password(password):
            user.record_failed_login()
            db.session.commit()

            # Log failed login
            AuditLog.log_login(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                status='failure',
                error_message='Invalid password'
            )
            db.session.commit()

            return None, None, None, 'Invalid email/username or password'

        # Check if email verification is required
        if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True) and not user.email_verified:
            return None, None, None, 'Please verify your email before logging in'

        # Check if password change is required
        if user.must_change_password:
            return None, None, None, 'Password change required. Please reset your password.'

        # Record successful login
        user.record_login()
        db.session.commit()

        # Create JWT tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        # Create session
        session = Session.create_session(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session.session_token = access_token
        session.refresh_token = refresh_token

        db.session.add(session)
        db.session.commit()

        # Log successful login
        AuditLog.log_login(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            status='success'
        )
        db.session.commit()

        return user, access_token, refresh_token, None

    @staticmethod
    def logout_user(user, session_token=None, ip_address=None):
        """
        Logout user and revoke session

        Args:
            user: User object
            session_token: Session token to revoke
            ip_address: Client IP address
        """
        # Revoke session if token provided
        if session_token:
            session = Session.find_by_token(session_token)
            if session and session.user_id == user.id:
                session.revoke()
                db.session.commit()

        # Log logout
        AuditLog.log_logout(user=user, ip_address=ip_address)
        db.session.commit()

    @staticmethod
    def refresh_access_token(user, old_refresh_token):
        """
        Refresh access token using refresh token

        Args:
            user: User object
            old_refresh_token: Current refresh token

        Returns:
            tuple: (access_token, refresh_token, error_message)
        """
        # Find session by refresh token
        session = Session.find_by_refresh_token(old_refresh_token)

        if not session or session.user_id != user.id:
            return None, None, 'Invalid refresh token'

        if not session.is_valid():
            return None, None, 'Session expired or revoked'

        # Create new tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)

        # Update session
        session.session_token = access_token
        session.refresh_token = refresh_token
        session.update_activity()

        db.session.commit()

        return access_token, refresh_token, None

    @staticmethod
    def send_verification_email(user):
        """
        Send email verification email

        Args:
            user: User object
        """
        if not user.email_verification_token:
            user.generate_email_verification_token()
            db.session.commit()

        # Create verification URL
        # TODO: Get base URL from config
        verification_url = f"http://localhost:3117/auth/verify-email?token={user.email_verification_token}"

        # Send email
        msg = Message(
            subject='Verify your email - PL/SQL Workbench',
            recipients=[user.email],
            html=f"""
            <h2>Welcome to PL/SQL Workbench!</h2>
            <p>Hi {user.full_name or user.username},</p>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}">Verify Email</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <br>
            <p>Best regards,<br>PL/SQL Workbench Team</p>
            """
        )

        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {str(e)}")

    @staticmethod
    def verify_email(token):
        """
        Verify user email with token

        Args:
            token: Verification token

        Returns:
            tuple: (success, error_message)
        """
        # Find user by verification token
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            return False, 'Invalid verification token'

        # Verify email
        if user.verify_email(token):
            db.session.commit()

            # Log email verification
            AuditLog.log_action(
                action='verify_email',
                user=user,
                details={'email': user.email}
            )
            db.session.commit()

            return True, None
        else:
            return False, 'Verification token expired'

    @staticmethod
    def request_password_reset(email, ip_address=None):
        """
        Request password reset and send email

        Args:
            email: User email
            ip_address: Client IP address

        Returns:
            tuple: (success, error_message)
        """
        user = User.find_by_email(email)

        if not user:
            # Don't reveal if email exists
            return True, None

        # Generate reset token
        token = user.generate_password_reset_token()
        db.session.commit()

        # Create reset URL
        reset_url = f"http://localhost:3117/auth/reset-password?token={token}"

        # Send email
        msg = Message(
            subject='Password Reset - PL/SQL Workbench',
            recipients=[user.email],
            html=f"""
            <h2>Password Reset Request</h2>
            <p>Hi {user.full_name or user.username},</p>
            <p>We received a request to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request a password reset, please ignore this email.</p>
            <br>
            <p>Best regards,<br>PL/SQL Workbench Team</p>
            """
        )

        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send password reset email: {str(e)}")

        # Log password reset request
        AuditLog.log_action(
            action='request_password_reset',
            user=user,
            ip_address=ip_address,
            details={'email': email}
        )
        db.session.commit()

        return True, None

    @staticmethod
    def reset_password(token, new_password):
        """
        Reset password using token

        Args:
            token: Reset token
            new_password: New password

        Returns:
            tuple: (success, error_message)
        """
        # Validate new password
        is_valid, error = AuthService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Find user by reset token
        user = User.query.filter_by(password_reset_token=token).first()

        if not user:
            return False, 'Invalid reset token'

        # Reset password
        if user.reset_password(token, new_password):
            db.session.commit()

            # Log password reset
            AuditLog.log_action(
                action='password_reset',
                user=user,
                details={'method': 'token'}
            )
            db.session.commit()

            return True, None
        else:
            return False, 'Reset token expired'

    @staticmethod
    def change_password(user, old_password, new_password):
        """
        Change user password (requires old password)

        Args:
            user: User object
            old_password: Current password
            new_password: New password

        Returns:
            tuple: (success, error_message)
        """
        # Verify old password
        if not user.check_password(old_password):
            return False, 'Current password is incorrect'

        # Validate new password
        is_valid, error = AuthService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Check if new password is same as old
        if user.check_password(new_password):
            return False, 'New password must be different from current password'

        # Set new password
        user.set_password(new_password)
        db.session.commit()

        # Log password change
        AuditLog.log_action(
            action='password_change',
            user=user,
            details={'method': 'user_initiated'}
        )
        db.session.commit()

        return True, None

    @staticmethod
    def get_user_sessions(user):
        """
        Get all active sessions for user

        Args:
            user: User object

        Returns:
            list: List of active sessions
        """
        sessions = Session.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(Session.last_activity.desc()).all()

        return sessions

    @staticmethod
    def revoke_session(user, session_id):
        """
        Revoke a specific user session

        Args:
            user: User object
            session_id: Session ID to revoke

        Returns:
            tuple: (success, error_message)
        """
        session = Session.query.get(session_id)

        if not session or session.user_id != user.id:
            return False, 'Session not found'

        session.revoke()
        db.session.commit()

        # Log session revocation
        AuditLog.log_action(
            action='revoke_session',
            user=user,
            details={'session_id': session_id}
        )
        db.session.commit()

        return True, None

    @staticmethod
    def revoke_all_sessions(user, except_current=None):
        """
        Revoke all user sessions except optionally the current one

        Args:
            user: User object
            except_current: Session ID to keep active

        Returns:
            int: Number of sessions revoked
        """
        query = Session.query.filter_by(
            user_id=user.id,
            is_active=True
        )

        if except_current:
            query = query.filter(Session.id != except_current)

        sessions = query.all()
        count = 0

        for session in sessions:
            session.revoke()
            count += 1

        db.session.commit()

        # Log sessions revocation
        AuditLog.log_action(
            action='revoke_all_sessions',
            user=user,
            details={'count': count, 'except_current': except_current}
        )
        db.session.commit()

        return count
