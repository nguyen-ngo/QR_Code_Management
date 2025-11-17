"""
Authentication and Authorization Decorators
==========================================

Consolidated authentication decorators to eliminate duplication.
Extracted from app.py for better code organization.
"""

from functools import wraps
from flask import session, flash, redirect, url_for
from utils.validation import has_admin_privileges, has_staff_level_access

def login_required(f):
    """
    Decorator to ensure user is logged in
    
    Usage:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return render_template('dashboard.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to ensure user has admin privileges
    
    Usage:
        @app.route('/admin/users')
        @admin_required
        def manage_users():
            return render_template('users.html')
    """
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
    """
    Decorator to ensure user has staff-level or admin privileges
    
    Usage:
        @app.route('/attendance/records')
        @staff_or_admin_required
        def view_records():
            return render_template('records.html')
    """
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

def project_manager_required(f):
    """
    Decorator to ensure user is project manager or admin
    
    Usage:
        @app.route('/projects/dashboard')
        @project_manager_required
        def project_dashboard():
            return render_template('project_dashboard.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user_role = session.get('role')
        if user_role not in ['admin', 'project_manager']:
            flash('Project Manager access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def payroll_required(f):
    """
    Decorator to ensure user is payroll staff or admin
    
    Usage:
        @app.route('/payroll/process')
        @payroll_required
        def process_payroll():
            return render_template('payroll.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll']:
            flash('Payroll access required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function