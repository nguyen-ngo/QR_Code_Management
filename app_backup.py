from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import qrcode
import io
import base64
import os
from sqlalchemy import text
import re
import uuid
from user_agents import parse

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Ratkhonho123@localhost/qr_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    """
    User model to manage system users with role-based access control
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin or staff
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    active_status = db.Column(db.Boolean, default=True)
    last_login_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]))
    created_qr_codes = db.relationship('QRCode', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify user password"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.role == 'admin'

# QR Code Model
class QRCode(db.Model):
    """
    QR Code model to manage QR code records and metadata
    """
    __tablename__ = 'qr_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    location_address = db.Column(db.Text, nullable=False)
    location_event = db.Column(db.String(200), nullable=False)
    qr_code_image = db.Column(db.Text, nullable=False)  # Base64 encoded image
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    active_status = db.Column(db.Boolean, default=True)
    qr_url = db.Column(db.String(255), unique=True, nullable=True)

class AttendanceData(db.Model):
    """
    Attendance tracking model for QR code check-ins
    """
    __tablename__ = 'attendance_data'
    
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_codes.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False, default=datetime.today)
    check_in_time = db.Column(db.Time, nullable=False, default=datetime.now().time)
    device_info = db.Column(db.String(200))
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    location_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='present')
    created_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_timestamp = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    qr_code = db.relationship('QRCode', backref=db.backref('attendance_records', lazy='dynamic'))

# Update your existing QRCode model to include the qr_url field
# Add this line to the QRCode model class:
# qr_url = db.Column(db.String(255), unique=True, nullable=True)

# Add these utility functions after your existing utility functions

def generate_qr_url(name, qr_id):
    """Generate a unique URL for QR code destination"""
    # Clean the name for URL use
    clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    clean_name = re.sub(r'\s+', '-', clean_name.strip())
    clean_name = clean_name.lower()
    
    # Create unique URL
    url_slug = f"qr-{qr_id}-{clean_name}"
    return url_slug[:200]  # Limit length

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
            
        return device_info[:200]  # Limit length
    except:
        return "Unknown Device"

def get_client_ip():
    """Get client IP address"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']
    
# Authentication decorator
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
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            flash('Admin privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Utility function to generate QR code
def generate_qr_code(data):
    """Generate QR code image and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

# Routes
@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User authentication endpoint"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, active_status=True).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            # Update last login date
            user.last_login_date = datetime.utcnow()
            db.session.commit()
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')
'''

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint"""
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        
        # Create new user (default role: staff)
        new_user = User(
            full_name=full_name,
            email=email,
            username=username,
            role='staff'
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout endpoint"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard after login - Fixed to show all QR codes"""
    user = User.query.get(session['user_id'])
    
    # Get ALL QR codes (both active and inactive) with proper error handling
    # The frontend filtering will handle display logic
    try:
        qr_codes = QRCode.query.order_by(QRCode.created_date.desc()).all()  # ✅ Fixed: removed filter
    except Exception as e:
        print(f"Error fetching QR codes: {e}")
        qr_codes = []
    
    return render_template('dashboard.html', user=user, qr_codes=qr_codes)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'profile':
            # Update profile information
            user.full_name = request.form['full_name']
            user.email = request.form['email']
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            
        elif form_type == 'password':
            # Update password
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            
            if user.check_password(current_password):
                user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect.', 'error')
        
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=user)

@app.route('/users')
@admin_required
def users():
    """User management page (Admin only) - Enhanced with better data"""
    try:
        # Get all users with their QR code counts
        all_users = db.session.query(User).all()
        
        # Add QR code counts to each user
        for user in all_users:
            user.qr_code_count = user.created_qr_codes.count()
            user.active_qr_count = user.created_qr_codes.filter_by(active_status=True).count()
        
        print(f"Found {len(all_users)} users for admin view")
        return render_template('users.html', users=all_users)
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        flash('Error loading users. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user (Admin only) - Fixed validation"""
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')
            role = request.form.get('role', '')
            
            # Validation
            if not all([full_name, email, username, password, role]):
                flash('All fields are required.', 'error')
                return render_template('create_user.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('create_user.html')
            
            if role not in ['staff', 'admin']:
                flash('Invalid role specified.', 'error')
                return render_template('create_user.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('create_user.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('create_user.html')
            
            # Create user
            new_user = User(
                full_name=full_name,
                email=email,
                username=username,
                role=role,
                created_by=session['user_id'],
                created_date=datetime.utcnow(),
                active_status=True
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'User "{full_name}" created successfully!', 'success')
            print(f"Admin {session['username']} created user: {username} with role: {role}")
            
            return redirect(url_for('users'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            flash('Error creating user. Please try again.', 'error')
            return render_template('create_user.html')
    
    return render_template('create_user.html')

@app.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    """Deactivate user (Admin only) - Fixed with proper validation"""
    try:
        user_to_delete = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_delete:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        # Prevent self-deletion
        if user_to_delete.id == current_user.id:
            flash('You cannot deactivate your own account. Ask another admin to do this.', 'error')
            return redirect(url_for('users'))
        
        # Check if trying to delete the last admin
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate the last admin user. Promote another user to admin first.', 'error')
                return redirect(url_for('users'))
        
        # Deactivate the user instead of deleting
        user_to_delete.active_status = False
        db.session.commit()
        
        flash(f'User "{user_to_delete.full_name}" has been deactivated successfully.', 'success')
        print(f"Admin {current_user.username} deactivated user: {user_to_delete.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deactivating user: {e}")
        flash('Error deactivating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/reactivate', methods=['GET', 'POST'])
@admin_required
def reactivate_user(user_id):
    """Reactivate a deactivated user (Admin only)"""
    try:
        user_to_reactivate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_reactivate:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if user_to_reactivate.active_status:
            flash('User is already active.', 'info')
        else:
            user_to_reactivate.active_status = True
            db.session.commit()
            flash(f'User "{user_to_reactivate.full_name}" has been reactivated successfully.', 'success')
            print(f"Admin {current_user.username} reactivated user: {user_to_reactivate.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error reactivating user: {e}")
        flash('Error reactivating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/promote', methods=['GET', 'POST'])
@admin_required
def promote_user(user_id):
    """Promote a staff user to admin (Admin only)"""
    try:
        user_to_promote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_promote:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if user_to_promote.role == 'admin':
            flash('User is already an admin.', 'info')
        else:
            user_to_promote.role = 'admin'
            db.session.commit()
            flash(f'"{user_to_promote.full_name}" has been promoted to admin.', 'success')
            print(f"Admin {current_user.username} promoted user {user_to_promote.username} to admin")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error promoting user: {e}")
        flash('Error promoting user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/demote', methods=['GET', 'POST'])
@admin_required
def demote_user(user_id):
    """Demote an admin user to staff (Admin only)"""
    try:
        user_to_demote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_demote:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        # Prevent self-demotion
        if user_to_demote.id == current_user.id:
            flash('You cannot demote yourself. Have another admin do this.', 'error')
            return redirect(url_for('users'))
        
        # Check if this is the last admin
        active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
        if active_admin_count <= 1 and user_to_demote.role == 'admin':
            flash('Cannot demote the last admin user. Promote another user to admin first.', 'error')
            return redirect(url_for('users'))
        
        if user_to_demote.role == 'staff':
            flash('User is already staff.', 'info')
        else:
            user_to_demote.role = 'staff'
            db.session.commit()
            flash(f'"{user_to_demote.full_name}" has been demoted to staff.', 'success')
            print(f"Admin {current_user.username} demoted user {user_to_demote.username} to staff")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error demoting user: {e}")
        flash('Error demoting user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user information (Admin only)"""
    try:
        user_to_edit = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_edit:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            new_role = request.form.get('role', '')
            new_password = request.form.get('new_password', '').strip()
            
            # Validation
            if not all([full_name, email, new_role]):
                flash('Name, email, and role are required.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            if new_role not in ['staff', 'admin']:
                flash('Invalid role specified.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Check for email conflicts (excluding current user)
            existing_email_user = User.query.filter_by(email=email).first()
            if existing_email_user and existing_email_user.id != user_to_edit.id:
                flash('Email already in use by another user.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Prevent self-demotion
            if (user_to_edit.id == current_user.id and 
                user_to_edit.role == 'admin' and new_role == 'staff'):
                flash('You cannot demote yourself. Have another admin do this.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Check if demoting the last admin
            if (user_to_edit.role == 'admin' and new_role == 'staff'):
                active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
                if active_admin_count <= 1:
                    flash('Cannot demote the last admin user. Promote another user to admin first.', 'error')
                    return render_template('edit_user.html', user=user_to_edit)
            
            # Update user information
            user_to_edit.full_name = full_name
            user_to_edit.email = email
            user_to_edit.role = new_role
            
            # Handle password change if provided
            if new_password:
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'error')
                    return render_template('edit_user.html', user=user_to_edit)
                user_to_edit.set_password(new_password)
            
            db.session.commit()
            flash(f'User "{user_to_edit.full_name}" updated successfully.', 'success')
            print(f"Admin {current_user.username} updated user: {user_to_edit.username}")
            
            return redirect(url_for('users'))
        
        return render_template('edit_user.html', user=user_to_edit)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error editing user: {e}")
        flash('Error updating user. Please try again.', 'error')
        return redirect(url_for('users'))

# ENHANCED USER STATISTICS API
@app.route('/api/users/stats')
@admin_required
def user_stats_api():
    """API endpoint for user statistics"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(active_status=True).count()
        admin_users = User.query.filter_by(role='admin', active_status=True).count()
        staff_users = User.query.filter_by(role='staff', active_status=True).count()
        inactive_users = User.query.filter_by(active_status=False).count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = User.query.filter(User.created_date >= thirty_days_ago).count()
        
        # Recent logins (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = User.query.filter(
            User.last_login_date >= seven_days_ago,
            User.active_status == True
        ).count()
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'staff_users': staff_users,
            'inactive_users': inactive_users,
            'recent_registrations': recent_registrations,
            'recent_logins': recent_logins
        })
        
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': 'Failed to fetch user statistics'}), 500

@app.route('/users/<int:user_id>/permanently-delete', methods=['GET', 'POST'])
@admin_required
def permanently_delete_user(user_id):
    """Permanently delete user and all associated data (Admin only)"""
    try:
        user_to_delete = User.query.get_or_404(user_id)
        current_user = User.query.get(session['user_id'])
        
        # Security checks
        if user_to_delete.id == current_user.id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('users'))
        
        # Only allow deletion of inactive users for safety
        if user_to_delete.active_status:
            flash('User must be deactivated before permanent deletion.', 'error')
            return redirect(url_for('users'))
        
        # If deleting an admin, ensure at least one admin remains
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot delete the last admin user in the system.', 'error')
                return redirect(url_for('users'))
        
        user_name = user_to_delete.full_name
        user_qr_count = user_to_delete.created_qr_codes.count()
        
        # Delete all QR codes created by this user
        QRCode.query.filter_by(created_by=user_id).delete()
        
        # Update any users that were created by this user (set created_by to None)
        created_users = User.query.filter_by(created_by=user_id).all()
        for created_user in created_users:
            created_user.created_by = None
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'User "{user_name}" and {user_qr_count} associated QR codes have been permanently deleted.', 'success')
        print(f"Admin {current_user.username} permanently deleted user: {user_to_delete.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error permanently deleting user: {e}")
        flash('Error deleting user. Please try again.', 'error')
        return redirect(url_for('users'))
    
# BULK USER OPERATIONS
@app.route('/users/bulk/deactivate', methods=['POST'])
@admin_required
def bulk_deactivate_users():
    """Bulk deactivate multiple users (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        current_user_id = session['user_id']
        current_user = User.query.get(current_user_id)
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Filter out current user and validate
        valid_user_ids = []
        admin_count = User.query.filter_by(role='admin', active_status=True).count()
        admins_to_deactivate = 0
        
        for user_id in user_ids:
            if user_id == current_user_id:
                continue  # Skip current user
            
            user = User.query.get(user_id)
            if user and user.active_status:
                if user.role == 'admin':
                    admins_to_deactivate += 1
                valid_user_ids.append(user_id)
        
        # Check if we're trying to deactivate all admins
        if admin_count - admins_to_deactivate < 1:
            return jsonify({'error': 'Cannot deactivate all admin users'}), 400
        
        # Deactivate users
        deactivated_count = 0
        for user_id in valid_user_ids:
            user = User.query.get(user_id)
            if user:
                user.active_status = False
                deactivated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deactivated {deactivated_count} users',
            'deactivated_count': deactivated_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk deactivate: {e}")
        return jsonify({'error': 'Failed to deactivate users'}), 500

@app.route('/users/bulk/activate', methods=['POST'])
@admin_required
def bulk_activate_users():
    """Bulk activate multiple users (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Activate users
        activated_count = 0
        for user_id in user_ids:
            user = User.query.get(user_id)
            if user and not user.active_status:
                user.active_status = True
                activated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully activated {activated_count} users',
            'activated_count': activated_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk activate: {e}")
        return jsonify({'error': 'Failed to activate users'}), 500


@app.route('/users/bulk/permanently-delete', methods=['POST'])
@admin_required
def bulk_permanently_delete_users():
    """Bulk permanently delete multiple users and all associated data (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        current_user_id = session['user_id']
        current_user = User.query.get(current_user_id)
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Convert string IDs to integers for safety
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user IDs provided'}), 400
        
        # Security validations
        deleted_users = []
        deleted_qr_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                # Skip current user
                if user_id == current_user_id:
                    errors.append(f"Cannot delete your own account")
                    continue
                
                user_to_delete = User.query.get(user_id)
                if not user_to_delete:
                    errors.append(f"User with ID {user_id} not found")
                    continue
                
                # Only allow deletion of inactive users for safety
                if user_to_delete.active_status:
                    errors.append(f"User '{user_to_delete.full_name}' must be deactivated before permanent deletion")
                    continue
                
                # If deleting an admin, ensure at least one admin remains
                if user_to_delete.role == 'admin':
                    active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
                    if active_admin_count <= 1:
                        errors.append(f"Cannot delete the last admin user '{user_to_delete.full_name}'")
                        continue
                
                # Count QR codes before deletion for reporting
                user_qr_count = user_to_delete.created_qr_codes.count()
                deleted_qr_count += user_qr_count
                
                # Delete all QR codes created by this user
                QRCode.query.filter_by(created_by=user_id).delete()
                
                # Update any users that were created by this user (set created_by to None)
                created_users = User.query.filter_by(created_by=user_id).all()
                for created_user in created_users:
                    created_user.created_by = None
                
                # Delete the user
                deleted_users.append({
                    'name': user_to_delete.full_name,
                    'username': user_to_delete.username,
                    'qr_count': user_qr_count
                })
                
                db.session.delete(user_to_delete)
                
            except Exception as e:
                print(f"Error processing user {user_id}: {e}")
                errors.append(f"Error processing user ID {user_id}")
                continue
        
        # Commit all changes if we have deletions
        if deleted_users:
            db.session.commit()
            
            # Log the bulk deletion
            deleted_names = [user['name'] for user in deleted_users]
            print(f"Admin {current_user.username} permanently deleted {len(deleted_users)} users: {', '.join(deleted_names)}")
        
        # Prepare response message
        if deleted_users and not errors:
            message = f'Successfully deleted {len(deleted_users)} users and {deleted_qr_count} associated QR codes'
        elif deleted_users and errors:
            message = f'Deleted {len(deleted_users)} users and {deleted_qr_count} QR codes. {len(errors)} operations failed'
        elif not deleted_users and errors:
            return jsonify({
                'success': False,
                'error': 'No users could be deleted',
                'details': errors
            }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'No valid users to delete'
            }), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': len(deleted_users),
            'deleted_qr_count': deleted_qr_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk permanently delete users: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete users. Please try again.'
        }), 500
    
# ENHANCED LOGIN WITH BETTER SESSION MANAGEMENT
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced user authentication with better error handling"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        try:
            # Find user (case-insensitive username)
            user = User.query.filter(
                User.username.ilike(username),
                User.active_status == True
            ).first()
            
            if user and user.check_password(password):
                # Successful login
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['full_name'] = user.full_name
                
                # Update last login date
                user.last_login_date = datetime.utcnow()
                db.session.commit()
                
                flash(f'Welcome back, {user.full_name}!', 'success')
                print(f"User {user.username} logged in successfully")
                
                # Redirect to intended page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
                
            else:
                # Invalid credentials
                flash('Invalid username or password.', 'error')
                print(f"Failed login attempt for username: {username}")
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
    
    return render_template('login.html')

# Add this helper function to check admin requirements more safely
def is_admin_user(user_id):
    """Helper function to safely check if user is admin"""
    try:
        user = User.Query.get(user_id)
        return user and user.active_status and user.role == 'admin'
    except:
        return False

# Enhanced admin_required decorator with better error handling
def admin_required(f):
    """Enhanced decorator to ensure user has admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
        
        if not is_admin_user(session['user_id']):
            flash('Administrator privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/qr-codes/create', methods=['GET', 'POST'])
@login_required
def create_qr_code():
    """Create new QR code"""
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        location_address = request.form['location_address']
        location_event = request.form['location_event']
        
        # Create QR code record first (without QR image and URL)
        new_qr_code = QRCode(
            name=name,
            location=location,
            location_address=location_address,
            location_event=location_event,
            qr_code_image='',  # Temporary empty value
            qr_url='',         # Temporary empty value
            created_by=session['user_id']
        )
        
        # Add to session and flush to get the ID
        db.session.add(new_qr_code)
        db.session.flush()  # This assigns the ID without committing
        
        # Now we can use the ID to generate the URL
        qr_url = generate_qr_url(name, new_qr_code.id)
        
        # Generate QR code data with the destination URL
        qr_data = f"{request.url_root}qr/{qr_url}"
        qr_image = generate_qr_code(qr_data)
        
        # Update the QR code with the URL and image
        new_qr_code.qr_url = qr_url
        new_qr_code.qr_code_image = qr_image
        
        # Now commit all changes
        db.session.commit()
        
        flash('QR code created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_qr_code.html')

@app.route('/qr-codes/<int:qr_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_qr_code(qr_id):
    """Edit existing QR code"""
    qr_code = QRCode.query.get_or_404(qr_id)
    
    if request.method == 'POST':
        # Store original name for comparison
        original_name = qr_code.name
        
        # Update QR code fields
        new_name = request.form['name']
        qr_code.name = new_name
        qr_code.location = request.form['location']
        qr_code.location_address = request.form['location_address']
        qr_code.location_event = request.form['location_event']

        # Check if name changed and handle URL regeneration
        if original_name != new_name:
            # Name changed, regenerate URL
            new_qr_url = generate_qr_url(new_name, qr_code.id)
            qr_code.qr_url = new_qr_url
            
            # Update QR code data with new URL
            qr_data = f"{request.url_root}qr/{new_qr_url}"
        else:
            # Name didn't change, use existing URL (if it exists)
            if qr_code.qr_url:
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
            else:
                # Fallback: generate URL if it doesn't exist (for legacy QR codes)
                new_qr_url = generate_qr_url(new_name, qr_code.id)
                qr_code.qr_url = new_qr_url
                qr_data = f"{request.url_root}qr/{new_qr_url}"

        # Regenerate QR code with updated data (destination URL)
        qr_code.qr_code_image = generate_qr_code(qr_data)

        db.session.commit()
        
        flash('QR code updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_qr_code.html', qr_code=qr_code)

@app.route('/qr-codes/<int:qr_id>/delete')
@admin_required
def delete_qr_code(qr_id):
    """Delete QR code (Admin only)"""
    qr_code = QRCode.query.get_or_404(qr_id)
    qr_code.active_status = False
    db.session.commit()
    
    flash('QR code deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/qr/<string:qr_url>')
def qr_destination(qr_url):
    """QR code destination page where staff check in"""
    try:
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        
        if not qr_code:
            flash('QR code not found or inactive.', 'error')
            return render_template('qr_not_found.html'), 404
        
        # Log the scan
        print(f"QR Code scanned: {qr_code.name} at {datetime.now()}")
        
        return render_template('qr_destination.html', qr_code=qr_code)
        
    except Exception as e:
        print(f"Error loading QR destination: {e}")
        flash('Error loading QR code destination.', 'error')
        return render_template('qr_not_found.html'), 500

@app.route('/qr/<string:qr_url>/checkin', methods=['POST'])
def qr_checkin(qr_url):
    """Handle staff check-in submission"""
    try:
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        
        if not qr_code:
            return jsonify({
                'success': False,
                'message': 'QR code not found or inactive.'
            }), 404
        
        # Get form data
        employee_id = request.form.get('employee_id', '').strip()
        
        if not employee_id:
            return jsonify({
                'success': False,
                'message': 'Employee ID is required.'
            }), 400
        
        # Validate employee ID format (adjust regex as needed)
        if not re.match(r'^[A-Za-z0-9]{3,20}$', employee_id):
            return jsonify({
                'success': False,
                'message': 'Invalid employee ID format. Use 3-20 alphanumeric characters.'
            }), 400
        
        # Check for duplicate check-ins today
        today = datetime.today()
        existing_checkin = AttendanceData.query.filter_by(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today
        ).first()
        
        if existing_checkin:
            return jsonify({
                'success': False,
                'message': f'You have already checked in today at {existing_checkin.check_in_time.strftime("%H:%M")}.'
            }), 409
        
        # Get device and location info
        user_agent_string = request.headers.get('User-Agent', '')
        device_info = detect_device_info(user_agent_string)
        ip_address = get_client_ip()
        
        # Create attendance record
        attendance = AttendanceData(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today,
            check_in_time=datetime.now().time(),
            device_info=device_info,
            user_agent=user_agent_string,
            ip_address=ip_address,
            location_name=qr_code.location,
            status='present'
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        print(f"Check-in recorded: {employee_id} at {qr_code.name}")
        
        return jsonify({
            'success': True,
            'message': f'Check-in successful! Welcome to {qr_code.location_event}.',
            'data': {
                'employee_id': employee_id.upper(),
                'location': qr_code.location,
                'event': qr_code.location_event,
                'time': datetime.now().strftime('%H:%M'),
                'date': today.strftime('%B %d, %Y')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error during check-in: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during check-in. Please try again.'
        }), 500
    
@app.route('/qr-codes/<int:qr_id>/toggle-status', methods=['POST'])
@login_required
def toggle_qr_status(qr_id):
    """Toggle QR code active/inactive status"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        
        # Toggle the status
        qr_code.active_status = not qr_code.active_status
        db.session.commit()
        
        status_text = "activated" if qr_code.active_status else "deactivated"
        flash(f'QR code "{qr_code.name}" has been {status_text} successfully!', 'success')
        
        return jsonify({
            'success': True,
            'new_status': qr_code.active_status,
            'status_text': 'Active' if qr_code.active_status else 'Inactive',
            'message': f'QR code {status_text} successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling QR status: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating QR code status. Please try again.'
        }), 500

@app.route('/qr-codes/<int:qr_id>/activate', methods=['POST'])
@login_required
def activate_qr_code(qr_id):
    """Activate a QR code"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        qr_code.active_status = True
        db.session.commit()
        
        flash(f'QR code "{qr_code.name}" has been activated successfully!', 'success')
        return jsonify({
            'success': True,
            'new_status': True,
            'status_text': 'Active',
            'message': 'QR code activated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error activating QR code: {e}")
        return jsonify({
            'success': False,
            'message': 'Error activating QR code. Please try again.'
        }), 500

@app.route('/qr-codes/<int:qr_id>/deactivate', methods=['POST'])
@login_required
def deactivate_qr_code(qr_id):
    """Deactivate a QR code"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        qr_code.active_status = False
        db.session.commit()
        
        flash(f'QR code "{qr_code.name}" has been deactivated successfully!', 'success')
        return jsonify({
            'success': True,
            'new_status': False,
            'status_text': 'Inactive',
            'message': 'QR code deactivated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deactivating QR code: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deactivating QR code. Please try again.'
        }), 500

@app.route('/attendance')
#@admin_required
def attendance_report():
    """Attendance report page (Admin only)"""
    try:
        # Get filter parameters
        date_filter = request.args.get('date', '')
        location_filter = request.args.get('location', '')
        employee_filter = request.args.get('employee', '')
        
        # Base query using the view
        query = db.session.execute(text("SELECT * FROM attendance_report WHERE 1=1"))
        
        # Apply filters (you can enhance this with proper SQLAlchemy filtering)
        attendance_records = query.fetchall()
        
        # Get unique locations for filter dropdown
        locations_query = db.session.execute(text("""
            SELECT DISTINCT location_name 
            FROM attendance_data 
            ORDER BY location_name
        """))
        locations = [row[0] for row in locations_query.fetchall()]
        
        # Get attendance statistics
        stats_query = db.session.execute(text("""
            SELECT 
                COUNT(*) as total_checkins,
                COUNT(DISTINCT employee_id) as unique_employees,
                COUNT(DISTINCT qr_code_id) as active_locations,
                COUNT(CASE WHEN check_in_date = CURRENT_DATE THEN 1 END) as today_checkins
            FROM attendance_data
        """))
        stats = stats_query.fetchone()
        
        return render_template('attendance_report.html', 
                             attendance_records=attendance_records,
                             locations=locations,
                             stats=stats,
                             date_filter=date_filter,
                             location_filter=location_filter,
                             employee_filter=employee_filter)
        
    except Exception as e:
        print(f"Error loading attendance report: {e}")
        flash('Error loading attendance report.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/attendance/stats')
@admin_required
def attendance_stats_api():
    """API endpoint for attendance statistics"""
    try:
        # Daily stats for the last 7 days
        daily_stats = db.session.execute(text("""
            SELECT 
                check_in_date,
                COUNT(*) as checkins,
                COUNT(DISTINCT employee_id) as unique_employees
            FROM attendance_data 
            WHERE check_in_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY check_in_date
            ORDER BY check_in_date DESC
        """)).fetchall()
        
        # Location stats
        location_stats = db.session.execute(text("""
            SELECT 
                location_name,
                COUNT(*) as total_checkins,
                COUNT(DISTINCT employee_id) as unique_employees
            FROM attendance_data
            GROUP BY location_name
            ORDER BY total_checkins DESC
            LIMIT 10
        """)).fetchall()
        
        # Peak hours
        hourly_stats = db.session.execute(text("""
            SELECT 
                EXTRACT(hour FROM check_in_time) as hour,
                COUNT(*) as checkins
            FROM attendance_data
            WHERE check_in_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY EXTRACT(hour FROM check_in_time)
            ORDER BY hour
        """)).fetchall()
        
        return jsonify({
            'daily_stats': [{'date': str(row[0]), 'checkins': row[1], 'employees': row[2]} for row in daily_stats],
            'location_stats': [{'location': row[0], 'checkins': row[1], 'employees': row[2]} for row in location_stats],
            'hourly_stats': [{'hour': int(row[0]), 'checkins': row[1]} for row in hourly_stats]
        })
        
    except Exception as e:
        print(f"Error fetching attendance stats: {e}")
        return jsonify({'error': 'Failed to fetch attendance statistics'}), 500

# Jinja2 filters for better template functionality
@app.template_filter('days_since')
def days_since_filter(date):
    """Calculate days since a given date"""
    if not date:
        return 0
    from datetime import datetime
    now = datetime.utcnow()
    return (now - date).days

@app.template_filter('time_ago')
def time_ago_filter(date):
    """Human readable time ago"""
    if not date:
        return 'Never'
    from datetime import datetime
    now = datetime.utcnow()
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors with user-friendly page"""
    if app.debug:
        # Let Flask handle debug errors naturally
        return None
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Server Error</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>🔧 Something went wrong</h1>
        <p>We're working to fix this issue. Please try again later.</p>
        <a href="/" style="color: #2563eb;">← Back to Home</a>
    </body>
    </html>
    ''', 500

@app.errorhandler(404)
def not_found(error):
    """Handle page not found errors"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Page Not Found</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>🔍 Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/" style="color: #2563eb;">← Back to Home</a>
    </body>
    </html>
    ''', 404

# Initialize database tables
def create_tables():
    """Create database tables and default admin user"""
    db.create_all()
    
    # Create default admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            full_name='System Administrator',
            email='admin@example.com',
            username='admin',
            role='admin'
        )
        admin.set_password('admin123')  # Change this in production
        db.session.add(admin)
        db.session.commit()

def update_existing_qr_codes():
    """Update existing QR codes with URLs and regenerate QR images"""
    try:
        qr_codes = QRCode.query.filter_by(active_status=True).all()
        
        for qr_code in qr_codes:
            if not qr_code.qr_url:
                # Generate URL
                qr_code.qr_url = generate_qr_url(qr_code.name, qr_code.id)
                
                # Regenerate QR code with destination URL
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
                qr_code.qr_code_image = generate_qr_code(qr_data)
        
        db.session.commit()
        print(f"Updated {len(qr_codes)} QR codes with destination URLs")
        
    except Exception as e:
        print(f"Error updating existing QR codes: {e}")
        db.session.rollback()

if __name__ == '__main__':
    with app.app_context():
        create_tables()
        update_existing_qr_codes()
    app.run(debug=True, host="0.0.0.0")
