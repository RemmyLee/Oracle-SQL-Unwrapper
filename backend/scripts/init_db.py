#!/usr/bin/env python3
"""
Database Initialization Script for PL/SQL Workbench
Sets up initial database with tables, roles, permissions, and admin user
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app import create_app
from backend.extensions import db
from backend.models import User, Role, Permission, RolePermission
from datetime import datetime
import getpass


def create_default_permissions():
    """Create default permissions for the system"""
    permissions = [
        # User management
        ('manage_users', 'Can manage users (create, update, delete)', 'users'),
        ('view_users', 'Can view user list', 'users'),

        # Role & permission management
        ('manage_roles', 'Can manage roles', 'roles'),
        ('manage_permissions', 'Can manage permissions', 'roles'),
        ('assign_roles', 'Can assign roles to users', 'roles'),

        # Dashboard management
        ('create_dashboards', 'Can create new dashboards', 'dashboards'),
        ('edit_dashboards', 'Can edit any dashboard', 'dashboards'),
        ('delete_dashboards', 'Can delete any dashboard', 'dashboards'),
        ('view_dashboards', 'Can view dashboards', 'dashboards'),
        ('share_dashboards', 'Can share dashboards', 'dashboards'),
        ('publish_dashboards', 'Can publish dashboards', 'dashboards'),

        # Query management
        ('execute_queries', 'Can execute SQL queries', 'queries'),
        ('save_queries', 'Can save queries', 'queries'),
        ('view_query_history', 'Can view query history', 'queries'),
        ('delete_queries', 'Can delete queries', 'queries'),

        # Connection management
        ('manage_connections', 'Can manage database connections', 'connections'),
        ('view_connections', 'Can view database connections', 'connections'),
        ('use_connections', 'Can use database connections', 'connections'),

        # Report management
        ('create_reports', 'Can create reports', 'reports'),
        ('edit_reports', 'Can edit reports', 'reports'),
        ('delete_reports', 'Can delete reports', 'reports'),
        ('view_reports', 'Can view reports', 'reports'),
        ('export_reports', 'Can export reports', 'reports'),

        # System administration
        ('view_audit_logs', 'Can view audit logs', 'admin'),
        ('manage_settings', 'Can manage system settings', 'admin'),
        ('view_statistics', 'Can view system statistics', 'admin'),
    ]

    created_permissions = []

    for permission_name, description, category in permissions:
        # Check if permission already exists
        perm = Permission.query.filter_by(permission_name=permission_name).first()

        if not perm:
            perm = Permission(
                permission_name=permission_name,
                description=description,
                category=category
            )
            db.session.add(perm)
            print(f"  ✓ Created permission: {permission_name}")
        else:
            print(f"  • Permission already exists: {permission_name}")

        created_permissions.append(perm)

    db.session.commit()
    return created_permissions


def create_default_roles():
    """Create default roles for the system"""
    roles = [
        ('Admin', 'System administrator with full access', True),
        ('User', 'Regular user with standard access', True),
        ('Viewer', 'Read-only user', True),
        ('Editor', 'User who can create and edit content', True),
    ]

    created_roles = []

    for role_name, description, is_system in roles:
        # Check if role already exists
        role = Role.query.filter_by(role_name=role_name).first()

        if not role:
            role = Role(
                role_name=role_name,
                description=description,
                is_system=is_system
            )
            db.session.add(role)
            print(f"  ✓ Created role: {role_name}")
        else:
            print(f"  • Role already exists: {role_name}")

        created_roles.append(role)

    db.session.commit()
    return created_roles


def assign_permissions_to_roles():
    """Assign appropriate permissions to each role"""

    # Get roles
    admin_role = Role.query.filter_by(role_name='Admin').first()
    user_role = Role.query.filter_by(role_name='User').first()
    viewer_role = Role.query.filter_by(role_name='Viewer').first()
    editor_role = Role.query.filter_by(role_name='Editor').first()

    # Admin gets all permissions
    all_permissions = Permission.query.all()
    for perm in all_permissions:
        if not RolePermission.query.filter_by(role_id=admin_role.id, permission_id=perm.id).first():
            role_perm = RolePermission(role_id=admin_role.id, permission_id=perm.id)
            db.session.add(role_perm)

    print(f"  ✓ Assigned all permissions to Admin role")

    # User gets standard permissions
    user_permissions = [
        'view_users',
        'view_dashboards', 'create_dashboards', 'share_dashboards',
        'execute_queries', 'save_queries', 'view_query_history',
        'view_connections', 'use_connections',
        'create_reports', 'view_reports', 'export_reports',
    ]

    for perm_name in user_permissions:
        perm = Permission.query.filter_by(permission_name=perm_name).first()
        if perm and not RolePermission.query.filter_by(role_id=user_role.id, permission_id=perm.id).first():
            role_perm = RolePermission(role_id=user_role.id, permission_id=perm.id)
            db.session.add(role_perm)

    print(f"  ✓ Assigned standard permissions to User role")

    # Viewer gets read-only permissions
    viewer_permissions = [
        'view_users',
        'view_dashboards',
        'view_query_history',
        'view_connections',
        'view_reports',
    ]

    for perm_name in viewer_permissions:
        perm = Permission.query.filter_by(permission_name=perm_name).first()
        if perm and not RolePermission.query.filter_by(role_id=viewer_role.id, permission_id=perm.id).first():
            role_perm = RolePermission(role_id=viewer_role.id, permission_id=perm.id)
            db.session.add(role_perm)

    print(f"  ✓ Assigned read-only permissions to Viewer role")

    # Editor gets content creation permissions
    editor_permissions = [
        'view_users',
        'view_dashboards', 'create_dashboards', 'edit_dashboards', 'share_dashboards', 'publish_dashboards',
        'execute_queries', 'save_queries', 'view_query_history', 'delete_queries',
        'view_connections', 'use_connections',
        'create_reports', 'edit_reports', 'view_reports', 'export_reports',
    ]

    for perm_name in editor_permissions:
        perm = Permission.query.filter_by(permission_name=perm_name).first()
        if perm and not RolePermission.query.filter_by(role_id=editor_role.id, permission_id=perm.id).first():
            role_perm = RolePermission(role_id=editor_role.id, permission_id=perm.id)
            db.session.add(role_perm)

    print(f"  ✓ Assigned content creation permissions to Editor role")

    db.session.commit()


def create_admin_user(email, username, password):
    """Create the initial admin user"""

    # Check if user already exists
    existing_user = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()

    if existing_user:
        print(f"\n⚠️  User already exists with email '{email}' or username '{username}'")
        return None

    # Create admin user
    admin_user = User(
        email=email,
        username=username,
        email_verified=True,  # Auto-verify admin
        email_verified_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )

    admin_user.set_password(password)

    db.session.add(admin_user)
    db.session.commit()

    # Assign Admin role
    admin_role = Role.query.filter_by(role_name='Admin').first()
    if admin_role:
        from backend.models import UserRole
        user_role = UserRole(
            user_id=admin_user.id,
            role_id=admin_role.id
        )
        db.session.add(user_role)
        db.session.commit()

    print(f"\n✓ Created admin user: {email}")
    return admin_user


def main():
    """Main initialization function"""
    print("=" * 60)
    print("PL/SQL Workbench - Database Initialization")
    print("=" * 60)
    print()

    # Create app and context
    app = create_app()

    with app.app_context():
        # Create all tables
        print("1. Creating database tables...")
        db.create_all()
        print("  ✓ Database tables created")
        print()

        # Create default permissions
        print("2. Creating default permissions...")
        create_default_permissions()
        print()

        # Create default roles
        print("3. Creating default roles...")
        create_default_roles()
        print()

        # Assign permissions to roles
        print("4. Assigning permissions to roles...")
        assign_permissions_to_roles()
        print()

        # Create admin user
        print("5. Creating admin user...")
        print()

        # Get admin credentials
        print("Please provide admin user credentials:")
        email = input("  Email: ").strip()
        username = input("  Username: ").strip()
        password = getpass.getpass("  Password: ")
        password_confirm = getpass.getpass("  Confirm Password: ")

        if password != password_confirm:
            print("\n❌ Passwords do not match!")
            sys.exit(1)

        if len(password) < 8:
            print("\n❌ Password must be at least 8 characters!")
            sys.exit(1)

        admin_user = create_admin_user(email, username, password)

        if admin_user:
            print()
            print("=" * 60)
            print("✅ Database initialization completed successfully!")
            print("=" * 60)
            print()
            print("You can now start the application and log in with:")
            print(f"  Email: {email}")
            print(f"  Username: {username}")
            print()
        else:
            print()
            print("=" * 60)
            print("⚠️  Database initialization completed with warnings")
            print("=" * 60)
            print()


if __name__ == '__main__':
    main()
