#!/usr/bin/env python3
"""
Simple Health Check - Windows Compatible
=======================================
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def health_check():
    """Run database health check"""
    try:
        from app import app, db, logger_handler
        
        print("Database Health Check - Windows Compatible")
        print("=" * 50)
        
        with app.app_context():
            health_status = {
                'overall': 'healthy',
                'issues': [],
                'warnings': [],
                'recommendations': []
            }
            
            # Check database connectivity
            try:
                result = db.session.execute(text("SELECT 1 as test")).fetchone()
                if result and result.test == 1:
                    print("[OK] Database connectivity: WORKING")
                else:
                    print("[ERROR] Database connectivity: FAILED - Unexpected result")
                    health_status['issues'].append("Database connectivity test failed")
            except Exception as e:
                print(f"[ERROR] Database connectivity: FAILED - {e}")
                health_status['overall'] = 'critical'
                health_status['issues'].append(f"Database connectivity failed: {e}")
            
            # Check critical tables exist
            critical_tables = ['attendance_data', 'qr_codes', 'users', 'projects', 'log_events']
            existing_tables = []
            
            print("\nTable Status:")
            for table in critical_tables:
                try:
                    # Use SHOW TABLES for better MySQL compatibility
                    table_check = db.session.execute(text(f"SHOW TABLES LIKE '{table}'")).fetchone()
                    if table_check:
                        # Get row count
                        count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        row_count = count_result[0] if count_result else 0
                        print(f"[OK] {table}: EXISTS ({row_count:,} rows)")
                        existing_tables.append(table)
                    else:
                        print(f"[MISSING] {table}: NOT FOUND")
                        health_status['issues'].append(f"Critical table {table} is missing")
                except Exception as e:
                    print(f"[ERROR] {table}: ERROR - {e}")
                    health_status['issues'].append(f"Could not check table {table}: {e}")
            
            # Check maintenance tables
            maintenance_tables = ['attendance_audit', 'attendance_statistics_cache']
            print("\nMaintenance Tables:")
            for table in maintenance_tables:
                try:
                    table_check = db.session.execute(text(f"SHOW TABLES LIKE '{table}'")).fetchone()
                    if table_check:
                        count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                        row_count = count_result[0] if count_result else 0
                        print(f"[OK] {table}: EXISTS ({row_count:,} rows)")
                    else:
                        print(f"[MISSING] {table}: NOT FOUND")
                        health_status['warnings'].append(f"Maintenance table {table} is missing")
                except Exception as e:
                    print(f"[ERROR] {table}: ERROR - {e}")
            
            # Check for indexes on existing tables
            print("\nIndex Analysis:")
            missing_indexes = 0
            for table in existing_tables:
                try:
                    # Check if table has performance indexes
                    index_check = db.session.execute(text(f"""
                        SELECT COUNT(*) as index_count 
                        FROM INFORMATION_SCHEMA.STATISTICS 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table}' 
                        AND INDEX_NAME != 'PRIMARY'
                    """)).fetchone()
                    
                    index_count = index_check.index_count if index_check else 0
                    if index_count == 0:
                        print(f"[WARNING] {table}: No performance indexes")
                        missing_indexes += 1
                    else:
                        print(f"[OK] {table}: {index_count} indexes")
                        
                except Exception as e:
                    print(f"[ERROR] {table} indexes: {e}")
            
            if missing_indexes > 0:
                health_status['warnings'].append(f"{missing_indexes} tables have no performance indexes")
                health_status['recommendations'].append("Add performance indexes")
            
            # Check triggers
            print("\nTrigger Status:")
            try:
                trigger_count_query = """
                    SELECT COUNT(*) as trigger_count
                    FROM INFORMATION_SCHEMA.TRIGGERS 
                    WHERE TRIGGER_SCHEMA = DATABASE()
                """
                
                trigger_result = db.session.execute(text(trigger_count_query)).fetchone()
                trigger_count = trigger_result.trigger_count if trigger_result else 0
                
                if trigger_count > 0:
                    print(f"[OK] Database triggers: {trigger_count} found")
                else:
                    print("[WARNING] Database triggers: None found")
                    health_status['warnings'].append("No database triggers found")
                    health_status['recommendations'].append("Consider adding audit triggers")
                    
            except Exception as e:
                print(f"[ERROR] Trigger check failed: {e}")
                health_status['warnings'].append("Trigger check failed")
            
            # Determine overall health
            if len(health_status['issues']) > 0:
                health_status['overall'] = 'critical'
            elif len(health_status['warnings']) > 3:
                health_status['overall'] = 'warning'
            
            # Print summary
            print(f"\n{'='*50}")
            print(f"OVERALL HEALTH: {health_status['overall'].upper()}")
            print(f"{'='*50}")
            
            # Report issues
            if health_status['issues']:
                print("\nCRITICAL ISSUES:")
                for i, issue in enumerate(health_status['issues'], 1):
                    print(f"{i}. {issue}")
            
            if health_status['warnings']:
                print("\nWARNINGS:")
                for i, warning in enumerate(health_status['warnings'], 1):
                    print(f"{i}. {warning}")
            
            if health_status['recommendations']:
                print("\nRECOMMENDATIONS:")
                for i, rec in enumerate(health_status['recommendations'], 1):
                    print(f"{i}. {rec}")
            
            # Provide actionable next steps
            print("\nNEXT STEPS:")
            if health_status['overall'] == 'critical':
                print("1. Address critical issues above")
                print("2. Verify database connection and table creation")
                print("3. Check Flask app initialization")
            elif health_status['overall'] == 'warning':
                print("1. Add performance indexes: python db_maintenance.py add-indexes")
                print("2. Set up audit triggers for data tracking")
                print("3. Run regular maintenance")
            else:
                print("1. System is healthy!")
                print("2. Run regular maintenance: python db_maintenance.py cleanup")
                print("3. Monitor performance metrics")
                
            return health_status
            
    except ImportError as e:
        print(f"[ERROR] Could not import Flask app: {e}")
        print("Make sure you're running this from your Flask app directory")
        return {'overall': 'critical', 'issues': [f"Import error: {e}"]}
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return {'overall': 'critical', 'issues': [f"Health check error: {e}"]}

if __name__ == "__main__":
    health_check()
