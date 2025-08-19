"""
User Model for QR Attendance Management System
==============================================

User model to manage system users with role-based access control.
Extracted from app.py for better code organization.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Valid user roles (kept in sync with app.py)
STAFF_LEVEL_ROLES = ['staff', 'payroll', 'project_manager']

# Import db from app - this works because app.py imports this file after db is created
import sys
from . import base

class User(base.db.Model):
    """
    User model to manage system users with role-based access control
    """
    __tablename__ = 'users'
    
    id = base.db.Column(base.db.Integer, primary_key=True)
    full_name = base.db.Column(base.db.String(100), nullable=False)
    email = base.db.Column(base.db.String(120), unique=True, nullable=False)
    username = base.db.Column(base.db.String(80), unique=True, nullable=False)
    password_hash = base.db.Column(base.db.String(255), nullable=False)
    role = base.db.Column(base.db.String(20), nullable=False, default='staff')  # admin or staff
    created_by = base.db.Column(base.db.Integer, base.db.ForeignKey('users.id'), nullable=True)
    created_date = base.db.Column(base.db.DateTime, default=datetime.utcnow)
    active_status = base.db.Column(base.db.Boolean, default=True)
    last_login_date = base.db.Column(base.db.DateTime, nullable=True)
    
    # Relationships
    created_users = base.db.relationship('User', backref=base.db.backref('creator', remote_side=[id]))
    created_qr_codes = base.db.relationship('QRCode', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify user password"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.role == 'admin'
    
    def has_staff_permissions(self):
        """Check if user has staff-level permissions (includes new roles)"""
        return self.role in STAFF_LEVEL_ROLES
    
    def has_export_permissions(user_role):
        """Check if user role has export permissions"""
        return user_role in ['admin', 'payroll']

    def get_role_display_name(self):
        """Get user-friendly role name"""
        role_names = {
            'admin': 'Administrator',
            'staff': 'Staff User',
            'payroll': 'Payroll Specialist',
            'project_manager': 'Project Manager'
        }
        return role_names.get(self.role, self.role.title())