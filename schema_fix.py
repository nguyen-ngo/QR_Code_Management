#!/usr/bin/env python3
"""
Database Schema Fix Script

This script fixes the password_hash column length issue and other potential
schema mismatches between PostgreSQL and MySQL.

Usage:
    python fix_schema.py
"""

import sys
import os

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db
    from sqlalchemy import text, inspect
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def fix_mysql_schema():
    """Fix MySQL schema to accommodate PostgreSQL data types"""
    print("🔧 FIXING MYSQL SCHEMA")
    print("=" * 50)
    
    try:
        with app.app_context():
            # Check current schema
            inspector = inspect(db.engine)
            
            # Fix users table
            print("📋 Checking users table schema...")
            users_columns = inspector.get_columns('users')
            
            schema_fixes = []
            
            # Check password_hash column length
            password_hash_col = next((col for col in users_columns if col['name'] == 'password_hash'), None)
            if password_hash_col:
                # Check if it's too small (PostgreSQL scrypt hashes can be 200+ characters)
                if password_hash_col['type'].length and password_hash_col['type'].length < 255:
                    schema_fixes.append("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255)")
                    print(f"   ⚠️  password_hash column too small ({password_hash_col['type'].length} chars)")
                else:
                    print(f"   ✅ password_hash column size OK")
            
            # Check for other potential issues
            qr_codes_columns = inspector.get_columns('qr_codes')
            
            # Check qr_code_image column (base64 images can be very long)
            qr_image_col = next((col for col in qr_codes_columns if col['name'] == 'qr_code_image'), None)
            if qr_image_col:
                # QR code images should be TEXT or LONGTEXT, not VARCHAR
                if hasattr(qr_image_col['type'], 'length') and qr_image_col['type'].length:
                    schema_fixes.append("ALTER TABLE qr_codes MODIFY COLUMN qr_code_image LONGTEXT")
                    print(f"   ⚠️  qr_code_image should be LONGTEXT")
                else:
                    print(f"   ✅ qr_code_image column type OK")
            
            # Check location_address column
            location_addr_col = next((col for col in qr_codes_columns if col['name'] == 'location_address'), None)
            if location_addr_col:
                if hasattr(location_addr_col['type'], 'length') and location_addr_col['type'].length and location_addr_col['type'].length < 500:
                    schema_fixes.append("ALTER TABLE qr_codes MODIFY COLUMN location_address TEXT")
                    print(f"   ⚠️  location_address column too small")
                else:
                    print(f"   ✅ location_address column size OK")
            
            # Check attendance_data table
            print("📋 Checking attendance_data table schema...")
            attendance_columns = inspector.get_columns('attendance_data')
            
            # Check address column
            address_col = next((col for col in attendance_columns if col['name'] == 'address'), None)
            if address_col:
                if hasattr(address_col['type'], 'length') and address_col['type'].length and address_col['type'].length < 500:
                    schema_fixes.append("ALTER TABLE attendance_data MODIFY COLUMN address VARCHAR(500)")
                    print(f"   ⚠️  address column too small")
                else:
                    print(f"   ✅ address column size OK")
            
            # Check user_agent column (can be very long)
            user_agent_col = next((col for col in attendance_columns if col['name'] == 'user_agent'), None)
            if user_agent_col:
                if hasattr(user_agent_col['type'], 'length') and user_agent_col['type'].length:
                    schema_fixes.append("ALTER TABLE attendance_data MODIFY COLUMN user_agent TEXT")
                    print(f"   ⚠️  user_agent should be TEXT")
                else:
                    print(f"   ✅ user_agent column type OK")
            
            # Apply fixes
            if schema_fixes:
                print(f"\n🔨 Applying {len(schema_fixes)} schema fixes...")
                for i, fix in enumerate(schema_fixes, 1):
                    try:
                        print(f"   {i}. {fix}")
                        db.session.execute(text(fix))
                        print(f"      ✅ Applied successfully")
                    except Exception as e:
                        print(f"      ❌ Failed: {e}")
                        db.session.rollback()
                        return False
                
                db.session.commit()
                print(f"\n✅ All schema fixes applied successfully!")
                return True
            else:
                print(f"\n✅ No schema fixes needed - schema looks good!")
                return True
                
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_current_schema():
    """Show current MySQL schema for debugging"""
    print("\n📋 CURRENT MYSQL SCHEMA")
    print("=" * 30)
    
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            
            tables = ['users', 'qr_codes', 'attendance_data']
            
            for table in tables:
                if table in inspector.get_table_names():
                    print(f"\n📊 {table} table:")
                    columns = inspector.get_columns(table)
                    
                    for col in columns:
                        col_type = str(col['type'])
                        nullable = "NULL" if col['nullable'] else "NOT NULL"
                        default = f" DEFAULT {col['default']}" if col['default'] else ""
                        print(f"   {col['name']:<20} {col_type:<20} {nullable}{default}")
                else:
                    print(f"\n❌ {table} table not found")
                    
    except Exception as e:
        print(f"❌ Error showing schema: {e}")

def test_data_compatibility():
    """Test if sample data would fit in current schema"""
    print("\n🧪 TESTING DATA COMPATIBILITY")
    print("=" * 35)
    
    # Test password hash length
    sample_password_hash = "scrypt:32768:8:1$GMnEGe3K4utb6mNW$3472a6003b60b095d4a9cbb201fe85e662a4d03b7162cf0c5ca896112f04b8f04c202311002ec17d56ef3ad15b232175762ad80be289cb83d546095ddfe14c77"
    print(f"📏 Sample password hash length: {len(sample_password_hash)} characters")
    
    # Test QR code image (typical base64 image)
    sample_qr_image = "iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAYAAAB5fY51" + "A" * 2000  # Simulate base64 image
    print(f"📏 Sample QR image length: {len(sample_qr_image)} characters")
    
    # Test user agent string
    sample_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    print(f"📏 Sample user agent length: {len(sample_user_agent)} characters")
    
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            
            # Check users table
            users_columns = inspector.get_columns('users')
            password_col = next((col for col in users_columns if col['name'] == 'password_hash'), None)
            
            if password_col and hasattr(password_col['type'], 'length') and password_col['type'].length:
                if len(sample_password_hash) > password_col['type'].length:
                    print(f"❌ Password hash won't fit (needs {len(sample_password_hash)}, has {password_col['type'].length})")
                else:
                    print(f"✅ Password hash will fit")
            else:
                print(f"✅ Password hash column is TEXT/unlimited")
                
    except Exception as e:
        print(f"❌ Error testing compatibility: {e}")

def main():
    """Main function"""
    print("MYSQL SCHEMA FIX UTILITY")
    print("=" * 60)
    
    # Show current schema
    show_current_schema()
    
    # Test compatibility
    test_data_compatibility()
    
    # Ask user if they want to apply fixes
    print(f"\n" + "="*60)
    response = input("Apply schema fixes? (y/n): ").lower().strip()
    
    if response == 'y':
        success = fix_mysql_schema()
        
        if success:
            print(f"\n🎉 Schema fixes completed!")
            print(f"💡 You can now run the migration script again:")
            print(f"   python migrate_fixed.py --import-mysql")
        else:
            print(f"\n❌ Schema fixes failed. Check the errors above.")
    else:
        print(f"\n📋 Schema fixes skipped.")
        print(f"💡 To manually fix the password_hash issue, run:")
        print(f"   ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255);")

if __name__ == '__main__':
    main()
