"""
routes/users.py
===============
User management routes (admin-only operations).

Routes: /users/*, /api/users/stats, /api/locations-by-projects,
        /api/roles/permissions, /api/geocode, /api/reverse-geocode
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, url_for
from datetime import datetime, timedelta
import json

from extensions import db, logger_handler
from models.permissions import UserLocationPermission, UserProjectPermission
from models.project import Project
from models.qrcode import QRCode
from models.user import User
from sqlalchemy import text
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import (
                           admin_required,
                           generate_qr_code,
                           get_qr_styling,
                           get_role_permissions,
                           has_admin_privileges,
                           has_staff_level_access,
                           is_valid_role,
                           login_required,
                           staff_or_admin_required,
                           VALID_ROLES,
                           STAFF_LEVEL_ROLES)
from utils.geocoding import (geocode_address_enhanced,
                             get_all_locations_from_qr_codes,
                             get_coordinates_from_address_enhanced,
                             reverse_geocode_coordinates,
                             gmaps_client)
from werkzeug.security import generate_password_hash

bp = Blueprint('users', __name__)



@bp.route('/users', endpoint='users')
@admin_required
def users():
    """Display all users (Admin only)"""
    try:
        users = User.query.order_by(User.created_date.desc()).all()
        return render_template('users.html', users=users)
    except Exception as e:
        logger_handler.log_database_error('users_list', e)
        flash('Error loading users list.', 'error')
        return redirect(url_for('dashboard.dashboard'))

@bp.route('/users/create', methods=['GET', 'POST'], endpoint='create_user')
@admin_required
@log_database_operations('user_creation')
def create_user():
    """Create new user (Admin only) with Project Manager permissions support"""
    if request.method == 'POST':
        try:
            # Get basic form data
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            role = request.form.get('role', '')

            # Validate required fields
            if not all([full_name, email, username, password, role]):
                flash('All fields are required.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                return render_template('create_user.html', projects=projects, locations=locations)

            # Validate role
            if role not in VALID_ROLES:
                flash(f'Invalid role selected. Valid roles: {", ".join(VALID_ROLES)}', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                return render_template('create_user.html', projects=projects, locations=locations)

            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                return render_template('create_user.html', projects=projects, locations=locations)

            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                return render_template('create_user.html', projects=projects, locations=locations)

            # Create new user
            new_user = User(
                full_name=full_name,
                email=email,
                username=username,
                role=role,
                created_by=session['user_id']
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.flush()  # Get the user ID without committing

            # Handle Project Manager permissions
            if role == 'project_manager':
                # Get selected projects - getlist returns empty list if field doesn't exist
                selected_projects = request.form.getlist('assigned_projects')
                
                # Validate and filter project IDs
                valid_project_ids = []
                if selected_projects:
                    for pid in selected_projects:
                        try:
                            project_id = int(pid)
                            # Verify project exists
                            if Project.query.get(project_id):
                                valid_project_ids.append(project_id)
                        except (ValueError, TypeError):
                            logger_handler.logger.warning(f"Invalid project ID received: {pid}")
                
                # Add project permissions
                if valid_project_ids:
                    for project_id in valid_project_ids:
                        try:
                            permission = UserProjectPermission(
                                user_id=new_user.id,
                                project_id=project_id
                            )
                            db.session.add(permission)
                        except Exception as e:
                            logger_handler.logger.error(f"Error adding project permission: {e}")
                    
                    logger_handler.logger.info(
                        f"Admin {session['username']} assigned {len(valid_project_ids)} projects to new Project Manager {username}"
                    )

                # Get selected locations
                selected_locations = request.form.getlist('assigned_locations')
                
                # Filter and clean location names
                valid_locations = []
                if selected_locations:
                    for location in selected_locations:
                        location_clean = location.strip()
                        if location_clean:
                            valid_locations.append(location_clean)
                
                # Add location permissions
                if valid_locations:
                    for location_name in valid_locations:
                        try:
                            permission = UserLocationPermission(
                                user_id=new_user.id,
                                location_name=location_name
                            )
                            db.session.add(permission)
                        except Exception as e:
                            logger_handler.logger.error(f"Error adding location permission: {e}")
                    
                    logger_handler.logger.info(
                        f"Admin {session['username']} assigned {len(valid_locations)} locations to new Project Manager {username}"
                    )

            # Commit all changes
            db.session.commit()

            # Log user creation
            logger_handler.logger.info(f"Admin user {session['username']} created new user: {username} with role {role}")

            flash(f'User "{full_name}" created successfully with role "{role}".', 'success')
            return redirect(url_for('users.users'))

        except KeyError as e:
            db.session.rollback()
            logger_handler.logger.error(f"Missing form field: {e}")
            flash(f'Missing required field: {e}. Please fill in all fields.', 'error')
            projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
            locations = get_all_locations_from_qr_codes()
            return render_template('create_user.html', projects=projects, locations=locations)
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('user_creation', e)
            logger_handler.logger.error(f"User creation error details: {str(e)}")
            flash('User creation failed. Please try again.', 'error')
            projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
            locations = get_all_locations_from_qr_codes()
            return render_template('create_user.html', projects=projects, locations=locations)

    # GET request - load form with projects and locations
    try:
        projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
        locations = get_all_locations_from_qr_codes()
        return render_template('create_user.html', projects=projects, locations=locations)
    except Exception as e:
        logger_handler.logger.error(f"Error loading create user form: {e}")
        flash('Error loading form. Please try again.', 'error')
        return redirect(url_for('users.users'))

def get_all_locations_from_qr_codes():
    """Helper function to get all unique locations from QR codes"""
    try:
        result = db.session.execute(text("""
            SELECT DISTINCT location 
            FROM qr_codes 
            WHERE location IS NOT NULL 
            AND active_status = 1
            ORDER BY location
        """))
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger_handler.logger.error(f"Error loading locations: {e}")
        return []
    
@bp.route('/users/<int:user_id>/delete', methods=['GET', 'POST'], endpoint='delete_user')
@admin_required
def delete_user(user_id):
    """Deactivate user (Admin only) - Fixed with proper validation"""
    try:
        user_to_delete = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_delete:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        # Prevent self-deletion
        if user_to_delete.id == current_user.id:
            flash('You cannot deactivate your own account. Ask another admin to do this.', 'error')
            return redirect(url_for('users.users'))

        # Check if trying to delete the last admin
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate the last admin user. Promote another user to admin first.', 'error')
                return redirect(url_for('users.users'))

        # Deactivate the user instead of deleting
        user_to_delete.active_status = False
        db.session.commit()

        flash(f'User "{user_to_delete.full_name}" has been deactivated successfully.', 'success')
        print(f"Admin {current_user.username} deactivated user: {user_to_delete.username}")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        print(f"Error deactivating user: {e}")
        flash('Error deactivating user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/reactivate', methods=['GET', 'POST'], endpoint='reactivate_user')
@admin_required
def reactivate_user(user_id):
    """Reactivate a deactivated user (Admin only)"""
    try:
        user_to_reactivate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_reactivate:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        if user_to_reactivate.active_status:
            flash('User is already active.', 'info')
        else:
            user_to_reactivate.active_status = True
            db.session.commit()
            flash(f'User "{user_to_reactivate.full_name}" has been reactivated successfully.', 'success')
            print(f"Admin {current_user.username} reactivated user: {user_to_reactivate.username}")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        print(f"Error reactivating user: {e}")
        flash('Error reactivating user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/promote', methods=['GET', 'POST'], endpoint='promote_user')
@admin_required
def promote_user(user_id):
    """Promote a staff user to admin (Admin only)"""
    try:
        user_to_promote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_promote:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        if user_to_promote.role == 'admin':
            flash('User is already an admin.', 'info')
        else:
            user_to_promote.role = 'admin'
            db.session.commit()
            flash(f'"{user_to_promote.full_name}" has been promoted to admin.', 'success')
            print(f"Admin {current_user.username} promoted user {user_to_promote.username} to admin")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        print(f"Error promoting user: {e}")
        flash('Error promoting user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/demote', methods=['GET', 'POST'], endpoint='demote_user')
@admin_required
def demote_user(user_id):
    """Demote an admin user to staff (Admin only)"""
    try:
        user_to_demote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_demote:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        # Prevent self-demotion
        if user_to_demote.id == current_user.id:
            flash('You cannot demote yourself. Have another admin do this.', 'error')
            return redirect(url_for('users.users'))

        # Check if this is the last admin
        active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
        if active_admin_count <= 1 and user_to_demote.role == 'admin':
            flash('Cannot demote the last admin user. Promote another user to admin first.', 'error')
            return redirect(url_for('users.users'))

        if has_staff_level_access(user_to_demote.role):
            flash('User already has staff-level permissions.', 'info')
        else:
            user_to_demote.role = 'staff'
            db.session.commit()
            flash(f'"{user_to_demote.full_name}" has been demoted to staff.', 'success')
            print(f"Admin {current_user.username} demoted user {user_to_demote.username} to staff")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        print(f"Error demoting user: {e}")
        flash('Error demoting user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'], endpoint='edit_user')
@admin_required
@log_database_operations('user_edit')
def edit_user(user_id):
    """Edit existing user with Project Manager permissions support"""
    try:
        user_to_edit = User.query.get_or_404(user_id)
        
        # Track old role for permission cleanup
        old_role = user_to_edit.role

        if request.method == 'POST':
            # Store old values for change tracking
            old_values = {
                'full_name': user_to_edit.full_name,
                'email': user_to_edit.email,
                'username': user_to_edit.username,
                'role': user_to_edit.role,
                'active_status': user_to_edit.active_status
            }
            changes = {}

            # Update basic info with validation
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            
            if not all([full_name, email, username]):
                flash('Name, email, and username are required.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                assigned_project_ids = []
                assigned_location_names = []
                if user_to_edit.role == 'project_manager':
                    assigned_project_ids = [p.project_id for p in UserProjectPermission.query.filter_by(user_id=user_id).all()]
                    assigned_location_names = [l.location_name for l in UserLocationPermission.query.filter_by(user_id=user_id).all()]
                return render_template('edit_user.html', user=user_to_edit, valid_roles=VALID_ROLES,
                                     projects=projects, locations=locations,
                                     assigned_project_ids=assigned_project_ids,
                                     assigned_location_names=assigned_location_names)

            user_to_edit.full_name = full_name
            user_to_edit.email = email
            user_to_edit.username = username
            
            # Update role with validation
            new_role = request.form.get('role', '')
            if new_role not in VALID_ROLES:
                flash(f'Invalid role selected. Valid roles: {", ".join(VALID_ROLES)}', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                locations = get_all_locations_from_qr_codes()
                assigned_project_ids = []
                assigned_location_names = []
                if user_to_edit.role == 'project_manager':
                    assigned_project_ids = [p.project_id for p in UserProjectPermission.query.filter_by(user_id=user_id).all()]
                    assigned_location_names = [l.location_name for l in UserLocationPermission.query.filter_by(user_id=user_id).all()]
                return render_template('edit_user.html', user=user_to_edit, valid_roles=VALID_ROLES,
                                     projects=projects, locations=locations,
                                     assigned_project_ids=assigned_project_ids,
                                     assigned_location_names=assigned_location_names)

            user_to_edit.role = new_role

            # Handle password update if provided
            new_password = request.form.get('new_password', '')
            if new_password and new_password.strip():
                user_to_edit.set_password(new_password)
                changes['password'] = 'Password updated'
                # Log password change
                logger_handler.log_security_event(
                    event_type="admin_password_change",
                    description=f"Admin {session['username']} changed password for user {user_to_edit.username}",
                    severity="MEDIUM"
                )

            # Handle Project Manager permissions
            if new_role == 'project_manager':
                # Update project permissions
                # First, remove existing project permissions
                try:
                    UserProjectPermission.query.filter_by(user_id=user_id).delete()
                except Exception as e:
                    logger_handler.logger.error(f"Error deleting old project permissions: {e}")
                
                # Add new project permissions
                selected_projects = request.form.getlist('assigned_projects')
                
                # Validate project IDs
                valid_project_ids = []
                if selected_projects:
                    for pid in selected_projects:
                        try:
                            project_id = int(pid)
                            # Verify project exists
                            if Project.query.get(project_id):
                                valid_project_ids.append(project_id)
                        except (ValueError, TypeError):
                            logger_handler.logger.warning(f"Invalid project ID received: {pid}")
                
                # Add validated project permissions
                if valid_project_ids:
                    for project_id in valid_project_ids:
                        try:
                            permission = UserProjectPermission(
                                user_id=user_id,
                                project_id=project_id
                            )
                            db.session.add(permission)
                        except Exception as e:
                            logger_handler.logger.error(f"Error adding project permission: {e}")
                    
                    changes['assigned_projects'] = f'{len(valid_project_ids)} projects assigned'
                    logger_handler.logger.info(
                        f"Admin {session['username']} updated project permissions for Project Manager {user_to_edit.username}: {len(valid_project_ids)} projects"
                    )

                # Update location permissions
                # First, remove existing location permissions
                try:
                    UserLocationPermission.query.filter_by(user_id=user_id).delete()
                except Exception as e:
                    logger_handler.logger.error(f"Error deleting old location permissions: {e}")
                
                # Add new location permissions
                selected_locations = request.form.getlist('assigned_locations')
                
                # Validate and clean locations
                valid_locations = []
                if selected_locations:
                    for location in selected_locations:
                        location_clean = location.strip()
                        if location_clean:
                            valid_locations.append(location_clean)
                
                # Add validated location permissions
                if valid_locations:
                    for location_name in valid_locations:
                        try:
                            permission = UserLocationPermission(
                                user_id=user_id,
                                location_name=location_name
                            )
                            db.session.add(permission)
                        except Exception as e:
                            logger_handler.logger.error(f"Error adding location permission: {e}")
                    
                    changes['assigned_locations'] = f'{len(valid_locations)} locations assigned'
                    logger_handler.logger.info(
                        f"Admin {session['username']} updated location permissions for Project Manager {user_to_edit.username}: {len(valid_locations)} locations"
                    )
            
            # If role changed from project_manager to something else, remove permissions
            elif old_role == 'project_manager' and new_role != 'project_manager':
                try:
                    UserProjectPermission.query.filter_by(user_id=user_id).delete()
                    UserLocationPermission.query.filter_by(user_id=user_id).delete()
                    logger_handler.logger.info(
                        f"Admin {session['username']} removed Project Manager permissions from user {user_to_edit.username} (role changed to {new_role})"
                    )
                except Exception as e:
                    logger_handler.logger.error(f"Error removing permissions: {e}")

            # Track changes
            for field, old_value in old_values.items():
                new_value = getattr(user_to_edit, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}

            # Commit all changes
            db.session.commit()

            # Log user update
            if changes:
                logger_handler.logger.info(f"Admin user {session['username']} updated user {user_to_edit.username}: {json.dumps(changes, default=str)}")

            flash(f'User "{user_to_edit.full_name}" updated successfully.', 'success')
            return redirect(url_for('users.users'))

        # GET request - load form with current assignments
        try:
            projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
            locations = get_all_locations_from_qr_codes()
            
            # Get current assignments if user is a project manager
            assigned_project_ids = []
            assigned_location_names = []
            
            if user_to_edit.role == 'project_manager':
                try:
                    assigned_project_ids = [p.project_id for p in UserProjectPermission.query.filter_by(user_id=user_id).all()]
                    assigned_location_names = [l.location_name for l in UserLocationPermission.query.filter_by(user_id=user_id).all()]
                except Exception as e:
                    logger_handler.logger.error(f"Error loading current permissions: {e}")

            return render_template('edit_user.html', 
                                 user=user_to_edit, 
                                 valid_roles=VALID_ROLES,
                                 projects=projects,
                                 locations=locations,
                                 assigned_project_ids=assigned_project_ids,
                                 assigned_location_names=assigned_location_names)
        except Exception as e:
            logger_handler.logger.error(f"Error loading edit user form: {e}")
            flash('Error loading edit form. Please try again.', 'error')
            return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_update', e)
        logger_handler.logger.error(f"User update error details: {str(e)}")
        flash('Error updating user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/toggle-status', methods=['POST'], endpoint='toggle_user_status')
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status via AJAX (Admin only)"""
    try:
        user_to_toggle = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_toggle:
            return jsonify({
                'success': False,
                'message': 'User not found.'
            }), 404

        # Prevent self-deactivation
        if user_to_toggle.id == current_user.id:
            return jsonify({
                'success': False,
                'message': 'You cannot deactivate yourself.'
            }), 400

        # Check if trying to deactivate the last admin
        if (user_to_toggle.role == 'admin' and
            user_to_toggle.active_status and
            User.query.filter_by(role='admin', active_status=True).count() <= 1):
            return jsonify({
                'success': False,
                'message': 'Cannot deactivate the last admin user.'
            }), 400

        # Toggle the status
        new_status = not user_to_toggle.active_status
        user_to_toggle.active_status = new_status
        db.session.commit()

        action = 'activated' if new_status else 'deactivated'
        message = f'"{user_to_toggle.full_name}" has been {action} successfully.'

        # Log status change
        logger_handler.logger.info(f"Admin {current_user.username} {action} user {user_to_toggle.username}")

        print(f"Admin {current_user.username} {action} user {user_to_toggle.username}")

        return jsonify({
            'success': True,
            'message': message,
            'new_status': new_status,
            'user_id': user_id
        })

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_status_toggle', e)
        print(f"Error toggling user status: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating user status. Please try again.'
        }), 500

@bp.route('/users/<int:user_id>/activate', methods=['GET', 'POST'], endpoint='activate_user')
@admin_required
def activate_user(user_id):
    """Activate a user (Admin only) - Alternative route"""
    try:
        user_to_activate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_activate:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        if user_to_activate.active_status:
            flash('User is already active.', 'info')
        else:
            user_to_activate.active_status = True
            db.session.commit()

            # Log activation
            logger_handler.logger.info(f"Admin {current_user.username} activated user {user_to_activate.username}")

            flash(f'"{user_to_activate.full_name}" has been activated.', 'success')
            print(f"Admin {current_user.username} activated user {user_to_activate.username}")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_activation', e)
        print(f"Error activating user: {e}")
        flash('Error activating user. Please try again.', 'error')
        return redirect(url_for('users.users'))

@bp.route('/users/<int:user_id>/deactivate', methods=['GET', 'POST'], endpoint='deactivate_user')
@admin_required
def deactivate_user(user_id):
    """Deactivate a user (Admin only) - Alternative route"""
    try:
        user_to_deactivate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])

        if not user_to_deactivate:
            flash('User not found.', 'error')
            return redirect(url_for('users.users'))

        # Prevent self-deactivation
        if user_to_deactivate.id == current_user.id:
            flash('You cannot deactivate yourself.', 'error')
            return redirect(url_for('users.users'))

        # Check if this is the last admin
        if user_to_deactivate.role == 'admin' and user_to_deactivate.active_status:
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate the last admin user.', 'error')
                return redirect(url_for('users.users'))

        if not user_to_deactivate.active_status:
            flash('User is already inactive.', 'info')
        else:
            user_to_deactivate.active_status = False
            db.session.commit()

            # Log deactivation
            logger_handler.logger.info(f"Admin {current_user.username} deactivated user {user_to_deactivate.username}")

            flash(f'"{user_to_deactivate.full_name}" has been deactivated.', 'success')
            print(f"Admin {current_user.username} deactivated user {user_to_deactivate.username}")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_deactivation', e)
        print(f"Error deactivating user: {e}")
        flash('Error deactivating user. Please try again.', 'error')
        return redirect(url_for('users.users'))

# ENHANCED USER STATISTICS API
@bp.route('/api/users/stats', endpoint='user_stats_api')
@admin_required
def user_stats_api():
    """API endpoint to get user statistics for dashboard"""
    try:
        # Get current date for recent activity calculations
        one_week_ago = datetime.now() - timedelta(days=7)

        total_users = User.query.count()
        active_users = User.query.filter_by(active_status=True).count()
        admin_users = User.query.filter_by(role='admin', active_status=True).count()
        staff_users = User.query.filter_by(role='staff', active_status=True).count()
        payroll_users = User.query.filter_by(role='payroll', active_status=True).count()
        project_manager_users = User.query.filter_by(role='project_manager', active_status=True).count()
        accounting_users = User.query.filter_by(role='accounting', active_status=True).count()
        inactive_users = User.query.filter_by(active_status=False).count()

        recent_registrations = User.query.filter(
            User.created_date >= one_week_ago
        ).count()

        recent_logins = User.query.filter(
            User.last_login_date >= one_week_ago
        ).count()

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'staff_users': staff_users,
            'payroll_users': payroll_users,
            'project_manager_users': project_manager_users,
            'accounting_users': accounting_users,
            'inactive_users': inactive_users,
            'recent_registrations': recent_registrations,
            'recent_logins': recent_logins
        })

    except Exception as e:
        logger_handler.log_database_error('user_stats_api', e)
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': 'Failed to fetch user statistics'}), 500
    
@bp.route('/api/locations-by-projects', methods=['POST'], endpoint='get_locations_by_projects')
@admin_required
def get_locations_by_projects():
    """Get locations that belong to selected projects"""
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        
        if not project_ids:
            # No projects selected, return empty list
            return jsonify({
                'success': True,
                'locations': [],
                'message': 'No projects selected'
            })
        
        # Get unique locations from QR codes that belong to selected projects
        result = db.session.execute(text("""
            SELECT DISTINCT location 
            FROM qr_codes 
            WHERE project_id IN :project_ids
            AND location IS NOT NULL 
            AND active_status = 1
            ORDER BY location
        """), {'project_ids': tuple(project_ids)})
        
        locations = [row[0] for row in result.fetchall()]
        
        return jsonify({
            'success': True,
            'locations': locations,
            'count': len(locations)
        })
        
    except Exception as e:
        logger_handler.logger.error(f"Error fetching locations by projects: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/roles/permissions', endpoint='role_permissions_api')
@admin_required
def role_permissions_api():
    """API endpoint to get role permissions data"""
    try:
        permissions_data = {}
        for role in VALID_ROLES:
            permissions_data[role] = get_role_permissions(role)

        return jsonify({
            'success': True,
            'roles': permissions_data,
            'valid_roles': VALID_ROLES,
            'staff_level_roles': STAFF_LEVEL_ROLES
        })

    except Exception as e:
        print(f"Error fetching role permissions: {e}")
        return jsonify({'error': 'Failed to fetch role permissions'}), 500

@bp.route('/api/geocode', methods=['POST'], endpoint='geocode_address_api')
@login_required
def geocode_address_api():
    """API endpoint to geocode an address and return coordinates using Google Maps"""
    try:
        data = request.get_json()
        address = data.get('address', '').strip()

        if not address:
            return jsonify({
                'success': False,
                'message': 'Address is required'
            }), 400

        # Log API geocoding request
        try:
            logger_handler.log_user_activity('api_geocoding_request', f'API geocoding request: {address[:50]}...')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")

        # Use the enhanced function that returns 3 values
        lat, lng, accuracy = get_coordinates_from_address_enhanced(address)

        if lat is not None and lng is not None:
            # Log successful API geocoding
            try:
                logger_handler.log_user_activity('api_geocoding_success', f'API geocoding success: {address[:50]}... -> {lat}, {lng} ({accuracy})')
            except Exception as log_error:
                print(f"⚠️ Logging error (non-critical): {log_error}")

            return jsonify({
                'success': True,
                'data': {
                    'latitude': lat,
                    'longitude': lng,
                    'accuracy': accuracy,
                    'coordinates_display': f"{lat:.10f}, {lng:.10f}",
                    'service_used': 'Google Maps' if gmaps_client else 'OpenStreetMap'
                },
                'message': f'Address geocoded successfully with {accuracy} accuracy using {"Google Maps" if gmaps_client else "OpenStreetMap"}'
            })
        else:
            # Log failed API geocoding
            try:
                logger_handler.log_user_activity('api_geocoding_failed', f'API geocoding failed: {address[:50]}...')
            except Exception as log_error:
                print(f"⚠️ Logging error (non-critical): {log_error}")

            return jsonify({
                'success': False,
                'message': 'Unable to geocode the provided address. Please verify the address is complete and accurate.'
            }), 404

    except Exception as e:
        print(f"❌ Geocoding API error: {e}")
        
        # Log API geocoding error
        try:
            logger_handler.log_flask_error('api_geocoding_error', f'API geocoding error: {str(e)}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")

        return jsonify({
            'success': False,
            'message': 'Internal server error during geocoding. Please try again.'
        }), 500

@bp.route('/api/reverse-geocode', methods=['POST'], endpoint='reverse_geocode_api')
@login_required
def reverse_geocode_api():
    """API endpoint for reverse geocoding coordinates to address using Google Maps"""
    try:
        data = request.get_json()
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'message': 'Latitude and longitude are required'
            }), 400

        # Log API reverse geocoding request
        try:
            logger_handler.log_user_activity('api_reverse_geocoding_request', f'API reverse geocoding: {latitude}, {longitude}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")

        # Use the reverse geocoding function
        address = reverse_geocode_coordinates(latitude, longitude)

        if address:
            return jsonify({
                'success': True,
                'data': {
                    'address': address,
                    'coordinates': f"{latitude}, {longitude}",
                    'service_used': 'Google Maps' if gmaps_client else 'OpenStreetMap'
                },
                'message': f'Coordinates reverse geocoded successfully using {"Google Maps" if gmaps_client else "OpenStreetMap"}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to reverse geocode the provided coordinates.'
            }), 404

    except Exception as e:
        print(f"❌ Reverse geocoding API error: {e}")
        
        # Log API reverse geocoding error
        try:
            logger_handler.log_flask_error('api_reverse_geocoding_error', f'API reverse geocoding error: {str(e)}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")

        return jsonify({
            'success': False,
            'message': 'Internal server error during reverse geocoding. Please try again.'
        }), 500

@bp.route('/users/<int:user_id>/permanently-delete', methods=['GET', 'POST'], endpoint='permanently_delete_user')
@admin_required
def permanently_delete_user(user_id):
    """Permanently delete user but preserve associated QR codes (Admin only)"""
    try:
        user_to_delete = User.query.get_or_404(user_id)
        current_user = User.query.get(session['user_id'])

        # Security checks
        if user_to_delete.id == current_user.id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('users.users'))

        # Only allow deletion of inactive users for safety
        if user_to_delete.active_status:
            flash('User must be deactivated before permanent deletion.', 'error')
            return redirect(url_for('users.users'))

        # If deleting an admin, ensure at least one admin remains
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot delete the last admin user in the system.', 'error')
                return redirect(url_for('users.users'))

        user_name = user_to_delete.full_name
        user_qr_count = user_to_delete.created_qr_codes.count()
        username = user_to_delete.username

        # MODIFIED: Preserve QR codes by setting created_by to NULL instead of deleting them
        orphaned_qr_codes = QRCode.query.filter_by(created_by=user_id).all()
        for qr_code in orphaned_qr_codes:
            qr_code.created_by = None

        # Update any users that were created by this user (set created_by to None)
        created_users = User.query.filter_by(created_by=user_id).all()
        for created_user in created_users:
            created_user.created_by = None

        # Log user deletion before actual deletion
        logger_handler.log_security_event(
            event_type="user_permanent_deletion",
            description=f"Admin {current_user.username} permanently deleted user {username}",
            severity="HIGH",
            additional_data={'deleted_user': username, 'qr_codes_orphaned': user_qr_count}
        )

        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()

        # Updated flash message to reflect QR codes are preserved
        flash(f'User "{user_name}" has been permanently deleted. {user_qr_count} QR codes created by this user are now orphaned but preserved.', 'success')
        print(f"Admin {current_user.username} permanently deleted user: {username}, preserved {user_qr_count} QR codes")

        return redirect(url_for('users.users'))

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_permanent_deletion', e)
        print(f"Error permanently deleting user: {e}")
        flash('Error deleting user. Please try again.', 'error')
        return redirect(url_for('users.users'))

# Admin logging routes