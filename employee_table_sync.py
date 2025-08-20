#!/usr/bin/env python3
"""
Employee Data Synchronization Script
===================================

This script synchronizes the employee table with a remote MySQL server.
It replicates data from the remote server to the local application database.

Features:
- Complete data synchronization from remote to local
- Comprehensive logging for all operations
- Error handling and rollback mechanisms
- Configurable connection parameters
- Maintains data integrity during sync operations
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError
import logging

# Load environment variables
load_dotenv()

class EmployeeSyncLogger:
    """Enhanced logging for employee synchronization operations"""
    
    def __init__(self, log_file: str = 'logs/employee_sync.log'):
        """Initialize logger with file and console output"""
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger('employee_sync')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _serialize_data(self, obj):
        """Convert objects to JSON serializable format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_data(item) for item in obj]
        else:
            return obj
    
    def info(self, message: str, data: Dict = None):
        """Log info message with optional data"""
        log_entry = {'message': message}
        if data:
            log_entry['data'] = self._serialize_data(data)
        self.logger.info(json.dumps(log_entry))
    
    def error(self, message: str, error: Exception = None, data: Dict = None):
        """Log error message with optional exception and data"""
        log_entry = {
            'message': message,
            'error_type': type(error).__name__ if error else None,
            'error_message': str(error) if error else None
        }
        if data:
            log_entry['data'] = self._serialize_data(data)
        self.logger.error(json.dumps(log_entry))
    
    def warning(self, message: str, data: Dict = None):
        """Log warning message with optional data"""
        log_entry = {'message': message}
        if data:
            log_entry['data'] = self._serialize_data(data)
        self.logger.warning(json.dumps(log_entry))

class EmployeeSynchronizer:
    """
    Employee data synchronization service for replicating remote employee data
    """
    
    def __init__(self, remote_config: Dict, local_config: Dict):
        """
        Initialize synchronizer with database configurations
        
        Args:
            remote_config: Remote MySQL database configuration
            local_config: Local MySQL database configuration
        """
        self.remote_config = remote_config
        self.local_config = local_config
        self.logger = EmployeeSyncLogger()
        self.remote_engine = None
        self.local_engine = None
        
        self.sync_stats = {
            'start_time': None,
            'end_time': None,
            'total_remote_records': 0,
            'total_local_records_before': 0,
            'total_local_records_after': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'records_deleted': 0,
            'errors_encountered': 0
        }
    
    def _create_connection_string(self, config: Dict) -> str:
        """Create MySQL connection string from configuration with proper URL encoding"""
        from urllib.parse import quote_plus
        
        # URL encode username and password to handle special characters
        username = quote_plus(config['username'])
        password = quote_plus(config['password'])
        host = config['host']
        port = config.get('port', 3306)
        database = config['database']
        
        return (
            f"mysql+pymysql://"
            f"{username}:{password}@"
            f"{host}:{port}/"
            f"{database}?charset=utf8mb4"
        )
    
    def connect_databases(self) -> bool:
        """
        Establish connections to both remote and local databases
        
        Returns:
            bool: True if both connections successful, False otherwise
        """
        try:
            # Connect to remote database
            remote_connection_string = self._create_connection_string(self.remote_config)
            self.remote_engine = create_engine(
                remote_connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Test remote connection
            with self.remote_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self.logger.info("Successfully connected to remote database", {
                'host': self.remote_config['host'],
                'database': self.remote_config['database']
            })
            
            # Connect to local database
            local_connection_string = self._create_connection_string(self.local_config)
            self.local_engine = create_engine(
                local_connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Test local connection
            with self.local_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self.logger.info("Successfully connected to local database", {
                'host': self.local_config['host'],
                'database': self.local_config['database']
            })
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to establish database connections", e)
            return False
    
    def fetch_remote_employees(self) -> List[Dict]:
        """
        Fetch all employee records from remote database
        
        Returns:
            List[Dict]: List of employee records
        """
        try:
            with self.remote_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT `index`, id, firstName, lastName, title, contractId
                    FROM employee
                    ORDER BY `index`
                """))
                
                employees = []
                for row in result:
                    employee = {
                        'index': row.index,
                        'id': row.id,
                        'firstName': row.firstName,
                        'lastName': row.lastName,
                        'title': row.title,
                        'contractId': row.contractId
                    }
                    employees.append(employee)
                
                self.sync_stats['total_remote_records'] = len(employees)
                self.logger.info(f"Fetched {len(employees)} employees from remote database")
                
                return employees
                
        except Exception as e:
            self.logger.error("Failed to fetch remote employee data", e)
            self.sync_stats['errors_encountered'] += 1
            return []
    
    def get_local_employee_count(self) -> int:
        """Get current count of local employee records"""
        try:
            with self.local_engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as count FROM employee"))
                count = result.fetchone().count
                return count
        except Exception as e:
            self.logger.error("Failed to get local employee count", e)
            return 0
    
    def create_employee_table_if_not_exists(self) -> bool:
        """
        Create employee table in local database if it doesn't exist
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.local_engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'employee'
                """))
                
                table_exists = result.fetchone().count > 0
                
                if not table_exists:
                    # Create table with same structure as provided SQL
                    conn.execute(text("""
                        CREATE TABLE `employee` (
                            `index` bigint NOT NULL AUTO_INCREMENT,
                            `id` bigint NOT NULL,
                            `firstName` varchar(50) NOT NULL,
                            `lastName` varchar(50) NOT NULL,
                            `title` varchar(20) DEFAULT NULL,
                            `contractId` bigint NOT NULL DEFAULT '1',
                            UNIQUE KEY `index_2` (`index`),
                            KEY `index` (`index`)
                        ) ENGINE=MyISAM DEFAULT CHARSET=latin1
                    """))
                    conn.commit()
                    
                    self.logger.info("Created employee table in local database")
                else:
                    self.logger.info("Employee table already exists in local database")
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to create employee table", e)
            return False
    
    def synchronize_employees(self, employees: List[Dict]) -> bool:
        """
        Synchronize employee data to local database
        
        Args:
            employees: List of employee records from remote database
            
        Returns:
            bool: True if synchronization successful, False otherwise
        """
        if not employees:
            self.logger.warning("No employee data to synchronize")
            return True
        
        try:
            with self.local_engine.begin() as conn:  # Use transaction
                # Get current local employee count
                self.sync_stats['total_local_records_before'] = self.get_local_employee_count()
                
                # Clear existing data (full replacement sync)
                delete_result = conn.execute(text("DELETE FROM employee"))
                deleted_count = delete_result.rowcount
                self.sync_stats['records_deleted'] = deleted_count
                
                self.logger.info(f"Cleared {deleted_count} existing employee records")
                
                # Insert new data
                insert_count = 0
                for employee in employees:
                    try:
                        conn.execute(text("""
                            INSERT INTO employee (`index`, id, firstName, lastName, title, contractId)
                            VALUES (:index, :id, :firstName, :lastName, :title, :contractId)
                        """), {
                            'index': employee['index'],
                            'id': employee['id'],
                            'firstName': employee['firstName'],
                            'lastName': employee['lastName'],
                            'title': employee['title'],
                            'contractId': employee['contractId']
                        })
                        insert_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to insert employee {employee['id']}", e, employee)
                        self.sync_stats['errors_encountered'] += 1
                        continue
                
                self.sync_stats['records_inserted'] = insert_count
                
                # Get final count
                result = conn.execute(text("SELECT COUNT(*) as count FROM employee"))
                self.sync_stats['total_local_records_after'] = result.fetchone().count
                
                self.logger.info(f"Successfully synchronized {insert_count} employee records")
                
                return True
                
        except Exception as e:
            self.logger.error("Failed to synchronize employee data", e)
            self.sync_stats['errors_encountered'] += 1
            return False
    
    def run_synchronization(self) -> Dict:
        """
        Execute complete employee synchronization process
        
        Returns:
            Dict: Synchronization statistics and results
        """
        self.sync_stats['start_time'] = datetime.now()
        
        self.logger.info("Starting employee synchronization process")
        
        try:
            # Step 1: Connect to databases
            if not self.connect_databases():
                self.sync_stats['end_time'] = datetime.now()
                return self.sync_stats
            
            # Step 2: Create table if needed
            if not self.create_employee_table_if_not_exists():
                self.sync_stats['end_time'] = datetime.now()
                return self.sync_stats
            
            # Step 3: Fetch remote data
            employees = self.fetch_remote_employees()
            if not employees and self.sync_stats['errors_encountered'] > 0:
                self.sync_stats['end_time'] = datetime.now()
                return self.sync_stats
            
            # Step 4: Synchronize data
            success = self.synchronize_employees(employees)
            
            # Step 5: Log final results
            self.sync_stats['end_time'] = datetime.now()
            duration = (self.sync_stats['end_time'] - self.sync_stats['start_time']).total_seconds()
            
            if success:
                self.logger.info("Employee synchronization completed successfully", {
                    'duration_seconds': duration,
                    'statistics': self.sync_stats
                })
            else:
                self.logger.error("Employee synchronization completed with errors", None, {
                    'duration_seconds': duration,
                    'statistics': self.sync_stats
                })
            
            return self.sync_stats
            
        except Exception as e:
            self.sync_stats['end_time'] = datetime.now()
            self.logger.error("Employee synchronization failed", e)
            self.sync_stats['errors_encountered'] += 1
            return self.sync_stats
        
        finally:
            # Close connections
            if self.remote_engine:
                self.remote_engine.dispose()
            if self.local_engine:
                self.local_engine.dispose()

def load_configuration() -> Tuple[Dict, Dict]:
    """
    Load database configurations from environment variables
    
    Returns:
        Tuple[Dict, Dict]: Remote and local database configurations
    """
    # Remote database configuration
    remote_config = {
        'host': os.getenv('REMOTE_DB_HOST', 'localhost'),
        'port': int(os.getenv('REMOTE_DB_PORT', 3306)),
        'username': os.getenv('REMOTE_DB_USERNAME', 'root'),
        'password': os.getenv('REMOTE_DB_PASSWORD', ''),
        'database': os.getenv('REMOTE_DB_NAME', 'remote_database')
    }
    
    # Local database configuration (from existing DATABASE_URL)
    database_url = os.getenv('DATABASE_URL', '')
    if database_url.startswith('mysql+pymysql://'):
        # Parse existing DATABASE_URL with proper URL decoding
        from urllib.parse import unquote_plus
        import re
        
        # Handle URL-encoded credentials
        match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
        if match:
            local_config = {
                'host': match.group(3),
                'port': int(match.group(4)),
                'username': unquote_plus(match.group(1)),
                'password': unquote_plus(match.group(2)),
                'database': match.group(5).split('?')[0]  # Remove parameters
            }
        else:
            raise ValueError("Invalid DATABASE_URL format")
    else:
        # Fallback configuration
        local_config = {
            'host': os.getenv('LOCAL_DB_HOST', 'localhost'),
            'port': int(os.getenv('LOCAL_DB_PORT', 3306)),
            'username': os.getenv('LOCAL_DB_USERNAME', 'root'),
            'password': os.getenv('LOCAL_DB_PASSWORD', ''),
            'database': os.getenv('LOCAL_DB_NAME', 'local_database')
        }
    
    return remote_config, local_config

def main():
    """Main execution function"""
    print("🔄 Employee Synchronization Script")
    print("=" * 50)
    
    try:
        # Load configurations
        remote_config, local_config = load_configuration()
        
        print(f"📡 Remote Server: {remote_config['host']}:{remote_config['port']}")
        print(f"💾 Local Server: {local_config['host']}:{local_config['port']}")
        print()
        
        # Initialize synchronizer
        synchronizer = EmployeeSynchronizer(remote_config, local_config)
        
        # Run synchronization
        stats = synchronizer.run_synchronization()
        
        # Display results
        print("\n📊 Synchronization Results:")
        print("=" * 30)
        print(f"⏱️  Duration: {(stats['end_time'] - stats['start_time']).total_seconds():.2f} seconds")
        print(f"📡 Remote Records: {stats['total_remote_records']}")
        print(f"💾 Local Records (Before): {stats['total_local_records_before']}")
        print(f"💾 Local Records (After): {stats['total_local_records_after']}")
        print(f"➕ Records Inserted: {stats['records_inserted']}")
        print(f"🗑️  Records Deleted: {stats['records_deleted']}")
        print(f"❌ Errors: {stats['errors_encountered']}")
        
        if stats['errors_encountered'] == 0:
            print("\n✅ Synchronization completed successfully!")
            return 0
        else:
            print(f"\n⚠️  Synchronization completed with {stats['errors_encountered']} errors")
            return 1
            
    except Exception as e:
        print(f"\n❌ Synchronization failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())