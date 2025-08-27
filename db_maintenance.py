# db_maintenance.py
"""
Fixed Simple Maintenance Script
==============================

Fixes SQL parameter binding issues and datetime deprecation warnings.
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def cleanup_data(dry_run=False):
    """Clean up old data from maintenance tables - FIXED VERSION"""
    try:
        from app import app, db
        
        print("Data Cleanup - Fixed Version")
        print("=" * 35)
        
        with app.app_context():
            # Define cleanup operations
            # (table_name, date_column, retention_days, description)
            tables_to_clean = [
                ('attendance_audit', 'change_timestamp', 90, 'Audit trail records'),
                ('attendance_statistics_cache', 'expires_at', 1, 'Expired cache entries'),
                ('log_events', 'created_timestamp', 180, 'Old system logs')
            ]
            
            total_records_to_clean = 0
            total_records_cleaned = 0
            
            print(f"Retention policy:")
            for table, col, days, desc in tables_to_clean:
                print(f"  - {desc}: {days} days")
            
            print("\nAnalyzing tables...\n")
            
            for table_name, date_column, retention_days, description in tables_to_clean:
                try:
                    # Check if table exists
                    table_check = db.session.execute(text(f"SHOW TABLES LIKE '{table_name}'")).fetchone()
                    
                    if not table_check:
                        print(f"[SKIP] {table_name}: Table doesn't exist")
                        continue
                    
                    # Calculate cutoff date (using timezone-aware datetime)
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
                    cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Count total records in table
                    total_count_query = f"SELECT COUNT(*) as total FROM {table_name}"
                    total_result = db.session.execute(text(total_count_query)).fetchone()
                    total_records = total_result.total if total_result else 0
                    
                    # Count records to clean - Fixed SQL syntax
                    count_query = f"""
                        SELECT COUNT(*) as count 
                        FROM {table_name} 
                        WHERE {date_column} < :cutoff_date
                    """
                    count_result = db.session.execute(
                        text(count_query), 
                        {'cutoff_date': cutoff_str}
                    ).fetchone()
                    
                    records_to_clean = count_result.count if count_result else 0
                    records_to_keep = total_records - records_to_clean
                    
                    if records_to_clean > 0:
                        print(f"[{table_name}]")
                        print(f"  Total records: {total_records:,}")
                        print(f"  Records to clean: {records_to_clean:,}")
                        print(f"  Records to keep: {records_to_keep:,}")
                        print(f"  Cutoff date: {cutoff_str}")
                        
                        if dry_run:
                            print(f"  [DRY RUN] Would delete {records_to_clean:,} records")
                        else:
                            # Perform cleanup - Fixed SQL syntax
                            delete_query = f"""
                                DELETE FROM {table_name} 
                                WHERE {date_column} < :cutoff_date
                            """
                            result = db.session.execute(
                                text(delete_query), 
                                {'cutoff_date': cutoff_str}
                            )
                            actual_deleted = result.rowcount
                            print(f"  [CLEANED] Deleted {actual_deleted:,} records")
                            total_records_cleaned += actual_deleted
                        
                        total_records_to_clean += records_to_clean
                        print()  # Empty line for readability
                        
                    else:
                        print(f"[{table_name}]")
                        print(f"  Total records: {total_records:,}")
                        print(f"  No old records to clean (all newer than {retention_days} days)")
                        print()
                        
                except Exception as e:
                    print(f"[ERROR] Error processing {table_name}: {e}")
                    print(f"  Error type: {type(e).__name__}")
                    print()
            
            # Summary
            print("=" * 35)
            if dry_run:
                if total_records_to_clean > 0:
                    print(f"[DRY RUN SUMMARY]")
                    print(f"Would clean {total_records_to_clean:,} total records")
                    print(f"No changes made to database")
                else:
                    print(f"[DRY RUN SUMMARY]")
                    print(f"No records need cleaning")
            else:
                if total_records_cleaned > 0:
                    # Commit changes
                    db.session.commit()
                    print(f"[CLEANUP COMPLETED]")
                    print(f"Successfully cleaned {total_records_cleaned:,} total records")
                else:
                    print(f"[NO CLEANUP NEEDED]")
                    print(f"All records are within retention policy")
                    
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
        print(f"Error type: {type(e).__name__}")
        try:
            db.session.rollback()
            print("Database changes rolled back")
        except:
            pass

def add_performance_indexes():
    """Add basic performance indexes - FIXED VERSION"""
    try:
        from app import app, db
        
        print("Adding Performance Indexes - Fixed Version")
        print("=" * 45)
        
        with app.app_context():
            # Define critical indexes with better error handling
            indexes_to_create = [
                {
                    'name': 'idx_attendance_date_employee',
                    'table': 'attendance_data',
                    'columns': 'check_in_date DESC, employee_id',
                    'purpose': 'Optimize attendance queries by date and employee'
                },
                {
                    'name': 'idx_attendance_qr_date',
                    'table': 'attendance_data', 
                    'columns': 'qr_code_id, check_in_date DESC',
                    'purpose': 'Optimize queries by QR code and date'
                },
                {
                    'name': 'idx_attendance_location_date',
                    'table': 'attendance_data',
                    'columns': 'location_name, check_in_date DESC',
                    'purpose': 'Optimize queries by location'
                },
                {
                    'name': 'idx_qrcode_project_active',
                    'table': 'qr_codes',
                    'columns': 'project_id, active_status',
                    'purpose': 'Optimize project-based QR code queries'
                },
                {
                    'name': 'idx_users_username_active',
                    'table': 'users',
                    'columns': 'username, active_status',
                    'purpose': 'Optimize user authentication'
                },
                {
                    'name': 'idx_log_events_timestamp_category',
                    'table': 'log_events',
                    'columns': 'created_timestamp DESC, event_category',
                    'purpose': 'Optimize log queries and filtering'
                }
            ]
            
            indexes_created = 0
            indexes_skipped = 0
            indexes_failed = 0
            
            for index_def in indexes_to_create:
                print(f"\nProcessing {index_def['name']}...")
                
                try:
                    # Check if table exists first
                    table_check = db.session.execute(
                        text(f"SHOW TABLES LIKE :table_name"), 
                        {'table_name': index_def['table']}
                    ).fetchone()
                    
                    if not table_check:
                        print(f"  [SKIP] Table {index_def['table']} doesn't exist")
                        indexes_skipped += 1
                        continue
                    
                    # Check if index already exists
                    index_check = db.session.execute(text("""
                        SELECT COUNT(*) as count
                        FROM INFORMATION_SCHEMA.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = :table_name
                        AND INDEX_NAME = :index_name
                    """), {
                        'table_name': index_def['table'],
                        'index_name': index_def['name']
                    }).fetchone()
                    
                    if index_check and index_check.count > 0:
                        print(f"  [EXISTS] Index already exists")
                        indexes_skipped += 1
                        continue
                    
                    # Create the index
                    create_sql = f"""
                        CREATE INDEX {index_def['name']} 
                        ON {index_def['table']} ({index_def['columns']})
                    """
                    
                    db.session.execute(text(create_sql))
                    
                    print(f"  [CREATED] Successfully created index")
                    print(f"  Purpose: {index_def['purpose']}")
                    indexes_created += 1
                        
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate' in error_msg or 'already exists' in error_msg:
                        print(f"  [EXISTS] Index already exists (detected in error)")
                        indexes_skipped += 1
                    else:
                        print(f"  [ERROR] Failed to create index: {e}")
                        indexes_failed += 1
            
            # Commit changes if any indexes were created
            if indexes_created > 0:
                db.session.commit()
            
            # Summary
            print(f"\n{'=' * 45}")
            print(f"INDEX CREATION SUMMARY")
            print(f"{'=' * 45}")
            print(f"Created: {indexes_created}")
            print(f"Skipped (already exist): {indexes_skipped}")
            print(f"Failed: {indexes_failed}")
            print(f"Total processed: {len(indexes_to_create)}")
            
            if indexes_created > 0:
                print(f"\n[SUCCESS] Created {indexes_created} new performance indexes")
                print("These indexes will improve query performance for:")
                print("- Attendance filtering by date/employee/location")
                print("- User authentication")
                print("- QR code project queries")
                print("- Log event filtering")
            elif indexes_skipped == len(indexes_to_create):
                print(f"\n[INFO] All indexes already exist - no action needed")
            else:
                print(f"\n[WARNING] Some indexes could not be created")
                
    except Exception as e:
        print(f"[ERROR] Index creation failed: {e}")
        try:
            db.session.rollback()
        except:
            pass

def show_table_info():
    """Show detailed information about database tables"""
    try:
        from app import app, db
        
        print("Database Table Information - Detailed")
        print("=" * 45)
        
        with app.app_context():
            # Get all tables
            tables_result = db.session.execute(text("SHOW TABLES")).fetchall()
            table_names = [row[0] for row in tables_result]
            
            print(f"Database: {db.engine.url.database}")
            print(f"Total tables: {len(table_names)}\n")
            
            # Header for table info
            print(f"{'Table Name':<25} {'Rows':<10} {'Size (MB)':<10} {'Indexes':<8} {'Type'}")
            print("-" * 70)
            
            total_size = 0
            total_rows = 0
            
            for table in sorted(table_names):
                try:
                    # Get row count
                    count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    row_count = count_result[0] if count_result else 0
                    
                    # Get table size and type
                    info_query = f"""
                        SELECT 
                            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as size_mb,
                            ENGINE as engine_type
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}'
                    """
                    info_result = db.session.execute(text(info_query)).fetchone()
                    size_mb = info_result.size_mb if info_result and info_result.size_mb else 0
                    engine_type = info_result.engine_type if info_result else 'Unknown'
                    
                    # Get index count
                    index_query = f"""
                        SELECT COUNT(*) as index_count
                        FROM INFORMATION_SCHEMA.STATISTICS 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table}' 
                        AND INDEX_NAME != 'PRIMARY'
                    """
                    index_result = db.session.execute(text(index_query)).fetchone()
                    index_count = index_result.index_count if index_result else 0
                    
                    # Determine table category
                    table_type = "System"
                    if table in ['attendance_data', 'qr_codes', 'users', 'projects']:
                        table_type = "Core"
                    elif table in ['attendance_audit', 'attendance_statistics_cache', 'log_events']:
                        table_type = "Maintenance" 
                    elif table in ['customers', 'tenant_configs']:
                        table_type = "Config"
                    
                    print(f"{table:<25} {row_count:<10,} {size_mb:<10.1f} {index_count:<8} {table_type}")
                    
                    total_size += size_mb
                    total_rows += row_count
                    
                except Exception as e:
                    print(f"{table:<25} {'ERROR':<10} {'N/A':<10} {'N/A':<8} - {str(e)[:20]}")
            
            # Summary
            print("-" * 70)
            print(f"{'TOTALS':<25} {total_rows:<10,} {total_size:<10.1f}")
            
            # Additional insights
            print(f"\nTable Categories:")
            core_tables = [t for t in table_names if t in ['attendance_data', 'qr_codes', 'users', 'projects']]
            maintenance_tables = [t for t in table_names if t in ['attendance_audit', 'attendance_statistics_cache', 'log_events']]
            
            print(f"  Core tables: {len(core_tables)} ({', '.join(core_tables)})")
            print(f"  Maintenance tables: {len(maintenance_tables)} ({', '.join(maintenance_tables)})")
            print(f"  Other tables: {len(table_names) - len(core_tables) - len(maintenance_tables)}")
            
    except Exception as e:
        print(f"[ERROR] Failed to get table info: {e}")

def analyze_performance():
    """Analyze database performance and suggest optimizations"""
    try:
        from app import app, db
        
        print("Database Performance Analysis")
        print("=" * 35)
        
        with app.app_context():
            # Check for tables without indexes
            tables_to_check = ['attendance_data', 'qr_codes', 'users', 'log_events']
            
            print("Index Coverage Analysis:")
            print("-" * 25)
            
            tables_needing_indexes = []
            
            for table in tables_to_check:
                try:
                    # Check if table exists
                    table_check = db.session.execute(
                        text(f"SHOW TABLES LIKE :table_name"), 
                        {'table_name': table}
                    ).fetchone()
                    
                    if not table_check:
                        continue
                    
                    # Count non-primary indexes
                    index_query = f"""
                        SELECT COUNT(*) as index_count
                        FROM INFORMATION_SCHEMA.STATISTICS 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table}' 
                        AND INDEX_NAME != 'PRIMARY'
                    """
                    index_result = db.session.execute(text(index_query)).fetchone()
                    index_count = index_result.index_count if index_result else 0
                    
                    # Get table size for impact assessment
                    size_query = f"""
                        SELECT 
                            TABLE_ROWS,
                            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as size_mb
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}'
                    """
                    size_result = db.session.execute(text(size_query)).fetchone()
                    row_count = size_result.TABLE_ROWS if size_result else 0
                    size_mb = size_result.size_mb if size_result and size_result.size_mb else 0
                    
                    status = "GOOD" if index_count > 0 else "NEEDS INDEXES"
                    priority = "HIGH" if row_count > 1000 and index_count == 0 else "MEDIUM"
                    
                    print(f"{table:<20} {index_count:<3} indexes  {row_count:<8,} rows  {status}")
                    
                    if index_count == 0 and row_count > 100:
                        tables_needing_indexes.append({
                            'table': table,
                            'rows': row_count,
                            'size_mb': size_mb,
                            'priority': priority
                        })
                        
                except Exception as e:
                    print(f"{table:<20} ERROR - {e}")
            
            # Recommendations
            if tables_needing_indexes:
                print(f"\nPerformance Recommendations:")
                print("-" * 28)
                
                for table_info in sorted(tables_needing_indexes, key=lambda x: x['rows'], reverse=True):
                    print(f"• {table_info['table']}: Add performance indexes")
                    print(f"  Rows: {table_info['rows']:,}, Priority: {table_info['priority']}")
                
                print(f"\nTo add indexes: python db_maintenance.py add-indexes")
            else:
                print(f"\n[GOOD] All major tables have performance indexes")
            
            # Check for large tables that might need optimization
            print(f"\nLarge Table Analysis:")
            print("-" * 22)
            
            large_tables_query = """
                SELECT 
                    TABLE_NAME,
                    TABLE_ROWS,
                    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) as size_mb
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_ROWS > 1000
                ORDER BY TABLE_ROWS DESC
            """
            
            large_tables = db.session.execute(text(large_tables_query)).fetchall()
            
            if large_tables:
                for table in large_tables:
                    print(f"{table.TABLE_NAME:<20} {table.TABLE_ROWS:<8,} rows  {table.size_mb:<6.1f} MB")
                
                if any(table.TABLE_ROWS > 10000 for table in large_tables):
                    print(f"\nTip: Consider regular cleanup for tables with >10k rows")
            else:
                print("No large tables found (all have <1000 rows)")
            
    except Exception as e:
        print(f"[ERROR] Performance analysis failed: {e}")

def main():
    """Main function with enhanced commands"""
    if len(sys.argv) < 2:
        print("Fixed Simple Maintenance Script")
        print("=" * 35)
        print("Available commands:")
        print("  cleanup [--dry-run]     - Clean up old data")
        print("  add-indexes             - Add performance indexes")
        print("  table-info              - Show detailed table information") 
        print("  analyze-performance     - Analyze database performance")
        print("  health-check            - Run health check")
        print("")
        print("Examples:")
        print("  python db_maintenance.py cleanup --dry-run")
        print("  python db_maintenance.py add-indexes")
        print("  python db_maintenance.py table-info")
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == 'cleanup':
            dry_run = '--dry-run' in sys.argv
            cleanup_data(dry_run=dry_run)
            
        elif command == 'add-indexes':
            add_performance_indexes()
            
        elif command == 'table-info':
            show_table_info()
            
        elif command == 'analyze-performance':
            analyze_performance()
            
        elif command == 'health-check':
            # Run health check from the other script
            try:
                from db_health_check import health_check
                health_check()
            except ImportError:
                print("[ERROR] simple_health_check.py not found")
                print("Run: python windows_compatible_fix.py first")
            
        else:
            print(f"Unknown command: {command}")
            print("Use: cleanup, add-indexes, table-info, analyze-performance, or health-check")
            
    except KeyboardInterrupt:
        print("\n[CANCELLED] Operation cancelled by user")
    except Exception as e:
        print(f"[ERROR] Command failed: {e}")

if __name__ == "__main__":
    main()