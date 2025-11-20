"""
Role-Based Access Control (RBAC) models
Implements comprehensive permission system for dashboard access control
"""

from datetime import datetime
from backend.extensions import db


class Role(db.Model):
    """
    Role model for RBAC system

    Roles group permissions and can be assigned to users.
    Examples: Admin, Developer, Viewer, Dashboard Creator, etc.
    """

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # System roles cannot be deleted or modified by users
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    # Role status
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user_roles = db.relationship('UserRole', back_populates='role', cascade='all, delete-orphan', lazy='dynamic')
    permissions = db.relationship('RolePermission', back_populates='role', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.role_name}>'

    def has_permission(self, permission_name):
        """Check if role has specific permission"""
        return any(rp.permission.permission_name == permission_name for rp in self.permissions)

    def get_permissions(self):
        """Get list of permission names"""
        return [rp.permission.permission_name for rp in self.permissions]

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'role_name': self.role_name,
            'display_name': self.display_name,
            'description': self.description,
            'is_system': self.is_system,
            'is_active': self.is_active,
            'permissions': self.get_permissions(),
            'user_count': self.user_roles.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def find_by_name(role_name):
        """Find role by name"""
        return Role.query.filter_by(role_name=role_name).first()


class Permission(db.Model):
    """
    Permission model for granular access control

    Permissions define specific actions that can be performed.
    Examples: dashboard.create, dashboard.edit, query.execute, etc.
    """

    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    permission_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Permission category for organization
    category = db.Column(db.String(50), nullable=True, index=True)

    # System permissions cannot be deleted
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    roles = db.relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Permission {self.permission_name}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'permission_name': self.permission_name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def find_by_name(permission_name):
        """Find permission by name"""
        return Permission.query.filter_by(permission_name=permission_name).first()


class UserRole(db.Model):
    """
    Association table for User-Role many-to-many relationship
    Tracks which roles are assigned to which users
    """

    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)

    # Track who granted the role and when
    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Optional expiration date for temporary access
    expires_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='user_roles', foreign_keys=[user_id])
    role = db.relationship('Role', back_populates='user_roles')
    granter = db.relationship('User', foreign_keys=[granted_by])

    # Unique constraint: user can have each role only once
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )

    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'

    def is_expired(self):
        """Check if role assignment has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'role_name': self.role.role_name,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'granted_by': self.granted_by,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }


class RolePermission(db.Model):
    """
    Association table for Role-Permission many-to-many relationship
    Defines which permissions belong to which roles
    """

    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)

    # Track when permission was added to role
    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    role = db.relationship('Role', back_populates='permissions')
    permission = db.relationship('Permission', back_populates='roles')

    # Unique constraint: role can have each permission only once
    __table_args__ = (
        db.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    def __repr__(self):
        return f'<RolePermission role_id={self.role_id} permission_id={self.permission_id}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'role_id': self.role_id,
            'permission_id': self.permission_id,
            'permission_name': self.permission.permission_name,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None
        }
