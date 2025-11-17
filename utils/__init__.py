"""
Utilities Package for QR Attendance Management System
====================================================

This package provides consolidated utility functions extracted from app.py
for better code organization and reusability.

Modules:
    - auth_decorators: Authentication and authorization decorators
    - validation: Role validation and permissions checking
    - location_utils: Location and geocoding utilities
    - qr_utils: QR code generation utilities
    - date_time_utils: Date and time formatting utilities
    - helpers: General helper functions
"""

# Authentication decorators
from .auth_decorators import (
    login_required,
    admin_required,
    staff_or_admin_required,
    project_manager_required,
    payroll_required
)

# Validation functions
from .validation import (
    is_valid_role,
    has_admin_privileges,
    has_staff_level_access,
    has_export_permissions,
    get_role_permissions,
    VALID_ROLES,
    STAFF_LEVEL_ROLES
)

# Export all for easy importing
__all__ = [
    # Decorators
    'login_required',
    'admin_required',
    'staff_or_admin_required',
    'project_manager_required',
    'payroll_required',
    
    # Validation
    'is_valid_role',
    'has_admin_privileges',
    'has_staff_level_access',
    'has_export_permissions',
    'get_role_permissions',
    'VALID_ROLES',
    'STAFF_LEVEL_ROLES',
]