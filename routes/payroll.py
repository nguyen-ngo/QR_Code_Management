"""
routes/payroll.py
=================
Payroll dashboard and Excel export routes.

Routes: /payroll, /payroll/export-excel, /api/working-hours/calculate,
        /api/employee/<id>/miss-punch-details
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, send_file
from datetime import datetime, date, timedelta, time
import io, json, traceback, os

from extensions import db, logger_handler
from sqlalchemy import text
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import (url_for,
                           admin_required,
                           has_admin_privileges,
                           has_staff_level_access,
                           login_required,
                           staff_or_admin_required)
from working_hours_calculator import WorkingHoursCalculator, round_time_to_quarter_hour, convert_minutes_to_base100, round_base100_hours
from payroll_excel_exporter import PayrollExcelExporter
from enhanced_payroll_excel_exporter import EnhancedPayrollExcelExporter

bp = Blueprint('payroll', __name__)

def _get_models():
    """Return model classes from the current app context."""
    from flask import current_app
    return current_app.config['_models']


@bp.route('/payroll', endpoint='payroll_dashboard')
@login_required
def payroll_dashboard():
    """Payroll dashboard for calculating and exporting working hours"""
    AttendanceData, Employee, Project, TimeAttendance, QRCode, User = _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["Project"], _get_models()["TimeAttendance"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Check if user has payroll access
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll', 'accounting']:
            logger_handler.logger.warning(f"User {session.get('username', 'unknown')} (role: {user_role}) attempted to access payroll dashboard without permissions")
            flash('Access denied. Only administrators and payroll staff can access payroll features.', 'error')
            return redirect(url_for('dashboard'))

        print("📊 Loading payroll dashboard")

        # Log payroll dashboard access
        logger_handler.logger.info(f"User {session.get('username', 'unknown')} accessed payroll dashboard")

        # Get filter parameters with defaults
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        project_filter = request.args.get('project_filter', '')
        
        # Set default date range if not provided (last 2 weeks)
        if not date_from or not date_to:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=13)  # 2 weeks (14 days)
            date_from = start_date.strftime('%Y-%m-%d')
            date_to = end_date.strftime('%Y-%m-%d')

        # Get list of projects for dropdown
        projects = []
        try:
            projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
            print(f"📊 Found {len(projects)} active projects for filter")
        except Exception as e:
            print(f"⚠️ Error loading projects: {e}")

        # Get attendance records for the period
        attendance_records = []
        working_hours_data = None

        if date_from and date_to:
            try:
                start_date = datetime.strptime(date_from, '%Y-%m-%d')
                end_date = datetime.strptime(date_to, '%Y-%m-%d')

                # Query attendance records with optional project filter
                query = db.session.query(AttendanceData).join(QRCode, AttendanceData.qr_code_id == QRCode.id)

                # Apply date filter
                query = query.filter(
                    AttendanceData.check_in_date >= start_date.date(),
                    AttendanceData.check_in_date <= end_date.date()
                )

                # Apply project filter if selected
                if project_filter and project_filter != '':
                    query = query.filter(QRCode.project_id == int(project_filter))
                    print(f"📊 Applied project filter: {project_filter}")

                query = query.order_by(AttendanceData.employee_id, AttendanceData.check_in_date, AttendanceData.check_in_time)

                attendance_records = query.all()
                print(f"📊 Found {len(attendance_records)} attendance records for payroll calculation")

                # Calculate working hours if we have records
                if attendance_records:
                    calculator = WorkingHoursCalculator()
                    working_hours_data = calculator.calculate_all_employees_hours(
                        start_date, end_date, attendance_records
                    )
                    print(f"📊 Calculated hours for {working_hours_data['employee_count']} employees")

            except ValueError as e:
                print(f"⚠️ Invalid date format: {e}")
                flash('Invalid date format. Please use YYYY-MM-DD format.', 'error')
            except Exception as e:
                print(f"❌ Error calculating working hours: {e}")
                logger_handler.log_database_error('payroll_calculation', e)
                flash('Error calculating working hours. Please check the server logs.', 'error')

        # Get employee names for display
        employee_names = {}
        if working_hours_data:
            try:
                # Use the same SQL approach as attendance report - JOIN with CAST
                employee_ids = list(working_hours_data['employees'].keys())
                if employee_ids:
                    # Build a query similar to attendance report
                    placeholders = ','.join([f"'{emp_id}'" for emp_id in employee_ids])
                    employee_query = db.session.execute(text(f"""
                        SELECT 
                            ad.employee_id,
                            CONCAT(e.lastName, ',', e.firstName) as full_name 
                        FROM attendance_data ad
                        LEFT JOIN employee e ON CAST(ad.employee_id AS UNSIGNED) = e.id
                        WHERE ad.employee_id IN ({placeholders})
                        GROUP BY ad.employee_id, e.firstName, e.lastName
                    """))

                    for row in employee_query:
                        if row[1]:  # Only add if we got a name
                            employee_names[str(row[0])] = row[1]

                print(f"📊 Retrieved names for {len(employee_names)} employees using CAST method")

            except Exception as e:
                print(f"⚠️ Could not load employee names: {e}")
                import traceback
                print(f"⚠️ Traceback: {traceback.format_exc()}")
                # Continue without names - will use employee IDs

        # Get selected project name for display
        selected_project_name = ''
        if project_filter:
            try:
                selected_project = Project.query.get(int(project_filter))
                if selected_project:
                    selected_project_name = selected_project.name
            except Exception as e:
                print(f"⚠️ Error getting selected project name: {e}")

        return render_template('payroll_dashboard.html',
                             working_hours_data=working_hours_data,
                             employee_names=employee_names,
                             projects=projects,
                             date_from=date_from,
                             date_to=date_to,
                             project_filter=project_filter,
                             selected_project_name=selected_project_name,
                             user_role=user_role)

    except Exception as e:
        print(f"❌ Error loading payroll dashboard: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

        logger_handler.log_flask_error(
            'payroll_dashboard_error',
            str(e),
            stack_trace=traceback.format_exc()
        )

        flash('Error loading payroll dashboard. Please check the server logs.', 'error')
        return redirect(url_for('dashboard'))

@bp.route('/payroll/export-excel', methods=['POST'], endpoint='export_payroll_excel')
@login_required
@log_database_operations('payroll_excel_export')
def export_payroll_excel():
    """Export payroll report to Excel with working hours calculations including SP/PW support"""
    AttendanceData, Employee, Project, TimeAttendance, QRCode, User = _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["Project"], _get_models()["TimeAttendance"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Check permissions
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll', 'accounting']:
            logger_handler.logger.warning(f"User {session.get('username', 'unknown')} (role: {user_role}) attempted unauthorized payroll Excel export")
            flash('Access denied. Only administrators and payroll staff can export payroll data.', 'error')
            return redirect(url_for('payroll_dashboard'))

        print("📊 Payroll Excel export started")

        # Get parameters from form
        date_from = request.form.get('date_from')
        date_to = request.form.get('date_to')
        project_filter = request.form.get('project_filter', '')
        report_type = request.form.get('report_type', 'payroll')  # 'payroll', 'detailed', 'template', 'enhanced', 'detailed_sp_pw'

        if not date_from or not date_to:
            flash('Please provide both start and end dates for the export.', 'error')
            return redirect(url_for('payroll_dashboard'))

        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD format.', 'error')
            return redirect(url_for('payroll_dashboard'))

        # Get attendance records with project filter and QR code data
        query = db.session.query(AttendanceData, QRCode).join(QRCode, AttendanceData.qr_code_id == QRCode.id)

        # Apply date filter
        query = query.filter(
            AttendanceData.check_in_date >= start_date.date(),
            AttendanceData.check_in_date <= end_date.date()
        )

        # Apply project filter if selected
        if project_filter and project_filter != '':
            query = query.filter(QRCode.project_id == int(project_filter))
            print(f"📊 Applied project filter to export: {project_filter}")

        query = query.order_by(AttendanceData.employee_id, AttendanceData.check_in_date, AttendanceData.check_in_time)

        # Get the results and attach QR code data to attendance records
        query_results = query.all()
        attendance_records = []

        for attendance_data, qr_code in query_results:
            # Attach the QR code object to the attendance record
            attendance_data.qr_code = qr_code
            attendance_records.append(attendance_data)

        print(f"📊 Export: Found {len(attendance_records)} records with QR data")

        if not attendance_records:
            flash('No attendance records found for the selected date range and project.', 'warning')
            return redirect(url_for('payroll_dashboard'))

        print(f"📊 Exporting {len(attendance_records)} attendance records to Excel")

        # Get employee names using the same method as dashboard
        employee_names = {}
        try:
            employee_ids = list(set(str(record.employee_id) for record in attendance_records))
            if employee_ids:
                # Use the same SQL approach as attendance report - JOIN with CAST
                placeholders = ','.join([f"'{emp_id}'" for emp_id in employee_ids])
                employee_query = db.session.execute(text(f"""
                    SELECT 
                        ad.employee_id,
                        CONCAT(e.firstName, ' ', e.lastName) as full_name 
                    FROM attendance_data ad
                    LEFT JOIN employee e ON CAST(ad.employee_id AS UNSIGNED) = e.id
                    WHERE ad.employee_id IN ({placeholders})
                    GROUP BY ad.employee_id, e.firstName, e.lastName
                """))

                for row in employee_query:
                    if row[1]:  # Only add if we got a name
                        employee_names[str(row[0])] = row[1]

            print(f"📊 Retrieved names for {len(employee_names)} employees for export using CAST method")

        except Exception as e:
            print(f"⚠️ Could not load employee names for export: {e}")
            import traceback
            print(f"⚠️ Traceback: {traceback.format_exc()}")

        # Get project name for enhanced reports and filename
        project_name = None
        project_name_for_filename = ''
        if project_filter:
            try:
                project = Project.query.get(int(project_filter))
                if project:
                    project_name = project.name
                    project_name_for_filename = f"_{project.name.replace(' ', '_')}"
            except Exception as e:
                print(f"⚠️ Error getting project name: {e}")

        # Generate Excel file based on report type
        excel_file = None
        filename_prefix = 'payroll_report'

        if report_type == 'enhanced':
            # Use enhanced exporter for SP/PW reports
            print("📊 Creating enhanced payroll report with SP/PW support")
            try:
                from enhanced_payroll_excel_exporter import EnhancedPayrollExcelExporter
                exporter = EnhancedPayrollExcelExporter(company_name=os.environ.get('COMPANY_NAME', 'Your Company'))
                excel_file = exporter.create_enhanced_payroll_report(
                    start_date, end_date, attendance_records, employee_names, project_name
                )
                filename_prefix = 'enhanced_payroll_report'
                print("✅ Enhanced payroll report created successfully")
            except ImportError:
                print("⚠️ Enhanced exporter not available, falling back to standard exporter")
                # Fall back to standard exporter
                exporter = PayrollExcelExporter(
                    company_name=os.environ.get('COMPANY_NAME', 'Your Company'),
                    contract_name=os.environ.get('CONTRACT_NAME', 'Default Contract')
                )
                excel_file = exporter.create_payroll_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'payroll_report'
            except Exception as e:
                print(f"⚠️ Error with enhanced exporter: {e}, falling back to standard exporter")
                # Fall back to standard exporter
                exporter = PayrollExcelExporter(
                    company_name=os.environ.get('COMPANY_NAME', 'Your Company'),
                    contract_name=os.environ.get('CONTRACT_NAME', 'Default Contract')
                )
                excel_file = exporter.create_payroll_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'payroll_report'

        elif report_type == 'detailed_sp_pw':
            # Detailed daily SP/PW breakdown
            print("📊 Creating detailed SP/PW daily breakdown report")
            try:
                from enhanced_payroll_excel_exporter import EnhancedPayrollExcelExporter
                exporter = EnhancedPayrollExcelExporter(company_name=os.environ.get('COMPANY_NAME', 'Your Company'))
                excel_file = exporter.create_detailed_sp_pw_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'detailed_sp_pw_report'
                print("✅ Detailed SP/PW report created successfully")
            except ImportError:
                print("⚠️ Enhanced exporter not available, falling back to detailed hours report")
                # Fall back to standard detailed report
                exporter = PayrollExcelExporter(
                    company_name=os.environ.get('COMPANY_NAME', 'Your Company'),
                    contract_name=os.environ.get('CONTRACT_NAME', 'Default Contract')
                )
                excel_file = exporter.create_detailed_hours_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'detailed_hours_report'
            except Exception as e:
                print(f"⚠️ Error with enhanced exporter: {e}, falling back to detailed hours report")
                # Fall back to standard detailed report
                exporter = PayrollExcelExporter(
                    company_name=os.environ.get('COMPANY_NAME', 'Your Company'),
                    contract_name=os.environ.get('CONTRACT_NAME', 'Default Contract')
                )
                excel_file = exporter.create_detailed_hours_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'detailed_hours_report'

        else:
            # Use standard exporter for existing report types
            exporter = PayrollExcelExporter(
                company_name=os.environ.get('COMPANY_NAME', 'Your Company'),
                contract_name=os.environ.get('CONTRACT_NAME', 'Default Contract')
            )

            if report_type == 'detailed':
                excel_file = exporter.create_detailed_hours_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'detailed_hours_report'
            elif report_type == 'template':
                excel_file = exporter.create_template_format_report(
                    start_date, end_date, attendance_records, employee_names, project_name
                )
                filename_prefix = 'time_attendance_report'
            else:
                # Default payroll report
                excel_file = exporter.create_payroll_report(
                    start_date, end_date, attendance_records, employee_names
                )
                filename_prefix = 'payroll_report'

        if excel_file:
            # Generate filename with timestamp and project name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{filename_prefix}_{date_from}_to_{date_to}{project_name_for_filename}_{timestamp}.xlsx'

            print(f"📊 Payroll Excel file generated successfully: {filename}")

            # Log successful export
            logger_handler.logger.info(f"Payroll Excel export generated by user {session.get('username', 'unknown')}: {filename}")
            if report_type == 'template':
                logger_handler.logger.info(f"Template format hours export generated by user {session.get('username', 'unknown')}: {filename}")
            elif report_type == 'enhanced':
                logger_handler.logger.info(f"Enhanced payroll export with SP/PW generated by user {session.get('username', 'unknown')}: {filename}")
            elif report_type == 'detailed_sp_pw':
                logger_handler.logger.info(f"Detailed SP/PW breakdown export generated by user {session.get('username', 'unknown')}: {filename}")

            return send_file(
                excel_file,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('Error generating payroll Excel file.', 'error')
            return redirect(url_for('payroll_dashboard'))

    except Exception as e:
        print(f"❌ Error in export_payroll_excel route: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

        logger_handler.log_flask_error(
            'payroll_excel_export_error',
            str(e),
            stack_trace=traceback.format_exc()
        )

        flash('Error generating payroll Excel export. Please check the server logs.', 'error')
        return redirect(url_for('payroll_dashboard'))

@bp.route('/api/working-hours/calculate', methods=['POST'], endpoint='calculate_working_hours_api')
@login_required
@log_database_operations('working_hours_api_calculation')
def calculate_working_hours_api():
    """API endpoint for calculating working hours"""
    AttendanceData, Employee, Project, TimeAttendance, QRCode, User = _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["Project"], _get_models()["TimeAttendance"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Check permissions
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll', 'accounting']:
            return jsonify({
                'success': False,
                'message': 'Access denied. Insufficient permissions.'
            }), 403

        # Get parameters from JSON request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        employee_id = data.get('employee_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        if not all([employee_id, date_from, date_to]):
            return jsonify({
                'success': False,
                'message': 'Missing required parameters: employee_id, date_from, date_to'
            }), 400

        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400

        # Get attendance records for the employee
        query = db.session.query(AttendanceData).filter(
            AttendanceData.employee_id == str(employee_id),
            AttendanceData.check_in_date >= start_date.date(),
            AttendanceData.check_in_date <= end_date.date()
        ).order_by(AttendanceData.check_in_date, AttendanceData.check_in_time)

        attendance_records = query.all()

        # Calculate working hours using WorkingHoursCalculator
        calculator = WorkingHoursCalculator()
        hours_data = calculator.calculate_employee_hours(
            str(employee_id), start_date, end_date, attendance_records
        )

        # Log API usage
        logger_handler.logger.info(f"Working hours API used by {session.get('username', 'unknown')} for employee {employee_id}")

        return jsonify({
            'success': True,
            'data': hours_data
        })

    except Exception as e:
        print(f"❌ Error in calculate_working_hours_api: {e}")
        logger_handler.log_flask_error(
            'working_hours_api_error',
            str(e),
            stack_trace=traceback.format_exc()
        )

        return jsonify({
            'success': False,
            'message': 'Internal server error. Please check the server logs.'
        }), 500

@bp.route('/api/employee/<employee_id>/miss-punch-details', methods=['GET'], endpoint='get_miss_punch_details')
@login_required
@log_database_operations('miss_punch_details_api')
def get_miss_punch_details(employee_id):
    """API endpoint to get detailed miss punch information for an employee"""
    AttendanceData, Employee, Project, TimeAttendance, QRCode, User = _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["Project"], _get_models()["TimeAttendance"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Check permissions
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll', 'accounting']:
            return jsonify({
                'success': False,
                'message': 'Access denied. Insufficient permissions.'
            }), 403

        # Get date parameters from query string (from the current payroll filters)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        project_filter = request.args.get('project_filter', '')
        
        if not all([date_from, date_to]):
            return jsonify({
                'success': False,
                'message': 'Missing required parameters: date_from, date_to'
            }), 400

        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400

        # Get employee name using proper firstName and lastName fields
        try:
            employee_query = db.session.execute(text("""
                                                     SELECT e.id,
                                                            CONCAT(e.firstName, ' ', e.lastName) as full_name
                                                     FROM employee e
                                                     WHERE e.id = :emp_id
                                                     """), {'emp_id': int(employee_id)})

            employee_row = employee_query.fetchone()
            employee_name = employee_row.full_name if employee_row and employee_row.full_name else f"Employee {employee_id}"
            print(f"📋 Retrieved employee name: {employee_name} for ID: {employee_id}")
        except Exception as e:
            print(f"⚠️ Could not load employee name for ID {employee_id}: {e}")
            import traceback
            print(f"⚠️ Traceback: {traceback.format_exc()}")
            employee_name = f"Employee {employee_id}"

        # Get attendance records for the employee within the period
        query = db.session.query(AttendanceData).filter(
            AttendanceData.employee_id == str(employee_id),
            AttendanceData.check_in_date >= start_date.date(),
            AttendanceData.check_in_date <= end_date.date()
        )

        # Apply project filter if provided
        if project_filter:
            try:
                project_id = int(project_filter)
                query = query.join(QRCode, AttendanceData.qr_code_id == QRCode.id) \
                    .filter(QRCode.project_id == project_id)
            except ValueError:
                pass  # Invalid project_id, ignore filter

        attendance_records = query.order_by(
            AttendanceData.check_in_date,
            AttendanceData.check_in_time
        ).all()

        # Convert to the format expected by the calculator
        converted_records = []
        for record in records:
            # Get distance from the TimeAttendance record
            distance_value = getattr(record, 'distance', None)
            
            converted_record = type('Record', (), {
                'id': record.id,
                'employee_id': str(record.employee_id),
                'check_in_date': record.attendance_date,
                'check_in_time': record.attendance_time,
                'location_name': record.location_name,
                'latitude': None,
                'longitude': None,
                'distance': distance_value,  # ADD THIS LINE
                'qr_code': type('QRCode', (), {
                    'location': record.location_name,
                    'location_address': record.recorded_address or '',
                    'project': None
                })()
            })()
            converted_records.append(converted_record)

        # Calculate working hours using the same calculator as the dashboard

        # Calculate hours for this employee
        hours_data = calculator.calculate_employee_hours(
            str(employee_id), start_date, end_date, converted_records
        )

        # Extract miss punch details
        miss_punch_days = []
        if 'daily_hours' in hours_data:
            for date_str, day_data in hours_data['daily_hours'].items():
                if day_data.get('is_miss_punch', False):
                    # Get the actual records for this day
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    day_records = [r for r in converted_records if r.check_in_date == date_obj]

                    # Format the records information with event types
                    record_details = []
                    for i, record in enumerate(day_records):
                        # Determine event type based on position (alternating check-in/check-out)
                        # First record is always check-in, then alternates
                        event_type = "Check In" if i % 2 == 0 else "Check Out"

                        record_details.append({
                            'time': record.check_in_time.strftime('%H:%M:%S'),
                            'event_type': event_type,
                            'location': record.location_name or 'Unknown Location',
                            'has_gps': record.latitude is not None and record.longitude is not None
                        })

                    miss_punch_days.append({
                        'date': date_str,
                        'date_formatted': datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y (%A)'),
                        'records_count': day_data.get('records_count', 0),
                        'records': record_details,
                        'reason': 'Incomplete punch pairs - missing check-in or check-out' if len(
                            day_records) % 2 != 0 else 'Invalid work period duration'
                    })

        # Log the API access
        logger_handler.logger.info(
            f"Miss punch details API accessed by {session.get('username', 'unknown')} for employee {employee_id}")

        return jsonify({
            'success': True,
            'data': {
                'employee_id': employee_id,
                'employee_name': employee_name,
                'period': f"{date_from} to {date_to}",
                'miss_punch_count': len(miss_punch_days),
                'miss_punch_days': miss_punch_days
            }
        })

    except Exception as e:
        print(f"❌ Error in get_miss_punch_details: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

        logger_handler.log_flask_error(
            'miss_punch_details_api_error',
            str(e),
            stack_trace=traceback.format_exc()
        )

        return jsonify({
            'success': False,
            'message': 'Internal server error. Please check the server logs.'
        }), 500

def get_employee_name(employee_id):
    """Helper function to get employee full name by ID"""
    Employee = _get_models()["Employee"]
    try:
        result = db.session.execute(text("""
            SELECT CONCAT(firstName, ' ', lastName) as full_name 
            FROM employee 
            WHERE id = :employee_id
        """), {'employee_id': employee_id})

        row = result.fetchone()
        return row[0] if row else f"Employee {employee_id}"

    except Exception as e:
        print(f"⚠️ Error getting employee name for ID {employee_id}: {e}")
        return f"Employee {employee_id}"

def get_qr_code_checkin_count(qr_code_id):
    """Helper function to get total check-ins count for a QR code"""
    AttendanceData = _get_models()["AttendanceData"]
    try:
        count = AttendanceData.query.filter_by(qr_code_id=qr_code_id).count()
        logger_handler.logger.info(f"QR Code {qr_code_id} total check-ins: {count}")
        return count
    except Exception as e:
        logger_handler.logger.error(f"Error getting check-ins count for QR {qr_code_id}: {e}")
        return 0
    
@bp.context_processor
def inject_payroll_utils():
    """Inject payroll utility functions into templates"""
    return {
        'get_employee_name': get_employee_name,
        'format_hours': lambda hours: f"{hours:.2f}" if hours else "0.00"
    }

@bp.context_processor
def inject_dashboard_utils():
    """Inject dashboard utility functions into templates"""
    return {
        'get_qr_code_checkin_count': get_qr_code_checkin_count
    }
