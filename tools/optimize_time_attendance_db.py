#!/usr/bin/env python3
"""
==============================================================================
Time Attendance Database Optimization Script
==============================================================================

Standalone script for optimizing the time_attendance table.
Can be run manually or as a cronjob.

Usage:
    python optimize_time_attendance_db.py --action optimize
    python optimize_time_attendance_db.py --action analyze
    python optimize_time_attendance_db.py --action archive --days 365
    python optimize_time_attendance_db.py --action cleanup --days 90
    python optimize_time_attendance_db.py --action report
    python optimize_time_attendance_db.py --action all

Requirements:
    - Must be run from the application directory
    - Database credentials must be configured in config.py or environment

Author: Database Optimization Team
Date: 2025-10-14
==============================================================================
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import logging

# Add the application directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and database
try:
    from app import app, db
    from models.time_attendance import TimeAttendance
    from sqlalchemy import text
except ImportError as e:
    print(f"❌ Error: Cannot import required modules: {e}")
    print("   Make sure this script is in the same directory as app.py")
    sys.exit(1)


class TimeAttendanceOptimizer:
    """Standalone optimizer for time_attendance table"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO if self.verbose else logging.WARNING,
            format=log_format
        )
        self.logger = logging.getLogger(__name__)
    
    def log(self, message, level='info'):
        """Log message with appropriate level"""
        if level == 'info':
            self.logger.info(message)
            if self.verbose:
                print(f"ℹ️  {message}")
        elif level == 'success':
            self.logger.info(message)
            if self.verbose:
                print(f"✅ {message}")
        elif level == 'warning':
            self.logger.warning(message)
            if self.verbose:
                print(f"⚠️  {message}")
        elif level == 'error':
            self.logger.error(message)
            if self.verbose:
                print(f"❌ {message}")
    
    def create_indexes(self):
        """Create optimized indexes for time_attendance table"""
        self.log("Creating optimized indexes...", 'info')
        
        indexes = [
            {
                'name': 'idx_ta_employee_date_time',
                'columns': 'employee_id, attendance_date DESC, attendance_time DESC',
                'purpose': 'Employee-based queries with date filtering'
            },
            {
                'name': 'idx_ta_date_location_employee',
                'columns': 'attendance_date DESC, location_name, employee_id',
                'purpose': 'Date and location filtering'
            },
            {
                'name': 'idx_ta_project_date_employee',
                'columns': 'project_id, attendance_date DESC, employee_id',
                'purpose': 'Project-based attendance queries'
            },
            {
                'name': 'idx_ta_batch_date',
                'columns': 'import_batch_id, attendance_date DESC',
                'purpose': 'Import batch management'
            },
            {
                'name': 'idx_ta_action_date_employee',
                'columns': 'action_description, attendance_date DESC, employee_id',
                'purpose': 'Action-based analytics'
            },
            {
                'name': 'idx_ta_date_time_desc',
                'columns': 'attendance_date DESC, attendance_time DESC, id DESC',
                'purpose': 'Recent records retrieval'
            },
            {
                'name': 'idx_ta_location_action_date',
                'columns': 'location_name, action_description, attendance_date DESC',
                'purpose': 'Location-based action analysis'
            },
        ]
        
        created = 0
        skipped = 0
        failed = 0
        
        for idx in indexes:
            try:
                # Check if index exists
                check_query = f"""
                    SELECT COUNT(*) as count 
                    FROM INFORMATION_SCHEMA.STATISTICS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'time_attendance' 
                    AND INDEX_NAME = '{idx['name']}'
                """
                result = db.session.execute(text(check_query)).fetchone()
                
                if result and result.count > 0:
                    self.log(f"Index {idx['name']} already exists - skipped", 'info')
                    skipped += 1
                    continue
                
                # Create index
                create_query = f"""
                    CREATE INDEX {idx['name']} 
                    ON time_attendance ({idx['columns']})
                """
                
                self.log(f"Creating index: {idx['name']}", 'info')
                db.session.execute(text(create_query))
                db.session.commit()
                
                self.log(f"Created index: {idx['name']} - {idx['purpose']}", 'success')
                created += 1
                
            except Exception as e:
                self.log(f"Failed to create index {idx['name']}: {str(e)[:100]}", 'warning')
                failed += 1
                db.session.rollback()
                continue
        
        self.log(f"Index creation complete: {created} created, {skipped} skipped, {failed} failed", 'success')
        return {'created': created, 'skipped': skipped, 'failed': failed}
    
    def analyze_table(self):
        """Analyze time_attendance table statistics"""
        self.log("Analyzing table statistics...", 'info')
        
        try:
            stats_query = """
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT employee_id) as unique_employees,
                    COUNT(DISTINCT location_name) as unique_locations,
                    COUNT(DISTINCT DATE(attendance_date)) as unique_dates,
                    COUNT(DISTINCT import_batch_id) as unique_batches,
                    COUNT(DISTINCT project_id) as unique_projects,
                    MIN(attendance_date) as earliest_date,
                    MAX(attendance_date) as latest_date,
                    COUNT(CASE WHEN recorded_address IS NOT NULL THEN 1 END) as records_with_address
                FROM time_attendance
            """
            
            result = db.session.execute(text(stats_query)).fetchone()
            
            # Get table size
            size_query = """
                SELECT 
                    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb,
                    ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_mb,
                    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_mb
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'time_attendance'
            """
            
            size_result = db.session.execute(text(size_query)).fetchone()
            
            if result:
                date_range_days = (result.latest_date - result.earliest_date).days if result.latest_date and result.earliest_date else 0
                
                stats = {
                    'total_records': result.total_records,
                    'unique_employees': result.unique_employees,
                    'unique_locations': result.unique_locations,
                    'unique_dates': result.unique_dates,
                    'unique_batches': result.unique_batches,
                    'unique_projects': result.unique_projects,
                    'earliest_date': result.earliest_date,
                    'latest_date': result.latest_date,
                    'date_range_days': date_range_days,
                    'records_with_address': result.records_with_address,
                    'table_size_mb': size_result.size_mb if size_result else 0,
                    'data_size_mb': size_result.data_mb if size_result else 0,
                    'index_size_mb': size_result.index_mb if size_result else 0
                }
                
                print("\n" + "="*60)
                print("📊 TIME ATTENDANCE TABLE STATISTICS")
                print("="*60)
                print(f"Total Records:        {stats['total_records']:>15,}")
                print(f"Unique Employees:     {stats['unique_employees']:>15,}")
                print(f"Unique Locations:     {stats['unique_locations']:>15,}")
                print(f"Unique Dates:         {stats['unique_dates']:>15,}")
                print(f"Import Batches:       {stats['unique_batches']:>15,}")
                print(f"Projects:             {stats['unique_projects']:>15,}")
                print(f"Date Range:           {stats['date_range_days']:>15,} days")
                print(f"Earliest Date:        {stats['earliest_date']:>15}")
                print(f"Latest Date:          {stats['latest_date']:>15}")
                print(f"Records w/ Address:   {stats['records_with_address']:>15,}")
                print(f"\nTable Size:           {stats['table_size_mb']:>15.2f} MB")
                print(f"  Data Size:          {stats['data_size_mb']:>15.2f} MB")
                print(f"  Index Size:         {stats['index_size_mb']:>15.2f} MB")
                print("="*60 + "\n")
                
                return stats
            
        except Exception as e:
            self.log(f"Error analyzing table: {e}", 'error')
            return None
    
    def optimize_table(self):
        """Run MySQL OPTIMIZE TABLE and ANALYZE TABLE"""
        self.log("Optimizing table structure...", 'info')
        
        try:
            # Analyze table
            self.log("Running ANALYZE TABLE...", 'info')
            db.session.execute(text("ANALYZE TABLE time_attendance"))
            db.session.commit()
            self.log("ANALYZE TABLE completed", 'success')
            
            # Optimize table
            self.log("Running OPTIMIZE TABLE (this may take a while)...", 'info')
            db.session.execute(text("OPTIMIZE TABLE time_attendance"))
            db.session.commit()
            self.log("OPTIMIZE TABLE completed", 'success')
            
            return {'success': True}
            
        except Exception as e:
            self.log(f"Error optimizing table: {e}", 'error')
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def create_archive_table(self):
        """Create archive table if it doesn't exist"""
        try:
            create_query = """
                CREATE TABLE IF NOT EXISTS time_attendance_archive 
                LIKE time_attendance
            """
            db.session.execute(text(create_query))
            db.session.commit()
            return True
        except Exception as e:
            self.log(f"Error creating archive table: {e}", 'error')
            db.session.rollback()
            return False
    
    def archive_old_records(self, days=365, execute=False):
        """Archive records older than specified days"""
        self.log(f"Archive process for records older than {days} days...", 'info')
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Count records to archive
            count_query = """
                SELECT COUNT(*) as count 
                FROM time_attendance 
                WHERE attendance_date < :cutoff_date
            """
            result = db.session.execute(
                text(count_query),
                {'cutoff_date': cutoff_date.date()}
            ).fetchone()
            
            records_to_archive = result.count if result else 0
            
            print(f"\n📦 Archive Summary:")
            print(f"   Cutoff Date:       {cutoff_date.date()}")
            print(f"   Records to Archive: {records_to_archive:,}")
            
            if records_to_archive == 0:
                self.log("No records to archive", 'info')
                return {'records_archived': 0}
            
            if not execute:
                print(f"\n⚠️  DRY RUN MODE - No records will be archived")
                print(f"   Use --execute flag to actually archive records\n")
                return {'records_archived': 0, 'dry_run': True}
            
            # Create archive table
            if not self.create_archive_table():
                return {'success': False, 'error': 'Failed to create archive table'}
            
            # Archive records in batches
            self.log("Starting archive process...", 'info')
            batch_size = 10000
            total_archived = 0
            
            while total_archived < records_to_archive:
                # Insert to archive
                archive_query = """
                    INSERT INTO time_attendance_archive 
                    SELECT * FROM time_attendance 
                    WHERE attendance_date < :cutoff_date 
                    LIMIT :batch_size
                """
                
                db.session.execute(
                    text(archive_query),
                    {'cutoff_date': cutoff_date.date(), 'batch_size': batch_size}
                )
                
                # Delete from main table
                delete_query = """
                    DELETE FROM time_attendance 
                    WHERE attendance_date < :cutoff_date 
                    LIMIT :batch_size
                """
                
                result = db.session.execute(
                    text(delete_query),
                    {'cutoff_date': cutoff_date.date(), 'batch_size': batch_size}
                )
                
                rows_affected = result.rowcount
                
                if rows_affected == 0:
                    break
                
                db.session.commit()
                total_archived += rows_affected
                
                self.log(f"Archived {total_archived:,} / {records_to_archive:,} records...", 'info')
                
                # Safety limit
                if total_archived >= 100000:
                    self.log("Reached safety limit of 100,000 records per run", 'warning')
                    break
            
            self.log(f"Archive complete: {total_archived:,} records archived", 'success')
            return {'records_archived': total_archived, 'success': True}
            
        except Exception as e:
            self.log(f"Error during archive: {e}", 'error')
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def cleanup_old_records(self, days=90, execute=False):
        """Delete records older than specified days"""
        self.log(f"Cleanup process for records older than {days} days...", 'info')
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Count records to delete
            count_query = """
                SELECT COUNT(*) as count 
                FROM time_attendance 
                WHERE import_date < :cutoff_date
            """
            result = db.session.execute(
                text(count_query),
                {'cutoff_date': cutoff_date}
            ).fetchone()
            
            records_to_delete = result.count if result else 0
            
            print(f"\n🗑️  Cleanup Summary:")
            print(f"   Cutoff Date:        {cutoff_date.date()}")
            print(f"   Records to Delete:  {records_to_delete:,}")
            
            if records_to_delete == 0:
                self.log("No records to delete", 'info')
                return {'records_deleted': 0}
            
            if not execute:
                print(f"\n⚠️  DRY RUN MODE - No records will be deleted")
                print(f"   Use --execute flag to actually delete records\n")
                return {'records_deleted': 0, 'dry_run': True}
            
            # Delete records
            delete_query = """
                DELETE FROM time_attendance 
                WHERE import_date < :cutoff_date
            """
            
            self.log("Deleting old records...", 'info')
            db.session.execute(
                text(delete_query),
                {'cutoff_date': cutoff_date}
            )
            db.session.commit()
            
            self.log(f"Cleanup complete: {records_to_delete:,} records deleted", 'success')
            return {'records_deleted': records_to_delete, 'success': True}
            
        except Exception as e:
            self.log(f"Error during cleanup: {e}", 'error')
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def generate_report(self):
        """Generate comprehensive optimization report"""
        print("\n" + "="*60)
        print("📋 TIME ATTENDANCE OPTIMIZATION REPORT")
        print("="*60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get statistics
        stats = self.analyze_table()
        
        if stats:
            # Generate recommendations
            print("\n" + "="*60)
            print("💡 RECOMMENDATIONS")
            print("="*60)
            
            recommendations = []
            
            if stats['total_records'] > 100000:
                recommendations.append({
                    'priority': 'HIGH',
                    'type': 'Indexing',
                    'message': f"Table has {stats['total_records']:,} records. Run index optimization."
                })
            
            if stats['total_records'] > 500000:
                recommendations.append({
                    'priority': 'HIGH',
                    'type': 'Archiving',
                    'message': f"Consider archiving records older than 365 days."
                })
            
            if stats['table_size_mb'] > 500:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'type': 'Optimization',
                    'message': f"Table size is {stats['table_size_mb']:.2f} MB. Run OPTIMIZE TABLE."
                })
            
            if stats['date_range_days'] > 365:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'type': 'Data Retention',
                    'message': f"Data spans {stats['date_range_days']} days. Implement retention policy."
                })
            
            if stats['index_size_mb'] > stats['data_size_mb'] * 1.5:
                recommendations.append({
                    'priority': 'LOW',
                    'type': 'Index Review',
                    'message': f"Index size ({stats['index_size_mb']:.2f} MB) is large. Review index usage."
                })
            
            if not recommendations:
                print("✓ No major issues found. Database is well optimized.\n")
            else:
                for rec in recommendations:
                    priority_icon = "🔴" if rec['priority'] == 'HIGH' else "🟡" if rec['priority'] == 'MEDIUM' else "🟢"
                    print(f"{priority_icon} [{rec['priority']}] {rec['type']}")
                    print(f"   {rec['message']}\n")
            
            print("="*60)
            
            # Suggested actions
            print("\n💻 SUGGESTED ACTIONS:")
            print("-"*60)
            if stats['total_records'] > 100000:
                print("• python optimize_time_attendance_db.py --action optimize")
            if stats['total_records'] > 500000:
                print("• python optimize_time_attendance_db.py --action archive --days 365 --execute")
            if stats['date_range_days'] > 180:
                print("• python optimize_time_attendance_db.py --action cleanup --days 90 --execute")
            print("="*60 + "\n")


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description='Time Attendance Database Optimization Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --action optimize              # Create indexes and optimize table
  %(prog)s --action analyze               # Analyze table statistics
  %(prog)s --action archive --days 365    # Archive records older than 365 days (dry run)
  %(prog)s --action archive --days 365 --execute  # Actually archive records
  %(prog)s --action cleanup --days 90 --execute   # Delete records older than 90 days
  %(prog)s --action report                # Generate optimization report
  %(prog)s --action all                   # Run full optimization (indexes + analyze + optimize)
        """
    )
    
    parser.add_argument(
        '--action',
        required=True,
        choices=['optimize', 'analyze', 'archive', 'cleanup', 'report', 'all', 'indexes'],
        help='Action to perform'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Number of days for archive/cleanup (default: 365)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute archive/cleanup (otherwise dry run)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress verbose output'
    )
    
    args = parser.parse_args()
    
    # Create optimizer instance
    optimizer = TimeAttendanceOptimizer(verbose=not args.quiet)
    
    print("\n" + "="*60)
    print("🔧 TIME ATTENDANCE DATABASE OPTIMIZER")
    print("="*60)
    print(f"Action: {args.action.upper()}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    try:
        with app.app_context():
            if args.action == 'indexes':
                optimizer.create_indexes()
            
            elif args.action == 'optimize':
                optimizer.create_indexes()
                optimizer.optimize_table()
            
            elif args.action == 'analyze':
                optimizer.analyze_table()
            
            elif args.action == 'archive':
                optimizer.archive_old_records(days=args.days, execute=args.execute)
            
            elif args.action == 'cleanup':
                optimizer.cleanup_old_records(days=args.days, execute=args.execute)
            
            elif args.action == 'report':
                optimizer.generate_report()
            
            elif args.action == 'all':
                optimizer.create_indexes()
                optimizer.analyze_table()
                optimizer.optimize_table()
                print("\n✅ Full optimization complete!")
            
            print("\n" + "="*60)
            print("✅ OPTIMIZATION COMPLETED SUCCESSFULLY")
            print("="*60 + "\n")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()