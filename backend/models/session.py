"""
Session management models
Tracks active user sessions for security and audit purposes
"""

from datetime import datetime, timedelta
from backend.extensions import db
import secrets


class Session(db.Model):
    """
    User session model for tracking active sessions

    Features:
    - JWT token storage
    - Refresh token support
    - Device tracking
    - IP address logging
    - Session expiration
    - Manual revocation
    """

    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Session identifiers
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=True, index=True)

    # Session metadata
    device_name = db.Column(db.String(100), nullable=True)
    device_type = db.Column(db.String(50), nullable=True)  # desktop, mobile, tablet
    browser = db.Column(db.String(100), nullable=True)
    operating_system = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    # Location tracking
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    country = db.Column(db.String(2), nullable=True)  # ISO country code
    city = db.Column(db.String(100), nullable=True)

    # Session status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='sessions')

    def __repr__(self):
        return f'<Session {self.session_token[:8]}... user_id={self.user_id}>'

    @staticmethod
    def create_session(user, ip_address=None, user_agent=None, expires_in=86400):
        """
        Create new session for user

        Args:
            user: User object
            ip_address: Client IP address
            user_agent: User agent string
            expires_in: Session duration in seconds (default 24 hours)

        Returns:
            Session object
        """
        session = Session(
            user_id=user.id,
            session_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
        )

        # Parse user agent for device info
        if user_agent:
            session._parse_user_agent(user_agent)

        return session

    def _parse_user_agent(self, user_agent):
        """Parse user agent string for device information"""
        # Basic user agent parsing (can be enhanced with user-agents library)
        user_agent_lower = user_agent.lower()

        # Detect device type
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            self.device_type = 'mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            self.device_type = 'tablet'
        else:
            self.device_type = 'desktop'

        # Detect browser
        if 'chrome' in user_agent_lower:
            self.browser = 'Chrome'
        elif 'firefox' in user_agent_lower:
            self.browser = 'Firefox'
        elif 'safari' in user_agent_lower:
            self.browser = 'Safari'
        elif 'edge' in user_agent_lower:
            self.browser = 'Edge'
        else:
            self.browser = 'Unknown'

        # Detect OS
        if 'windows' in user_agent_lower:
            self.operating_system = 'Windows'
        elif 'mac' in user_agent_lower or 'darwin' in user_agent_lower:
            self.operating_system = 'macOS'
        elif 'linux' in user_agent_lower:
            self.operating_system = 'Linux'
        elif 'android' in user_agent_lower:
            self.operating_system = 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            self.operating_system = 'iOS'
        else:
            self.operating_system = 'Unknown'

    def is_expired(self):
        """Check if session has expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """Check if session is valid (active, not revoked, not expired)"""
        return self.is_active and not self.is_revoked and not self.is_expired()

    def revoke(self):
        """Revoke session"""
        self.is_active = False
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()

    def refresh(self, expires_in=86400):
        """
        Refresh session expiration

        Args:
            expires_in: New session duration in seconds (default 24 hours)
        """
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.refresh_token = secrets.token_urlsafe(32)
        self.last_activity = datetime.utcnow()

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'browser': self.browser,
            'operating_system': self.operating_system,
            'ip_address': self.ip_address,
            'country': self.country,
            'city': self.city,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_current': False  # Will be set by API
        }

    @staticmethod
    def find_by_token(session_token):
        """Find session by token"""
        return Session.query.filter_by(session_token=session_token, is_active=True).first()

    @staticmethod
    def find_by_refresh_token(refresh_token):
        """Find session by refresh token"""
        return Session.query.filter_by(refresh_token=refresh_token, is_active=True).first()

    @staticmethod
    def cleanup_expired_sessions():
        """Remove expired sessions from database"""
        expired = Session.query.filter(
            Session.expires_at < datetime.utcnow(),
            Session.is_active == True
        ).all()

        for session in expired:
            session.is_active = False

        return len(expired)
