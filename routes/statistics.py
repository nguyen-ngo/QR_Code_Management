"""
routes/statistics.py
====================
Statistics dashboard and export routes.

Routes: /statistics, /api/statistics/export
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, send_file, make_response, current_app, url_for
from datetime import datetime, date, timedelta
import io, json, traceback

from extensions import db, logger_handler
from models.employee import Employee
from models.project import Project
from models.user import User
from sqlalchemy import text
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import login_required, staff_or_admin_required

bp = Blueprint('statistics', __name__)



@bp.route('/statistics', endpoint='qr_statistics')
@login_required
def qr_statistics():
    """QR Code Statistics Dashboard with comprehensive analytics"""
    try:
        # Log statistics page access
        logger_handler.logger.info(f"User {session.get('username', 'unknown')} accessed QR code statistics dashboard")
        
        # Get filter parameters
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        qr_code_filter = request.args.get('qr_code', '')
        project_filter = request.args.get('project', '')
        
        # Build date filter
        date_filter = ""
        if date_from:
            date_filter += f" AND ad.check_in_date >= '{date_from}'"
        if date_to:
            date_filter += f" AND ad.check_in_date <= '{date_to}'"
        
        # QR Code filter
        qr_filter = ""
        if qr_code_filter:
            qr_filter = f" AND ad.qr_code_id = {qr_code_filter}"
            
        # Project filter
        project_filter_clause = ""
        if project_filter:
            project_filter_clause = f" AND qc.project_id = {project_filter}"

        # 1. General Statistics
        general_stats = db.session.execute(text(f"""
            SELECT 
                COUNT(*) as total_scans,
                COUNT(DISTINCT ad.employee_id) as unique_users,
                COUNT(DISTINCT ad.qr_code_id) as active_qr_codes,
                COUNT(DISTINCT DATE(ad.check_in_date)) as active_days,
                COUNT(CASE WHEN ad.check_in_date = CURRENT_DATE THEN 1 END) as today_scans,
                COUNT(CASE WHEN ad.check_in_date >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY) THEN 1 END) as week_scans,
                COUNT(CASE WHEN ad.latitude IS NOT NULL AND ad.longitude IS NOT NULL THEN 1 END) as gps_enabled_scans
            FROM attendance_data ad
            LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE 1=1 {date_filter} {qr_filter} {project_filter_clause}
        """)).fetchone()

        # 2. Device Statistics
        device_stats = db.session.execute(text(f"""
            SELECT 
                CASE 
                    WHEN device_info LIKE '%iPhone%' OR device_info LIKE '%iOS%' THEN 'iOS'
                    WHEN device_info LIKE '%Android%' THEN 'Android'
                    WHEN device_info LIKE '%Windows%' THEN 'Windows'
                    WHEN device_info LIKE '%Mac%' OR device_info LIKE '%macOS%' THEN 'macOS'
                    WHEN device_info LIKE '%Linux%' THEN 'Linux'
                    ELSE 'Other'
                END as device_type,
                COUNT(*) as scan_count,
                COUNT(DISTINCT employee_id) as unique_users
            FROM attendance_data ad
            LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE device_info IS NOT NULL {date_filter} {qr_filter} {project_filter_clause}
            GROUP BY device_type
            ORDER BY scan_count DESC
        """)).fetchall()

        # 3. Browser Statistics (from User Agent)
        browser_stats = db.session.execute(text(f"""
            SELECT 
                CASE 
                    WHEN user_agent LIKE '%Chrome%' AND user_agent NOT LIKE '%Edge%' THEN 'Chrome'
                    WHEN user_agent LIKE '%Safari%' AND user_agent NOT LIKE '%Chrome%' THEN 'Safari'
                    WHEN user_agent LIKE '%Firefox%' THEN 'Firefox'
                    WHEN user_agent LIKE '%Edge%' THEN 'Edge'
                    WHEN user_agent LIKE '%Opera%' THEN 'Opera'
                    ELSE 'Other'
                END as browser_type,
                COUNT(*) as scan_count,
                COUNT(DISTINCT employee_id) as unique_users
            FROM attendance_data ad
            LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE user_agent IS NOT NULL {date_filter} {qr_filter} {project_filter_clause}
            GROUP BY browser_type
            ORDER BY scan_count DESC
        """)).fetchall()

        # 4. Location Statistics  
        location_stats = db.session.execute(text(f"""
            SELECT 
                qc.name as qr_name,
                qc.location as qr_location,
                qc.location_event,
                COUNT(*) as total_scans,
                COUNT(DISTINCT ad.employee_id) as unique_users,
                COUNT(CASE WHEN ad.latitude IS NOT NULL THEN 1 END) as gps_scans,
                MIN(ad.check_in_date) as first_scan,
                MAX(ad.check_in_date) as last_scan
            FROM attendance_data ad
            JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE 1=1 {date_filter} {qr_filter} {project_filter_clause}
            GROUP BY qc.id, qc.name, qc.location, qc.location_event
            ORDER BY total_scans DESC
        """)).fetchall()

        # 5. IP Address Analysis (Top 3 Most Active)
        ip_stats = db.session.execute(text(f"""
            SELECT 
                ip_address,
                COUNT(*) as scan_count,
                COUNT(DISTINCT employee_id) as unique_users,
                COUNT(DISTINCT qr_code_id) as qr_codes_used,
                MIN(check_in_date) as first_scan,
                MAX(check_in_date) as last_scan
            FROM attendance_data ad
            LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE ip_address IS NOT NULL {date_filter} {qr_filter} {project_filter_clause}
            GROUP BY ip_address
            ORDER BY scan_count DESC
            LIMIT 3
        """)).fetchall()

        # 6. Project Statistics (if projects exist)
        project_stats = db.session.execute(text(f"""
            SELECT 
                p.id,
                p.name as project_name,
                COUNT(*) as total_scans,
                COUNT(DISTINCT ad.employee_id) as unique_users,
                COUNT(DISTINCT ad.qr_code_id) as qr_codes_in_project,
                AVG(CASE WHEN ad.latitude IS NOT NULL THEN 1.0 ELSE 0.0 END) * 100 as gps_usage_percentage
            FROM attendance_data ad
            JOIN qr_codes qc ON ad.qr_code_id = qc.id
            LEFT JOIN projects p ON qc.project_id = p.id
            WHERE p.id IS NOT NULL {date_filter} {qr_filter} {project_filter_clause}
            GROUP BY p.id, p.name
            ORDER BY total_scans DESC
        """)).fetchall()

        # Get dropdown options for filters
        qr_codes_list = db.session.execute(text("""
            SELECT DISTINCT qc.id, qc.name, qc.location
            FROM qr_codes qc
            JOIN attendance_data ad ON qc.id = ad.qr_code_id
            WHERE qc.active_status = true
            ORDER BY qc.name
        """)).fetchall()

        projects_list = db.session.execute(text("""
            SELECT DISTINCT p.id, p.name
            FROM projects p
            JOIN qr_codes qc ON p.id = qc.project_id
            JOIN attendance_data ad ON qc.id = ad.qr_code_id
            WHERE p.active_status = true
            ORDER BY p.name
        """)).fetchall()

        # Log successful statistics generation
        logger_handler.logger.info(
            f"Generated statistics report for user {session.get('username', 'unknown')} "
            f"with {general_stats.total_scans} total scans. Filters applied: "
            f"date_from={date_from}, date_to={date_to}, qr_code={qr_code_filter}, project={project_filter}"
        )

        return render_template('statistics.html',
                             general_stats=general_stats,
                             device_stats=device_stats,
                             browser_stats=browser_stats,
                             location_stats=location_stats,
                             ip_stats=ip_stats,
                             project_stats=project_stats,
                             qr_codes_list=qr_codes_list,
                             projects_list=projects_list,
                             date_from=date_from,
                             date_to=date_to,
                             qr_code_filter=qr_code_filter,
                             project_filter=project_filter,
                             today_date=datetime.now().strftime('%Y-%m-%d'))

    except Exception as e:
        # Log the error using the correct method
        logger_handler.log_database_error('statistics_page_error', e)
        flash('Error loading statistics. Please try again.', 'error')
        return redirect(url_for('dashboard.dashboard'))


@bp.route('/api/statistics/export', endpoint='export_statistics')
@login_required
def export_statistics():
    """Export statistics data to CSV/Excel"""
    try:
        # Check permissions
        if session.get('role') not in ['admin', 'payroll', 'accounting']:
            return jsonify({'error': 'Access denied'}), 403
            
        # Log export attempt
        logger_handler.logger.info(
            f"User {session.get('username', 'unknown')} (role: {session.get('role')}) "
            f"attempted to export statistics data in {request.args.get('format', 'csv')} format"
        )
        
        # Get comprehensive statistics for export
        export_data = db.session.execute(text("""
            SELECT 
                ad.id,
                ad.employee_id,
                COALESCE(CONCAT(e.firstName, ' ', e.lastName), ad.employee_id) as employee_name,
                ad.check_in_date,
                ad.check_in_time,
                qc.name as qr_code_name,
                qc.location as qr_location,
                qc.location_event,
                p.name as project_name,
                ad.device_info,
                ad.user_agent,
                ad.ip_address,
                ad.latitude,
                ad.longitude,
                ad.address,
                ad.location_name,
                ad.created_timestamp
            FROM attendance_data ad
            JOIN qr_codes qc ON ad.qr_code_id = qc.id
            LEFT JOIN projects p ON qc.project_id = p.id
            LEFT JOIN employee e ON CAST(ad.employee_id AS UNSIGNED) = e.id
            ORDER BY ad.created_timestamp DESC
        """)).fetchall()
        
        # Create CSV content
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Employee ID', 'Employee Name', 'Date', 'Time', 
            'QR Code', 'QR Location', 'Event', 'Project', 'Device', 
            'Browser Info', 'IP Address', 'Latitude', 'Longitude', 
            'Address', 'Location Name', 'Timestamp'
        ])
        
        # Write data
        for row in export_data:
            writer.writerow([
                row.id, row.employee_id, row.employee_name, 
                str(row.check_in_date), str(row.check_in_time),
                row.qr_code_name, row.qr_location, row.location_event,
                row.project_name or 'No Project', row.device_info or 'Unknown',
                row.user_agent or 'Unknown', row.ip_address or 'Unknown',
                row.latitude or '', row.longitude or '', 
                row.address or '', row.location_name or '',
                str(row.created_timestamp)
            ])
        
        output.seek(0)
        
        # Create response with proper file handling
        csv_data = output.getvalue()
        
        # Log successful export
        logger_handler.logger.info(
            f"User {session.get('username', 'unknown')} successfully exported "
            f"{len(export_data)} statistics records"
        )
        
        # Create response
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=qr_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
        
    except Exception as e:
        logger_handler.log_database_error('statistics_export_error', e)
        return jsonify({'error': 'Export failed'}), 500

    except Exception as e:
        # Log the error
        logger_handler.log_database_error('statistics_page_error', e)
        flash('Error loading statistics. Please try again.', 'error')
        return redirect(url_for('dashboard.dashboard'))

# EMPLOYEE MANAGEMENT ROUTES