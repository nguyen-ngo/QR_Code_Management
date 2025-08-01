#!/usr/bin/env python3
"""
Simple Database Migration for Geolocation
Run this script FIRST before updating your app.py
"""

import psycopg2
import os
import sys

# Database connection (adjust if needed)
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres1411@localhost/qr_management')

def add_location_columns():
    """Add location columns to attendance_data table"""
    
    print("🚀 Adding location tracking columns to your database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Check if attendance_data table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'attendance_data'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("❌ attendance_data table not found!")
            print("   Make sure your QR system is set up first")
            return False
        
        print("✅ attendance_data table found")
        
        # Add location columns (using IF NOT EXISTS for safety)
        location_columns = [
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS latitude FLOAT",
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS longitude FLOAT", 
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS accuracy FLOAT",
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS altitude FLOAT",
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS location_source VARCHAR(50) DEFAULT 'manual'",
            "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS address VARCHAR(255)"
        ]
        
        print("\n📝 Adding columns...")
        for sql in location_columns:
            try:
                cursor.execute(sql)
                column_name = sql.split()[4]  # Extract column name
                print(f"   ✅ Added: {column_name}")
            except Exception as e:
                print(f"   ⚠️  Column may already exist: {e}")
        
        # Commit changes
        conn.commit()
        
        # Verify columns were added
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'attendance_data' 
            AND column_name IN ('latitude', 'longitude', 'accuracy', 
                               'altitude', 'location_source', 'address')
            ORDER BY column_name;
        """)
        
        added_columns = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Verification:")
        print(f"   ✅ Location columns found: {len(added_columns)}")
        if added_columns:
            print(f"   📝 Columns: {', '.join(added_columns)}")
        
        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM attendance_data")
        total_records = cursor.fetchone()[0]
        print(f"   📊 Total attendance records: {total_records}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database migration completed successfully!")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"   Check your DATABASE_URL: {DATABASE_URL}")
        return False

if __name__ == "__main__":
    print("📍 QR Code System - Geolocation Migration")
    print("=" * 50)
    
    # Test connection first
    if not test_connection():
        print("\n❌ Cannot connect to database. Please check:")
        print("1. PostgreSQL is running")
        print("2. Database credentials are correct")
        print("3. Database exists")
        sys.exit(1)
    
    # Run migration
    success = add_location_columns()
    
    if success:
        print("\n✅ Ready for geolocation integration!")
        print("\nNext steps:")
        print("1. Replace your qr_destination.html template")
        print("2. Replace your qr_destination.js file") 
        print("3. Update your qr_checkin route in app.py")
        print("4. Restart your Flask application")
        print("5. Test geolocation on a mobile device")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        print("\nYou can also add the columns manually:")
        print("ALTER TABLE attendance_data ADD COLUMN latitude FLOAT;")
        print("ALTER TABLE attendance_data ADD COLUMN longitude FLOAT;")
        print("ALTER TABLE attendance_data ADD COLUMN accuracy FLOAT;")
        print("ALTER TABLE attendance_data ADD COLUMN altitude FLOAT;")
        print("ALTER TABLE attendance_data ADD COLUMN location_source VARCHAR(50) DEFAULT 'manual';")
        print("ALTER TABLE attendance_data ADD COLUMN address VARCHAR(255);")
    
    print("\n" + "=" * 50)