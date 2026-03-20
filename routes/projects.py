"""
routes/projects.py
==================
Project CRUD and related API routes.

Routes: /projects, /projects/create, /projects/<id>/edit,
        /projects/<id>/toggle, /api/projects/active
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, url_for
import json
from datetime import datetime

from extensions import db, logger_handler
from models.project import Project
from models.user import User
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import admin_required, login_required, staff_or_admin_required

bp = Blueprint('projects', __name__)



@bp.route('/projects', endpoint='projects')
@admin_required
def projects():
    """Display all projects"""
    try:
        projects = Project.query.order_by(Project.created_date.desc()).all()
        return render_template('projects.html', projects=projects)
    except Exception as e:
        logger_handler.log_database_error('projects_list', e)
        flash('Error loading projects list.', 'error')
        return redirect(url_for('dashboard.dashboard'))

@bp.route('/projects/create', methods=['GET', 'POST'], endpoint='create_project')
@admin_required
@log_database_operations('project_creation')
def create_project():
    """Create new project"""
    if request.method == 'POST':
        try:
            name = request.form['name']
            description = request.form.get('description', '')

            # Check if project name already exists
            if Project.query.filter_by(name=name).first():
                flash('Project name already exists.', 'error')
                return render_template('create_project.html')

            # Create new project
            new_project = Project(
                name=name,
                description=description,
                created_by=session['user_id']
            )

            db.session.add(new_project)
            db.session.commit()

            # Log project creation
            logger_handler.logger.info(f"User {session['username']} created new project: {name}")

            flash(f'Project "{name}" created successfully.', 'success')
            return redirect(url_for('projects.projects'))

        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('project_creation', e)
            flash('Project creation failed. Please try again.', 'error')

    return render_template('create_project.html')

@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'], endpoint='edit_project')
@admin_required
@log_database_operations('project_edit')
def edit_project(project_id):
    """Edit existing project"""
    try:
        project = Project.query.get_or_404(project_id)

        if request.method == 'POST':
            old_name = project.name
            old_description = project.description

            project.name = request.form['name']
            project.description = request.form.get('description', '')

            db.session.commit()

            # Log project update
            changes = {}
            if old_name != project.name:
                changes['name'] = {'old': old_name, 'new': project.name}
            if old_description != project.description:
                changes['description'] = {'old': old_description, 'new': project.description}

            if changes:
                logger_handler.logger.info(f"User {session['username']} updated project {project_id}: {json.dumps(changes)}")

            flash(f'Project "{project.name}" updated successfully.', 'success')
            return redirect(url_for('projects.projects'))

        return render_template('edit_project.html', project=project)

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('project_edit', e)
        flash('Project update failed. Please try again.', 'error')
        return redirect(url_for('projects.projects'))

@bp.route('/projects/<int:project_id>/toggle', methods=['POST'], endpoint='toggle_project')
@admin_required
@log_database_operations('project_toggle')
def toggle_project(project_id):
    """Toggle project active status"""
    try:
        project = Project.query.get_or_404(project_id)
        old_status = project.active_status
        project.active_status = not project.active_status

        db.session.commit()

        # Log status change
        status = "activated" if project.active_status else "deactivated"
        logger_handler.logger.info(f"User {session['username']} {status} project: {project.name}")

        flash(f'Project "{project.name}" {status} successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('project_toggle', e)
        flash('Failed to update project status.', 'error')

    return redirect(url_for('projects.projects'))

# API ENDPOINTS FOR DROPDOWN FUNCTIONALITY
@bp.route('/api/projects/active', endpoint='api_active_projects')
@login_required
def api_active_projects():
    """Get active projects for dropdown"""
    try:
        projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()

        projects_data = [
            {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'qr_count': project.qr_count
            }
            for project in projects
        ]

        return jsonify({
            'success': True,
            'projects': projects_data
        })

    except Exception as e:
        logger_handler.log_database_error('api_active_projects', e)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch projects'
        }), 500

# QR CODE MANAGEMENT ROUTES