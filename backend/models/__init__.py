"""Database models for application metadata"""

# Phase 1-3 models
from .user import User
from .connection import OracleConnection
from .query_history import QueryHistory, SavedQuery

# Phase 4 models (Authentication & RBAC)
from .role import Role, Permission, UserRole, RolePermission
from .session import Session
from .audit import AuditLog

# Phase 5 models (Dashboard Builder - Full Implementation)
from .dashboard import (
    Dashboard,
    DashboardComponent,
    DashboardDataSource,
    DashboardShare,
    DashboardVersion,
    DashboardTemplate
)

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
    'Dashboard',
    'DashboardComponent',
    'DashboardDataSource',
    'DashboardShare',
    'DashboardVersion',
    'DashboardTemplate'
]
