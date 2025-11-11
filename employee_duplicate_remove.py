#!/usr/bin/env python3
"""
Employee Duplicate Removal Script
==================================

This script identifies and removes duplicate employee records based on their ID field,
keeping only the newest record (highest 'index' value) for each unique employee ID.

IMPORTANT: 
- Always backup your database before running this script
- This script performs PERMANENT deletions
- Run with --dry-run first to preview changes

Usage:
    python remove_duplicate_employees.py --dry-run    # Preview changes only
    python remove_duplicate_employees.py              # Execute removal
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DuplicateEmployeeRemover:
    """Handles identification and removal of duplicate employee records"""
    
    def __init__(self, database_url):
        """Initialize with database connection"""
        self.database_url = database_url
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.stats = {
            'total_records': 0,
            'unique_employees': 0,
            'duplicate_records': 0,
            'records_to_remove': 0,
            'records_removed': 0
        }
        
        self.duplicate_groups = []
        
    def analyze_duplicates(self):
        """Identify duplicate employee records"""
        print("\n" + "="*70)
        print("EMPLOYEE DUPLICATE ANALYSIS")
        print("="*70 + "\n")
        
        try:
            # Get total employee count
            count_query = text("SELECT COUNT(*) as total FROM employee")
            result = self.session.execute(count_query).fetchone()
            self.stats['total_records'] = result.total
            
            print(f"📊 Total employee records in database: {self.stats['total_records']}")
            
            # Find duplicate employee IDs
            duplicate_query = text("""
                SELECT 
                    id as employee_id,
                    COUNT(*) as occurrence_count,
                    GROUP_CONCAT(`index` ORDER BY `index` DESC) as all_indices,
                    MAX(`index`) as newest_index,
                    GROUP_CONCAT(CONCAT(firstName, ' ', lastName) ORDER BY `index` DESC SEPARATOR ' | ') as names
                FROM employee
                GROUP BY id
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC, id
            """)
            
            duplicate_results = self.session.execute(duplicate_query).fetchall()
            
            if not duplicate_results:
                print("\n✅ No duplicate employee records found!")
                print("   All employee IDs are unique.\n")
                return False
            
            # Process duplicate groups
            print(f"\n⚠️  Found {len(duplicate_results)} employee IDs with duplicates:\n")
            
            for row in duplicate_results:
                employee_id = row.employee_id
                occurrence_count = row.occurrence_count
                all_indices = [int(idx) for idx in row.all_indices.split(',')]
                newest_index = row.newest_index
                names = row.names
                
                # Records to remove (all except newest)
                indices_to_remove = [idx for idx in all_indices if idx != newest_index]
                
                duplicate_group = {
                    'employee_id': employee_id,
                    'occurrence_count': occurrence_count,
                    'newest_index': newest_index,
                    'indices_to_remove': indices_to_remove,
                    'names': names
                }
                
                self.duplicate_groups.append(duplicate_group)
                self.stats['records_to_remove'] += len(indices_to_remove)
                
                print(f"  Employee ID: {employee_id}")
                print(f"  • Occurrences: {occurrence_count}")
                print(f"  • Names: {names}")
                print(f"  • Will keep: index {newest_index} (newest)")
                print(f"  • Will remove: indices {indices_to_remove}")
                print()
            
            self.stats['unique_employees'] = self.stats['total_records'] - self.stats['records_to_remove']
            self.stats['duplicate_records'] = self.stats['records_to_remove']
            
            # Print summary
            print("─" * 70)
            print(f"\n📈 SUMMARY:")
            print(f"   Total records currently: {self.stats['total_records']}")
            print(f"   Unique employee IDs: {len(duplicate_results) + (self.stats['total_records'] - len(duplicate_results) - self.stats['records_to_remove'])}")
            print(f"   Records after cleanup: {self.stats['unique_employees']}")
            print(f"   Records to be removed: {self.stats['records_to_remove']}")
            print()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def remove_duplicates(self, dry_run=True):
        """Remove duplicate employee records (keeping newest)"""
        
        if not self.duplicate_groups:
            print("No duplicates to remove.")
            return False
        
        if dry_run:
            print("\n" + "="*70)
            print("DRY RUN MODE - NO CHANGES WILL BE MADE")
            print("="*70 + "\n")
            print("The following records WOULD BE removed:\n")
            
            for group in self.duplicate_groups:
                print(f"  Employee ID {group['employee_id']}:")
                print(f"    Removing indices: {group['indices_to_remove']}")
            
            print(f"\n  Total records that would be removed: {self.stats['records_to_remove']}")
            print("\n✓ Dry run complete. Run without --dry-run to execute removal.\n")
            return True
        
        # Actual removal
        print("\n" + "="*70)
        print("REMOVING DUPLICATE RECORDS")
        print("="*70 + "\n")
        
        try:
            removed_count = 0
            
            for group in self.duplicate_groups:
                employee_id = group['employee_id']
                indices_to_remove = group['indices_to_remove']
                
                print(f"Processing Employee ID {employee_id}...")
                
                for index_to_remove in indices_to_remove:
                    delete_query = text("""
                        DELETE FROM employee 
                        WHERE `index` = :index_val
                    """)
                    
                    self.session.execute(delete_query, {'index_val': index_to_remove})
                    removed_count += 1
                    print(f"  ✓ Removed index {index_to_remove}")
            
            # Commit all changes
            self.session.commit()
            self.stats['records_removed'] = removed_count
            
            print(f"\n✅ Successfully removed {removed_count} duplicate records!")
            
            # Verify final count
            verify_query = text("SELECT COUNT(*) as total FROM employee")
            result = self.session.execute(verify_query).fetchone()
            final_count = result.total
            
            print(f"\n📊 Final verification:")
            print(f"   Records before: {self.stats['total_records']}")
            print(f"   Records removed: {self.stats['records_removed']}")
            print(f"   Records now: {final_count}")
            print(f"   Expected: {self.stats['unique_employees']}")
            
            if final_count == self.stats['unique_employees']:
                print("\n✅ Verification successful! Record counts match.\n")
            else:
                print("\n⚠️  Warning: Record count mismatch. Please verify manually.\n")
            
            return True
            
        except Exception as e:
            self.session.rollback()
            print(f"\n❌ Error during removal: {e}")
            print("Changes have been rolled back.")
            import traceback
            traceback.print_exc()
            return False
    
    def create_backup_log(self):
        """Create a log file documenting what will be removed"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"duplicate_removal_log_{timestamp}.txt"
        
        try:
            with open(log_filename, 'w') as f:
                f.write("="*70 + "\n")
                f.write("EMPLOYEE DUPLICATE REMOVAL LOG\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                
                f.write(f"Total records analyzed: {self.stats['total_records']}\n")
                f.write(f"Duplicate records found: {self.stats['records_to_remove']}\n")
                f.write(f"Unique employees after cleanup: {self.stats['unique_employees']}\n\n")
                
                f.write("DUPLICATE GROUPS:\n")
                f.write("-"*70 + "\n\n")
                
                for group in self.duplicate_groups:
                    f.write(f"Employee ID: {group['employee_id']}\n")
                    f.write(f"  Occurrences: {group['occurrence_count']}\n")
                    f.write(f"  Names: {group['names']}\n")
                    f.write(f"  Keeping: index {group['newest_index']} (newest)\n")
                    f.write(f"  Removing: indices {group['indices_to_remove']}\n\n")
            
            print(f"📄 Log file created: {log_filename}\n")
            return log_filename
            
        except Exception as e:
            print(f"⚠️  Could not create log file: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        self.session.close()
        self.engine.dispose()

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Remove duplicate employee records, keeping only the newest record for each employee ID',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python remove_duplicate_employees.py --dry-run    # Preview changes
  python remove_duplicate_employees.py              # Execute removal
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually removing records'
    )
    
    args = parser.parse_args()
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("\n❌ Error: DATABASE_URL not found in environment variables")
        print("   Please ensure .env file exists with DATABASE_URL configured\n")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("EMPLOYEE DUPLICATE REMOVAL TOOL")
    print("="*70)
    print("\nThis script will identify and remove duplicate employee records")
    print("based on their ID field, keeping only the newest record (highest index).\n")
    
    if args.dry_run:
        print("🔍 Running in DRY RUN mode - no changes will be made\n")
    else:
        print("⚠️  WARNING: This will permanently delete duplicate records!")
        print("   Make sure you have backed up your database.\n")
        
        response = input("Continue with removal? (yes/no): ")
        if response.lower() != 'yes':
            print("\n❌ Operation cancelled.\n")
            sys.exit(0)
    
    # Initialize remover
    remover = DuplicateEmployeeRemover(database_url)
    
    try:
        # Step 1: Analyze duplicates
        has_duplicates = remover.analyze_duplicates()
        
        if not has_duplicates:
            remover.close()
            sys.exit(0)
        
        # Step 2: Create log file
        remover.create_backup_log()
        
        # Step 3: Remove duplicates
        success = remover.remove_duplicates(dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print("✓ Dry run completed successfully")
                print("  Run without --dry-run to execute the removal\n")
            else:
                print("✅ Duplicate removal completed successfully!\n")
            sys.exit(0)
        else:
            print("❌ Operation failed. Please check the errors above.\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        remover.close()

if __name__ == '__main__':
    main()