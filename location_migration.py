#!/usr/bin/env python3
"""
Location Database Migration
Adds location columns to attendance_data table
"""

import psycopg2
import os
import sys

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres1411@localhost/qr_management')

def add_location_columns():
    """Add location tracking columns to attendance_data table"""
    
    print("🚀 Adding location columns to attendance_data table...")
    
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
            print("   Make sure your QR system is running first")
            return False
        
        print("✅ attendance_data table found")
        
        # Add location columns one by one with error handling
        location_columns = [
            {
                'name': 'latitude',
                'sql': 'ALTER TABLE attendance_data ADD COLUMN latitude DOUBLE PRECISION',
                'description': 'GPS latitude coordinate'
            },
            {
                'name': 'longitude', 
                'sql': 'ALTER TABLE attendance_data ADD COLUMN longitude DOUBLE PRECISION',
                'description': 'GPS longitude coordinate'
            },
            {
                'name': 'location_accuracy',
                'sql': 'ALTER TABLE attendance_data ADD COLUMN location_accuracy DOUBLE PRECISION',
                'description': 'GPS accuracy in meters'
            },
            {
                'name': 'address',
                'sql': 'ALTER TABLE attendance_data ADD COLUMN address VARCHAR(500)',
                'description': 'Resolved address from coordinates'
            },
            {
                'name': 'location_source',
                'sql': "ALTER TABLE attendance_data ADD COLUMN location_source VARCHAR(50) DEFAULT 'manual'",
                'description': 'Source of location data (gps, network, manual)'
            },
            {
                'name': 'location_timestamp',
                'sql': 'ALTER TABLE attendance_data ADD COLUMN location_timestamp TIMESTAMP',
                'description': 'When location was captured'
            }
        ]
        
        added_columns = []
        skipped_columns = []
        
        for column in location_columns:
            try:
                # Check if column already exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'attendance_data' 
                        AND column_name = %s
                    );
                """, (column['name'],))
                
                if cursor.fetchone()[0]:
                    print(f"   ⏭️  Column '{column['name']}' already exists")
                    skipped_columns.append(column['name'])
                    continue
                
                # Add the column
                cursor.execute(column['sql'])
                added_columns.append(column['name'])
                print(f"   ✅ Added '{column['name']}' - {column['description']}")
                
            except Exception as e:
                print(f"   ❌ Error adding '{column['name']}': {e}")
        
        # Commit all changes
        conn.commit()
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Added columns: {len(added_columns)}")
        print(f"   ⏭️  Skipped columns: {len(skipped_columns)}")
        
        if added_columns:
            print(f"   📝 New columns: {', '.join(added_columns)}")
        
        if skipped_columns:
            print(f"   📝 Existing columns: {', '.join(skipped_columns)}")
        
        # Verify the columns were added
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'attendance_data' 
            AND column_name IN ('latitude', 'longitude', 'location_accuracy', 
                               'address', 'location_source', 'location_timestamp')
            ORDER BY column_name;
        """)
        
        columns_info = cursor.fetchall()
        
        print(f"\n📋 Location columns in database:")
        for col_name, col_type in columns_info:
            print(f"   • {col_name}: {col_type}")
        
        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM attendance_data")
        total_records = cursor.fetchone()[0]
        print(f"\n📊 Total attendance records: {total_records}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Location columns added successfully!")
        print("\nNext step: Update your app.py to save location data")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def verify_columns():
    """Verify location columns exist and show sample data"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check columns exist
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'attendance_data' 
            AND column_name IN ('latitude', 'longitude', 'location_accuracy', 
                               'address', 'location_source', 'location_timestamp')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        
        print(f"\n🔍 Verification Results:")
        print(f"   Found {len(columns)} location columns:")
        
        for col_name, col_type, nullable in columns:
            null_text = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"   • {col_name}: {col_type} ({null_text})")
        
        # Show sample with location data if any exists
        cursor.execute("""
            SELECT employee_id, latitude, longitude, location_accuracy, 
                   address, location_source, created_timestamp
            FROM attendance_data 
            WHERE latitude IS NOT NULL 
            ORDER BY created_timestamp DESC 
            LIMIT 3;
        """)
        
        location_records = cursor.fetchall()
        
        if location_records:
            print(f"\n📍 Sample records with location data:")
            for record in location_records:
                emp_id, lat, lng, acc, addr, source, timestamp = record
                print(f"   • {emp_id}: {lat:.6f}, {lng:.6f} (±{acc}m) - {source}")
                if addr:
                    print(f"     Address: {addr}")
        else:
            print(f"\n📍 No location data found yet (will be captured on next check-ins)")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful")
        print(f"   PostgreSQL version: {version.split()[1]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("📍 QR Code System - Location Database Migration")
    print("=" * 60)
    
    # Test connection first
    if not test_connection():
        print("\n❌ Cannot connect to database. Please check:")
        print("1. PostgreSQL is running")
        print("2. Database credentials are correct") 
        print("3. Database 'qr_management' exists")
        sys.exit(1)
    
    # Run migration
    success = add_location_columns()
    
    if success:
        # Verify columns were added
        verify_columns()
        
        print("\n✅ Database migration completed!")
        print("\n📋 Next steps:")
        print("1. Update your app.py with the location-saving code")
        print("2. Restart your Flask application")
        print("3. Test check-in with location data")
        print("4. Check database for saved location records")
    else:
        print("\n❌ Migration failed!")
        print("\nManual SQL commands (if needed):")
        print("ALTER TABLE attendance_data ADD COLUMN latitude DOUBLE PRECISION;")
        print("ALTER TABLE attendance_data ADD COLUMN longitude DOUBLE PRECISION;")
        print("ALTER TABLE attendance_data ADD COLUMN location_accuracy DOUBLE PRECISION;")
        print("ALTER TABLE attendance_data ADD COLUMN address VARCHAR(500);")
        print("ALTER TABLE attendance_data ADD COLUMN location_source VARCHAR(50) DEFAULT 'manual';")
        print("ALTER TABLE attendance_data ADD COLUMN location_timestamp TIMESTAMP;")
    
    print("\n" + "=" * 60)