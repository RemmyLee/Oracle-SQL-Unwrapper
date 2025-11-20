"""
Audit logging models
Comprehensive activity tracking for security and compliance
"""

from datetime import datetime
from backend.extensions import db


class AuditLog(db.Model):
    """
    Audit log model for tracking all user activities

    Features:
    - Action tracking (create, read, update, delete)
    - Resource tracking (what was accessed/modified)
    - User identification
    - IP address logging
    - Request details
    - Change tracking (before/after states)
    - Compliance support
    """

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # Action information
    action = db.Column(db.String(50), nullable=False, index=True)  # login, logout, create, update, delete, view, execute
    resource_type = db.Column(db.String(50), nullable=True, index=True)  # dashboard, query, connection, user, etc.
    resource_id = db.Column(db.Integer, nullable=True)
    resource_name = db.Column(db.String(200), nullable=True)

    # Request details
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = db.Column(db.String(500), nullable=True)

    # Change tracking (JSON format)
    old_values = db.Column(db.JSON, nullable=True)  # State before change
    new_values = db.Column(db.JSON, nullable=True)  # State after change
    details = db.Column(db.JSON, nullable=True)  # Additional context

    # Result
    status = db.Column(db.String(20), default='success', nullable=False)  # success, failure, error
    error_message = db.Column(db.Text, nullable=True)

    # Session tracking
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship('User', back_populates='audit_logs', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog {self.action} {self.resource_type}:{self.resource_id}>'

    @staticmethod
    def log_action(action, user=None, resource_type=None, resource_id=None,
                   resource_name=None, ip_address=None, user_agent=None,
                   request_method=None, request_path=None, old_values=None,
                   new_values=None, details=None, status='success', error_message=None,
                   session_id=None):
        """
        Create audit log entry

        Args:
            action: Action performed (e.g., 'login', 'create', 'update')
            user: User object or user_id
            resource_type: Type of resource (e.g., 'dashboard', 'query')
            resource_id: ID of the resource
            resource_name: Name of the resource
            ip_address: Client IP address
            user_agent: User agent string
            request_method: HTTP method
            request_path: Request URL path
            old_values: State before change (dict)
            new_values: State after change (dict)
            details: Additional context (dict)
            status: success, failure, or error
            error_message: Error message if status is not success
            session_id: Session ID

        Returns:
            AuditLog object
        """
        user_id = user.id if hasattr(user, 'id') else user

        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            old_values=old_values,
            new_values=new_values,
            details=details,
            status=status,
            error_message=error_message,
            session_id=session_id
        )

        db.session.add(log)
        return log

    @staticmethod
    def log_login(user, ip_address=None, user_agent=None, status='success', error_message=None):
        """Log user login attempt"""
        return AuditLog.log_action(
            action='login',
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )

    @staticmethod
    def log_logout(user, ip_address=None):
        """Log user logout"""
        return AuditLog.log_action(
            action='logout',
            user=user,
            ip_address=ip_address
        )

    @staticmethod
    def log_create(user, resource_type, resource_id, resource_name=None, new_values=None,
                   ip_address=None, request_path=None):
        """Log resource creation"""
        return AuditLog.log_action(
            action='create',
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            new_values=new_values,
            ip_address=ip_address,
            request_method='POST',
            request_path=request_path
        )

    @staticmethod
    def log_update(user, resource_type, resource_id, resource_name=None,
                   old_values=None, new_values=None, ip_address=None, request_path=None):
        """Log resource update"""
        return AuditLog.log_action(
            action='update',
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            request_method='PUT',
            request_path=request_path
        )

    @staticmethod
    def log_delete(user, resource_type, resource_id, resource_name=None,
                   old_values=None, ip_address=None, request_path=None):
        """Log resource deletion"""
        return AuditLog.log_action(
            action='delete',
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            old_values=old_values,
            ip_address=ip_address,
            request_method='DELETE',
            request_path=request_path
        )

    @staticmethod
    def log_view(user, resource_type, resource_id, resource_name=None,
                 ip_address=None, request_path=None):
        """Log resource view/access"""
        return AuditLog.log_action(
            action='view',
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            request_method='GET',
            request_path=request_path
        )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'ip_address': self.ip_address,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'details': self.details,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def get_user_activity(user_id, limit=100, offset=0):
        """Get audit logs for specific user"""
        return AuditLog.query.filter_by(user_id=user_id)\
            .order_by(AuditLog.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()

    @staticmethod
    def get_resource_history(resource_type, resource_id, limit=100):
        """Get audit logs for specific resource"""
        return AuditLog.query.filter_by(
            resource_type=resource_type,
            resource_id=resource_id
        ).order_by(AuditLog.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def search_logs(action=None, resource_type=None, user_id=None,
                    start_date=None, end_date=None, status=None,
                    limit=100, offset=0):
        """Search audit logs with filters"""
        query = AuditLog.query

        if action:
            query = query.filter_by(action=action)
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(AuditLog.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()
