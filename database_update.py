#!/usr/bin/env python3
"""
Database Update Script for QR Code Management System
Adds attendance tracking functionality to existing database
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def create_app():
    """Create Flask application for database updates"""
    app = Flask(__name__)
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres1411@localhost/qr_management')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'update-key-change-in-production'
    
    return app

def add_attendance_table():
    """Add attendance_data table to existing database"""
    
    print("🔄 Adding attendance tracking functionality...")
    print("=" * 60)
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Create attendance_data table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS attendance_data (
                id SERIAL PRIMARY KEY,
                qr_code_id INTEGER NOT NULL REFERENCES qr_codes(id) ON DELETE CASCADE,
                employee_id VARCHAR(50) NOT NULL,
                check_in_date DATE NOT NULL,
                check_in_time TIME NOT NULL,
                device_info VARCHAR(200),
                user_agent TEXT,
                ip_address VARCHAR(45),
                location_name VARCHAR(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'present',
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            db.session.execute(text(create_table_sql))
            print("✅ Created attendance_data table")
            
            # Create indexes for better performance
            indexes_sql = [
                "CREATE INDEX IF NOT EXISTS idx_attendance_qr_code ON attendance_data(qr_code_id);",
                "CREATE INDEX IF NOT EXISTS idx_attendance_employee ON attendance_data(employee_id);",
                "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_data(check_in_date);",
                "CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance_data(created_timestamp);"
            ]
            
            for index_sql in indexes_sql:
                db.session.execute(text(index_sql))
            
            print("✅ Created database indexes")
            
            # Add QR code URL field to qr_codes table if it doesn't exist
            add_url_field_sql = """
            ALTER TABLE qr_codes 
            ADD COLUMN IF NOT EXISTS qr_url VARCHAR(255) UNIQUE;
            """
            
            db.session.execute(text(add_url_field_sql))
            print("✅ Added qr_url field to qr_codes table")
            
            # Update existing QR codes with unique URLs
            update_urls_sql = """
            UPDATE qr_codes 
            SET qr_url = CONCAT('qr-', id, '-', LOWER(REPLACE(REPLACE(name, ' ', '-'), '''', '')))
            WHERE qr_url IS NULL;
            """
            
            db.session.execute(text(update_urls_sql))
            print("✅ Generated URLs for existing QR codes")
            
            # Create a view for attendance reporting
            create_view_sql = """
            CREATE OR REPLACE VIEW attendance_report AS
            SELECT 
                ad.id,
                ad.employee_id,
                ad.check_in_date,
                ad.check_in_time,
                ad.device_info,
                ad.location_name,
                ad.status,
                ad.created_timestamp,
                qc.name as qr_code_name,
                qc.location as qr_location,
                qc.location_event,
                qc.location_address,
                u.full_name as qr_creator_name
            FROM attendance_data ad
            JOIN qr_codes qc ON ad.qr_code_id = qc.id
            JOIN users u ON qc.created_by = u.id
            ORDER BY ad.created_timestamp DESC;
            """
            
            db.session.execute(text(create_view_sql))
            print("✅ Created attendance_report view")
            
            # Commit all changes
            db.session.commit()
            
            print("\n🎉 Database update completed successfully!")
            print("\n📋 Changes Summary:")
            print("   - Added attendance_data table")
            print("   - Created performance indexes")
            print("   - Added qr_url field to qr_codes")
            print("   - Generated URLs for existing QR codes")
            print("   - Created attendance_report view")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during database update: {str(e)}")
            print("\n🔧 Troubleshooting tips:")
            print("   1. Ensure PostgreSQL is running")
            print("   2. Check database connection string")
            print("   3. Verify database user has CREATE permissions")
            sys.exit(1)

def create_sample_attendance():
    """Create sample attendance data for testing"""
    
    print("\n📦 Creating sample attendance data...")
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Get existing QR codes
            qr_codes_result = db.session.execute(text("SELECT id, name FROM qr_codes WHERE active_status = true LIMIT 3"))
            qr_codes = qr_codes_result.fetchall()
            
            if not qr_codes:
                print("   ⚠️  No active QR codes found, skipping sample data creation")
                return
            
            # Sample attendance data
            sample_data = [
                {
                    'employee_id': 'EMP001',
                    'device_info': 'iPhone 14 Pro - iOS 16.5',
                    'status': 'present'
                },
                {
                    'employee_id': 'EMP002', 
                    'device_info': 'Samsung Galaxy S23 - Android 13',
                    'status': 'present'
                },
                {
                    'employee_id': 'EMP003',
                    'device_info': 'iPad Air - iOS 16.5',
                    'status': 'present'
                }
            ]
            
            for i, qr_code in enumerate(qr_codes):
                if i < len(sample_data):
                    sample = sample_data[i]
                    
                    insert_sql = """
                    INSERT INTO attendance_data 
                    (qr_code_id, employee_id, check_in_date, check_in_time, device_info, location_name, status)
                    VALUES (:qr_id, :emp_id, CURRENT_DATE, CURRENT_TIME, :device, :location, :status)
                    """
                    
                    db.session.execute(text(insert_sql), {
                        'qr_id': qr_code[0],
                        'emp_id': sample['employee_id'],
                        'device': sample['device_info'],
                        'location': qr_code[1],
                        'status': sample['status']
                    })
            
            db.session.commit()
            print(f"   ✅ Created {len(sample_data)} sample attendance records")
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Failed to create sample data: {str(e)}")

def verify_database():
    """Verify database changes were applied correctly"""
    
    print("\n🔍 Verifying database changes...")
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if attendance_data table exists
            table_check = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'attendance_data'
                );
            """))
            
            if table_check.fetchone()[0]:
                print("   ✅ attendance_data table exists")
                
                # Count records
                count_result = db.session.execute(text("SELECT COUNT(*) FROM attendance_data"))
                record_count = count_result.fetchone()[0]
                print(f"   📊 Found {record_count} attendance records")
            else:
                print("   ❌ attendance_data table not found")
                return False
            
            # Check if qr_url field was added
            field_check = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'qr_codes' AND column_name = 'qr_url'
                );
            """))
            
            if field_check.fetchone()[0]:
                print("   ✅ qr_url field added to qr_codes table")
                
                # Check how many QR codes have URLs
                url_count = db.session.execute(text("SELECT COUNT(*) FROM qr_codes WHERE qr_url IS NOT NULL"))
                url_records = url_count.fetchone()[0]
                print(f"   📊 {url_records} QR codes have generated URLs")
            else:
                print("   ❌ qr_url field not found in qr_codes table")
                return False
            
            # Check if view exists
            view_check = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = 'attendance_report'
                );
            """))
            
            if view_check.fetchone()[0]:
                print("   ✅ attendance_report view created")
            else:
                print("   ❌ attendance_report view not found")
                return False
            
            print("\n✅ All database changes verified successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Verification failed: {str(e)}")
            return False

def rollback_changes():
    """Rollback database changes if needed"""
    
    print("\n⚠️  WARNING: This will remove all attendance tracking functionality!")
    confirm = input("Are you sure you want to rollback? Type 'ROLLBACK' to confirm: ")
    
    if confirm != 'ROLLBACK':
        print("❌ Rollback cancelled")
        return
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Drop view
            db.session.execute(text("DROP VIEW IF EXISTS attendance_report"))
            print("   ✅ Dropped attendance_report view")
            
            # Drop table
            db.session.execute(text("DROP TABLE IF EXISTS attendance_data"))
            print("   ✅ Dropped attendance_data table")
            
            # Remove qr_url column
            db.session.execute(text("ALTER TABLE qr_codes DROP COLUMN IF EXISTS qr_url"))
            print("   ✅ Removed qr_url column")
            
            db.session.commit()
            print("\n✅ Rollback completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during rollback: {str(e)}")

def main():
    """Main script entry point"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'update':
            add_attendance_table()
            
            # Ask if user wants sample data
            create_sample = input("\n❓ Would you like to create sample attendance data? (y/N): ").lower().strip()
            if create_sample in ['y', 'yes']:
                create_sample_attendance()
                
            verify_database()
            
        elif command == 'verify':
            verify_database()
            
        elif command == 'rollback':
            rollback_changes()
            
        elif command == 'sample':
            create_sample_attendance()
            
        else:
            print("❌ Unknown command. Available commands:")
            print("   update   - Add attendance tracking to database")
            print("   verify   - Verify database changes")
            print("   rollback - Remove attendance tracking (DANGEROUS)")
            print("   sample   - Create sample attendance data")
    else:
        # Default action is update
        add_attendance_table()
        verify_database()

if __name__ == '__main__':
    main()