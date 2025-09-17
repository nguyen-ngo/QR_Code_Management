"""
Time Attendance Import Service
=============================

Service to handle importing time attendance data from Excel files.
Provides functionality to parse Excel files and import data into the time_attendance table.
"""

import pandas as pd
import uuid
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any, Optional, Tuple
import traceback

class TimeAttendanceImportService:
    """Service to handle time attendance data import from Excel files"""
    
    def __init__(self, db, logger_handler=None):
        """Initialize the import service with database and logger"""
        self.db = db
        self.logger = logger_handler
        
    def import_from_excel(self, file_path: str, created_by: int = None, 
                         import_source: str = None) -> Dict[str, Any]:
        """
        Import time attendance data from Excel file
        
        Args:
            file_path: Path to the Excel file
            created_by: User ID who initiated the import
            import_source: Description of import source
            
        Returns:
            Dictionary containing import results
        """
        batch_id = str(uuid.uuid4())
        import_results = {
            'batch_id': batch_id,
            'total_records': 0,
            'imported_records': 0,
            'failed_records': 0,
            'errors': [],
            'success': False,
            'import_date': datetime.utcnow()
        }
        
        try:
            # Log import start
            if self.logger:
                self.logger.logger.info(f"Starting time attendance import from {file_path} by user {created_by}")
            
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                error_msg = f"Missing required columns: {', '.join(missing_columns)}"
                import_results['errors'].append(error_msg)
                if self.logger:
                    self.logger.logger.error(f"Import failed - {error_msg}")
                return import_results
            
            import_results['total_records'] = len(df)
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Parse date and time
                    attendance_date = pd.to_datetime(row['Date']).date()
                    
                    # Handle time parsing - could be string or time object
                    time_str = str(row['Time'])
                    if ':' in time_str:
                        attendance_time = datetime.strptime(time_str, '%H:%M:%S').time()
                    else:
                        # Handle Excel time format
                        attendance_time = pd.to_datetime(row['Time']).time()
                    
                    # Create TimeAttendance record
                    from models.time_attendance import TimeAttendance
                    
                    time_attendance_record = TimeAttendance(
                        employee_id=str(row['ID']).strip(),
                        employee_name=str(row['Name']).strip(),
                        platform=str(row.get('Platform', '')).strip() if pd.notna(row.get('Platform')) else None,
                        attendance_date=attendance_date,
                        attendance_time=attendance_time,
                        location_name=str(row['Location Name']).strip(),
                        action_description=str(row['Action Description']).strip(),
                        event_description=str(row.get('Event Description', '')).strip() if pd.notna(row.get('Event Description')) else None,
                        recorded_address=str(row.get('Recorded Address', '')).strip() if pd.notna(row.get('Recorded Address')) else None,
                        import_batch_id=batch_id,
                        import_source=import_source or f"Excel Import - {file_path}",
                        created_by=created_by
                    )
                    
                    self.db.session.add(time_attendance_record)
                    import_results['imported_records'] += 1
                    
                except Exception as e:
                    import_results['failed_records'] += 1
                    error_msg = f"Row {index + 2}: {str(e)}"
                    import_results['errors'].append(error_msg)
                    
                    if self.logger:
                        self.logger.logger.warning(f"Failed to import row {index + 2}: {e}")
                    
                    continue
            
            # Commit all records
            self.db.session.commit()
            import_results['success'] = True
            
            # Log successful import
            if self.logger:
                self.logger.logger.info(
                    f"Time attendance import completed - Batch: {batch_id}, "
                    f"Total: {import_results['total_records']}, "
                    f"Imported: {import_results['imported_records']}, "
                    f"Failed: {import_results['failed_records']}"
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
    
    def validate_excel_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate Excel file structure before import
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'valid': False,
            'total_rows': 0,
            'columns': [],
            'sample_data': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)
            
            validation_results['total_rows'] = len(df)
            validation_results['columns'] = df.columns.tolist()
            
            # Get sample data (first 5 rows)
            sample_rows = df.head(5).to_dict('records')
            validation_results['sample_data'] = sample_rows
            
            # Validate required columns
            required_columns = ['ID', 'Name', 'Date', 'Time', 'Location Name', 'Action Description']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_results['errors'].append(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Check for empty required fields
            for col in required_columns:
                if col in df.columns:
                    empty_count = df[col].isna().sum()
                    if empty_count > 0:
                        validation_results['warnings'].append(
                            f"Column '{col}' has {empty_count} empty values"
                        )
            
            # Validate date format
            if 'Date' in df.columns:
                try:
                    pd.to_datetime(df['Date'], errors='coerce')
                except:
                    validation_results['errors'].append("Invalid date format in 'Date' column")
            
            # Set valid flag
            validation_results['valid'] = len(validation_results['errors']) == 0
            
        except Exception as e:
            validation_results['errors'].append(f"Failed to read Excel file: {str(e)}")
        
        return validation_results
    
    def get_import_summary(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of imported data by batch ID
        
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
            
            return {
                'batch_id': batch_id,
                'total_records': total_records,
                'unique_employees': unique_employees,
                'unique_locations': unique_locations,
                'date_range': date_range,
                'actions': actions,
                'import_date': records[0].import_date if records else None,
                'import_source': records[0].import_source if records else None
            }
            
        except Exception as e:
            if self.logger:
                self.logger.logger.error(f"Failed to get import summary for batch {batch_id}: {e}")
            return None