#!/usr/bin/env python3
"""
Location Data Migration Script
Run this FIRST to add location columns to your existing database
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres1411@localhost/qr_management')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

def add_location_columns():
    """Add location tracking columns to attendance_data table"""
    print("🚀 Adding location tracking capabilities to your QR system...")
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'attendance_data'
                );
            """))
            
            if not result.fetchone()[0]:
                print("❌ attendance_data table not found. Please set up your QR system first.")
                return False
            
            print("✅ Found attendance_data table")
            
            # Add location columns with IF NOT EXISTS for safety
            location_columns = [
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS latitude FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS longitude FLOAT", 
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS accuracy FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS altitude FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS location_source VARCHAR(50) DEFAULT 'manual'",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS address VARCHAR(500)"
            ]
            
            print("\n📝 Adding location columns...")
            for sql_command in location_columns:
                try:
                    db.session.execute(text(sql_command))
                    column_name = sql_command.split()[4]
                    print(f"   ✅ Added: {column_name}")
                except Exception as e:
                    print(f"   ⚠️  Column may already exist: {e}")
            
            db.session.commit()
            
            # Verify columns were added
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'attendance_data' 
                AND column_name IN ('latitude', 'longitude', 'accuracy', 
                                   'altitude', 'location_source', 'address')
                ORDER BY column_name;
            """))
            
            added_columns = [row[0] for row in result.fetchall()]
            print(f"\n✅ Migration completed! Added {len(added_columns)} location columns:")
            print(f"   📝 Columns: {', '.join(added_columns)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_location_columns()
    if success:
        print("\n🎉 Database migration successful!")
        print("   Now you can update your app.py with the enhanced AttendanceData model")
    else:
        print("❌ Migration failed. Please check your database connection and try again.")
        sys.exit(1)