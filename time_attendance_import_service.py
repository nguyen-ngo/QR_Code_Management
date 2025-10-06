"""
Enhanced Time Attendance Import Service
========================================

Improved service with duplicate detection, advanced validation, 
and better error handling for Excel imports.
"""

import pandas as pd
import uuid
from datetime import datetime, time
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional, Tuple
import traceback
import hashlib

class TimeAttendanceImportService:
    """Enhanced service to handle time attendance data import from Excel files"""
    
    def __init__(self, db, logger_handler=None):
        """Initialize the import service with database and logger"""
        self.db = db
        self.logger = logger_handler
        
    def import_from_excel(self, file_path: str, created_by: int = None, 
                         import_source: str = None, skip_duplicates: bool = True) -> Dict[str, Any]:
        """
        Import time attendance data from Excel file with enhanced validation
        
        Args:
            file_path: Path to the Excel file
            created_by: User ID who initiated the import
            import_source: Description of import source
            skip_duplicates: Whether to skip duplicate records
            
        Returns:
            Dictionary containing import results
        """
        batch_id = str(uuid.uuid4())
        import_results = {
            'batch_id': batch_id,
            'total_records': 0,
            'imported_records': 0,
            'failed_records': 0,
            'duplicate_records': 0,
            'skipped_records': 0,
            'errors': [],
            'warnings': [],
            'success': False,
            'import_date': datetime.utcnow()
        }
        
        try:
            # Log import start
            if self.logger:
                self.logger.logger.info(f"Starting enhanced time attendance import from {file_path} by user {created_by}")
            
            # Read Excel file with multiple sheet support
            try:
                excel_file = pd.ExcelFile(file_path)
                sheet_name = excel_file.sheet_names[0]  # Use first sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                if self.logger:
                    self.logger.logger.info(f"Reading sheet: {sheet_name} with {len(df)} rows")
            except Exception as e:
                error_msg = f"Failed to read Excel file: {str(e)}"
                import_results['errors'].append(error_msg)
                if self.logger:
                    self.logger.logger.error(error_msg)
                return import_results
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                import_results['errors'].append(error_msg)
                if self.logger:
                    self.logger.logger.error(error_msg)
                return import_results
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            import_results['total_records'] = len(df)
            
            if import_results['total_records'] == 0:
                error_msg = "No valid data rows found in Excel file"
                import_results['errors'].append(error_msg)
                return import_results
            
            # Track duplicates using hash
            duplicate_hashes = set()
            if skip_duplicates:
                duplicate_hashes = self._get_existing_record_hashes()
            
            # Process each row with enhanced validation
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row['ID']) or pd.isna(row['Name']):
                        import_results['skipped_records'] += 1
                        import_results['warnings'].append(f"Row {index + 2}: Skipped due to missing ID or Name")
                        continue
                    
                    # Validate and parse date
                    try:
                        attendance_date = pd.to_datetime(row['Date']).date()
                    except Exception as date_error:
                        import_results['failed_records'] += 1
                        import_results['errors'].append(f"Row {index + 2}: Invalid date format - {str(date_error)}")
                        continue
                    
                    # Validate and parse time with multiple format support
                    try:
                        attendance_time = self._parse_time_field(row['Time'])
                    except Exception as time_error:
                        import_results['failed_records'] += 1
                        import_results['errors'].append(f"Row {index + 2}: Invalid time format - {str(time_error)}")
                        continue
                    
                    # Prepare record data
                    record_data = {
                        'employee_id': str(row['ID']).strip(),
                        'employee_name': str(row['Name']).strip(),
                        'platform': str(row.get('Platform', '')).strip() if pd.notna(row.get('Platform')) else None,
                        'attendance_date': attendance_date,
                        'attendance_time': attendance_time,
                        'location_name': str(row['Location Name']).strip(),
                        'action_description': str(row['Action Description']).strip(),
                        'event_description': str(row.get('Event Description', '')).strip() if pd.notna(row.get('Event Description')) else None,
                        'recorded_address': str(row.get('Recorded Address', '')).strip() if pd.notna(row.get('Recorded Address')) else None,
                    }
                    
                    # Check for duplicates
                    if skip_duplicates:
                        record_hash = self._generate_record_hash(record_data)
                        if record_hash in duplicate_hashes:
                            import_results['duplicate_records'] += 1
                            import_results['warnings'].append(
                                f"Row {index + 2}: Duplicate record for {record_data['employee_name']} "
                                f"on {attendance_date} at {attendance_time} - Skipped"
                            )
                            continue
                        duplicate_hashes.add(record_hash)
                    
                    # Create TimeAttendance record
                    from models.time_attendance import TimeAttendance
                    
                    time_attendance_record = TimeAttendance(
                        **record_data,
                        import_batch_id=batch_id,
                        import_source=import_source or f"Excel Import - {file_path}",
                        created_by=created_by
                    )
                    
                    self.db.session.add(time_attendance_record)
                    import_results['imported_records'] += 1
                    
                    # Commit in batches for better performance
                    if import_results['imported_records'] % 100 == 0:
                        self.db.session.flush()
                    
                except Exception as e:
                    import_results['failed_records'] += 1
                    error_msg = f"Row {index + 2}: {str(e)}"
                    import_results['errors'].append(error_msg)
                    
                    if self.logger:
                        self.logger.logger.warning(f"Failed to import row {index + 2}: {e}")
                    
                    continue
            
            # Final commit
            self.db.session.commit()
            import_results['success'] = import_results['imported_records'] > 0
            
            # Log successful import
            if self.logger:
                self.logger.logger.info(
                    f"Time attendance import completed - Batch: {batch_id}, "
                    f"Total: {import_results['total_records']}, "
                    f"Imported: {import_results['imported_records']}, "
                    f"Failed: {import_results['failed_records']}, "
                    f"Duplicates: {import_results['duplicate_records']}, "
                    f"Skipped: {import_results['skipped_records']}"
                )
            
        except SQLAlchemyError as e:
            self.db.session.rollback()
            error_msg = f"Database error during import: {str(e)}"
            import_results['errors'].append(error_msg)
            
            if self.logger:
                self.logger.log_database_error('time_attendance_import', e)
        
        except Exception as e:
            self.db.session.rollback()
            error_msg = f"Unexpected error during import: {str(e)}"
            import_results['errors'].append(error_msg)
            import_results['traceback'] = traceback.format_exc()
            
            if self.logger:
                self.logger.logger.error(f"Time attendance import failed: {e}")
                self.logger.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return import_results
    
    def _parse_time_field(self, time_value) -> time:
        """
        Parse time field with multiple format support
        
        Args:
            time_value: Time value from Excel (string, datetime, or time object)
            
        Returns:
            time object
        """
        if pd.isna(time_value):
            raise ValueError("Time value is empty")
        
        # If already a time object
        if isinstance(time_value, time):
            return time_value
        
        # Convert to string and try parsing
        time_str = str(time_value).strip()
        
        # Try common time formats
        time_formats = [
            '%H:%M:%S',
            '%H:%M',
            '%I:%M:%S %p',
            '%I:%M %p',
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue
        
        # Try pandas datetime parsing as fallback
        try:
            return pd.to_datetime(time_value).time()
        except:
            pass
        
        raise ValueError(f"Unable to parse time value: {time_value}")
    
    def _generate_record_hash(self, record_data: Dict) -> str:
        """
        Generate unique hash for a record to detect duplicates
        
        Args:
            record_data: Dictionary containing record information
            
        Returns:
            Hash string
        """
        hash_string = (
            f"{record_data['employee_id']}_"
            f"{record_data['attendance_date']}_"
            f"{record_data['attendance_time']}_"
            f"{record_data['location_name']}_"
            f"{record_data['action_description']}"
        )
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _get_existing_record_hashes(self) -> set:
        """
        Get hashes of existing records to detect duplicates
        
        Returns:
            Set of record hashes
        """
        try:
            from models.time_attendance import TimeAttendance
            
            existing_records = TimeAttendance.query.all()
            hashes = set()
            
            for record in existing_records:
                record_data = {
                    'employee_id': record.employee_id,
                    'attendance_date': record.attendance_date,
                    'attendance_time': record.attendance_time,
                    'location_name': record.location_name,
                    'action_description': record.action_description
                }
                hashes.add(self._generate_record_hash(record_data))
            
            return hashes
        except Exception as e:
            if self.logger:
                self.logger.logger.warning(f"Failed to get existing record hashes: {e}")
            return set()
    
    def validate_excel_file(self, file_path: str) -> Dict[str, Any]:
        """
        Enhanced Excel file validation with detailed analysis
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'valid': False,
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'columns': [],
            'sample_data': [],
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Get file information
            import os
            file_stats = os.stat(file_path)
            validation_results['file_info'] = {
                'size': file_stats.st_size,
                'size_mb': round(file_stats.st_size / (1024 * 1024), 2)
            }
            
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Remove empty rows
            original_row_count = len(df)
            df = df.dropna(how='all')
            
            validation_results['total_rows'] = len(df)
            validation_results['columns'] = df.columns.tolist()
            
            if original_row_count > len(df):
                validation_results['warnings'].append(
                    f"Removed {original_row_count - len(df)} completely empty rows"
                )
            
            # Get sample data (first 5 rows)
            sample_rows = df.head(5).to_dict('records')
            validation_results['sample_data'] = sample_rows
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_results['errors'].append(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )
            
            # Check for empty required fields
            valid_row_count = 0
            for index, row in df.iterrows():
                is_valid = True
                for col in required_columns:
                    if col in df.columns and pd.isna(row[col]):
                        is_valid = False
                        break
                
                if is_valid:
                    valid_row_count += 1
            
            validation_results['valid_rows'] = valid_row_count
            validation_results['invalid_rows'] = len(df) - valid_row_count
            
            if validation_results['invalid_rows'] > 0:
                validation_results['warnings'].append(
                    f"{validation_results['invalid_rows']} rows have missing required data"
                )
            
            # Validate date format
            if 'Date' in df.columns:
                invalid_dates = 0
                for idx, date_val in df['Date'].items():
                    if pd.notna(date_val):
                        try:
                            pd.to_datetime(date_val)
                        except:
                            invalid_dates += 1
                
                if invalid_dates > 0:
                    validation_results['warnings'].append(
                        f"{invalid_dates} rows have invalid date format"
                    )
            
            # Validate time format
            if 'Time' in df.columns:
                invalid_times = 0
                for idx, time_val in df['Time'].items():
                    if pd.notna(time_val):
                        try:
                            self._parse_time_field(time_val)
                        except:
                            invalid_times += 1
                
                if invalid_times > 0:
                    validation_results['warnings'].append(
                        f"{invalid_times} rows have invalid time format"
                    )
            
            # Check for potential duplicates
            if all(col in df.columns for col in ['ID', 'Date', 'Time', 'Location Name']):
                duplicate_check = df[['ID', 'Date', 'Time', 'Location Name']].duplicated()
                duplicate_count = duplicate_check.sum()
                
                if duplicate_count > 0:
                    validation_results['warnings'].append(
                        f"{duplicate_count} potential duplicate records detected"
                    )
            
            # Set valid flag
            validation_results['valid'] = (
                len(validation_results['errors']) == 0 and 
                validation_results['valid_rows'] > 0
            )
            
        except Exception as e:
            validation_results['errors'].append(f"Failed to validate Excel file: {str(e)}")
            if self.logger:
                self.logger.logger.error(f"Validation error: {e}")
        
        return validation_results
    
    def get_import_summary(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed summary of imported data by batch ID
        
        Args:
            batch_id: Import batch identifier
            
        Returns:
            Dictionary containing import summary
        """
        try:
            from models.time_attendance import TimeAttendance
            
            records = TimeAttendance.get_by_import_batch(batch_id)
            
            if not records:
                return None
            
            # Calculate summary statistics
            total_records = len(records)
            unique_employees = len(set(record.employee_id for record in records))
            unique_locations = len(set(record.location_name for record in records))
            date_range = {
                'start': min(record.attendance_date for record in records),
                'end': max(record.attendance_date for record in records)
            }
            
            # Group by action description
            actions = {}
            for record in records:
                action = record.action_description
                actions[action] = actions.get(action, 0) + 1
            
            # Group by employee
            employee_summary = {}
            for record in records:
                emp_id = record.employee_id
                if emp_id not in employee_summary:
                    employee_summary[emp_id] = {
                        'name': record.employee_name,
                        'count': 0
                    }
                employee_summary[emp_id]['count'] += 1
            
            return {
                'batch_id': batch_id,
                'total_records': total_records,
                'unique_employees': unique_employees,
                'unique_locations': unique_locations,
                'date_range': date_range,
                'actions': actions,
                'employee_summary': employee_summary,
                'import_date': records[0].import_date if records else None,
                'import_source': records[0].import_source if records else None
            }
            
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Failed to get import summary for batch {batch_id}: {e}")
            return None
    
    def delete_import_batch(self, batch_id: str, deleted_by: int = None) -> Dict[str, Any]:
        """
        Delete all records from a specific import batch
        
        Args:
            batch_id: Import batch identifier
            deleted_by: User ID who initiated the deletion
            
        Returns:
            Dictionary containing deletion results
        """
        result = {
            'success': False,
            'deleted_count': 0,
            'message': ''
        }
        
        try:
            from models.time_attendance import TimeAttendance
            
            records = TimeAttendance.query.filter_by(import_batch_id=batch_id).all()
            deleted_count = len(records)
            
            if deleted_count == 0:
                result['message'] = 'No records found for this batch'
                return result
            
            # Delete records
            for record in records:
                self.db.session.delete(record)
            
            self.db.session.commit()
            
            # Log deletion
            if self.logger:
                self.logger.logger.info(
                    f"User {deleted_by} deleted import batch {batch_id} - "
                    f"Removed {deleted_count} records"
                )
            
            result['success'] = True
            result['deleted_count'] = deleted_count
            result['message'] = f'Successfully deleted {deleted_count} records'
            
        except Exception as e:
            self.db.session.rollback()
            result['message'] = f'Error deleting batch: {str(e)}'
            
            if self.logger:
                self.logger.logger.error(f"Failed to delete batch {batch_id}: {e}")
        
        return result
    