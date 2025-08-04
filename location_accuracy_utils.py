#!/usr/bin/env python3
"""
Location Accuracy Database Utilities

Additional utility functions for managing location accuracy data
in your attendance system database.

Usage:
    python location_accuracy_utils.py [command] [options]

Commands:
    check-schema      Verify database schema for location accuracy
    add-field         Add location_accuracy field to attendance_data table
    stats             Show location accuracy statistics
    export-report     Export detailed location accuracy report
    verify-data       Verify data integrity for location accuracy

Author: Attendance System Enhancement Team
"""

import sys
import os
import csv
from datetime import datetime, date
import json

# Add your app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, AttendanceData, QRCode
    from app import get_location_accuracy_level_enhanced
    from sqlalchemy import text, inspect
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

class LocationAccuracyUtils:
    """Utility class for location accuracy database management"""
    
    def __init__(self):
        self.app = app
        
    def check_database_schema(self):
        """Check if the database schema supports location accuracy"""
        print("🔍 CHECKING DATABASE SCHEMA")
        print("=" * 50)
        
        with self.app.app_context():
            inspector = inspect(db.engine)
            
            # Check attendance_data table
            try:
                columns = inspector.get_columns('attendance_data')
                column_names = [col['name'] for col in columns]
                
                print("📋 Attendance Data Table Columns:")
                required_fields = [
                    'id', 'qr_code_id', 'employee_id', 'check_in_date', 'check_in_time',
                    'latitude', 'longitude', 'address', 'location_accuracy'
                ]
                
                for field in required_fields:
                    status = "✅" if field in column_names else "❌"
                    print(f"   {status} {field}")
                
                # Check for location_accuracy field specifically
                has_accuracy_field = 'location_accuracy' in column_names
                
                if has_accuracy_field:
                    # Get field details
                    accuracy_col = next((col for col in columns if col['name'] == 'location_accuracy'), None)
                    if accuracy_col:
                        print(f"\n📊 location_accuracy field details:")
                        print(f"   Type: {accuracy_col['type']}")
                        print(f"   Nullable: {accuracy_col['nullable']}")
                        print(f"   Default: {accuracy_col.get('default', 'None')}")
                
                return has_accuracy_field
                
            except Exception as e:
                print(f"❌ Error checking schema: {e}")
                return False
    
    def add_location_accuracy_field(self):
        """Add location_accuracy field to attendance_data table if missing"""
        print("🔧 ADDING LOCATION ACCURACY FIELD")
        print("=" * 50)
        
        with self.app.app_context():
            try:
                # Check if field already exists
                if self.check_database_schema():
                    print("ℹ️ location_accuracy field already exists")
                    return True
                
                print("➕ Adding location_accuracy field...")
                
                # Add the field
                db.session.execute(text("""
                    ALTER TABLE attendance_data 
                    ADD COLUMN location_accuracy FLOAT
                """))
                
                db.session.commit()
                print("✅ Successfully added location_accuracy field")
                
                # Verify addition
                if self.check_database_schema():
                    print("✅ Field addition verified")
                    return True
                else:
                    print("❌ Field addition verification failed")
                    return False
                    
            except Exception as e:
                print(f"❌ Error adding field: {e}")
                db.session.rollback()
                return False
    
    def show_location_accuracy_stats(self):
        """Show comprehensive statistics about location accuracy data"""
        print("📊 LOCATION ACCURACY STATISTICS")
        print("=" * 60)
        
        with self.app.app_context():
            try:
                # Basic counts
                total_records = db.session.query(AttendanceData).count()
                records_with_location = db.session.query(AttendanceData).filter(
                    AttendanceData.latitude.isnot(None),
                    AttendanceData.longitude.isnot(None)
                ).count()
                
                records_with_accuracy = db.session.query(AttendanceData).filter(
                    AttendanceData.location_accuracy.isnot(None)
                ).count()
                
                print(f"Total Records:              {total_records:,}")
                print(f"Records with GPS Data:      {records_with_location:,}")
                print(f"Records with Accuracy:      {records_with_accuracy:,}")
                
                if total_records > 0:
                    gps_percentage = (records_with_location / total_records) * 100
                    accuracy_percentage = (records_with_accuracy / total_records) * 100
                    print(f"GPS Coverage:               {gps_percentage:.1f}%")
                    print(f"Accuracy Coverage:          {accuracy_percentage:.1f}%")
                
                # Accuracy level distribution
                if records_with_accuracy > 0:
                    print("\n📈 ACCURACY LEVEL DISTRIBUTION")
                    print("-" * 40)
                    
                    accuracy_records = db.session.query(AttendanceData.location_accuracy).filter(
                        AttendanceData.location_accuracy.isnot(None)
                    ).all()
                    
                    levels = {}
                    total_distance = 0
                    
                    for record in accuracy_records:
                        accuracy = record[0]
                        level = get_location_accuracy_level_enhanced(accuracy)
                        levels[level] = levels.get(level, 0) + 1
                        total_distance += accuracy
                    
                    for level in ['excellent', 'very_good', 'good', 'fair', 'poor', 'very_poor']:
                        count = levels.get(level, 0)
                        percentage = (count / records_with_accuracy) * 100 if records_with_accuracy > 0 else 0
                        print(f"{level.replace('_', ' ').title():12} {count:6,} ({percentage:5.1f}%)")
                    
                    avg_accuracy = total_distance / len(accuracy_records)
                    print(f"\nAverage Distance:           {avg_accuracy:.4f} miles")
                
                # Recent activity
                print("\n📅 RECENT ACTIVITY (Last 7 Days)")
                print("-" * 40)
                
                seven_days_ago = date.today().replace(day=date.today().day - 7) if date.today().day > 7 else date.today().replace(month=date.today().month - 1, day=date.today().day + 30 - 7)
                
                recent_records = db.session.query(AttendanceData).filter(
                    AttendanceData.check_in_date >= seven_days_ago
                ).count()
                
                recent_with_accuracy = db.session.query(AttendanceData).filter(
                    AttendanceData.check_in_date >= seven_days_ago,
                    AttendanceData.location_accuracy.isnot(None)
                ).count()
                
                print(f"Recent Check-ins:           {recent_records:,}")
                print(f"Recent with Accuracy:       {recent_with_accuracy:,}")
                
                if recent_records > 0:
                    recent_percentage = (recent_with_accuracy / recent_records) * 100
                    print(f"Recent Accuracy Rate:       {recent_percentage:.1f}%")
                
            except Exception as e:
                print(f"❌ Error generating statistics: {e}")
    
    def export_location_accuracy_report(self, output_file=None):
        """Export detailed location accuracy report to CSV"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"location_accuracy_report_{timestamp}.csv"
        
        print(f"📄 EXPORTING LOCATION ACCURACY REPORT")
        print(f"Output File: {output_file}")
        print("=" * 60)
        
        with self.app.app_context():
            try:
                # Query all records with their QR code information
                query = db.session.query(AttendanceData, QRCode).join(
                    QRCode, AttendanceData.qr_code_id == QRCode.id
                ).order_by(AttendanceData.check_in_date.desc(), AttendanceData.check_in_time.desc())
                
                records = query.all()
                
                print(f"Found {len(records)} records to export")
                
                # Write CSV file
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = [
                        'attendance_id', 'employee_id', 'check_in_date', 'check_in_time',
                        'location_name', 'qr_address', 'checkin_address',
                        'checkin_latitude', 'checkin_longitude', 'gps_accuracy_meters',
                        'location_accuracy_miles', 'accuracy_level',
                        'has_gps_data', 'has_location_accuracy', 'device_info'
                    ]
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for attendance, qr_code in records:
                        accuracy_level = 'unknown'
                        if attendance.location_accuracy:
                            accuracy_level = get_location_accuracy_level_enhanced(attendance.location_accuracy)
                        
                        writer.writerow({
                            'attendance_id': attendance.id,
                            'employee_id': attendance.employee_id,
                            'check_in_date': attendance.check_in_date.isoformat(),
                            'check_in_time': attendance.check_in_time.isoformat(),
                            'location_name': attendance.location_name,
                            'qr_address': qr_code.location_address,
                            'checkin_address': attendance.address or 'Not captured',
                            'checkin_latitude': attendance.latitude,
                            'checkin_longitude': attendance.longitude,
                            'gps_accuracy_meters': attendance.accuracy,
                            'location_accuracy_miles': attendance.location_accuracy,
                            'accuracy_level': accuracy_level,
                            'has_gps_data': attendance.latitude is not None and attendance.longitude is not None,
                            'has_location_accuracy': attendance.location_accuracy is not None,
                            'device_info': attendance.device_info or 'Unknown'
                        })
                
                print(f"✅ Report exported successfully to {output_file}")
                return output_file
                
            except Exception as e:
                print(f"❌ Error exporting report: {e}")
                return None
    
    def verify_data_integrity(self):
        """Verify data integrity for location accuracy calculations"""
        print("🔍 VERIFYING DATA INTEGRITY")
        print("=" * 50)
        
        with self.app.app_context():
            try:
                issues = []
                
                # Check for records with coordinates but no address
                no_address_with_coords = db.session.query(AttendanceData).filter(
                    AttendanceData.latitude.isnot(None),
                    AttendanceData.longitude.isnot(None),
                    AttendanceData.address.is_(None)
                ).count()
                
                if no_address_with_coords > 0:
                    issues.append(f"{no_address_with_coords} records have GPS coordinates but no address")
                
                # Check for invalid coordinates
                invalid_coords = db.session.query(AttendanceData).filter(
                    db.or_(
                        AttendanceData.latitude < -90,
                        AttendanceData.latitude > 90,
                        AttendanceData.longitude < -180,
                        AttendanceData.longitude > 180
                    )
                ).count()
                
                if invalid_coords > 0:
                    issues.append(f"{invalid_coords} records have invalid GPS coordinates")
                
                # Check for QR codes without addresses
                qr_no_address = db.session.query(QRCode).filter(
                    db.or_(
                        QRCode.location_address.is_(None),
                        QRCode.location_address == ''
                    )
                ).count()
                
                if qr_no_address > 0:
                    issues.append(f"{qr_no_address} QR codes have no address defined")
                
                # Check for impossible accuracy values
                extreme_accuracy = db.session.query(AttendanceData).filter(
                    db.or_(
                        AttendanceData.location_accuracy < 0,
                        AttendanceData.location_accuracy > 1000  # More than 1000 miles seems extreme
                    )
                ).count()
                
                if extreme_accuracy > 0:
                    issues.append(f"{extreme_accuracy} records have extreme location accuracy values")
                
                # Report results
                if issues:
                    print("⚠️  Data integrity issues found:")
                    for issue in issues:
                        print(f"   • {issue}")
                else:
                    print("✅ No data integrity issues found")
                
                return len(issues) == 0
                
            except Exception as e:
                print(f"❌ Error during verification: {e}")
                return False


def main():
    """Main entry point for utility commands"""
    if len(sys.argv) < 2:
        print("""
Usage: python location_accuracy_utils.py [command]

Commands:
    check-schema      Check database schema
    add-field         Add location_accuracy field
    stats             Show statistics
    export-report     Export CSV report
    verify-data       Verify data integrity
    help              Show this help
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    utils = LocationAccuracyUtils()
    
    if command == 'check-schema':
        utils.check_database_schema()
    elif command == 'add-field':
        utils.add_location_accuracy_field()
    elif command == 'stats':
        utils.show_location_accuracy_stats()
    elif command == 'export-report':
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        utils.export_location_accuracy_report(output_file)
    elif command == 'verify-data':
        utils.verify_data_integrity()
    elif command == 'help':
        print(__doc__)
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'help' to see available commands")
        sys.exit(1)


if __name__ == '__main__':
    main()