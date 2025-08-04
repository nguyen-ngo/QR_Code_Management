#!/usr/bin/env python3
"""
Database Update Verification Script

Quick script to verify that location accuracy calculations
are being properly saved to the database.

Usage:
    python verify_database_updates.py

This script will:
1. Check database connection
2. Count records with location_accuracy
3. Show sample records
4. Display recent updates
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add your app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, AttendanceData, QRCode
    from app import get_location_accuracy_level_enhanced
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def verify_database_updates():
    """Comprehensive verification of database updates"""
    print("🔍 DATABASE UPDATE VERIFICATION")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Basic counts
            total_records = db.session.query(AttendanceData).count()
            records_with_accuracy = db.session.query(AttendanceData).filter(
                AttendanceData.location_accuracy.isnot(None)
            ).count()
            
            print(f"📊 Database Status:")
            print(f"   Total attendance records: {total_records:,}")
            print(f"   Records with location_accuracy: {records_with_accuracy:,}")
            
            if total_records > 0:
                coverage = (records_with_accuracy / total_records) * 100
                print(f"   Coverage: {coverage:.1f}%")
            
            # Show sample records with accuracy
            if records_with_accuracy > 0:
                print(f"\n📝 Sample Records with Location Accuracy:")
                print("-" * 40)
                
                sample_records = db.session.query(AttendanceData, QRCode).join(
                    QRCode, AttendanceData.qr_code_id == QRCode.id
                ).filter(
                    AttendanceData.location_accuracy.isnot(None)
                ).order_by(AttendanceData.id.desc()).limit(5).all()
                
                for attendance, qr_code in sample_records:
                    accuracy_level = get_location_accuracy_level_enhanced(attendance.location_accuracy)
                    print(f"   • Record {attendance.id}: Employee {attendance.employee_id}")
                    print(f"     Date: {attendance.check_in_date} | Location: {attendance.location_name}")
                    print(f"     Accuracy: {attendance.location_accuracy:.4f} miles ({accuracy_level})")
                    print(f"     QR Address: {qr_code.location_address[:50]}...")
                    if attendance.address:
                        print(f"     Check-in Address: {attendance.address[:50]}...")
                    print()
            
            # Check for recent updates (if any exist)
            print(f"📅 Recent Activity Check:")
            print("-" * 30)
            
            yesterday = date.today() - timedelta(days=1)
            recent_records = db.session.query(AttendanceData).filter(
                AttendanceData.check_in_date >= yesterday
            ).count()
            
            recent_with_accuracy = db.session.query(AttendanceData).filter(
                AttendanceData.check_in_date >= yesterday,
                AttendanceData.location_accuracy.isnot(None)
            ).count()
            
            print(f"   Recent records (last 24h): {recent_records}")
            print(f"   Recent with accuracy: {recent_with_accuracy}")
            
            # Accuracy level distribution
            if records_with_accuracy > 0:
                print(f"\n📈 Accuracy Level Distribution:")
                print("-" * 35)
                
                accuracy_records = db.session.query(AttendanceData.location_accuracy).filter(
                    AttendanceData.location_accuracy.isnot(None)
                ).all()
                
                levels = {}
                for record in accuracy_records:
                    accuracy = record[0]
                    level = get_location_accuracy_level_enhanced(accuracy)
                    levels[level] = levels.get(level, 0) + 1
                
                for level in ['excellent', 'very_good', 'good', 'fair', 'poor', 'very_poor']:
                    count = levels.get(level, 0)
                    if count > 0:
                        percentage = (count / records_with_accuracy) * 100
                        print(f"   {level.replace('_', ' ').title():12} {count:6,} ({percentage:5.1f}%)")
            
            # Database integrity checks
            print(f"\n🔍 Database Integrity Checks:")
            print("-" * 35)
            
            # Check for invalid accuracy values
            invalid_accuracy = db.session.query(AttendanceData).filter(
                AttendanceData.location_accuracy < 0
            ).count()
            
            extreme_accuracy = db.session.query(AttendanceData).filter(
                AttendanceData.location_accuracy > 100
            ).count()
            
            print(f"   Invalid accuracy values (< 0): {invalid_accuracy}")
            print(f"   Extreme accuracy values (> 100 mi): {extreme_accuracy}")
            
            if invalid_accuracy == 0 and extreme_accuracy == 0:
                print("   ✅ All accuracy values are within reasonable ranges")
            
            print(f"\n✅ Database verification completed successfully")
            
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            import traceback
            traceback.print_exc()

def test_database_connection():
    """Test basic database connectivity"""
    print("🔌 Testing Database Connection...")
    
    with app.app_context():
        try:
            # Simple query to test connection
            count = db.session.query(AttendanceData).count()
            print(f"✅ Database connection successful")
            print(f"   Found {count:,} attendance records")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

def main():
    """Main execution function"""
    print("DATABASE UPDATE VERIFICATION TOOL")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test connection first
    if not test_database_connection():
        print("Cannot proceed without database connection")
        sys.exit(1)
    
    print()
    
    # Run verification
    verify_database_updates()
    
    print(f"\nVerification completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == '__main__':
    main()