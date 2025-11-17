"""
Validation Utilities for QR Attendance Management System
========================================================

Role validation and permissions checking functions.
Extracted from app.py for better code organization.
"""

# Valid user roles
VALID_ROLES = ['admin', 'staff', 'payroll', 'project_manager']
STAFF_LEVEL_ROLES = ['staff', 'payroll', 'project_manager']

def is_valid_role(role):
    """
    Check if role is valid
    
    Args:
        role (str): User role to validate
    
    Returns:
        bool: True if role is valid
    """
    return role in VALID_ROLES

def has_admin_privileges(role):
    """
    Check if role has admin privileges
    
    Args:
        role (str): User role to check
    
    Returns:
        bool: True if role is admin
    """
    return role == 'admin'

def has_staff_level_access(role):
    """
    Check if role has staff-level access (includes payroll, project_manager)
    
    Args:
        role (str): User role to check
    
    Returns:
        bool: True if role has staff-level permissions
    """
    return role in STAFF_LEVEL_ROLES

def has_export_permissions(role):
    """
    Check if user role has export permissions
    
    Args:
        role (str): User role to check
    
    Returns:
        bool: True if role can export data
    """
    return role in ['admin', 'payroll']

def get_role_permissions(role):
    """
    Get permissions description for a role
    
    Args:
        role (str): User role
    
    Returns:
        dict: Role permissions with title, permissions list, and restrictions
    """
    permissions = {
        'admin': {
            'title': 'Administrator Permissions',
            'permissions': [
                'Full QR code management (create, edit, delete)',
                'Complete user management capabilities',
                'System configuration access',
                'View all system analytics',
                'Bulk operations and data export',
                'Access to all admin features'
            ],
            'restrictions': ['With great power comes great responsibility!']
        },
        'staff': {
            'title': 'Staff User Permissions',
            'permissions': [
                'View QR codes and attendance records',
                'Check-in to attendance',
                'View own attendance history'
            ],
            'restrictions': [
                'Cannot create or modify QR codes',
                'Cannot manage users',
                'Limited export capabilities'
            ]
        },
        'payroll': {
            'title': 'Payroll Specialist Permissions',
            'permissions': [
                'Full payroll processing access',
                'Export attendance and payroll data',
                'View all attendance records',
                'Generate payroll reports'
            ],
            'restrictions': [
                'Cannot manage QR codes',
                'Cannot manage users',
                'Read-only access to configurations'
            ]
        },
        'project_manager': {
            'title': 'Project Manager Permissions',
            'permissions': [
                'View assigned project data',
                'View assigned location data',
                'Generate project reports',
                'Monitor project attendance'
            ],
            'restrictions': [
                'Access limited to assigned projects/locations',
                'Cannot modify QR codes',
                'Cannot manage users',
                'Read-only access'
            ]
        }
    }
    
    return permissions.get(role, {
        'title': 'Unknown Role',
        'permissions': [],
        'restrictions': ['Invalid role specified']
    })