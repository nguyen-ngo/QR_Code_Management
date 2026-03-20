"""
routes/dashboard.py
===================
Dashboard and related API routes.

Routes: /dashboard, /project/<id>/qr-codes, /dashboard/search,
        /api/dashboard/stats, /api/dashboard/realtime
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify
from datetime import datetime, timedelta, date, time

from extensions import db, logger_handler
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import url_for, login_required

bp = Blueprint('dashboard', __name__)

def _get_models():
    """Return model classes from the current app context."""
    from flask import current_app
    return current_app.config['_models']


@bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    """Enhanced project-centric dashboard with search filters"""
    User, QRCode, Project, AttendanceData = _get_models()["User"], _get_models()["QRCode"], _get_models()["Project"], _get_models()["AttendanceData"]
    try:
        user = User.query.get(session['user_id'])
        
        # Get search parameters from URL
        search_name = request.args.get('search_name', '').strip()
        search_status = request.args.get('search_status', '').strip()
        
        # Build QR codes query with filters
        qr_query = QRCode.query
        
        # Apply name filter if provided
        if search_name:
            qr_query = qr_query.filter(QRCode.name.ilike(f'%{search_name}%'))
        
        # Apply status filter if provided
        if search_status == 'active':
            qr_query = qr_query.filter(QRCode.active_status == True)
        elif search_status == 'inactive':
            qr_query = qr_query.filter(QRCode.active_status == False)
        
        # Execute query
        qr_codes = qr_query.order_by(QRCode.created_date.desc()).all()
        projects = Project.query.order_by(Project.name.asc()).all()
        
        # Log dashboard access with filter info
        filter_info = []
        if search_name:
            filter_info.append(f"name contains '{search_name}'")
        if search_status:
            filter_info.append(f"status is {search_status}")
        
        log_message = f"User {session['username']} accessed dashboard: {len(qr_codes)} QR codes"
        if filter_info:
            log_message += f" (filtered: {', '.join(filter_info)})"
        
        logger_handler.logger.info(log_message)
        
        return render_template('dashboard.html',
                             user=user,
                             qr_codes=qr_codes,
                             projects=projects,
                             search_name=search_name,
                             search_status=search_status)
    
    except Exception as e:
        logger_handler.log_database_error('dashboard_load', e)
        print(f"Error loading dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('login'))

@bp.route('/project/<int:project_id>/qr-codes', endpoint='project_qr_codes')
@login_required
def project_qr_codes(project_id):
    """
    View all QR codes for a specific project with search filters
    Allows filtering by name and status within the project
    """
    User, QRCode, Project, AttendanceData = _get_models()["User"], _get_models()["QRCode"], _get_models()["Project"], _get_models()["AttendanceData"]
    try:
        # Get the project
        project = Project.query.get_or_404(project_id)
        
        # Get search parameters from URL
        search_name = request.args.get('search_name', '').strip()
        search_status = request.args.get('search_status', '').strip()
        
        # Build QR codes query with filters for this project only
        qr_query = QRCode.query.filter_by(project_id=project_id)
        
        # Apply name filter if provided
        if search_name:
            qr_query = qr_query.filter(QRCode.name.ilike(f'%{search_name}%'))
        
        # Apply status filter if provided
        if search_status == 'active':
            qr_query = qr_query.filter(QRCode.active_status == True)
        elif search_status == 'inactive':
            qr_query = qr_query.filter(QRCode.active_status == False)
        
        # Execute query
        qr_codes = qr_query.order_by(QRCode.created_date.desc()).all()
        
        # Log access with filter info
        filter_info = []
        if search_name:
            filter_info.append(f"name contains '{search_name}'")
        if search_status:
            filter_info.append(f"status is {search_status}")
        
        log_message = f"User {session['username']} viewed project '{project.name}' QR codes: {len(qr_codes)} QR codes"
        if filter_info:
            log_message += f" (filtered: {', '.join(filter_info)})"
        
        logger_handler.logger.info(log_message)
        
        return render_template('project_qr_codes.html',
                             project=project,
                             qr_codes=qr_codes,
                             search_name=search_name,
                             search_status=search_status)
    
    except Exception as e:
        logger_handler.log_database_error('project_qr_codes_view', e)
        print(f"Error loading project QR codes: {e}")
        flash('Error loading project QR codes. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    
@bp.route('/dashboard/search', methods=['GET'], endpoint='search_qr_codes')
@login_required
def search_qr_codes():
    """Search QR codes - redirect to dashboard with filters"""
    User, QRCode, Project, AttendanceData = _get_models()["User"], _get_models()["QRCode"], _get_models()["Project"], _get_models()["AttendanceData"]
    search_name = request.args.get('search_name', '').strip()
    search_status = request.args.get('search_status', '').strip()
    
    # Log search activity
    logger_handler.logger.info(
        f"User {session['username']} searched QR codes: "
        f"name='{search_name}', status='{search_status}'"
    )
    
    # Redirect to dashboard with search parameters
    return redirect(url_for('dashboard', search_name=search_name, search_status=search_status))

@bp.route('/api/dashboard/stats', endpoint='dashboard_stats_api')
@login_required
def dashboard_stats_api():
    """API endpoint for dashboard statistics"""
    User, QRCode, Project, AttendanceData = _get_models()["User"], _get_models()["QRCode"], _get_models()["Project"], _get_models()["AttendanceData"]
    try:
        # Get current stats
        total_qr_codes = QRCode.query.filter_by(active_status=True).count()
        
        # Today's check-ins
        today = datetime.utcnow().date()
        today_checkins = AttendanceData.query.filter(
            AttendanceData.check_in_date == today
        ).count()
        
        # Active projects
        active_projects = Project.query.filter_by(active_status=True).count()
        
        # Unique locations
        unique_locations = db.session.query(
            AttendanceData.location_name
        ).distinct().count()
        
        # Calculate trends (compared to last month)
        last_month = datetime.utcnow() - timedelta(days=30)
        
        # QR codes trend
        old_qr_count = QRCode.query.filter(
            QRCode.created_date <= last_month,
            QRCode.active_status == True
        ).count()
        qr_change = ((total_qr_codes - old_qr_count) / max(old_qr_count, 1)) * 100
        
        # Check-ins trend (yesterday)
        yesterday = today - timedelta(days=1)
        yesterday_checkins = AttendanceData.query.filter(
            AttendanceData.check_in_date == yesterday
        ).count()
        checkin_change = ((today_checkins - yesterday_checkins) / max(yesterday_checkins, 1)) * 100
        
        return jsonify({
            'success': True,
            'total_qr_codes': total_qr_codes,
            'today_checkins': today_checkins,
            'active_projects': active_projects,
            'unique_locations': unique_locations,
            'qr_change': round(qr_change, 1),
            'checkin_change': round(checkin_change, 1),
            'project_change': 0,  # You can calculate this based on your needs
            'location_change': 0   # You can calculate this based on your needs
        })
        
    except Exception as e:
        logger_handler.log_database_error('dashboard_stats_api', e)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch dashboard statistics'
        }), 500

@bp.route('/api/dashboard/realtime', endpoint='dashboard_realtime_api')
@login_required
def dashboard_realtime_api():
    """API endpoint for real-time dashboard data"""
    User, QRCode, Project, AttendanceData = _get_models()["User"], _get_models()["QRCode"], _get_models()["Project"], _get_models()["AttendanceData"]
    try:
        # Get recent activity (last 10 check-ins)
        recent_activity = db.session.query(
            AttendanceData.employee_id,
            AttendanceData.location_name,
            AttendanceData.check_in_time,
            AttendanceData.check_in_date
        ).order_by(
            AttendanceData.check_in_date.desc(),
            AttendanceData.check_in_time.desc()
        ).limit(10).all()
        
        activity_data = [
            {
                'employee_id': activity.employee_id,
                'location': activity.location_name,
                'time': activity.check_in_time.strftime('%H:%M'),
                'date': activity.check_in_date.strftime('%Y-%m-%d')
            }
            for activity in recent_activity
        ]
        
        return jsonify({
            'success': True,
            'recent_activity': activity_data
        })
        
    except Exception as e:
        logger_handler.log_database_error('dashboard_realtime_api', e)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch real-time data'
        }), 500
    
# USER MANAGEMENT ROUTES