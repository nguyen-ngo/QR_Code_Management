"""
routes/auth.py
==============
Authentication and user-profile routes.

Routes: /, /register, /login, /logout, /profile
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, url_for
from datetime import datetime
import json

from extensions import db, logger_handler
from models.user import User
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import admin_required, login_required, staff_or_admin_required
from turnstile_utils import turnstile_utils

bp = Blueprint('auth', __name__)



@bp.route('/', endpoint='index')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'], endpoint='register')
@log_user_activity('user_registration')
def register():
    """User registration endpoint"""
    if request.method == 'POST':
        try:
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

            # Log successful user registration
            logger_handler.logger.info(f"New user registered: {username} ({email})")

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('user_registration', e)
            flash('Registration failed. Please try again.', 'error')

    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    """Enhanced user authentication with Turnstile and comprehensive logging"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        turnstile_response = request.form.get('cf-turnstile-response', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        # Verify Turnstile if enabled
        if turnstile_utils.is_enabled():
            if not turnstile_utils.verify_turnstile(turnstile_response):
                # Log failed Turnstile attempt
                logger_handler.log_security_event(
                    event_type="turnstile_verification_failed",
                    description=f"Failed Turnstile verification for username: {username}",
                    severity="HIGH"
                )
                flash('Please complete the security verification.', 'error')
                return render_template('login.html')

        try:
            # Find user (case-insensitive username)
            user = User.query.filter(
                User.username.like(username),
                User.active_status == True
            ).first()

            if user and user.check_password(password):
                # Check if "Remember Me" is checked
                remember_me = request.form.get('remember_me') == 'on'
                
                # Set session as permanent if "Remember Me" is checked
                if remember_me:
                    session.permanent = True
                    session['remember_me'] = True
                else:
                    session.permanent = False
                    session['remember_me'] = False
                
                # Successful login
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['full_name'] = user.full_name
                session['login_time'] = datetime.now().isoformat()

                # Update last login date
                user.last_login_date = datetime.utcnow()
                db.session.commit()

                # Log successful login with Turnstile info
                logger_handler.log_user_login(
                    user_id=user.id,
                    username=user.username,
                    success=True
                )
                
                # Log successful Turnstile verification
                if turnstile_utils.is_enabled():
                    logger_handler.log_security_event(
                        event_type="turnstile_verification_success",
                        description=f"Successful Turnstile verification for user: {user.username}",
                        severity="INFO"
                    )

                flash(f'Welcome back, {user.full_name}!', 'success')
                logger_handler.logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")

                # Redirect to intended page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('attendance.attendance_report'))

            else:
                # Invalid credentials - log failed attempt
                user_id = user.id if user else None
                logger_handler.log_user_login(
                    user_id=user_id,
                    username=username,
                    success=False,
                    failure_reason="Invalid credentials"
                )

                flash('Invalid username or password.', 'error')
                logger_handler.logger.warning(f"Failed login attempt for username: {username}")

        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('user_login', e)
            logger_handler.logger.error(f"Login error for username '{username}': {e}")
            flash('Login error. Please try again.', 'error')

    return render_template('login.html')

@bp.route('/logout', endpoint='logout')
def logout():
    """User logout endpoint with session duration logging"""
    user_id = session.get('user_id')
    username = session.get('username')
    login_time_str = session.get('login_time')

    # Calculate session duration
    session_duration = None
    if login_time_str:
        try:
            login_time = datetime.fromisoformat(login_time_str)
            session_duration = (datetime.now() - login_time).total_seconds() / 60  # minutes
        except:
            pass

    # Log user logout
    if user_id and username:
        logger_handler.log_user_logout(
            user_id=user_id,
            username=username,
            session_duration=session_duration
        )

    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'], endpoint='profile')
@login_required
@log_user_activity('profile_update')
def profile():
    """User profile management with logging"""
    try:
        user = db.session.get(User, session['user_id'])

        if request.method == 'POST':
            form_type = request.form.get('form_type')

            if form_type == 'profile':
                # Track changes for logging
                old_name = user.full_name
                old_email = user.email

                # Update profile information
                user.full_name = request.form['full_name']
                user.email = request.form['email']

                # Check for changes
                changes = {}
                if old_name != user.full_name:
                    changes['full_name'] = {'old': old_name, 'new': user.full_name}
                if old_email != user.email:
                    changes['email'] = {'old': old_email, 'new': user.email}

                db.session.commit()

                # Log profile update if there were changes
                if changes:
                    logger_handler.logger.info(f"User profile updated: {user.username} - Changes: {json.dumps(changes)}")

                flash('Profile updated successfully!', 'success')

            elif form_type == 'password':
                # Update password
                current_password = request.form['current_password']
                new_password = request.form['new_password']

                if user.check_password(current_password):
                    user.set_password(new_password)
                    db.session.commit()

                    # Log password change
                    logger_handler.log_security_event(
                        event_type="password_change",
                        description=f"User {user.username} changed password",
                        severity="MEDIUM"
                    )

                    flash('Password updated successfully!', 'success')
                else:
                    # Log failed password change attempt
                    logger_handler.log_security_event(
                        event_type="password_change_failed",
                        description=f"Failed password change attempt for user {user.username}",
                        severity="HIGH"
                    )
                    flash('Current password is incorrect.', 'error')

        return render_template('profile.html', user=user)

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('profile_update', e)
        flash('Profile update failed. Please try again.', 'error')
        return redirect(url_for('dashboard.dashboard'))
