"""
Enhanced Time Attendance Import Service with Duplicate Review
============================================================

Added functionality to detect and present duplicates for user review.
"""

import pandas as pd
import uuid
from datetime import datetime, time
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional, Tuple
import traceback
import hashlib

class TimeAttendanceImportService:
    """Enhanced service with duplicate detection and review"""
    
    def __init__(self, db, logger_handler=None):
        """Initialize the import service with database and logger"""
        self.db = db
        self.logger = logger_handler

    def _update_progress(self, current: int, total: int, status: str = "Processing"):
        """
        Update progress information for real-time tracking
        
        Args:
            current: Current record number being processed
            total: Total number of records
            status: Status message
        """
        if hasattr(self, 'progress_callback') and self.progress_callback:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.progress_callback({
                'current': current,
                'total': total,
                'percentage': percentage,
                'status': status
            })

    def _parse_excel_hyperlink(self, cell_value: str) -> str:
        """
        Parse Excel HYPERLINK formula to extract the display text (address)
        
        Handles formats like:
        - =HYPERLINK("http://maps.google.com/maps?q=[lat],[long]","123 Maint Street")
        - Regular text (no formula)
        
        Args:
            cell_value: The cell value which may contain a HYPERLINK formula
            
        Returns:
            Extracted address text or original value if not a hyperlink
        """
        if not cell_value or not isinstance(cell_value, str):
            return cell_value
        
        # Check if it's a HYPERLINK formula
        if cell_value.strip().startswith('=HYPERLINK('):
            try:
                # Extract content between HYPERLINK parentheses
                # Pattern: =HYPERLINK("url","display_text")
                import re
                
                # Match the display text (second quoted string)
                pattern = r'=HYPERLINK\s*\(\s*"[^"]*"\s*,\s*"([^"]*)"\s*\)'
                match = re.search(pattern, cell_value)
                
                if match:
                    address_text = match.group(1)
                    if self.logger:
                        self.logger.logger.debug(f"Parsed HYPERLINK: {cell_value[:50]}... -> {address_text}")
                    return address_text.strip()
                else:
                    # If pattern doesn't match, try to extract any quoted text after comma
                    parts = cell_value.split(',', 1)
                    if len(parts) > 1:
                        # Get text between last quotes
                        text_part = parts[1].strip().rstrip(')')
                        if '"' in text_part:
                            # Extract text between quotes
                            address_text = text_part.split('"')[1] if text_part.count('"') >= 2 else text_part
                            if self.logger:
                                self.logger.logger.debug(f"Parsed HYPERLINK (fallback): {cell_value[:50]}... -> {address_text}")
                            return address_text.strip()
            except Exception as e:
                if self.logger:
                    self.logger.logger.warning(f"Failed to parse HYPERLINK formula: {cell_value[:50]}... Error: {e}")
                # Return original if parsing fails
                return cell_value
        
        # Not a hyperlink formula, return as-is
        return cell_value.strip() if isinstance(cell_value, str) else cell_value
    
    def _process_recorded_address(self, row):
        """
        Process recorded address field, handling Excel HYPERLINK formulas
        
        Args:
            row: DataFrame row containing the 'Recorded Address' column
            
        Returns:
            Parsed address string or None
        """
        recorded_address_value = row.get('Recorded Address', '')
        
        if pd.notna(recorded_address_value):
            # Convert to string and parse if it's a HYPERLINK formula
            address_str = str(recorded_address_value).strip()
            parsed_address = self._parse_excel_hyperlink(address_str)
            return parsed_address if parsed_address else None
        
        return None
    
    def analyze_for_duplicates(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze file for potential duplicates WITHOUT importing
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing duplicate analysis
        """
        analysis_result = {
            'success': False,
            'total_records': 0,
            'new_records': 0,
            'duplicate_records': 0,
            'duplicates': [],
            'errors': []
        }
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                analysis_result['errors'].append(f"Missing columns: {', '.join(missing_columns)}")
                return analysis_result
            
            # Remove empty rows
            df = df.dropna(how='all')
            analysis_result['total_records'] = len(df)
            
            # Get existing record hashes
            existing_hashes = self._get_existing_record_hashes_with_data()
            
            # Process each row
            duplicates_list = []
            new_records_count = 0
            
            # Process each row with enhanced validation
            for index, row in df.iterrows():
                # Update progress every 10 records or on last record
                if (index + 1) % 10 == 0 or (index + 1) == len(df):
                    self._update_progress(
                        index + 1, 
                        len(df), 
                        f"Processing row {index + 2} of {len(df) + 1}"
                    )
                
                try:
                    # Skip empty rows
                    if pd.isna(row['ID']) or pd.isna(row['Name']):
                        continue
                    
                    # Parse date and time
                    attendance_date = pd.to_datetime(row['Date']).date()
                    attendance_time = self._parse_time_field(row['Time'])
                    
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
                        'recorded_address': self._process_recorded_address(row),
                    }
                    
                    # Check for duplicates
                    record_hash = self._generate_record_hash(record_data)
                    
                    if record_hash in existing_hashes:
                        # Found duplicate - get existing record details
                        existing_record = existing_hashes[record_hash]
                        
                        duplicates_list.append({
                            'row_number': index + 2,
                            'new_record': record_data,
                            'existing_record': existing_record,
                            'hash': record_hash
                        })
                    else:
                        new_records_count += 1
                
                except Exception as e:
                    analysis_result['errors'].append(f"Row {index + 2}: {str(e)}")
                    continue
            
            analysis_result['success'] = True
            analysis_result['new_records'] = new_records_count
            analysis_result['duplicate_records'] = len(duplicates_list)
            analysis_result['duplicates'] = duplicates_list
            
            if self.logger:
                self.logger.logger.info(
                    f"Duplicate analysis complete - Total: {analysis_result['total_records']}, "
                    f"New: {new_records_count}, Duplicates: {len(duplicates_list)}"
                )
        
        except Exception as e:
            analysis_result['errors'].append(f"Analysis failed: {str(e)}")
            if self.logger:
                self.logger.logger.error(f"Duplicate analysis error: {e}")
        
        return analysis_result
    
    def analyze_for_invalid_rows(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze file for invalid rows with detailed error information
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing invalid row analysis
        """
        analysis_result = {
            'success': False,
            'total_rows': 0,
            'valid_rows': 0,
            'invalid_rows': 0,
            'invalid_details': [],
            'errors': []
        }
        
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                analysis_result['errors'].append(f"Missing columns: {', '.join(missing_columns)}")
                return analysis_result
            
            # Remove empty rows
            df = df.dropna(how='all')
            analysis_result['total_rows'] = len(df)
            
            # Process each row and collect invalid ones
            invalid_list = []
            valid_count = 0
            
            for index, row in df.iterrows():
                row_errors = []
                row_data = {
                    'employee_id': None,
                    'employee_name': None,
                    'platform': None,
                    'attendance_date': None,
                    'attendance_time': None,
                    'location_name': None,
                    'action_description': None,
                    'event_description': None,
                    'recorded_address': None
                }
                
                # Check ID
                if pd.isna(row['ID']):
                    row_errors.append("Missing Employee ID")
                else:
                    row_data['employee_id'] = str(row['ID']).strip()
                
                # Check Name
                if pd.isna(row['Name']):
                    row_errors.append("Missing Employee Name")
                else:
                    row_data['employee_name'] = str(row['Name']).strip()
                
                # Check and parse Date
                if pd.isna(row['Date']):
                    row_errors.append("Missing Date")
                else:
                    try:
                        attendance_date = pd.to_datetime(row['Date']).date()
                        row_data['attendance_date'] = attendance_date
                    except Exception:
                        row_errors.append(f"Invalid date format: {row['Date']}")
                
                # Check and parse Time
                if pd.isna(row['Time']):
                    row_errors.append("Missing Time")
                else:
                    try:
                        attendance_time = self._parse_time_field(row['Time'])
                        row_data['attendance_time'] = attendance_time
                    except Exception as e:
                        row_errors.append(f"Invalid time format: {row['Time']}")
                
                # Check Location Name
                if pd.isna(row['Location Name']):
                    row_errors.append("Missing Location Name")
                else:
                    row_data['location_name'] = str(row['Location Name']).strip()
                
                # Check Action Description
                if pd.isna(row['Action Description']):
                    row_errors.append("Missing Action Description")
                else:
                    row_data['action_description'] = str(row['Action Description']).strip()
                
                # Optional fields
                if pd.notna(row.get('Platform')):
                    row_data['platform'] = str(row['Platform']).strip()
                
                if pd.notna(row.get('Event Description')):
                    row_data['event_description'] = str(row['Event Description']).strip()
                
                row_data['recorded_address'] = self._process_recorded_address(row)
                
                # If row has errors, add to invalid list
                if row_errors:
                    invalid_list.append({
                        'row_number': index + 2,  # +2 for header and 0-based index
                        'row_data': row_data,
                        'errors': row_errors
                    })
                else:
                    valid_count += 1
            
            analysis_result['success'] = True
            analysis_result['valid_rows'] = valid_count
            analysis_result['invalid_rows'] = len(invalid_list)
            analysis_result['invalid_details'] = invalid_list
            
            if self.logger:
                self.logger.logger.info(
                    f"Invalid row analysis complete - Total: {analysis_result['total_rows']}, "
                    f"Valid: {valid_count}, Invalid: {len(invalid_list)}"
                )
        
        except Exception as e:
            analysis_result['errors'].append(f"Analysis failed: {str(e)}")
            if self.logger:
                self.logger.logger.error(f"Invalid row analysis error: {e}")
        
        return analysis_result
    
    def import_from_excel(self, file_path: str, created_by: int = None, 
                         import_source: str = None, skip_duplicates: bool = True,
                         force_import_hashes: List[str] = None) -> Dict[str, Any]:
        """
        Import time attendance data from Excel file with enhanced duplicate handling
        
        Args:
            file_path: Path to the Excel file
            created_by: User ID who initiated the import
            import_source: Description of import source
            skip_duplicates: Whether to skip duplicate records
            force_import_hashes: List of hashes to force import (user confirmed duplicates)
            
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
            'forced_duplicates': 0,
            'errors': [],
            'warnings': [],
            'success': False,
            'import_date': datetime.utcnow()
        }
        
        force_import_hashes = force_import_hashes or []
        
        try:
            # Log import start
            if self.logger:
                self.logger.logger.info(
                    f"Starting enhanced time attendance import from {file_path} by user {created_by} "
                    f"(skip_duplicates={skip_duplicates}, force_import={len(force_import_hashes)})"
                )
            
            # Read Excel file
            try:
                excel_file = pd.ExcelFile(file_path)
                sheet_name = excel_file.sheet_names[0]
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
                    
                    # Validate and parse time
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
                        'recorded_address': self._process_recorded_address(row),
                    }
                    
                    # Check for duplicates
                    if skip_duplicates:
                        record_hash = self._generate_record_hash(record_data)
                        
                        # If duplicate and NOT in force import list, skip it
                        if record_hash in duplicate_hashes and record_hash not in force_import_hashes:
                            import_results['duplicate_records'] += 1
                            import_results['warnings'].append(
                                f"Row {index + 2}: Duplicate record for {record_data['employee_name']} "
                                f"on {attendance_date} at {attendance_time} - Skipped"
                            )
                            continue
                        
                        # If in force import list, track it
                        if record_hash in force_import_hashes:
                            import_results['forced_duplicates'] += 1
                        
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
                    f"Forced: {import_results['forced_duplicates']}, "
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
        """Parse time field with multiple format support"""
        if pd.isna(time_value):
            raise ValueError("Time value is empty")
        
        if isinstance(time_value, time):
            return time_value
        
        time_str = str(time_value).strip()
        
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
        
        try:
            return pd.to_datetime(time_value).time()
        except:
            pass
        
        raise ValueError(f"Unable to parse time value: {time_value}")
    
    def _generate_record_hash(self, record_data: Dict) -> str:
        """Generate unique hash for a record to detect duplicates"""
        hash_string = (
            f"{record_data['employee_id']}_"
            f"{record_data['attendance_date']}_"
            f"{record_data['attendance_time']}_"
            f"{record_data['location_name']}_"
            f"{record_data['action_description']}"
        )
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _get_existing_record_hashes(self) -> set:
        """Get hashes of existing records (hash only)"""
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
    
    def _get_existing_record_hashes_with_data(self) -> Dict[str, Dict]:
        """Get hashes with full existing record data for comparison"""
        try:
            from models.time_attendance import TimeAttendance
            
            existing_records = TimeAttendance.query.all()
            hash_map = {}
            
            for record in existing_records:
                record_data = {
                    'employee_id': record.employee_id,
                    'attendance_date': record.attendance_date,
                    'attendance_time': record.attendance_time,
                    'location_name': record.location_name,
                    'action_description': record.action_description
                }
                record_hash = self._generate_record_hash(record_data)
                
                hash_map[record_hash] = {
                    'id': record.id,
                    'employee_id': record.employee_id,
                    'employee_name': record.employee_name,
                    'platform': record.platform,
                    'attendance_date': record.attendance_date,
                    'attendance_time': record.attendance_time,
                    'location_name': record.location_name,
                    'action_description': record.action_description,
                    'event_description': record.event_description,
                    'recorded_address': record.recorded_address,
                    'import_batch_id': record.import_batch_id,
                    'import_date': record.import_date,
                    'import_source': record.import_source
                }
            
            return hash_map
        except Exception as e:
            if self.logger:
                self.logger.logger.warning(f"Failed to get existing records with data: {e}")
            return {}
    
    def validate_excel_file(self, file_path: str) -> Dict[str, Any]:
        """Enhanced Excel file validation with detailed analysis"""
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
            import os
            file_stats = os.stat(file_path)
            validation_results['file_info'] = {
                'size': file_stats.st_size,
                'size_mb': round(file_stats.st_size / (1024 * 1024), 2)
            }
            
            excel_file = pd.ExcelFile(file_path)
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            original_row_count = len(df)
            df = df.dropna(how='all')
            
            validation_results['total_rows'] = len(df)
            validation_results['columns'] = df.columns.tolist()
            
            if original_row_count > len(df):
                validation_results['warnings'].append(
                    f"Removed {original_row_count - len(df)} completely empty rows"
                )
            
            sample_rows = df.head(5).to_dict('records')
            validation_results['sample_data'] = sample_rows
            
            required_columns = ['ID', 'Date', 'Time', 'Location Name', 'Action Description', 'Event Description', 'Recorded Address']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_results['errors'].append(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )
            
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
            
            if all(col in df.columns for col in ['ID', 'Date', 'Time', 'Location Name']):
                duplicate_check = df[['ID', 'Date', 'Time', 'Location Name']].duplicated()
                duplicate_count = duplicate_check.sum()
                
                if duplicate_count > 0:
                    validation_results['warnings'].append(
                        f"{duplicate_count} potential duplicate records detected"
                    )
            
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
    