"""
routes/employees.py
===================
Employee CRUD and search routes.

Routes: /employees, /employees/create, /employees/<id>/edit,
        /employees/<id>/delete, /api/employees/search, /employees/<id>
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify
from datetime import datetime, date

from extensions import db, logger_handler
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import (url_for,
                           admin_required,
                           has_admin_privileges,
                           has_staff_level_access,
                           login_required,
                           staff_or_admin_required)

bp = Blueprint('employees', __name__)

def _get_models():
    """Return model classes from the current app context."""
    from flask import current_app
    return current_app.config['_models']


@bp.route('/employees', endpoint='employees')
@login_required
def employees():
    """Display employee management page with search and pagination"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Log user accessing employee management
        try:
            logger_handler.logger.info(f"User {session['username']} accessed employee management list")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        # Get search parameters
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Number of employees per page
        
        # Build query based on search
        query = Employee.query.outerjoin(Project, Employee.contractId == Project.id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Employee.firstName.like(search_pattern),
                    Employee.lastName.like(search_pattern),
                    Employee.title.like(search_pattern),
                    Employee.id.like(search_pattern)
                )
            )

        # Order by first name, then last name
        query = query.order_by(Employee.firstName, Employee.lastName)
        
        # Paginate results
        employees = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Get summary statistics
        total_employees = Employee.query.count()
        employees_with_title = Employee.query.filter(Employee.title.isnot(None)).filter(Employee.title != '').count()
        unique_titles = db.session.query(Employee.title).filter(Employee.title.isnot(None)).filter(Employee.title != '').distinct().count()
        
        stats = {
            'total_employees': total_employees,
            'employees_with_title': employees_with_title,
            'unique_titles': unique_titles,
            'search_results': employees.total if search else total_employees
        }
        
        return render_template('employees.html', 
                             employees=employees, 
                             search=search,
                             stats=stats)
        
    except Exception as e:
        logger_handler.log_database_error('employee_list', e)
        flash('Error loading employee list. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@bp.route('/employees/create', methods=['GET', 'POST'], endpoint='create_employee')
@login_required
@log_database_operations('employee_creation')
def create_employee():
    """Create new employee (Admin only)"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    if request.method == 'POST':
        try:
            # Get form data
            employee_id = request.form['employee_id'].strip()
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            title = request.form.get('title', '').strip()
            contract_id = request.form.get('contract_id', '1').strip()
            
            # Validate required fields
            if not all([employee_id, first_name, last_name, contract_id]):
                flash('Employee ID, First Name, Last Name, and Project are required.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('create_employee.html', projects=projects)
            
            # Validate employee ID is numeric
            try:
                employee_id_int = int(employee_id)
                contract_id_int = int(contract_id)
            except ValueError:
                flash('Employee ID must be numeric and Project must be selected.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('create_employee.html', projects=projects)
            
            # Check if employee ID already exists
            existing_employee = Employee.query.filter_by(id=employee_id_int).first()
            if existing_employee:
                flash(f'Employee with ID {employee_id} already exists.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('create_employee.html', projects=projects)
            
            # Create new employee
            new_employee = Employee(
                id=employee_id_int,
                firstName=first_name,
                lastName=last_name,
                title=title if title else None,
                contractId=contract_id_int
            )
            
            db.session.add(new_employee)
            db.session.commit()
            
            # Log employee creation with project info
            try:
                project = Project.query.get(contract_id_int)
                project_name = project.name if project else f"Project {contract_id_int}"
                logger_handler.logger.info(f"Admin user {session['username']} created new employee: {employee_id_int} - {first_name} {last_name} assigned to {project_name}")
            except Exception as log_error:
                print(f"⚠️ Logging error (non-critical): {log_error}")
            
            flash(f'Employee "{first_name} {last_name}" (ID: {employee_id}) created successfully.', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('employee_creation', e)
            flash('Failed to create employee. Please try again.', 'error')
            projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
            return render_template('create_employee.html', projects=projects)
    
    # GET request - load the form with projects
    projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
    return render_template('create_employee.html', projects=projects)

@bp.route('/employees/<int:employee_index>/edit', methods=['GET', 'POST'], endpoint='edit_employee')
@login_required  
@log_database_operations('employee_update')
def edit_employee(employee_index):
    """Edit existing employee (Admin only)"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Get employee by index (primary key)
        employee = Employee.query.get_or_404(employee_index)
        
        if request.method == 'POST':
            # Get form data
            employee_id = request.form['employee_id'].strip()
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            title = request.form.get('title', '').strip()
            contract_id = request.form.get('contract_id', '1').strip()

            # Validate required fields
            if not all([employee_id, first_name, last_name, contract_id]):
                flash('Employee ID, First Name, Last Name, and Project are required.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('edit_employee.html', employee=employee, projects=projects)
            
            # Validate numeric fields
            try:
                employee_id_int = int(employee_id)
                contract_id_int = int(contract_id)
            except ValueError:
                flash('Employee ID must be numeric and Project must be selected.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('edit_employee.html', employee=employee, projects=projects)
            
            # Check if employee ID already exists (but not for this employee)
            existing_employee = Employee.query.filter_by(id=employee_id_int).first()
            if existing_employee and existing_employee.index != employee.index:
                flash(f'Employee with ID {employee_id} already exists.', 'error')
                projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
                return render_template('edit_employee.html', employee=employee, projects=projects)
            
            # Store original values for logging
            original_data = {
                'id': employee.id,
                'firstName': employee.firstName,
                'lastName': employee.lastName,
                'title': employee.title,
                'contractId': employee.contractId
            }
            
            # Update employee data
            employee.id = employee_id_int
            employee.firstName = first_name
            employee.lastName = last_name
            employee.title = title if title else None
            employee.contractId = contract_id_int
            
            db.session.commit()
            
            # Log employee update with project info
            try:
                project = Project.query.get(contract_id_int)
                project_name = project.name if project else f"Project {contract_id_int}"
                logger_handler.logger.info(f"Admin user {session['username']} updated employee: {employee_index} - {first_name} {last_name} assigned to {project_name}")
            except Exception as log_error:
                print(f"⚠️ Logging error (non-critical): {log_error}")
            
            flash(f'Employee "{first_name} {last_name}" updated successfully.', 'success')
            return redirect(url_for('employees'))
        
        # GET request - load the form with projects
        projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
        return render_template('edit_employee.html', employee=employee, projects=projects)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('employee_update', e)
        flash('Error updating employee. Please try again.', 'error')
        return redirect(url_for('employees'))

@bp.route('/employees/<int:employee_index>/delete', methods=['POST'], endpoint='delete_employee')
@login_required
@log_database_operations('employee_deletion')
def delete_employee(employee_index):
    """Delete employee (Admin only) - Enhanced with better logging"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    try:
        print(f"🗑️ DELETE REQUEST: Employee index {employee_index}")
        print(f"📋 Request method: {request.method}")
        print(f"👤 User: {session.get('username', 'Unknown')}")
        
        # Get employee by index (primary key)
        employee = Employee.query.get_or_404(employee_index)
        print(f"✅ Found employee: {employee.firstName} {employee.lastName} (ID: {employee.id})")
        
        # Store employee data for logging before deletion
        employee_data = {
            'index': employee.index,
            'id': employee.id,
            'firstName': employee.firstName,
            'lastName': employee.lastName,
            'title': employee.title,
            'contractId': employee.contractId
        }
        
        # Check if employee has attendance records
        from models.attendance import AttendanceData
        attendance_count = AttendanceData.query.filter_by(employee_id=str(employee.id)).count()
        print(f"📊 Attendance records found: {attendance_count}")
        
        if attendance_count > 0:
            error_msg = f'Cannot delete employee "{employee.full_name}". Employee has {attendance_count} attendance records. Please contact system administrator.'
            print(f"❌ DELETION BLOCKED: {error_msg}")
            flash(error_msg, 'error')
            return redirect(url_for('employees'))
        
        # Proceed with deletion
        print(f"🗑️ Proceeding with deletion of employee: {employee_data['firstName']} {employee_data['lastName']}")
        
        db.session.delete(employee)
        db.session.commit()
        print("✅ Employee successfully deleted from database")
        
        # Log employee deletion
        try:
            logger_handler.logger.info(f"Admin user {session['username']} deleted employee: {employee_data['firstName']} {employee_data['lastName']} (ID: {employee_data['id']})")
            print(f"📋 Deletion logged successfully")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        success_msg = f'Employee "{employee_data["firstName"]} {employee_data["lastName"]}" deleted successfully.'
        flash(success_msg, 'success')
        print(f"✅ SUCCESS: {success_msg}")
        
        return redirect(url_for('employees'))
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('employee_deletion', e)
        error_msg = f'Error deleting employee. Please try again.'
        print(f"❌ ERROR in delete_employee: {e}")
        print(f"❌ Exception type: {type(e)}")
        flash(error_msg, 'error')
        return redirect(url_for('employees'))

@bp.route('/api/employees/search', endpoint='api_employees_search')
@login_required
def api_employees_search():
    """API endpoint for employee search (for AJAX)"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    try:
        search = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        
        if not search:
            return jsonify({'employees': []})
        
        employees = Employee.search_employees(search)[:limit]
        
        result = {
            'employees': [emp.to_dict() for emp in employees]
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger_handler.log_database_error('employee_search_api', e)
        return jsonify({'error': 'Search failed'}), 500

@bp.route('/employees/<int:employee_index>', endpoint='employee_detail')
@login_required
def employee_detail(employee_index):
    """View employee details with attendance summary"""
    Employee, AttendanceData, Project, QRCode, User = _get_models()["Employee"], _get_models()["AttendanceData"], _get_models()["Project"], _get_models()["QRCode"], _get_models()["User"]
    try:
        # Get employee by index (primary key)
        employee = Employee.query.outerjoin(Project, Employee.contractId == Project.id).filter(Employee.index == employee_index).first_or_404()
        
        # Get attendance statistics for this employee
        from models.attendance import AttendanceData
        
        # Total attendance records
        total_attendance = AttendanceData.query.filter_by(employee_id=str(employee.id)).count()
        
        # Recent attendance (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_attendance = AttendanceData.query.filter(
            AttendanceData.employee_id == str(employee.id),
            AttendanceData.check_in_date >= thirty_days_ago.date()
        ).count()
        
        # Most recent attendance record
        latest_attendance = AttendanceData.query.filter_by(employee_id=str(employee.id)).order_by(
            AttendanceData.check_in_date.desc(),
            AttendanceData.check_in_time.desc()
        ).first()
        
        # Get unique projects this employee has attended
        unique_projects = db.session.query(Project).join(
            QRCode, Project.id == QRCode.project_id
        ).join(
            AttendanceData, QRCode.id == AttendanceData.qr_code_id
        ).filter(
            AttendanceData.employee_id == str(employee.id)
        ).distinct().all()
        
        attendance_stats = {
            'total_attendance': total_attendance,
            'recent_attendance': recent_attendance,
            'latest_attendance': latest_attendance,
            'unique_projects': len(unique_projects),
            'projects': unique_projects
        }
        
        # Log employee detail view
        try:
            logger_handler.logger.info(f"User {session['username']} viewed employee detail: {employee.full_name} (ID: {employee.id})")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        return render_template('employee_detail.html', 
                             employee=employee, 
                             attendance_stats=attendance_stats)
        
    except Exception as e:
        logger_handler.log_database_error('employee_detail', e)
        flash('Error loading employee details. Please try again.', 'error')
        return redirect(url_for('employees'))
