"""
User model for authentication and authorization
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db


class User(UserMixin, db.Model):
    """User account model"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile
    full_name = db.Column(db.String(200))
    avatar_url = db.Column(db.String(255))

    # Settings
    preferences = db.Column(db.JSON, default={})
    theme = db.Column(db.String(20), default='dark')
    default_connection_id = db.Column(db.Integer, db.ForeignKey('oracle_connections.id'))

    # Role-based access
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'viewer'
    is_active = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    connections = db.relationship('OracleConnection', backref='owner', lazy='dynamic',
                                 foreign_keys='OracleConnection.user_id')
    query_history = db.relationship('QueryHistory', backref='user', lazy='dynamic')
    saved_queries = db.relationship('SavedQuery', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'theme': self.theme,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    def __repr__(self):
        return f'<User {self.username}>'
