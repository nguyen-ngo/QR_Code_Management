"""
QR Code Import Service
=====================

Service for handling bulk QR code imports from Excel files.
Follows the same patterns as TimeAttendanceImportService.

IMPORTANT: This service does NOT import any models.
All model classes must be passed as parameters from app.py.
"""

import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional, Tuple
import traceback


class QRCodeImportService:
    """Service for bulk QR code import from Excel files"""
    
    def __init__(self, db, logger_handler=None):
        """Initialize the import service with database and logger"""
        self.db = db
        self.logger = logger_handler

    def validate_excel_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate Excel file structure and data
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Required columns
            required_columns = [
                'QR Code Name',
                'QR Code Location',
                'Project',
                'Location Address',
                'Event'
            ]
            
            # Optional columns
            optional_columns = [
                'Latitude',
                'Longitude'
            ]
            
            # Check for required columns
            missing_columns = []
            for col in required_columns:
                if col not in df.columns:
                    missing_columns.append(col)
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f"Missing required columns: {', '.join(missing_columns)}",
                    'missing_columns': missing_columns
                }
            
            # Validate data
            errors = []
            warnings = []
            valid_rows = []
            invalid_rows = []
            
            for index, row in df.iterrows():
                row_num = index + 2  # Excel row number (header is row 1)
                row_errors = []
                
                # Validate QR Code Name
                if pd.isna(row['QR Code Name']) or str(row['QR Code Name']).strip() == '':
                    row_errors.append(f"Row {row_num}: QR Code Name is required")
                
                # Validate Location
                if pd.isna(row['QR Code Location']) or str(row['QR Code Location']).strip() == '':
                    row_errors.append(f"Row {row_num}: QR Code Location is required")
                
                # Validate Location Address
                if pd.isna(row['Location Address']) or str(row['Location Address']).strip() == '':
                    row_errors.append(f"Row {row_num}: Location Address is required")
                
                # Validate Event
                if pd.isna(row['Event']) or str(row['Event']).strip() == '':
                    row_errors.append(f"Row {row_num}: Event is required")
                
                # Validate Project (must be a string)
                if pd.isna(row['Project']) or str(row['Project']).strip() == '':
                    row_errors.append(f"Row {row_num}: Project is required")
                
                # Validate GPS coordinates if provided
                has_latitude = 'Latitude' in df.columns and not pd.isna(row.get('Latitude'))
                has_longitude = 'Longitude' in df.columns and not pd.isna(row.get('Longitude'))
                
                if has_latitude and has_longitude:
                    try:
                        lat = float(row['Latitude'])
                        lon = float(row['Longitude'])
                        
                        # Validate latitude range
                        if not (-90 <= lat <= 90):
                            row_errors.append(f"Row {row_num}: Latitude must be between -90 and 90")
                        
                        # Validate longitude range
                        if not (-180 <= lon <= 180):
                            row_errors.append(f"Row {row_num}: Longitude must be between -180 and 180")
                    except (ValueError, TypeError):
                        row_errors.append(f"Row {row_num}: Invalid GPS coordinates format")
                elif has_latitude or has_longitude:
                    warnings.append(f"Row {row_num}: Both Latitude and Longitude must be provided together")
                
                if row_errors:
                    errors.extend(row_errors)
                    invalid_rows.append({
                        'row_number': row_num,
                        'data': row.to_dict(),
                        'errors': row_errors
                    })
                else:
                    valid_rows.append({
                        'row_number': row_num,
                        'data': row.to_dict()
                    })
            
            return {
                'success': len(errors) == 0,
                'total_rows': len(df),
                'valid_rows': len(valid_rows),
                'invalid_rows': len(invalid_rows),
                'errors': errors,
                'warnings': warnings,
                'valid_data': valid_rows,
                'invalid_data': invalid_rows
            }
            
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Error validating Excel file: {e}")
            return {
                'success': False,
                'error': f"Error reading Excel file: {str(e)}",
                'total_rows': 0,
                'valid_rows': 0,
                'invalid_rows': 0,
                'errors': [str(e)],
                'warnings': []
            }

    def import_from_excel(
        self,
        file_path: str,
        created_by: int,
        generate_qr_code_func,
        generate_qr_url_func,
        request_url_root: str,
        project_lookup: Dict[str, int] = None,
        QRCode=None,
        Project=None,
        geocode_func=None
    ) -> Dict[str, Any]:
        """
        Import QR codes from Excel file
        
        Args:
            file_path: Path to the Excel file
            created_by: User ID who initiated the import
            generate_qr_code_func: Function to generate QR code image
            generate_qr_url_func: Function to generate QR URL
            request_url_root: Base URL for QR code destination
            project_lookup: Dictionary mapping project names to IDs
            QRCode: QRCode model class (passed from app.py)
            Project: Project model class (passed from app.py)
            geocode_func: Function to geocode addresses (optional, for auto-geocoding)
            
        Returns:
            Dictionary with import results
        """
        # Models are now passed as parameters to avoid import issues
        
        # Validate that model classes were passed
        if QRCode is None or Project is None:
            return {
                'success': False,
                'error': 'Model classes not provided. Please update your route to pass QRCode and Project models.',
                'imported_records': 0,
                'failed_records': 0,
                'errors': ['Model classes missing']
            }
        
        try:
            # First validate the file
            validation_result = self.validate_excel_file(file_path)
            
            if not validation_result['success']:
                return {
                    'success': False,
                    'error': validation_result.get('error', 'Validation failed'),
                    'imported_records': 0,
                    'failed_records': validation_result['total_rows'],
                    'errors': validation_result['errors']
                }
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Track import statistics
            imported_count = 0
            failed_count = 0
            geocoded_count = 0  # Track how many addresses were auto-geocoded
            errors = []
            imported_qr_codes = []
            
            # If no project lookup provided, create one
            if project_lookup is None:
                projects = Project.query.filter_by(active_status=True).all()
                project_lookup = {p.name: p.id for p in projects}
            
            for index, row in df.iterrows():
                row_num = index + 2
                
                try:
                    # Extract data
                    name = str(row['QR Code Name']).strip()
                    location = str(row['QR Code Location']).strip()
                    location_address = str(row['Location Address']).strip()
                    location_event = str(row['Event']).strip()
                    project_name = str(row['Project']).strip()
                    
                    # Get project ID
                    project_id = project_lookup.get(project_name)
                    if not project_id:
                        errors.append(f"Row {row_num}: Project '{project_name}' not found")
                        failed_count += 1
                        continue
                    
                    # Extract GPS coordinates if provided
                    address_latitude = None
                    address_longitude = None
                    has_coordinates = False
                    coordinate_accuracy = None
                    
                    if 'Latitude' in df.columns and 'Longitude' in df.columns:
                        if not pd.isna(row.get('Latitude')) and not pd.isna(row.get('Longitude')):
                            try:
                                address_latitude = float(row['Latitude'])
                                address_longitude = float(row['Longitude'])
                                has_coordinates = True
                                coordinate_accuracy = 'manual'
                                
                                if self.logger:
                                    self.logger.logger.info(f"Row {row_num}: Using provided coordinates ({address_latitude}, {address_longitude})")
                            except (ValueError, TypeError):
                                if self.logger:
                                    self.logger.logger.warning(f"Row {row_num}: Invalid coordinate format, will attempt geocoding")
                    
                    # Auto-geocode if coordinates not provided and geocode function available
                    if not has_coordinates and geocode_func and location_address:
                        try:
                            if self.logger:
                                self.logger.logger.info(f"Row {row_num}: Attempting to geocode address: {location_address[:50]}...")
                            
                            # Call the geocoding function
                            geocoded_lat, geocoded_lng, geocoded_accuracy = geocode_func(location_address)
                            
                            if geocoded_lat and geocoded_lng:
                                address_latitude = geocoded_lat
                                address_longitude = geocoded_lng
                                has_coordinates = True
                                coordinate_accuracy = geocoded_accuracy if geocoded_accuracy else 'geocoded'
                                geocoded_count += 1  # Increment geocoded counter
                                
                                if self.logger:
                                    self.logger.logger.info(
                                        f"Row {row_num}: Successfully geocoded to ({address_latitude}, {address_longitude}) "
                                        f"with accuracy: {coordinate_accuracy}"
                                    )
                            else:
                                if self.logger:
                                    self.logger.logger.warning(f"Row {row_num}: Geocoding returned no results for address")
                        except Exception as geocode_error:
                            if self.logger:
                                self.logger.logger.error(f"Row {row_num}: Geocoding error: {geocode_error}")
                            # Continue without coordinates - they're optional
                    
                    # Check for duplicate QR code name
                    existing_qr = QRCode.query.filter_by(name=name, active_status=True).first()
                    if existing_qr:
                        errors.append(f"Row {row_num}: QR code with name '{name}' already exists")
                        failed_count += 1
                        continue
                    
                    # Create new QR code record (without URL and image first)
                    new_qr_code = QRCode(
                        name=name,
                        location=location,
                        location_address=location_address,
                        location_event=location_event,
                        qr_code_image="",
                        qr_url="",
                        created_by=created_by,
                        project_id=project_id,
                        address_latitude=address_latitude,
                        address_longitude=address_longitude,
                        coordinate_accuracy=coordinate_accuracy,
                        coordinates_updated_date=datetime.utcnow() if has_coordinates else None,
                        fill_color='#000000',
                        back_color='#FFFFFF',
                        box_size=10,
                        border=4,
                        error_correction='H'  # Highest error correction level (30% recovery)
                    )
                    
                    # Add to session and flush to get ID
                    self.db.session.add(new_qr_code)
                    self.db.session.flush()
                    
                    # Generate URL and QR code image
                    qr_url = generate_qr_url_func(name, new_qr_code.id)
                    qr_data = f"{request_url_root}qr/{qr_url}"
                    qr_image = generate_qr_code_func(
                        data=qr_data,
                        fill_color='#000000',
                        back_color='#FFFFFF',
                        box_size=10,
                        border=4,
                        error_correction='H'  # Highest error correction level (30% recovery)
                    )
                    
                    # Update QR code with URL and image
                    new_qr_code.qr_url = qr_url
                    new_qr_code.qr_code_image = qr_image
                    
                    imported_count += 1
                    imported_qr_codes.append({
                        'name': name,
                        'location': location,
                        'project': project_name,
                        'id': new_qr_code.id
                    })
                    
                except Exception as row_error:
                    self.db.session.rollback()
                    error_msg = f"Row {row_num}: {str(row_error)}"
                    errors.append(error_msg)
                    failed_count += 1
                    
                    if self.logger:
                        self.logger.logger.error(f"Error importing row {row_num}: {row_error}")
            
            # Commit all successful imports
            if imported_count > 0:
                self.db.session.commit()
                
                if self.logger:
                    self.logger.logger.info(
                        f"Bulk QR code import completed: {imported_count} imported, {failed_count} failed, "
                        f"{geocoded_count} addresses auto-geocoded"
                    )
            
            return {
                'success': True,
                'imported_records': imported_count,
                'failed_records': failed_count,
                'geocoded_records': geocoded_count,
                'total_rows': len(df),
                'errors': errors,
                'imported_qr_codes': imported_qr_codes
            }
            
        except Exception as e:
            self.db.session.rollback()
            
            if self.logger:
                self.logger.logger.error(f"Error during QR code import: {e}")
                self.logger.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': str(e),
                'imported_records': 0,
                'failed_records': 0,
                'errors': [str(e)]
            }