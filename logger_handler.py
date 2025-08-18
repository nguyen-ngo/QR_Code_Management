#!/usr/bin/env python3
"""
Enhanced Logging Handler for QR Attendance Management System
==========================================================

This module provides comprehensive logging functionality for:
- User login/logout activities with session details
- QR code creation, modification, and deletion operations
- Database transaction errors and connection issues
- Flask application errors and exceptions
- Security events and unauthorized access attempts

Features:
- Structured JSON logging for better analytics
- Rotating log files to prevent disk space issues
- Different log levels for various event types
- Database logging table for critical events
- Performance monitoring and error tracking
"""

import logging
import logging.handlers
import json
import os
import traceback
from datetime import datetime, date, timedelta
from functools import wraps
from flask import request, session, g
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import uuid

class AppLogger:
    """
    Enhanced application logger with multiple output formats and destinations
    """
    
    def __init__(self, app=None, db=None):
        """Initialize the logger with Flask app and database instances"""
        self.app = app
        self.db = db
        self.logger = None
        self.security_logger = None
        
        if app:
            self.init_app(app, db)
    
    def init_app(self, app, db):
        """Initialize logging with Flask application context"""
        self.app = app
        self.db = db
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(app.root_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure main application logger
        self.logger = logging.getLogger('qr_attendance_app')
        self.logger.setLevel(logging.INFO)
        
        # Configure security logger for sensitive events
        self.security_logger = logging.getLogger('qr_attendance_security')
        self.security_logger.setLevel(logging.WARNING)
        
        # Remove existing handlers to avoid duplication
        self.logger.handlers.clear()
        self.security_logger.handlers.clear()
        
        # Setup file handlers with rotation
        self._setup_file_handlers(log_dir)
        
        # Setup console handler for development
        self._setup_console_handler()
        
        # Create database logging table
        self._create_log_table()
        
        # Register error handlers with Flask
        self._register_error_handlers()
        
        app.logger_handler = self
    
    def _setup_file_handlers(self, log_dir):
        """Setup rotating file handlers for different log types"""
        
        # Main application log (rotates when 10MB, keeps 5 files)
        app_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'application.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        app_handler.setLevel(logging.INFO)
        
        # Error log (rotates when 5MB, keeps 10 files)
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'errors.log'),
            maxBytes=5*1024*1024,   # 5MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        
        # Security log (rotates when 2MB, keeps 20 files for compliance)
        security_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'security.log'),
            maxBytes=2*1024*1024,   # 2MB
            backupCount=20
        )
        security_handler.setLevel(logging.WARNING)
        
        # Create custom formatter with JSON structure
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        app_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        security_handler.setFormatter(formatter)
        
        # Add handlers to loggers
        self.logger.addHandler(app_handler)
        self.logger.addHandler(error_handler)
        self.security_logger.addHandler(security_handler)
    
    def _setup_console_handler(self):
        """Setup console handler for development environment"""
        if self.app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            console_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            
            self.logger.addHandler(console_handler)
    
    def _create_log_table(self):
        """Create database table for storing critical log events"""
        try:
            with self.app.app_context():
                # Create log_events table if it doesn't exist
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS log_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_id VARCHAR(36) UNIQUE NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    event_category VARCHAR(30) NOT NULL,
                    user_id INT NULL,
                    username VARCHAR(80) NULL,
                    event_description TEXT NOT NULL,
                    event_data JSON NULL,
                    ip_address VARCHAR(45) NULL,
                    user_agent TEXT NULL,
                    request_path VARCHAR(500) NULL,
                    session_id VARCHAR(100) NULL,
                    severity_level VARCHAR(20) DEFAULT 'INFO',
                    created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_event_type (event_type),
                    INDEX idx_event_category (event_category),
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_timestamp (created_timestamp),
                    INDEX idx_severity_level (severity_level)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
                
                self.db.session.execute(text(create_table_sql))
                self.db.session.commit()
                
        except Exception as e:
            print(f"Warning: Could not create log_events table: {e}")
    
    def _register_error_handlers(self):
        """Register Flask error handlers for automatic logging"""
        
        @self.app.errorhandler(500)
        def handle_internal_error(error):
            """Log internal server errors automatically"""
            self.log_flask_error(
                error_type="InternalServerError",
                error_message=str(error),
                stack_trace=traceback.format_exc()
            )
            
            # Return user-friendly error page
            if self.app.debug:
                return None  # Let Flask handle debug errors
            
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Server Error</title></head>
            <body style="font-family: Arial; text-align: center; margin-top: 100px;">
                <h1>🔧 Something went wrong</h1>
                <p>We're working to fix this issue. Please try again later.</p>
                <a href="/" style="color: #2563eb;">← Back to Home</a>
            </body>
            </html>
            ''', 500
        
        @self.app.errorhandler(404)
        def handle_not_found(error):
            """Log 404 errors for security monitoring"""
            self.log_security_event(
                event_type="page_not_found",
                description=f"404 error: {request.path}",
                severity="LOW"
            )
            
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Page Not Found</title></head>
            <body style="font-family: Arial; text-align: center; margin-top: 100px;">
                <h1>🔍 Page Not Found</h1>
                <p>The page you're looking for doesn't exist.</p>
                <a href="/" style="color: #2563eb;">← Back to Home</a>
            </body>
            </html>
            ''', 404
    
    def _get_request_context(self):
        """Get current request context information"""
        if not request:
            return {}
        
        return {
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            'user_agent': request.headers.get('User-Agent', ''),
            'request_path': request.path,
            'request_method': request.method,
            'session_id': session.get('_id', 'anonymous'),
            'user_id': session.get('user_id'),
            'username': session.get('username')
        }
    
    def _log_to_database(self, event_type, event_category, description, event_data=None, severity='INFO'):
        """Log critical events to database table"""
        try:
            context = self._get_request_context()
            event_id = str(uuid.uuid4())
            
            insert_sql = """
            INSERT INTO log_events (
                event_id, event_type, event_category, user_id, username,
                event_description, event_data, ip_address, user_agent,
                request_path, session_id, severity_level
            ) VALUES (
                :event_id, :event_type, :event_category, :user_id, :username,
                :description, :event_data, :ip_address, :user_agent,
                :request_path, :session_id, :severity
            )
            """
            
            self.db.session.execute(text(insert_sql), {
                'event_id': event_id,
                'event_type': event_type,
                'event_category': event_category,
                'user_id': context.get('user_id'),
                'username': context.get('username'),
                'description': description,
                'event_data': json.dumps(event_data) if event_data else None,
                'ip_address': context.get('ip_address'),
                'user_agent': context.get('user_agent'),
                'request_path': context.get('request_path'),
                'session_id': context.get('session_id'),
                'severity': severity
            })
            
            self.db.session.commit()
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Database logging error: {e}")
            try:
                self.db.session.rollback()
            except:
                pass
    
    # USER LOGIN/LOGOUT LOGGING METHODS
    
    def log_user_login(self, user_id, username, success=True, failure_reason=None):
        """Log user login attempts with detailed session information"""
        context = self._get_request_context()
        
        event_data = {
            'user_id': user_id,
            'username': username,
            'success': success,
            'login_timestamp': datetime.now().isoformat(),
            'session_info': {
                'session_id': context.get('session_id'),
                'ip_address': context.get('ip_address'),
                'user_agent': context.get('user_agent')
            }
        }
        
        if failure_reason:
            event_data['failure_reason'] = failure_reason
        
        if success:
            message = f"User login successful: {username} (ID: {user_id})"
            self.logger.info(json.dumps({
                'event': 'user_login_success',
                'data': event_data
            }))
            
            # Log to database for security monitoring
            self._log_to_database(
                event_type='user_login_success',
                event_category='authentication',
                description=message,
                event_data=event_data,
                severity='INFO'
            )
        else:
            message = f"User login failed: {username} - {failure_reason}"
            self.security_logger.warning(json.dumps({
                'event': 'user_login_failure',
                'data': event_data
            }))
            
            # Log failed logins to database for security analysis
            self._log_to_database(
                event_type='user_login_failure',
                event_category='security',
                description=message,
                event_data=event_data,
                severity='WARNING'
            )
    
    def log_user_logout(self, user_id, username, session_duration=None):
        """Log user logout events with session duration"""
        context = self._get_request_context()
        
        event_data = {
            'user_id': user_id,
            'username': username,
            'logout_timestamp': datetime.now().isoformat(),
            'session_duration_minutes': session_duration,
            'session_info': {
                'session_id': context.get('session_id'),
                'ip_address': context.get('ip_address')
            }
        }
        
        message = f"User logout: {username} (ID: {user_id})"
        if session_duration:
            message += f" - Session duration: {session_duration} minutes"
        
        self.logger.info(json.dumps({
            'event': 'user_logout',
            'data': event_data
        }))
        
        # Log to database
        self._log_to_database(
            event_type='user_logout',
            event_category='authentication',
            description=message,
            event_data=event_data
        )
    
    # QR CODE LOGGING METHODS
    
    def log_qr_code_created(self, qr_code_id, qr_code_name, created_by_user_id, qr_data):
        """Log QR code creation events"""
        event_data = {
            'qr_code_id': qr_code_id,
            'qr_code_name': qr_code_name,
            'created_by_user_id': created_by_user_id,
            'created_timestamp': datetime.now().isoformat(),
            'qr_code_details': {
                'location': qr_data.get('location'),
                'location_address': qr_data.get('location_address'),
                'location_event': qr_data.get('location_event'),
                'has_coordinates': qr_data.get('has_coordinates', False)
            }
        }
        
        if qr_data.get('has_coordinates'):
            event_data['qr_code_details']['coordinates'] = {
                'latitude': qr_data.get('latitude'),
                'longitude': qr_data.get('longitude'),
                'accuracy': qr_data.get('coordinate_accuracy')
            }
        
        message = f"QR code created: {qr_code_name} (ID: {qr_code_id}) by user {created_by_user_id}"
        
        self.logger.info(json.dumps({
            'event': 'qr_code_created',
            'data': event_data
        }))
        
        # Log to database
        self._log_to_database(
            event_type='qr_code_created',
            event_category='qr_management',
            description=message,
            event_data=event_data
        )
    
    def log_qr_code_updated(self, qr_code_id, qr_code_name, updated_by_user_id, changes):
        """Log QR code modification events"""
        event_data = {
            'qr_code_id': qr_code_id,
            'qr_code_name': qr_code_name,
            'updated_by_user_id': updated_by_user_id,
            'updated_timestamp': datetime.now().isoformat(),
            'changes': changes
        }
        
        message = f"QR code updated: {qr_code_name} (ID: {qr_code_id}) by user {updated_by_user_id}"
        
        self.logger.info(json.dumps({
            'event': 'qr_code_updated',
            'data': event_data
        }))
        
        # Log to database
        self._log_to_database(
            event_type='qr_code_updated',
            event_category='qr_management',
            description=message,
            event_data=event_data
        )
    
    def log_qr_code_deleted(self, qr_code_id, qr_code_name, deleted_by_user_id):
        """Log QR code deletion events"""
        event_data = {
            'qr_code_id': qr_code_id,
            'qr_code_name': qr_code_name,
            'deleted_by_user_id': deleted_by_user_id,
            'deleted_timestamp': datetime.now().isoformat()
        }
        
        message = f"QR code deleted: {qr_code_name} (ID: {qr_code_id}) by user {deleted_by_user_id}"
        
        self.logger.warning(json.dumps({
            'event': 'qr_code_deleted',
            'data': event_data
        }))
        
        # Log to database with higher severity
        self._log_to_database(
            event_type='qr_code_deleted',
            event_category='qr_management',
            description=message,
            event_data=event_data,
            severity='WARNING'
        )
    
    def log_qr_code_accessed(self, qr_code_id, qr_code_name, access_method='scan'):
        """Log QR code access/scan events"""
        context = self._get_request_context()
        
        event_data = {
            'qr_code_id': qr_code_id,
            'qr_code_name': qr_code_name,
            'access_method': access_method,
            'access_timestamp': datetime.now().isoformat(),
            'access_info': {
                'ip_address': context.get('ip_address'),
                'user_agent': context.get('user_agent')
            }
        }
        
        message = f"QR code accessed: {qr_code_name} (ID: {qr_code_id}) via {access_method}"
        
        self.logger.info(json.dumps({
            'event': 'qr_code_accessed',
            'data': event_data
        }))

    def log_qr_code_generated(self, data_length, fill_color, back_color, box_size, border, error_correction):
        """Log QR code generation with customization details"""
        try:
            self.logger.info(f"QR code generated with customization - "
                    f"Data length: {data_length}, "
                    f"Fill: {fill_color}, Background: {back_color}, "
                    f"Box size: {box_size}, Border: {border}, "
                    f"Error correction: {error_correction}")
        except Exception as e:
            self.logger.error(f"Failed to log QR code generation: {e}")
    
    # DATABASE ERROR LOGGING METHODS
    
    def log_database_error(self, operation, error, query=None, parameters=None):
        """Log database operation errors"""
        event_data = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_timestamp': datetime.now().isoformat(),
            'database_info': {
                'query': query[:500] if query else None,  # Truncate long queries
                'parameters': str(parameters)[:200] if parameters else None
            }
        }
        
        if isinstance(error, SQLAlchemyError):
            event_data['sqlalchemy_error'] = True
            if hasattr(error, 'orig'):
                event_data['original_error'] = str(error.orig)
        
        message = f"Database error in {operation}: {type(error).__name__} - {str(error)}"
        
        self.logger.error(json.dumps({
            'event': 'database_error',
            'data': event_data
        }))
        
        # Log to database if possible (try/catch to avoid recursive errors)
        try:
            self._log_to_database(
                event_type='database_error',
                event_category='database',
                description=message,
                event_data=event_data,
                severity='ERROR'
            )
        except:
            # If database logging fails, just continue
            pass
    
    def log_database_connection_error(self, error):
        """Log database connection failures"""
        event_data = {
            'error_type': 'database_connection_failure',
            'error_message': str(error),
            'error_timestamp': datetime.now().isoformat()
        }
        
        message = f"Database connection error: {str(error)}"
        
        self.logger.critical(json.dumps({
            'event': 'database_connection_error',
            'data': event_data
        }))
    
    # FLASK ERROR LOGGING METHODS
    
    def log_flask_error(self, error_type, error_message, stack_trace=None, request_data=None):
        """Log Flask application errors"""
        context = self._get_request_context()
        
        event_data = {
            'error_type': error_type,
            'error_message': error_message,
            'error_timestamp': datetime.now().isoformat(),
            'request_context': context,
            'stack_trace': stack_trace[:2000] if stack_trace else None  # Truncate long traces
        }
        
        if request_data:
            event_data['request_data'] = request_data
        
        message = f"Flask error: {error_type} - {error_message}"
        
        self.logger.error(json.dumps({
            'event': 'flask_error',
            'data': event_data
        }))
        
        # Log to database
        self._log_to_database(
            event_type='flask_error',
            event_category='application',
            description=message,
            event_data=event_data,
            severity='ERROR'
        )
    
    # SECURITY EVENT LOGGING METHODS
    
    def log_security_event(self, event_type, description, severity='MEDIUM', additional_data=None):
        """Log security-related events"""
        context = self._get_request_context()
        
        event_data = {
            'security_event_type': event_type,
            'severity': severity,
            'event_timestamp': datetime.now().isoformat(),
            'request_context': context
        }
        
        if additional_data:
            event_data['additional_data'] = additional_data
        
        message = f"Security event: {event_type} - {description}"
        
        self.security_logger.warning(json.dumps({
            'event': 'security_event',
            'data': event_data
        }))
        
        # Log to database with high priority
        self._log_to_database(
            event_type='security_event',
            event_category='security',
            description=message,
            event_data=event_data,
            severity='WARNING'
        )
    
    # UTILITY METHODS
    def get_log_statistics(self, days=7):
        """Get logging statistics for the specified number of days"""
        try:
            from datetime import datetime, timedelta  # Import here as backup
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Initialize default stats
            stats = {
                'total_events': 0,
                'security_events': 0,
                'database_errors': 0,
                'user_activities': 0,
                'system_events': 0
            }
            
            # Check if table exists first
            try:
                table_check = self.db.session.execute(text("SHOW TABLES LIKE 'log_events'")).fetchone()
                if not table_check:
                    print("⚠️ log_events table does not exist")
                    return stats
            except Exception as table_error:
                print(f"⚠️ Cannot check if log_events table exists: {table_error}")
                return stats
            
            # Get total events count
            try:
                total_sql = """
                SELECT COUNT(*) as total_events
                FROM log_events 
                WHERE created_timestamp >= :cutoff_date
                """
                
                total_result = self.db.session.execute(text(total_sql), {'cutoff_date': cutoff_date}).fetchone()
                if total_result:
                    stats['total_events'] = total_result.total_events
                    print(f"✅ Found {stats['total_events']} total events in last {days} days")
            except Exception as total_error:
                print(f"⚠️ Error getting total events: {total_error}")
            
            # Get events by category
            try:
                category_sql = """
                SELECT 
                    event_category,
                    COUNT(*) as event_count
                FROM log_events 
                WHERE created_timestamp >= :cutoff_date
                GROUP BY event_category
                """
                
                category_result = self.db.session.execute(text(category_sql), {'cutoff_date': cutoff_date}).fetchall()
                
                for row in category_result:
                    category = row.event_category
                    count = row.event_count
                    print(f"✅ Found {count} events in category: {category}")
                    
                    if category == 'security':
                        stats['security_events'] = count
                    elif category == 'database':
                        stats['database_errors'] = count
                    elif category == 'user_activity':
                        stats['user_activities'] = count
                    elif category == 'system':
                        stats['system_events'] = count
                        
            except Exception as category_error:
                print(f"⚠️ Error getting category stats: {category_error}")
            
            print(f"📊 Final stats: {stats}")
            return stats
            
        except Exception as e:
            print(f"❌ Error in get_log_statistics: {e}")
            self.log_database_error('get_log_statistics', e)
            return {
                'total_events': 0,
                'security_events': 0,
                'database_errors': 0,
                'user_activities': 0,
                'system_events': 0
            }
    
    def cleanup_old_logs(self, days_to_keep=90):
        """Clean up old log entries from database"""
        try:
            from datetime import datetime, timedelta  # Import here as backup
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            print(f"🧹 Starting log cleanup: removing entries older than {cutoff_date}")
            
            # Check if table exists first
            try:
                table_check = self.db.session.execute(text("SHOW TABLES LIKE 'log_events'")).fetchone()
                if not table_check:
                    print("⚠️ log_events table does not exist")
                    return 0
            except Exception as table_error:
                print(f"⚠️ Cannot check if log_events table exists: {table_error}")
                return 0
            
            # First, count how many records will be deleted
            try:
                count_sql = """
                SELECT COUNT(*) as count_to_delete
                FROM log_events 
                WHERE created_timestamp < :cutoff_date 
                AND severity_level NOT IN ('ERROR', 'CRITICAL', 'HIGH')
                """
                
                count_result = self.db.session.execute(text(count_sql), {'cutoff_date': cutoff_date}).fetchone()
                count_to_delete = count_result.count_to_delete if count_result else 0
                
                print(f"📊 Found {count_to_delete} records to delete")
                
                if count_to_delete == 0:
                    print("✅ No old records found to cleanup")
                    return 0
                    
            except Exception as count_error:
                print(f"⚠️ Error counting records to delete: {count_error}")
                return 0
            
            # Perform the cleanup - exclude critical logs
            try:
                cleanup_sql = """
                DELETE FROM log_events 
                WHERE created_timestamp < :cutoff_date 
                AND severity_level NOT IN ('ERROR', 'CRITICAL', 'HIGH')
                """
                
                result = self.db.session.execute(text(cleanup_sql), {'cutoff_date': cutoff_date})
                deleted_count = result.rowcount
                self.db.session.commit()
                
                print(f"🗑️ Successfully deleted {deleted_count} old log entries")
                
                # Log the cleanup operation
                self.logger.info(f"Log cleanup completed: {deleted_count} entries removed (keeping entries newer than {days_to_keep} days)")
                
                return deleted_count
                
            except Exception as delete_error:
                print(f"❌ Error during deletion: {delete_error}")
                self.db.session.rollback()
                return 0
            
        except Exception as e:
            print(f"❌ Error in cleanup_old_logs: {e}")
            self.db.session.rollback()
            self.log_database_error('cleanup_old_logs', e)
            return 0

def get_recent_logs(self, days=7, limit=100, category_filter=None, severity_filter=None, search_term=None):
    """Enhanced method to get recent logs with filtering options"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Build the base query
        base_sql = """
        SELECT 
            event_id,
            event_type, 
            event_category, 
            event_description, 
            severity_level, 
            created_timestamp, 
            username, 
            ip_address,
            user_id
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """
        
        # Add filters
        params = {'cutoff_date': cutoff_date}
        
        if category_filter:
            base_sql += " AND event_category = :category_filter"
            params['category_filter'] = category_filter
        
        if severity_filter:
            base_sql += " AND severity_level = :severity_filter" 
            params['severity_filter'] = severity_filter
        
        if search_term:
            base_sql += " AND (event_description LIKE :search_term OR event_type LIKE :search_term OR username LIKE :search_term)"
            params['search_term'] = f"%{search_term}%"
        
        # Add ordering and limit
        base_sql += " ORDER BY created_timestamp DESC LIMIT :limit"
        params['limit'] = limit
        
        result = self.db.session.execute(text(base_sql), params).fetchall()
        
        logs = []
        for row in result:
            logs.append({
                'event_id': row.event_id,
                'event_type': row.event_type,
                'event_category': row.event_category,
                'description': row.event_description,
                'severity': row.severity_level,
                'timestamp': row.created_timestamp.isoformat(),
                'username': row.username or 'System',
                'ip_address': row.ip_address or '-',
                'user_id': row.user_id
            })
        
        return logs
        
    except Exception as e:
        self.log_database_error('get_recent_logs', e)
        print(f"Error in get_recent_logs: {e}")
        return []
    
# DECORATOR FUNCTIONS FOR AUTOMATIC LOGGING

def log_user_activity(activity_type):
    """Decorator to automatically log user activities"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Log successful activity
                if hasattr(g, 'app') and hasattr(g.app, 'logger_handler'):
                    logger = g.app.logger_handler
                    logger.logger.info(json.dumps({
                        'event': f'user_activity_{activity_type}',
                        'data': {
                            'user_id': session.get('user_id'),
                            'username': session.get('username'),
                            'activity': activity_type,
                            'timestamp': datetime.now().isoformat()
                        }
                    }))
                
                return result
                
            except Exception as e:
                # Log error
                if hasattr(g, 'app') and hasattr(g.app, 'logger_handler'):
                    logger = g.app.logger_handler
                    logger.log_flask_error(
                        error_type=f"activity_error_{activity_type}",
                        error_message=str(e),
                        stack_trace=traceback.format_exc()
                    )
                raise
        
        return decorated_function
    return decorator

def log_database_operations(operation_name):
    """Decorator to automatically log database operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                return result
                
            except Exception as e:
                # Log database error
                if hasattr(g, 'app') and hasattr(g.app, 'logger_handler'):
                    logger = g.app.logger_handler
                    logger.log_database_error(
                        operation=operation_name,
                        error=e
                    )
                raise
        
        return decorated_function
    return decorator

def verify_log_table_exists(self):
    """Verify that the log_events table exists and has the correct structure"""
    try:
        # Check if table exists
        check_table_sql = """
        SELECT COUNT(*) as table_exists 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'log_events'
        """
        
        result = self.db.session.execute(text(check_table_sql)).fetchone()
        
        if result.table_exists == 0:
            print("⚠️ log_events table does not exist. Creating it now...")
            self._create_log_table()
            return True
        
        # Check if table has records
        count_sql = "SELECT COUNT(*) as record_count FROM log_events"
        count_result = self.db.session.execute(text(count_sql)).fetchone()
        
        print(f"✅ log_events table exists with {count_result.record_count} records")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying log table: {e}")
        return False
    
# INITIALIZATION FUNCTION
def init_logging(app, db):
    """Initialize the logging system with the Flask app"""
    logger_handler = AppLogger(app, db)
    return logger_handler