"""
User model for authentication and authorization
Comprehensive user management for dashboard system (APEX-inspired)
"""

from datetime import datetime, timedelta
from flask_login import UserMixin
from backend.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import secrets


class User(UserMixin, db.Model):
    """
    User model with comprehensive authentication features

    Features:
    - Email/password authentication
    - Email verification
    - Password reset tokens
    - Account activation/deactivation
    - Profile management
    - Avatar support
    - Timezone and locale preferences
    - API key generation
    - Last login tracking
    - Role-based access control
    """

    __tablename__ = 'users'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Authentication
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile information
    full_name = db.Column(db.String(200), nullable=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # Contact information
    phone = db.Column(db.String(20), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    job_title = db.Column(db.String(100), nullable=True)

    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    account_locked = db.Column(db.Boolean, default=False, nullable=False)

    # Legacy role field (kept for backward compatibility with Phase 1-3)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'viewer'

    # Verification and reset tokens
    email_verification_token = db.Column(db.String(64), unique=True, nullable=True)
    email_verification_expires = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(64), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # API access
    api_key = db.Column(db.String(64), unique=True, nullable=True, index=True)
    api_key_created = db.Column(db.DateTime, nullable=True)

    # Preferences
    preferences = db.Column(db.JSON, default={})
    timezone = db.Column(db.String(50), default='UTC', nullable=False)
    locale = db.Column(db.String(10), default='en_US', nullable=False)
    theme = db.Column(db.String(20), default='dark', nullable=False)
    default_connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    # Security
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, nullable=True)

    # Relationships (existing - Phase 1-3)
    connections = db.relationship('OracleConnection', backref='owner', lazy='dynamic',
                                 foreign_keys='OracleConnection.user_id')
    query_history = db.relationship('QueryHistory', backref='user', lazy='dynamic')
    saved_queries = db.relationship('SavedQuery', backref='user', lazy='dynamic')

    # New relationships (Phase 4+)
    user_roles = db.relationship('UserRole', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    sessions = db.relationship('Session', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    owned_dashboards = db.relationship('Dashboard', back_populates='owner',
                                       foreign_keys='Dashboard.owner_id', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', back_populates='user',
                                foreign_keys='AuditLog.user_id', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.email}>'

    # Password methods
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()
        self.must_change_password = False

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    # Email verification
    def generate_email_verification_token(self, expires_in=86400):
        """Generate email verification token (default 24 hours)"""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_expires = datetime.utcnow() + timedelta(seconds=expires_in)
        return self.email_verification_token

    def verify_email(self, token):
        """Verify email with token"""
        if self.email_verification_token != token:
            return False

        if self.email_verification_expires < datetime.utcnow():
            return False

        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_expires = None
        return True

    # Password reset
    def generate_password_reset_token(self, expires_in=3600):
        """Generate password reset token (default 1 hour)"""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.utcnow() + timedelta(seconds=expires_in)
        return self.password_reset_token

    def verify_password_reset_token(self, token):
        """Verify password reset token"""
        if self.password_reset_token != token:
            return False

        if self.password_reset_expires < datetime.utcnow():
            return False

        return True

    def reset_password(self, token, new_password):
        """Reset password with token"""
        if not self.verify_password_reset_token(token):
            return False

        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_expires = None
        self.failed_login_attempts = 0
        self.account_locked = False
        return True

    # API key management
    def generate_api_key(self):
        """Generate new API key"""
        self.api_key = secrets.token_urlsafe(32)
        self.api_key_created = datetime.utcnow()
        return self.api_key

    def revoke_api_key(self):
        """Revoke API key"""
        self.api_key = None
        self.api_key_created = None

    # Login tracking
    def record_login(self):
        """Record successful login"""
        self.last_login = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.failed_login_attempts = 0
        self.last_failed_login = None

    def record_failed_login(self):
        """Record failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.utcnow()

        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.account_locked = True

    def unlock_account(self):
        """Unlock account"""
        self.account_locked = False
        self.failed_login_attempts = 0
        self.last_failed_login = None

    # Activity tracking
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    # Role checking (RBAC support)
    def has_role(self, role_name):
        """Check if user has specific role"""
        # Support both new RBAC system and legacy role field
        if hasattr(self, 'user_roles'):
            return any(ur.role.role_name == role_name for ur in self.user_roles)
        return self.role == role_name

    def has_permission(self, permission_name):
        """Check if user has specific permission"""
        # Superuser has all permissions
        if self.is_superuser:
            return True

        # Check through RBAC system
        if hasattr(self, 'user_roles'):
            for user_role in self.user_roles:
                if any(p.permission_name == permission_name for p in user_role.role.permissions):
                    return True

        return False

    def get_roles(self):
        """Get list of role names"""
        if hasattr(self, 'user_roles'):
            return [ur.role.role_name for ur in self.user_roles]
        return [self.role] if self.role else []

    def get_permissions(self):
        """Get list of all permissions"""
        if self.is_superuser:
            return ['*']  # All permissions

        permissions = set()
        if hasattr(self, 'user_roles'):
            for user_role in self.user_roles:
                for permission in user_role.role.permissions:
                    permissions.add(permission.permission_name)

        return list(permissions)

    # Serialization
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'user_id': self.id,  # Alias for consistency
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'phone': self.phone,
            'company': self.company,
            'job_title': self.job_title,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'email_verified': self.email_verified,
            'timezone': self.timezone,
            'locale': self.locale,
            'theme': self.theme,
            'role': self.role,  # Legacy
            'roles': self.get_roles(),  # New RBAC
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

        if include_sensitive:
            data.update({
                'account_locked': self.account_locked,
                'failed_login_attempts': self.failed_login_attempts,
                'must_change_password': self.must_change_password,
                'api_key': self.api_key,
                'last_activity': self.last_activity.isoformat() if self.last_activity else None,
                'permissions': self.get_permissions()
            })

        return data

    # Static methods
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        return User.query.filter_by(email=email.lower()).first()

    @staticmethod
    def find_by_username(username):
        """Find user by username"""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def find_by_api_key(api_key):
        """Find user by API key"""
        return User.query.filter_by(api_key=api_key, is_active=True).first()

    # Flask-Login methods
    def get_id(self):
        """Get user ID for Flask-Login"""
        return str(self.id)
