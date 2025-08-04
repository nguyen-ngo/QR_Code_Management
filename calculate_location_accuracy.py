#!/usr/bin/env python3
"""
Location Accuracy Calculator Script for Existing Database Records

This script calculates location accuracy for all existing attendance records
in the database where location_accuracy is NULL or needs recalculation.

Usage:
    python calculate_location_accuracy.py [options]

Options:
    --dry-run          Show what would be updated without making changes
    --force-recalc     Recalculate accuracy for all records (even existing ones)
    --batch-size N     Process records in batches of N (default: 100)
    --specific-date    Process only records from specific date (YYYY-MM-DD)
    --help            Show this help message

Author: Attendance System Location Enhancement
Version: 1.0
"""

import sys
import os
import argparse
from datetime import datetime, date
import time

# Add your app directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your Flask app and models
try:
    from app import app, db, AttendanceData, QRCode
    from app import (
        calculate_location_accuracy_enhanced,
        get_location_accuracy_level_enhanced,
        get_coordinates_from_address,
        calculate_distance_miles
    )
except ImportError as e:
    print(f"❌ Error importing app modules: {e}")
    print("Make sure this script is in the same directory as your app.py file")
    sys.exit(1)

# Configuration
DEFAULT_BATCH_SIZE = 100
GEOCODING_DELAY = 0.1  # Delay between geocoding requests to avoid rate limits

class LocationAccuracyCalculator:
    """Main class for calculating location accuracy for existing records"""
    
    def __init__(self, dry_run=False, force_recalc=False, batch_size=DEFAULT_BATCH_SIZE):
        self.dry_run = dry_run
        self.force_recalc = force_recalc
        self.batch_size = batch_size
        self.stats = {
            'total_records': 0,
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'accuracy_calculated': 0,
            'accuracy_failed': 0
        }
        
    def run(self, specific_date=None):
        """Main execution method"""
        print("🚀 LOCATION ACCURACY CALCULATOR - STARTING")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        print(f"Force Recalculation: {'YES' if self.force_recalc else 'NO'}")
        print(f"Batch Size: {self.batch_size}")
        if specific_date:
            print(f"Target Date: {specific_date}")
        print("=" * 60)
        
        with app.app_context():
            try:
                # Get records to process
                records = self._get_records_to_process(specific_date)
                self.stats['total_records'] = len(records)
                
                if not records:
                    print("ℹ️ No records found to process")
                    return
                
                print(f"📊 Found {len(records)} records to process")
                
                # Process records in batches
                self._process_records_in_batches(records)
                
                # Final database commit to ensure all changes are saved
                if not self.dry_run:
                    try:
                        db.session.commit()
                        print(f"\n💾 Final database commit completed successfully")
                    except Exception as e:
                        print(f"❌ Final commit error: {e}")
                        db.session.rollback()
                
                # Print final statistics
                self._print_final_stats()
                
            except Exception as e:
                print(f"❌ Fatal error: {e}")
                import traceback
                traceback.print_exc()
                
    def _get_records_to_process(self, specific_date=None):
        """Get attendance records that need location accuracy calculation"""
        query = db.session.query(AttendanceData).join(QRCode)
        
        if specific_date:
            query = query.filter(AttendanceData.check_in_date == specific_date)
        
        if not self.force_recalc:
            # Only get records where location_accuracy is NULL
            query = query.filter(AttendanceData.location_accuracy.is_(None))
        
        # Order by date and time for consistent processing
        query = query.order_by(
            AttendanceData.check_in_date.desc(),
            AttendanceData.check_in_time.desc()
        )
        
        return query.all()
    
    def _process_records_in_batches(self, records):
        """Process records in configurable batches"""
        total_batches = (len(records) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(records))
            batch_records = records[start_idx:end_idx]
            
            print(f"\n📦 BATCH {batch_num + 1}/{total_batches} - Processing records {start_idx + 1}-{end_idx}")
            print("-" * 50)
            
            self._process_batch(batch_records, batch_num + 1)
            
            # Small delay between batches to avoid overwhelming external services
            if batch_num < total_batches - 1:
                time.sleep(0.5)
    
    def _process_batch(self, records, batch_num):
        """Process a single batch of records"""
        batch_updates = []
        records_to_update = []
        
        for idx, record in enumerate(records, 1):
            try:
                result = self._process_single_record(record, batch_num, idx)
                if result:
                    batch_updates.append(result)
                    records_to_update.append(record)
                    
            except Exception as e:
                print(f"❌ Error processing record {record.id}: {e}")
                self.stats['errors'] += 1
        
        # Save updates to database
        if batch_updates and not self.dry_run:
            try:
                # Update each record in the database
                for i, update_data in enumerate(batch_updates):
                    record = records_to_update[i]
                    record.location_accuracy = update_data['accuracy']
                    
                    # Mark the record as modified
                    db.session.merge(record)
                
                # Commit all changes in this batch
                db.session.commit()
                print(f"✅ Successfully saved {len(batch_updates)} location accuracy updates to database")
                
            except Exception as e:
                print(f"❌ Database commit error: {e}")
                db.session.rollback()
                self.stats['errors'] += len(batch_updates)
                # Reset the updated count since commit failed
                self.stats['updated'] -= len(batch_updates)
                self.stats['accuracy_calculated'] -= len(batch_updates)
        
    def _process_single_record(self, record, batch_num, record_idx):
        """Process a single attendance record"""
        self.stats['processed'] += 1
        
        # Skip if already has accuracy and not forcing recalculation
        if record.location_accuracy is not None and not self.force_recalc:
            print(f"⏭️  [{batch_num}.{record_idx}] Record {record.id}: Already has accuracy ({record.location_accuracy:.4f} mi)")
            self.stats['skipped'] += 1
            return None
        
        # Get QR code information
        qr_code = record.qr_code
        if not qr_code:
            print(f"⚠️  [{batch_num}.{record_idx}] Record {record.id}: No QR code found")
            self.stats['skipped'] += 1
            return None
        
        print(f"🔄 [{batch_num}.{record_idx}] Processing: Employee {record.employee_id} | {record.check_in_date} | {qr_code.location}")
        
        # Calculate location accuracy
        location_accuracy = self._calculate_accuracy_for_record(record, qr_code)
        
        if location_accuracy is not None:
            accuracy_level = get_location_accuracy_level_enhanced(location_accuracy)
            
            # Always update the record object, database save happens in batch processing
            if not self.dry_run:
                # Update the record's location_accuracy field
                record.location_accuracy = location_accuracy
                print(f"✅ [{batch_num}.{record_idx}] Accuracy set: {location_accuracy:.4f} miles ({accuracy_level}) - Will save to database")
            else:
                print(f"✅ [{batch_num}.{record_idx}] Accuracy calculated: {location_accuracy:.4f} miles ({accuracy_level}) - DRY RUN")
            
            self.stats['updated'] += 1
            self.stats['accuracy_calculated'] += 1
            
            return {
                'record_id': record.id,
                'accuracy': location_accuracy,
                'level': accuracy_level
            }
        else:
            print(f"⚠️  [{batch_num}.{record_idx}] Could not calculate accuracy")
            self.stats['accuracy_failed'] += 1
            return None
    
    def _calculate_accuracy_for_record(self, record, qr_code):
        """Calculate location accuracy for a specific record"""
        try:
            # Add small delay to avoid overwhelming geocoding services
            time.sleep(GEOCODING_DELAY)
            
            return calculate_location_accuracy_enhanced(
                qr_address=qr_code.location_address,
                checkin_address=record.address,
                checkin_lat=record.latitude,
                checkin_lng=record.longitude
            )
        except Exception as e:
            print(f"    ❌ Calculation error: {e}")
            return None
    
    def _print_final_stats(self):
        """Print comprehensive final statistics"""
        print("\n" + "=" * 60)
        print("📊 FINAL STATISTICS")
        print("=" * 60)
        print(f"Total Records Found:     {self.stats['total_records']:,}")
        print(f"Records Processed:       {self.stats['processed']:,}")
        print(f"Records Updated:         {self.stats['updated']:,}")
        print(f"Records Skipped:         {self.stats['skipped']:,}")
        print(f"Errors Encountered:      {self.stats['errors']:,}")
        print("-" * 40)
        print(f"Accuracy Calculated:     {self.stats['accuracy_calculated']:,}")
        print(f"Accuracy Failed:         {self.stats['accuracy_failed']:,}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['accuracy_calculated'] / self.stats['processed']) * 100
            print(f"Success Rate:            {success_rate:.1f}%")
        
        print("=" * 60)
        
        if self.dry_run:
            print("🔍 DRY RUN COMPLETED - No changes were made to the database")
        else:
            print("✅ LIVE UPDATE COMPLETED - Database has been updated")
            
            # Verify database updates
            self._verify_database_updates()
        
        print("=" * 60)
    
    def _verify_database_updates(self):
        """Verify that the database updates were actually saved"""
        try:
            print("\n🔍 VERIFYING DATABASE UPDATES...")
            
            # Count records with location_accuracy that were just updated
            updated_count = db.session.query(AttendanceData).filter(
                AttendanceData.location_accuracy.isnot(None)
            ).count()
            
            print(f"📊 Database verification:")
            print(f"   Total records with location_accuracy: {updated_count:,}")
            
            if self.stats['updated'] > 0:
                print(f"   Expected updates from this run: {self.stats['updated']:,}")
                
                # Get a sample of recently updated records to verify
                sample_records = db.session.query(AttendanceData).filter(
                    AttendanceData.location_accuracy.isnot(None)
                ).limit(3).all()
                
                if sample_records:
                    print(f"   Sample updated records:")
                    for record in sample_records:
                        print(f"     • Record {record.id}: {record.location_accuracy:.4f} miles")
                else:
                    print("   ⚠️ No sample records found - verification inconclusive")
            
            print("✅ Database verification completed")
            
        except Exception as e:
            print(f"❌ Error during database verification: {e}")


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Calculate location accuracy for existing attendance records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python calculate_location_accuracy.py --dry-run
    python calculate_location_accuracy.py --force-recalc --batch-size 50
    python calculate_location_accuracy.py --specific-date 2025-01-15
    python calculate_location_accuracy.py --dry-run --specific-date 2025-01-15
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    parser.add_argument(
        '--force-recalc',
        action='store_true',
        help='Recalculate accuracy for all records (even existing ones)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'Process records in batches of N (default: {DEFAULT_BATCH_SIZE})'
    )
    
    parser.add_argument(
        '--specific-date',
        type=str,
        help='Process only records from specific date (YYYY-MM-DD format)'
    )
    
    args = parser.parse_args()
    
    # Validate specific date if provided
    specific_date = None
    if args.specific_date:
        try:
            specific_date = datetime.strptime(args.specific_date, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD (e.g., 2025-01-15)")
            sys.exit(1)
    
    # Validate batch size
    if args.batch_size < 1:
        print("❌ Batch size must be at least 1")
        sys.exit(1)
    
    # Create and run calculator
    calculator = LocationAccuracyCalculator(
        dry_run=args.dry_run,
        force_recalc=args.force_recalc,
        batch_size=args.batch_size
    )
    
    try:
        calculator.run(specific_date=specific_date)
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()