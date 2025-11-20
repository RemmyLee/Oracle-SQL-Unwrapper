"""Database models for application metadata"""

# Phase 1-3 models
from .user import User
from .connection import OracleConnection
from .query_history import QueryHistory, SavedQuery

# Phase 4 models (Authentication & RBAC)
from .role import Role, Permission, UserRole, RolePermission
from .session import Session
from .audit import AuditLog

# Phase 5+ models (Dashboard - stub for now)
from .dashboard import Dashboard

__all__ = [
    'User',
    'OracleConnection',
    'QueryHistory',
    'SavedQuery',
    'Role',
    'Permission',
    'UserRole',
    'RolePermission',
    'Session',
    'AuditLog',
    'Dashboard'
]
