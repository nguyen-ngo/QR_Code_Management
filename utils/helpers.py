
# ---------------------------------------------------------------------------
# url_for compatibility shim
# ---------------------------------------------------------------------------
# Flask Blueprints prefix endpoint names (e.g. 'attendance.attendance_report').
# The original codebase uses bare names (e.g. url_for('attendance_report')).
# This wrapper resolves bare names by searching registered blueprints,
# so zero url_for() calls in routes or templates need to change.
#
# IMPORTANT: Flask's url_for is aliased as _flask_url_for to avoid shadowing
# this function. Decorators in this module that redirect (login_required etc.)
# also use _flask_url_for directly since they only redirect to known bare names
# that this shim already handles.
# ---------------------------------------------------------------------------

import flask.helpers as _flask_helpers
# Capture Flask's original url_for BEFORE any shadowing
_flask_url_for = _flask_helpers.url_for


def url_for(endpoint, **values):
    """
    Drop-in replacement for flask.url_for that resolves bare endpoint names
    across Blueprints. Qualified names (containing '.') pass through unchanged.
    """
    from flask import current_app
    if '.' in endpoint:
        return _flask_url_for(endpoint, **values)
    try:
        return _flask_url_for(endpoint, **values)
    except Exception:
        pass
    for bp_name in sorted(current_app.blueprints.keys()):
        try:
            return _flask_url_for(f'{bp_name}.{endpoint}', **values)
        except Exception:
            pass
    return _flask_url_for(endpoint, **values)  # raises Flask's normal BuildError


"""
utils/helpers.py
================
Shared utility functions, decorators, QR-code generation helpers,
and role/permission helpers.

Extracted verbatim from app.py (lines 234-329, 910-969, 1274-1467).
No logic changes — only import paths updated.
"""

import io
import re
import os
import base64
from datetime import datetime, date, time, timedelta
from functools import wraps

import qrcode
from flask import session, redirect, flash, request
from user_agents import parse

from extensions import logger_handler

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
VALID_ROLES = ['admin', 'staff', 'payroll', 'project_manager', 'accounting']
STAFF_LEVEL_ROLES = ['staff', 'payroll', 'project_manager', 'accounting']


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_valid_role(role):
    """Check if role is valid"""
    return role in VALID_ROLES


def has_admin_privileges(role):
    """Check if role has admin privileges"""
    return role == 'admin'


def has_staff_level_access(role):
    """Check if role has staff-level access (includes new roles)"""
    return role in STAFF_LEVEL_ROLES


def get_role_permissions(role):
    """Get permissions description for a role"""
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
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        },
        'payroll': {
            'title': 'Payroll Specialist Permissions',
            'permissions': [
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
                'Access dashboard and reports',
                'Same permissions as Staff (additional features coming soon)'
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        },
        'project_manager': {
            'title': 'Project Manager Permissions',
            'permissions': [
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
                'Access dashboard and reports',
                'Same permissions as Staff (additional features coming soon)'
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        },
        'accounting': {
            'title': 'Accounting Specialist Permissions',
            'permissions': [
                'View and modify employee records',
                'Access attendance reports and analytics',
                'View and manage time attendance data',
                'Export payroll and attendance data',
                'Access financial reports and statistics',
                'Update personal profile information',
                'Delete attendance records (same as payroll)'
            ],
            'restrictions': [
                'Cannot create or delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings',
                'Cannot manage projects'
            ]
        }
    }
    return permissions.get(role, {})


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator to ensure user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to ensure user has admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        user_role = session.get('role')
        if not has_admin_privileges(user_role):
            flash('Administrator privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def staff_or_admin_required(f):
    """Decorator to ensure user has staff-level or admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        user_role = session.get('role')
        if not (has_admin_privileges(user_role) or has_staff_level_access(user_role)):
            flash('Insufficient privileges to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def is_admin_user(user_id):
    """Helper function to safely check if user is admin"""
    from extensions import db
    from models import set_db
    try:
        # User model is available through the app context
        from flask import current_app
        with current_app.app_context():
            # Access via db session to avoid circular import
            from sqlalchemy import text
            result = db.session.execute(
                text("SELECT role, active_status FROM users WHERE id = :uid"),
                {'uid': user_id}
            ).fetchone()
            return result and result.active_status and result.role == 'admin'
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

def detect_device_info(user_agent_string):
    """Extract device information from user agent"""
    try:
        user_agent = parse(user_agent_string)
        device_info = f"{user_agent.device.family}"
        if user_agent.os.family:
            device_info += f" - {user_agent.os.family}"
            if user_agent.os.version_string:
                device_info += f" {user_agent.os.version_string}"
        if user_agent.browser.family:
            device_info += f" ({user_agent.browser.family})"
        return device_info[:200]
    except Exception:
        return "Unknown Device"


def get_client_ip():
    """Get client IP address"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']


# ---------------------------------------------------------------------------
# QR code generation
# ---------------------------------------------------------------------------

def generate_qr_url(name, qr_id):
    """Generate a unique URL for QR code destination"""
    clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    clean_name = re.sub(r'\s+', '-', clean_name.strip())
    clean_name = clean_name.lower()
    url_slug = f"qr-{qr_id}-{clean_name}"
    return url_slug[:200]


def generate_qr_code(data, fill_color="black", back_color="white", box_size=10, border=4, error_correction='L'):
    """Generate a QR code image and return as base64 string"""
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_L),
            box_size=int(box_size),
            border=int(border),
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        try:
            logger_handler.log_qr_code_generated(
                data_length=len(data),
                fill_color=fill_color,
                back_color=back_color,
                box_size=box_size,
                border=border,
                error_correction=error_correction
            )
        except Exception:
            pass

        return img_str

    except Exception as e:
        logger_handler.log_database_error('qr_code_generation', e)
        return generate_default_qr_code(data)


def generate_default_qr_code(data):
    """Fallback function for basic QR code generation"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str


def get_qr_styling(qr_code):
    """Extract QR code styling parameters from database record"""
    return {
        'fill_color': getattr(qr_code, 'fill_color', '#000000') or '#000000',
        'back_color': getattr(qr_code, 'back_color', '#FFFFFF') or '#FFFFFF',
        'box_size': getattr(qr_code, 'box_size', 10) or 10,
        'border': getattr(qr_code, 'border', 4) or 4,
        'error_correction': getattr(qr_code, 'error_correction', 'L') or 'L'
    }


# ---------------------------------------------------------------------------
# Check-in history helpers
# ---------------------------------------------------------------------------

def get_employee_checkin_history(employee_id, qr_code_id, date_filter=None):
    """Get check-in history for an employee at a specific location"""
    from extensions import db
    try:
        if date_filter is None:
            date_filter = date.today()
        # AttendanceData imported at call site to avoid circular import
        from flask import current_app
        AttendanceData = current_app.config.get('_models', {}).get('AttendanceData')
        if AttendanceData:
            checkins = AttendanceData.query.filter_by(
                employee_id=employee_id.upper(),
                qr_code_id=qr_code_id,
                check_in_date=date_filter
            ).order_by(AttendanceData.check_in_time.asc()).all()
            return checkins
        return []
    except Exception as e:
        print(f"❌ Error retrieving checkin history: {e}")
        return []


def format_checkin_intervals(checkins):
    """Format time intervals between check-ins for display"""
    if len(checkins) < 2:
        return []

    intervals = []
    for i in range(1, len(checkins)):
        previous_time = datetime.combine(checkins[i - 1].check_in_date, checkins[i - 1].check_in_time)
        current_time = datetime.combine(checkins[i].check_in_date, checkins[i].check_in_time)
        interval = current_time - previous_time
        interval_minutes = int(interval.total_seconds() / 60)
        intervals.append({
            'from_time': checkins[i - 1].check_in_time.strftime('%H:%M'),
            'to_time': checkins[i].check_in_time.strftime('%H:%M'),
            'interval_minutes': interval_minutes,
            'interval_text': format_time_interval(interval_minutes)
        })
    return intervals


def format_time_interval(minutes):
    """Format minutes into human-readable time interval"""
    if minutes < 60:
        return f"{minutes} minutes"
    elif minutes < 1440:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours}h {remaining_minutes}m"
    else:
        days = minutes // 1440
        remaining_hours = (minutes % 1440) // 60
        if remaining_hours == 0:
            return f"{days} day{'s' if days != 1 else ''}"
        else:
            return f"{days}d {remaining_hours}h"
