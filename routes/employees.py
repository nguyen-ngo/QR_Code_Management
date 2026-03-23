"""
routes/employees.py
===================
Employee CRUD and search routes.

Routes: /employees, /employees/create, /employees/<id>/edit,
        /employees/<id>/delete, /api/employees/search, /employees/<id>
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, url_for
from datetime import datetime, date

from extensions import db, logger_handler
from models.attendance import AttendanceData
from models.employee import Employee
from models.project import Project
from models.qrcode import QRCode
from models.user import User
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import (
                           admin_required,
                           has_admin_privileges,
                           has_staff_level_access,
                           login_required,
                           staff_or_admin_required)

bp = Blueprint('employees', __name__)



@bp.route('/employees', endpoint='employees')
@login_required
def employees():
    """Display employee management page with search and pagination"""
    try:
        logger_handler.logger.info(f"User {session['username']} accessed employee management list")
        
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
        return redirect(url_for('dashboard.dashboard'))

@bp.route('/employees/create', methods=['GET', 'POST'], endpoint='create_employee')
@login_required
@log_database_operations('employee_creation')
def create_employee():
    """Create new employee (Admin only)"""
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
            project = Project.query.get(contract_id_int)
            project_name = project.name if project else f"Project {contract_id_int}"
            logger_handler.logger.info(
                f"User {session['username']} created new employee: "
                f"{employee_id_int} - {first_name} {last_name} assigned to {project_name}"
            )
            
            flash(f'Employee "{first_name} {last_name}" (ID: {employee_id}) created successfully.', 'success')
            return redirect(url_for('employees.employees'))
            
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
            project = Project.query.get(contract_id_int)
            project_name = project.name if project else f"Project {contract_id_int}"
            logger_handler.logger.info(
                f"User {session['username']} updated employee: "
                f"{employee_index} - {first_name} {last_name} assigned to {project_name}"
            )
            
            flash(f'Employee "{first_name} {last_name}" updated successfully.', 'success')
            return redirect(url_for('employees.employees'))
        
        # GET request - load the form with projects
        projects = Project.query.filter_by(active_status=True).order_by(Project.name).all()
        return render_template('edit_employee.html', employee=employee, projects=projects)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('employee_update', e)
        flash('Error updating employee. Please try again.', 'error')
        return redirect(url_for('employees.employees'))

@bp.route('/employees/<int:employee_index>/delete', methods=['POST'], endpoint='delete_employee')
@login_required
@log_database_operations('employee_deletion')
def delete_employee(employee_index):
    """Delete employee (Admin only)"""
    try:
        logger_handler.logger.info(
            f"User {session.get('username', 'Unknown')} initiated delete for employee index {employee_index}"
        )

        # Get employee by index (primary key)
        employee = Employee.query.get_or_404(employee_index)

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
        attendance_count = AttendanceData.query.filter_by(employee_id=str(employee.id)).count()

        if attendance_count > 0:
            error_msg = (
                f'Cannot delete employee "{employee.full_name}". '
                f'Employee has {attendance_count} attendance records. '
                f'Please contact system administrator.'
            )
            logger_handler.logger.warning(
                f"Deletion blocked for employee {employee_data['id']} "
                f"({employee_data['firstName']} {employee_data['lastName']}): "
                f"{attendance_count} attendance records exist"
            )
            flash(error_msg, 'error')
            return redirect(url_for('employees.employees'))

        db.session.delete(employee)
        db.session.commit()

        logger_handler.logger.info(
            f"User {session['username']} deleted employee: "
            f"{employee_data['firstName']} {employee_data['lastName']} (ID: {employee_data['id']})"
        )

        flash(
            f'Employee "{employee_data["firstName"]} {employee_data["lastName"]}" deleted successfully.',
            'success'
        )
        return redirect(url_for('employees.employees'))

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('employee_deletion', e)
        flash('Error deleting employee. Please try again.', 'error')
        return redirect(url_for('employees.employees'))

@bp.route('/api/employees/search', endpoint='api_employees_search')
@login_required
def api_employees_search():
    """API endpoint for employee search (for AJAX)"""
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
    try:
        # Get employee by index (primary key)
        employee = Employee.query.outerjoin(Project, Employee.contractId == Project.id).filter(Employee.index == employee_index).first_or_404()
        
        # Get attendance statistics for this employee
        
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
        logger_handler.logger.info(
            f"User {session['username']} viewed employee detail: {employee.full_name} (ID: {employee.id})"
        )
        
        return render_template('employee_detail.html', 
                             employee=employee, 
                             attendance_stats=attendance_stats)
        
    except Exception as e:
        logger_handler.log_database_error('employee_detail', e)
        flash('Error loading employee details. Please try again.', 'error')
        return redirect(url_for('employees.employees'))