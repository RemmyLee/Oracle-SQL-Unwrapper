"""
Oracle connection model for storing database connection details
"""

from datetime import datetime
from cryptography.fernet import Fernet
from flask import current_app
from backend.extensions import db


class OracleConnection(db.Model):
    """Oracle database connection configuration"""

    __tablename__ = 'oracle_connections'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Connection metadata
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#205AA7')  # Hex color for UI

    # Connection details (encrypted password)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=1521)
    service_name = db.Column(db.String(100))
    sid = db.Column(db.String(100))
    username = db.Column(db.String(100), nullable=False)
    password_encrypted = db.Column(db.LargeBinary)

    # Connection options
    connection_type = db.Column(db.String(20), default='service_name')  # 'service_name', 'sid', 'tns'
    ssl_enabled = db.Column(db.Boolean, default=False)
    wallet_path = db.Column(db.String(255))

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_tested = db.Column(db.DateTime)
    last_test_success = db.Column(db.Boolean)
    is_active = db.Column(db.Boolean, default=True)

    # Oracle version detected
    oracle_version = db.Column(db.String(100))

    def set_password(self, password: str):
        """Encrypt and store password"""
        encryption_key = current_app.config.get('ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not configured")

        # Ensure key is properly formatted for Fernet
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        # Pad or truncate to 32 bytes, then base64 encode
        import base64
        key = base64.urlsafe_b64encode(encryption_key.ljust(32)[:32])

        cipher = Fernet(key)
        self.password_encrypted = cipher.encrypt(password.encode())

    def get_password(self) -> str:
        """Decrypt and return password"""
        if not self.password_encrypted:
            return None

        encryption_key = current_app.config.get('ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not configured")

        # Ensure key is properly formatted for Fernet
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        import base64
        key = base64.urlsafe_b64encode(encryption_key.ljust(32)[:32])

        cipher = Fernet(key)
        return cipher.decrypt(self.password_encrypted).decode()

    def get_connection_string(self) -> str:
        """Generate cx_Oracle connection string"""
        if self.connection_type == 'service_name':
            dsn = f"{self.host}:{self.port}/{self.service_name}"
        elif self.connection_type == 'sid':
            dsn = f"{self.host}:{self.port}/{self.sid}"
        else:
            dsn = f"{self.host}:{self.port}"

        return f"{self.username}/{self.get_password()}@{dsn}"

    def to_dict(self, include_password=False):
        """Convert to dictionary (exclude password by default)"""
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'host': self.host,
            'port': self.port,
            'service_name': self.service_name,
            'sid': self.sid,
            'username': self.username,
            'connection_type': self.connection_type,
            'ssl_enabled': self.ssl_enabled,
            'is_active': self.is_active,
            'oracle_version': self.oracle_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_tested': self.last_tested.isoformat() if self.last_tested else None,
            'last_test_success': self.last_test_success
        }

        if include_password:
            result['password'] = self.get_password()

        return result

    def __repr__(self):
        return f'<OracleConnection {self.name}>'
