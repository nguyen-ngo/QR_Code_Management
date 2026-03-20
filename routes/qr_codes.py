"""
routes/qr_codes.py
==================
QR code management and destination handler routes.

Routes: /qr-codes/create, /qr-codes/bulk-import, /qr-codes/<id>/*,
        /qr/<string:qr_url>
"""
from flask import Blueprint, render_template, request, redirect, flash, session, jsonify, send_file, current_app
from datetime import datetime, date, timedelta, time
import io, os, base64, re, uuid, json, traceback

from extensions import db, logger_handler
from werkzeug.utils import secure_filename
from logger_handler import log_user_activity, log_database_operations
from utils.helpers import (
    url_for,
    admin_required,
    detect_device_info,
    generate_default_qr_code,
    generate_qr_code,
    generate_qr_url,
    get_client_ip,
    get_employee_checkin_history,
    get_qr_styling,
    login_required,
    staff_or_admin_required)
from utils.geocoding import (
    calculate_location_accuracy_enhanced,
    get_location_accuracy_level_enhanced,
    process_location_data_enhanced,
    reverse_geocode_coordinates,
    get_coordinates_from_address_enhanced)
from qr_code_import_service import QRCodeImportService
from turnstile_utils import turnstile_utils
import openpyxl

bp = Blueprint('qr_codes', __name__)

def _get_models():
    """Return model classes from the current app context."""
    from flask import current_app
    return current_app.config['_models']


@bp.route('/qr-codes/create', methods=['GET', 'POST'], endpoint='create_qr_code')
@login_required
@log_database_operations('qr_code_creation')
def create_qr_code():
    """Enhanced create QR code with customization options"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    if request.method == 'POST':
        try:
            # Existing form data
            name = request.form['name']
            location = request.form['location']
            location_address = request.form['location_address']
            location_event = request.form.get('location_event', '')
            project_id = request.form.get('project_id')

            # Extract coordinates data from form
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')

            # NEW: QR Code customization data
            fill_color = request.form.get('fill_color', '#000000')
            back_color = request.form.get('back_color', '#FFFFFF')
            box_size = int(request.form.get('box_size', 10))
            border = int(request.form.get('border', 4))
            error_correction = request.form.get('error_correction', 'L')
            style_id = request.form.get('style_id')  # Pre-defined style

            # Validate colors (basic hex validation)
            if not (fill_color.startswith('#') and len(fill_color) == 7):
                fill_color = '#000000'
            if not (back_color.startswith('#') and len(back_color) == 7):
                back_color = '#FFFFFF'

            # Convert coordinates to float if they exist
            address_latitude = None
            address_longitude = None
            has_coordinates = False

            if latitude and longitude:
                try:
                    address_latitude = float(latitude)
                    address_longitude = float(longitude)
                    has_coordinates = True
                    print(f"✓ Coordinates received: {address_latitude}, {address_longitude}")
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Invalid coordinates format: {e}")
                    address_latitude = None
                    address_longitude = None
                    has_coordinates = False

            # Validate project_id if provided
            project = None
            if project_id:
                try:
                    project_id = int(project_id)
                    project = Project.query.get(project_id)
                    if not project or not project.active_status:
                        flash('Selected project is not valid or inactive.', 'error')
                        return render_template('create_qr_code.html',
                                             projects=Project.query.filter_by(active_status=True).all(),
                                             styles=QRCodeStyle.query.all())
                except (ValueError, TypeError):
                    flash('Invalid project selection.', 'error')
                    return render_template('create_qr_code.html',
                                         projects=Project.query.filter_by(active_status=True).all(),
                                         styles=QRCodeStyle.query.all())

            # Create new QR code record first (without URL and image)
            new_qr_code = QRCode(
                name=name,
                location=location,
                location_address=location_address,
                location_event=location_event,
                qr_code_image="",  # Will be updated after URL generation
                qr_url="",  # Will be updated after ID is assigned
                created_by=session['user_id'],
                project_id=project_id,
                address_latitude=address_latitude,
                address_longitude=address_longitude,
                coordinate_accuracy=coordinate_accuracy if has_coordinates else None,
                coordinates_updated_date=datetime.utcnow() if has_coordinates else None,
                # NEW: Customization fields (only if columns exist)
                **({
                    'fill_color': fill_color,
                    'back_color': back_color,
                    'box_size': box_size,
                    'border': border,
                    'error_correction': error_correction,
                    'style_id': int(style_id) if style_id and style_id.isdigit() else None
                } if hasattr(QRCode, 'fill_color') else {})
            )

            # Add to session and flush to get the ID
            db.session.add(new_qr_code)
            db.session.flush()  # This assigns the ID without committing

            # Now generate the readable URL using the ID
            qr_url = generate_qr_url(name, new_qr_code.id)

            # Generate QR code data with the destination URL and custom styling
            qr_data = f"{request.url_root}qr/{qr_url}"
            qr_image = generate_qr_code(
                data=qr_data,
                fill_color=fill_color,
                back_color=back_color,
                box_size=box_size,
                border=border,
                error_correction=error_correction
            )

            # Update the QR code with the URL and image
            new_qr_code.qr_url = qr_url
            new_qr_code.qr_code_image = qr_image

            # Now commit all changes
            db.session.commit()

            # Enhanced logging with customization information
            logger_handler.log_qr_code_created(
                qr_code_id=new_qr_code.id,
                qr_code_name=name,
                created_by_user_id=session['user_id'],
                qr_data={
                    'location': location,
                    'location_address': location_address,
                    'location_event': location_event,
                    'has_coordinates': has_coordinates,
                    'customization': {
                        'fill_color': fill_color,
                        'back_color': back_color,
                        'box_size': box_size,
                        'border': border,
                        'error_correction': error_correction
                    }
                }
            )

            # Success message with customization info
            project_info = f" in project '{project.name}'" if project else ""
            coord_info = f" with coordinates ({new_qr_code.coordinates_display})" if has_coordinates else ""
            style_info = f" with custom styling (Fill: {fill_color}, Background: {back_color})"

            flash(f'QR Code "{name}" created successfully{project_info}{coord_info}{style_info}! URL: {qr_url}', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('qr_code_creation', e)
            flash('QR Code creation failed. Please try again.', 'error')
            print(f"❌ QR Code creation error: {e}")

    # Get active projects and styles for dropdown
    projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()
    styles = QRCodeStyle.query.order_by(QRCodeStyle.name.asc()).all()

    return render_template('create_qr_code.html', projects=projects, styles=styles)

@bp.route('/qr-codes/bulk-import', methods=['GET', 'POST'], endpoint='import_bulk_qr_codes')
@login_required
@log_database_operations('qr_code_bulk_import')
def import_bulk_qr_codes():
    """Bulk import QR codes from Excel file"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    
    if request.method == 'GET':
        return render_template('bulk_qr_import.html')
    
    try:
        proceed_import = request.form.get('proceed_import') == 'true'
        
        if proceed_import:
            if 'pending_qr_import_file' not in session or 'pending_qr_import_filename' not in session:
                flash('Import session expired. Please upload the file again.', 'error')
                return redirect(url_for('import_bulk_qr_codes'))
            
            temp_path = session['pending_qr_import_file']
            filename = session['pending_qr_import_filename']
            
            if not os.path.exists(temp_path):
                flash('Temporary file not found. Please upload the file again.', 'error')
                session.pop('pending_qr_import_file', None)
                session.pop('pending_qr_import_filename', None)
                return redirect(url_for('import_bulk_qr_codes'))
        else:
            if 'file' not in request.files:
                flash('No file uploaded.', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected.', 'error')
                return redirect(request.url)
            
            if not file.filename.lower().endswith(('.xlsx', '.xls')):
                flash('Please upload an Excel file (.xlsx or .xls).', 'error')
                return redirect(request.url)
            
            filename = secure_filename(file.filename)
            temp_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', '/tmp'), 
                                   f"temp_qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file.save(temp_path)
            
            session['pending_qr_import_file'] = temp_path
            session['pending_qr_import_filename'] = filename
        
        validate_only = request.form.get('validate_only') == 'true' and not proceed_import
        
        import_service = QRCodeImportService(db, logger_handler)
        
        if validate_only:
            validation_result = import_service.validate_excel_file(temp_path)
            
            if validation_result['success']:
                flash(f"Validation successful! Found {validation_result['valid_rows']} valid records.", 'success')
            else:
                flash(f"Validation found errors. Please fix them before importing.", 'error')
            
            return render_template('bulk_qr_import.html', validation_result=validation_result)
        
        projects = Project.query.filter_by(active_status=True).all()
        project_lookup = {p.name: p.id for p in projects}
        
        import_result = import_service.import_from_excel(
            file_path=temp_path,
            created_by=session['user_id'],
            generate_qr_code_func=generate_qr_code,
            generate_qr_url_func=generate_qr_url,
            request_url_root=request.url_root,
            project_lookup=project_lookup,
            QRCode=QRCode,
            Project=Project,
            geocode_func=get_coordinates_from_address_enhanced
        )
        
        if import_result['success']:
            logger_handler.logger.info(
                f"User {session['username']} successfully imported {import_result['imported_records']} QR codes via bulk import "
                f"({import_result.get('geocoded_records', 0)} addresses auto-geocoded)"
            )
            
            flash(f"Import successful! Imported {import_result['imported_records']} QR codes "
                f"out of {import_result['total_rows']} total records.", 'success')
            
            # Show geocoding info
            if import_result.get('geocoded_records', 0) > 0:
                flash(f"✓ {import_result['geocoded_records']} addresses were automatically geocoded using Google Maps.", 'info')
            
            if import_result['failed_records'] > 0:
                flash(f"Note: {import_result['failed_records']} records failed to import. "
                    f"Check the error details below.", 'warning')
        else:
            flash(f"Import failed: {import_result.get('error', 'Unknown error')}", 'error')
        
        session.pop('pending_qr_import_file', None)
        session.pop('pending_qr_import_filename', None)
        
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_error:
            logger_handler.logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
        
        return render_template('bulk_qr_import.html', import_result=import_result)
    
    except Exception as e:
        logger_handler.log_database_error('qr_code_bulk_import', e)
        flash(f'Import failed: {str(e)}', 'error')
        return redirect(url_for('import_bulk_qr_codes'))


@bp.route('/qr-codes/bulk-import/template', endpoint='download_qr_import_template')
@login_required
def download_qr_import_template():
    """Download Excel template for bulk QR code import"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        wb = Workbook()
        ws = wb.active
        ws.title = "QR Code Import Template"
        
        headers = [
            'QR Code Name',
            'QR Code Location',
            'Project',
            'Location Address',
            'Event',
            'Latitude',
            'Longitude'
        ]
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        example_data = [
            ['HQ-Entrance', 'Main Building', 'Corporate HQ', '123 Main St, Springfield, IL 62701', 'Check IN', 39.781721, -89.650148],
            ['HQ-Exit', 'Main Building', 'Corporate HQ', '123 Main St, Springfield, IL 62701', 'Check OUT', 39.781721, -89.650148],
            ['Site-A-Gate1', 'Construction Site A', 'Construction Projects', '456 Oak Ave, Chicago, IL 60601', 'Check IN', '', '']
        ]
        
        for row_num, row_data in enumerate(example_data, 2):
            for col_num, value in enumerate(row_data, 1):
                ws.cell(row=row_num, column=col_num, value=value)
        
        column_widths = [20, 20, 20, 40, 15, 15, 15]
        for col_num, width in enumerate(column_widths, 1):
            ws.column_dimensions[ws.cell(row=1, column=col_num).column_letter].width = width
        
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        logger_handler.logger.info(f"User {session.get('username', 'unknown')} downloaded QR import template")
        
        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='QR_Code_Import_Template.xlsx'
        )
    
    except Exception as e:
        logger_handler.log_flask_error('qr_import_template_download', str(e))
        flash('Error generating template. Please try again.', 'error')
        return redirect(url_for('import_bulk_qr_codes'))
    
@bp.route('/qr-codes/<int:qr_id>/edit', methods=['GET', 'POST'], endpoint='edit_qr_code')
@login_required
@log_database_operations('qr_code_edit')
def edit_qr_code(qr_id):
    """Enhanced edit QR code with customization support"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        qr_code = QRCode.query.get_or_404(qr_id)

        if request.method == 'POST':
            # Track changes for logging
            old_data = {
                'name': qr_code.name,
                'location': qr_code.location,
                'location_address': qr_code.location_address,
                'location_event': qr_code.location_event,
                'project_id': qr_code.project_id,
                'qr_url': qr_code.qr_url,
                'address_latitude': qr_code.address_latitude,
                'address_longitude': qr_code.address_longitude,
                'coordinate_accuracy': qr_code.coordinate_accuracy,
                # Track old styling
                'fill_color': getattr(qr_code, 'fill_color', '#000000'),
                'back_color': getattr(qr_code, 'back_color', '#FFFFFF')
            }

            # Update QR code fields
            new_name = request.form['name']
            qr_code.name = new_name
            qr_code.location = request.form['location']
            qr_code.location_address = request.form['location_address']
            qr_code.location_event = request.form.get('location_event', '')

            # Handle coordinates
            latitude = request.form.get('address_latitude')
            longitude = request.form.get('address_longitude')
            coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')

            if latitude and longitude:
                try:
                    qr_code.address_latitude = float(latitude)
                    qr_code.address_longitude = float(longitude)
                    qr_code.coordinate_accuracy = coordinate_accuracy
                    qr_code.coordinates_updated_date = datetime.utcnow()
                except (ValueError, TypeError):
                    pass
            elif latitude == '' and longitude == '':
                qr_code.address_latitude = None
                qr_code.address_longitude = None
                qr_code.coordinate_accuracy = None
                qr_code.coordinates_updated_date = None

            # Handle project association
            new_project_id = request.form.get('project_id')
            if new_project_id and new_project_id.strip():
                try:
                    new_project_id = int(new_project_id)
                    project = Project.query.get(new_project_id)
                    if project and project.active_status:
                        qr_code.project_id = new_project_id
                    else:
                        flash('Selected project is not valid or inactive.', 'error')
                        return render_template('edit_qr_code.html', qr_code=qr_code,
                                             projects=Project.query.filter_by(active_status=True).all(),
                                             styles=QRCodeStyle.query.all())
                except (ValueError, TypeError):
                    flash('Invalid project selection.', 'error')
                    return render_template('edit_qr_code.html', qr_code=qr_code,
                                         projects=Project.query.filter_by(active_status=True).all(),
                                         styles=QRCodeStyle.query.all())
            else:
                qr_code.project_id = None

            # Handle QR code customization (only if columns exist)
            fill_color = request.form.get('fill_color', '#000000')
            back_color = request.form.get('back_color', '#FFFFFF')
            box_size = int(request.form.get('box_size', 10))
            border = int(request.form.get('border', 4))
            error_correction = request.form.get('error_correction', 'L')
            style_id = request.form.get('style_id')

            # Update styling fields if they exist
            if hasattr(qr_code, 'fill_color'):
                qr_code.fill_color = fill_color
                qr_code.back_color = back_color
                qr_code.box_size = box_size
                qr_code.border = border
                qr_code.error_correction = error_correction
                qr_code.style_id = int(style_id) if style_id and style_id.isdigit() else None

            # Check if QR code needs regeneration
            name_changed = old_data['name'] != new_name
            styling_changed = (hasattr(qr_code, 'fill_color') and
                             (old_data['fill_color'] != fill_color or
                              old_data['back_color'] != back_color))

            if name_changed:
                new_qr_url = generate_qr_url(new_name, qr_code.id)
                qr_code.qr_url = new_qr_url

            # Regenerate QR code if name or styling changed
            if name_changed or styling_changed:
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"

                # Use new styling if available, otherwise use defaults
                styling = get_qr_styling(qr_code)
                qr_code.qr_code_image = generate_qr_code(
                    data=qr_data,
                    fill_color=styling['fill_color'],
                    back_color=styling['back_color'],
                    box_size=styling['box_size'],
                    border=styling['border'],
                    error_correction=styling['error_correction']
                )

            db.session.commit()

            # Success message
            flash(f'QR Code "{qr_code.name}" updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        # GET request - render edit form
        projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()
        styles = QRCodeStyle.query.order_by(QRCodeStyle.name.asc()).all()

        return render_template('edit_qr_code.html', qr_code=qr_code, projects=projects, styles=styles)

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('qr_code_edit', e)
        flash('QR Code update failed. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@bp.route('/qr-codes/<int:qr_id>/delete', methods=['GET', 'POST'], endpoint='delete_qr_code')
@admin_required
@log_database_operations('qr_code_deletion')
def delete_qr_code(qr_id):
    """Permanently delete QR code (Admin only) - Hard delete - PRESERVING EXACT ROUTE"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        print(f"✅ Found QR Code: {qr_code.name}")

        if request.method == 'POST':
            qr_name = qr_code.name
            qr_code_id = qr_code.id
            print(f"🗑️ ATTEMPTING TO DELETE: {qr_name}")

            # Check if QR exists before delete
            before_count = QRCode.query.count()
            print(f"📊 QR count before delete: {before_count}")

            # Log QR code deletion before actual deletion
            logger_handler.log_qr_code_deleted(
                qr_code_id=qr_code_id,
                qr_code_name=qr_name,
                deleted_by_user_id=session['user_id']
            )

            # Delete the QR code
            db.session.delete(qr_code)
            print("💾 Called db.session.delete()")

            db.session.commit()
            print("💾 Called db.session.commit()")

            # Check count after delete
            after_count = QRCode.query.count()
            print(f"📊 QR count after delete: {after_count}")
            print(f"✅ DELETE SUCCESS! Removed {before_count - after_count} records")

            flash(f'QR code "{qr_name}" has been permanently deleted!', 'success')
            return redirect(url_for('dashboard'))

        # GET request - show confirmation page
        print("📄 Showing confirmation page")
        return render_template('confirm_delete_qr.html', qr_code=qr_code)

    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('qr_code_deletion', e)
        print(f"❌ ERROR in delete route: {e}")
        print(f"❌ Exception type: {type(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        flash('Error deleting QR code. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    
@bp.route('/qr/<string:qr_url>', endpoint='qr_destination')
def qr_destination(qr_url):
    """QR code destination page where staff check in - PRESERVING EXACT ROUTE"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()

        if not qr_code:
            # Log invalid QR code access attempt
            logger_handler.log_security_event(
                event_type="invalid_qr_access",
                description=f"Attempt to access invalid QR code URL: {qr_url}",
                severity="MEDIUM"
            )
            flash('QR code not found or inactive.', 'error')
            return redirect(url_for('index'))

        # Log QR code access
        logger_handler.log_qr_code_accessed(
            qr_code_id=qr_code.id,
            qr_code_name=qr_code.name,
            access_method='scan'
        )

        return render_template('qr_destination.html', qr_code=qr_code)

    except Exception as e:
        logger_handler.log_database_error('qr_code_scan', e)
        flash('Error processing QR code scan.', 'error')
        return redirect(url_for('index'))

@bp.route('/qr/<string:qr_url>/checkin', methods=['POST'], endpoint='qr_checkin')
def qr_checkin(qr_url):
    """
    Enhanced staff check-in with location accuracy calculation
    Allows multiple check-ins with minimum interval between them
    PRESERVES coordinate-to-address conversion functionality
    """
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        print(f"\n🚀 STARTING ENHANCED CHECK-IN PROCESS")
        print(f"   QR URL: {qr_url}")
        print(f"   Timestamp: {datetime.now()}")

        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()

        if not qr_code:
            print(f"❌ QR code not found or inactive: {qr_url}")
            return jsonify({
                'success': False,
                'message': 'QR code not found or inactive.'
            }), 404

        print(f"✅ Found QR code: {qr_code.name} (ID: {qr_code.id})")
        print(f"   Location: {qr_code.location}")
        print(f"   QR Address: {qr_code.location_address}")

        # Get and validate employee ID
        employee_id = request.form.get('employee_id', '').strip()

        if not employee_id:
            return jsonify({
                'success': False,
                'message': 'Employee ID is required.'
            }), 400

        # Check for recent check-ins with 30-minute interval validation
        today = date.today()
        current_time = datetime.now()
        time_interval = int(os.environ.get('TIME_INTERVAL'))
        the_last_checkin_time = current_time - timedelta(minutes=time_interval)

        # Find the most recent check-in for this employee at this location today
        recent_checkin = AttendanceData.query.filter_by(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today
        ).order_by(AttendanceData.check_in_time.desc()).first()

        if recent_checkin:
            # Convert check_in_time (time) to datetime for comparison
            recent_checkin_datetime = datetime.combine(today, recent_checkin.check_in_time)

            # Check if 30 minutes have passed since the last check-in
            if recent_checkin_datetime > the_last_checkin_time:
                minutes_remaining = time_interval - int((current_time - recent_checkin_datetime).total_seconds() / 60)
                print(f"⚠️ Too soon for another {qr_code.location_event} for {employee_id}")
                print(f"   Last {qr_code.location_event}: {recent_checkin.check_in_time.strftime('%H:%M')}")
                print(f"   Minutes remaining: {minutes_remaining}")

                return jsonify({
                    'success': False,
                    'message': f"You can {qr_code.location_event} again in {minutes_remaining} minutes. Last {qr_code.location_event} was at {recent_checkin.check_in_time.strftime("%H:%M")}. \n"
                               f"Puedes volver a registrarte en {minutes_remaining} minutos. El último registro fue a las {recent_checkin.check_in_time.strftime("%H:%M")}."
                }), 400
            else:
                print(f"✅ {time_interval}-minute interval satisfied. Allowing new {qr_code.location_event} for {employee_id}")
        else:
            print(f"✅ First {qr_code.location_event} today for {employee_id}")

        # Process location data with coordinate-to-address conversion
        location_data = process_location_data_enhanced(request.form)

        # Get device and network info
        user_agent_string = request.headers.get('User-Agent', '')
        device_info = detect_device_info(user_agent_string)
        client_ip = get_client_ip()

        print(f"📱 Device Info: {device_info}")
        print(f"🌐 IP Address: {client_ip}")
        print(f"📍 Location Data: {location_data}")

        # Create attendance record
        print(f"\n💾 CREATING ATTENDANCE RECORD:")

        attendance = AttendanceData(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today,
            check_in_time=datetime.now().time(),
            device_info=device_info,
            user_agent=user_agent_string,
            ip_address=client_ip,
            location_name=qr_code.location,
            latitude=location_data['latitude'],
            longitude=location_data['longitude'],
            accuracy=location_data['accuracy'],
            altitude=location_data['altitude'],
            location_source=location_data['source'],
            address=location_data['address'],
            status='present',
            verification_required=False,  # Will be set below if needed
            verification_status=None
        )

        print(f"✅ Created base attendance record")

        # ENHANCED DEBUG: Calculate location accuracy with detailed logging
        print(f"\n🎯 CALCULATING LOCATION ACCURACY WITH ENHANCED DEBUG...")
        print(f"   📊 QR Code Details:")
        print(f"      ID: {qr_code.id}")
        print(f"      Name: {qr_code.name}")
        print(f"      Location: {qr_code.location}")
        print(f"      Location Address: {qr_code.location_address}")
        print(f"      Has location_address: {qr_code.location_address is not None}")
        print(f"      Location Address Length: {len(qr_code.location_address) if qr_code.location_address else 0}")

        print(f"   📍 Check-in Data:")
        print(f"      Latitude: {location_data['latitude']}")
        print(f"      Longitude: {location_data['longitude']}")
        print(f"      GPS Accuracy: {location_data['accuracy']}")
        print(f"      Address: {location_data['address']}")
        print(f"      Address Length: {len(location_data['address']) if location_data['address'] else 0}")
        print(f"      Source: {location_data['source']}")

        location_accuracy = None

        try:
            # Check if we have the required data
            if not qr_code.location_address:
                print(f"❌ QR code location_address is empty or None")
                print(f"   QR Code location_address value: '{qr_code.location_address}'")
            elif not location_data['address'] and not (location_data['latitude'] and location_data['longitude']):
                print(f"❌ No check-in address or coordinates available")
                print(f"   Check-in address: '{location_data['address']}'")
                print(f"   Check-in coords: {location_data['latitude']}, {location_data['longitude']}")
            else:
                print(f"✅ Required data available, proceeding with calculation...")

                location_accuracy = calculate_location_accuracy_enhanced(
                    qr_address=qr_code.location_address,
                    checkin_address=location_data['address'],
                    checkin_lat=location_data['latitude'],
                    checkin_lng=location_data['longitude']
                )

                print(f"📐 Location accuracy calculation result: {location_accuracy}")

                if location_accuracy is not None:
                    attendance.location_accuracy = location_accuracy
                    accuracy_level = get_location_accuracy_level_enhanced(location_accuracy)
                    print(f"✅ Location accuracy set successfully: {location_accuracy:.4f} miles ({accuracy_level})")
                    print(f"📊 Final attendance.location_accuracy value: {attendance.location_accuracy}")
                else:
                    print(f"⚠️ Could not calculate location accuracy - calculation returned None")

                # CHECK DISTANCE THRESHOLD FOR PHOTO VERIFICATION
                print(f"\n📸 CHECKING PHOTO VERIFICATION REQUIREMENT:")
                print(f"   Photo Verification Enabled: {current_app.config.get('PHOTO_VERIFICATION_ENABLED', True)}")
                requires_verification = False
                verification_photo_data = None
                
                if current_app.config.get('PHOTO_VERIFICATION_ENABLED', True) and location_accuracy is not None and location_accuracy > current_app.config.get('DISTANCE_THRESHOLD_FOR_VERIFICATION', 0.3):
                    print(f"⚠️ Distance ({location_accuracy:.3f} mi) exceeds threshold ({current_app.config.get('DISTANCE_THRESHOLD_FOR_VERIFICATION', 0.3)} mi)")
                    
                    # Check if photo was provided
                    verification_photo_data = request.form.get('verification_photo', None)
                    
                    if verification_photo_data:
                        print(f"✅ Verification photo provided (size: {len(verification_photo_data)} chars)")
                        
                        # Validate photo data (basic validation)
                        if verification_photo_data.startswith('data:image/'):
                            attendance.verification_photo = verification_photo_data
                            attendance.verification_required = True
                            attendance.verification_status = 'pending'
                            attendance.verification_timestamp = datetime.now()
                            print(f"✅ Photo verification set to PENDING status")
                        else:
                            print(f"⚠️ Invalid photo format provided")
                            return jsonify({
                                'success': False,
                                'message': 'Invalid photo format. Please try again.',
                                'requires_verification': True
                            }), 400
                    else:
                        print(f"❌ Photo verification REQUIRED but not provided")
                        return jsonify({
                            'success': False,
                            'message': 'Photo verification required. Distance from location is too far.',
                            'requires_verification': True,
                            'distance': round(location_accuracy, 3),
                            'threshold': current_app.config.get('DISTANCE_THRESHOLD_FOR_VERIFICATION', 0.3)
                        }), 400
                else:
                    print(f"✅ Distance within threshold - no verification needed")

        except Exception as e:
            print(f"❌ Error in location accuracy calculation: {e}")
            print(f"❌ Full traceback: {traceback.format_exc()}")

        # ENHANCED DEBUG: Save to database with verification
        try:
            print(f"\n💾 SAVING TO DATABASE...")
            print(f"   Attendance object before save:")
            print(f"      Employee ID: {attendance.employee_id}")
            print(f"      Location: {attendance.location_name}")
            print(f"      Latitude: {attendance.latitude}")
            print(f"      Longitude: {attendance.longitude}")
            print(f"      Address: {attendance.address}")
            print(f"      Location Accuracy: {attendance.location_accuracy}")

            db.session.add(attendance)
            db.session.commit()

            # Log verification if required
            if attendance.verification_required:
                logger_handler.log_photo_verification(
                    employee_id=attendance.employee_id,
                    qr_code_id=qr_code.id,
                    distance=location_accuracy,
                    status='pending'
                )

            # VERIFICATION: Read back from database
            saved_record = AttendanceData.query.get(attendance.id)
            print(f"✅ Successfully saved attendance record with ID: {attendance.id}")
            print(f"📊 Verification - location accuracy in database: {saved_record.location_accuracy}")

            if saved_record.location_accuracy != attendance.location_accuracy:
                print(f"⚠️ WARNING: Database value differs from object value!")
                print(f"   Object value: {attendance.location_accuracy}")
                print(f"   Database value: {saved_record.location_accuracy}")

            # Add enhanced logging for location accuracy save
            if attendance.location_accuracy is not None:
                logger_handler.logger.info(f"Location accuracy calculated and saved: {attendance.location_accuracy:.4f} miles for employee {attendance.employee_id}")
            else:
                logger_handler.logger.warning(f"Location accuracy could not be calculated for employee {attendance.employee_id} at QR {qr_code.name}")

            # Count total check-ins for today for this employee at this location
            today_checkin_count = AttendanceData.query.filter_by(
                qr_code_id=qr_code.id,
                employee_id=employee_id.upper(),
                check_in_date=today
            ).count()

            checkin_sequence_text = f"{qr_code.location_event} details"

        except Exception as e:
            print(f"❌ Database error: {e}")
            print(f"❌ Full traceback: {traceback.format_exc()}")
            db.session.rollback()
            logger_handler.log_database_error('checkin_save', e)
            return jsonify({
                'success': False,
                'message': 'Database error occurred.'
            }), 500

        # Return success response with sequence information
        response_data = {
            'success': True,
            'message': f'Check-in successful! {checkin_sequence_text} for today.',
            'data': {
                'employee_id': attendance.employee_id,
                'location': qr_code.location_address,
                'location_event': qr_code.location_event,
                'event': qr_code.location_event,  # Add both for compatibility
                'check_in_time': attendance.check_in_time.strftime('%I:%M %p'),  # 12-hour format
                'check_in_date': attendance.check_in_date.strftime('%B %d, %Y'),  # Full date format
                'device_info': attendance.device_info,
                'ip_address': attendance.ip_address,
                'location_accuracy': location_accuracy,
                'checkin_count_today': today_checkin_count,
                'checkin_sequence': checkin_sequence_text
            }
        }

        if location_data['address']:
            response_data['data']['address'] = location_data['address']

        if location_data['latitude'] and location_data['longitude']:
            response_data['data']['coordinates'] = f"{location_data['latitude']:.10f}, {location_data['longitude']:.10f}"

        # Enhanced logging for successful check-in with all details
        print(f"✅ Check-in completed successfully")
        print(f"   Employee ID: {attendance.employee_id}")
        print(f"   Time: {attendance.check_in_time.strftime('%I:%M %p')}")
        print(f"   Date: {attendance.check_in_date.strftime('%B %d, %Y')}")
        print(f"   Location: {attendance.location_name}")
        print(f"   Action: {qr_code.location_event}")
        print(f"   Address: {attendance.address}")
        print(f"   Today's count: {today_checkin_count}")
        
        # Log to database for audit trail
        logger_handler.logger.info(f"Check-in success - Employee: {attendance.employee_id}, Location: {attendance.location_name}, Time: {attendance.check_in_time}, Action: {qr_code.location_event}")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ Unexpected error in check-in process: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")

        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during check-in.'
        }), 500

@bp.route('/qr-codes/<int:qr_id>/toggle-status', methods=['POST'], endpoint='toggle_qr_status')
@login_required
def toggle_qr_status(qr_id):
    """Toggle QR code active/inactive status"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
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

@bp.route('/qr-codes/<int:qr_id>/copy-url', methods=['POST'], endpoint='copy_qr_url')
@login_required
def copy_qr_url(qr_id):
    """Log QR code URL copy action"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        
        # Log URL copy action
        logger_handler.logger.info(f"User {session.get('username', 'unknown')} copied URL for QR code {qr_code.name} (ID: {qr_id})")
        
        return jsonify({
            'success': True,
            'message': f'QR code URL copied to clipboard!',
            'url': f"{request.url_root}qr/{qr_code.qr_url}"
        })

    except Exception as e:
        logger_handler.logger.error(f"Error copying QR URL for ID {qr_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error copying QR code URL.'
        }), 500

@bp.route('/qr-codes/<int:qr_id>/open-link', methods=['POST'], endpoint='open_qr_link')
@login_required
def open_qr_link(qr_id):
    """Log QR code link open action"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        
        # Log link open action
        logger_handler.logger.info(f"User {session.get('username', 'unknown')} opened link for QR code {qr_code.name} (ID: {qr_id})")
        
        return jsonify({
            'success': True,
            'message': f'Opening QR code link...',
            'url': f"{request.url_root}qr/{qr_code.qr_url}"
        })

    except Exception as e:
        logger_handler.logger.error(f"Error opening QR link for ID {qr_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'Error opening QR code link.'
        }), 500

@bp.route('/qr-codes/<int:qr_id>/activate', methods=['POST'], endpoint='activate_qr_code')
@login_required
def activate_qr_code(qr_id):
    """Activate a QR code"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
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

@bp.route('/qr-codes/<int:qr_id>/deactivate', methods=['POST'], endpoint='deactivate_qr_code')
@login_required
def deactivate_qr_code(qr_id):
    """Deactivate a QR code"""
    QRCode, QRCodeStyle, Project, AttendanceData, Employee, User = _get_models()["QRCode"], _get_models()["QRCodeStyle"], _get_models()["Project"], _get_models()["AttendanceData"], _get_models()["Employee"], _get_models()["User"]
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
