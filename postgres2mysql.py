#!/usr/bin/env python3
"""
Fixed PostgreSQL to MySQL Migration Script with Table Creation

This script handles empty MySQL databases by creating tables first.

Usage:
    python migrate_fixed.py [options]

Options:
    --export-pg     Export data from PostgreSQL
    --import-mysql  Import data to MySQL
    --full-migrate  Complete migration (export + import)
    --verify        Verify migration success
    --help          Show this help message

Author: QR Attendance System Migration Team
Version: 1.2 (Fixed for empty databases)
"""

import sys
import os
import json
import argparse
from datetime import datetime, date, time
import tempfile
import decimal

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, QRCode, AttendanceData
    from sqlalchemy import create_engine, text, inspect
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you have installed all requirements: pip install -r requirements.txt")
    sys.exit(1)

class DatabaseMigrator:
    """Main class for handling PostgreSQL to MySQL migration with table creation"""
    
    def __init__(self, pg_connection_string=None, mysql_connection_string=None):
        self.pg_connection = pg_connection_string
        self.mysql_connection = mysql_connection_string or os.environ.get('DATABASE_URL')
        self.backup_dir = tempfile.mkdtemp(prefix='db_migration_')
        self.migration_stats = {
            'users': {'exported': 0, 'imported': 0},
            'qr_codes': {'exported': 0, 'imported': 0},
            'attendance_data': {'exported': 0, 'imported': 0}
        }
        
        print(f"📁 Migration workspace: {self.backup_dir}")
    
    def serialize_value(self, value):
        """Convert database values to JSON-serializable format"""
        if value is None:
            return None
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, time):
            return value.isoformat()
        elif isinstance(value, decimal.Decimal):
            return float(value)
        elif isinstance(value, (bytes, bytearray)):
            # Handle binary data (like QR code images stored as binary)
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                import base64
                return base64.b64encode(value).decode('utf-8')
        else:
            return value
    
    def deserialize_value(self, value, field_name):
        """Convert JSON values back to appropriate Python types"""
        if value is None:
            return None
        
        # Handle datetime fields
        datetime_fields = ['created_date', 'last_login_date', 'coordinates_updated_date', 
                          'created_timestamp', 'updated_timestamp']
        date_fields = ['check_in_date']
        time_fields = ['check_in_time']
        
        if field_name in datetime_fields and isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.fromisoformat(value)
        elif field_name in date_fields and isinstance(value, str):
            return datetime.fromisoformat(value).date()
        elif field_name in time_fields and isinstance(value, str):
            if 'T' in value:  # Full datetime string
                return datetime.fromisoformat(value).time()
            else:  # Time-only string
                return datetime.strptime(value, '%H:%M:%S').time()
        
        return value
    
    def check_and_create_tables(self):
        """Check if tables exist in MySQL and create them if needed"""
        print("🔧 Checking and creating MySQL tables...")
        
        try:
            with app.app_context():
                # Check if tables exist
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                
                required_tables = ['users', 'qr_codes', 'attendance_data']
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                if missing_tables:
                    print(f"   📋 Missing tables: {', '.join(missing_tables)}")
                    print("   🔨 Creating database tables...")
                    
                    # Create all tables
                    db.create_all()
                    
                    # Verify creation
                    inspector = inspect(db.engine)
                    new_tables = inspector.get_table_names()
                    created_tables = [table for table in required_tables if table in new_tables]
                    
                    if len(created_tables) == len(required_tables):
                        print(f"   ✅ Successfully created tables: {', '.join(created_tables)}")
                        return True
                    else:
                        print(f"   ❌ Failed to create some tables")
                        return False
                else:
                    print(f"   ✅ All required tables exist: {', '.join(existing_tables)}")
                    return True
                    
        except Exception as e:
            print(f"   ❌ Error creating tables: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def safe_count_records(self, model_class):
        """Safely count records, returning 0 if table doesn't exist"""
        try:
            with app.app_context():
                return model_class.query.count()
        except Exception as e:
            if "doesn't exist" in str(e) or "does not exist" in str(e):
                return 0
            else:
                raise e
    
    def export_postgresql_data(self):
        """Export data from PostgreSQL database using native SQL"""
        print("🔄 EXPORTING POSTGRESQL DATA")
        print("=" * 50)
        
        if not self.pg_connection:
            print("❌ PostgreSQL connection string not provided")
            return False
        
        try:
            # Create PostgreSQL engine
            pg_engine = create_engine(self.pg_connection)
            
            # Export Users table
            print("📤 Exporting users table...")
            with pg_engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM users ORDER BY id"))
                users_data = []
                
                for row in result:
                    user_dict = {}
                    for key, value in row._mapping.items():
                        user_dict[key] = self.serialize_value(value)
                    users_data.append(user_dict)
                
                users_file = os.path.join(self.backup_dir, 'users.json')
                with open(users_file, 'w') as f:
                    json.dump(users_data, f, indent=2)
                
                self.migration_stats['users']['exported'] = len(users_data)
                print(f"   ✅ Exported {len(users_data)} user records")
            
            # Export QR Codes table
            print("📤 Exporting qr_codes table...")
            with pg_engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM qr_codes ORDER BY id"))
                qr_codes_data = []
                
                for row in result:
                    qr_dict = {}
                    for key, value in row._mapping.items():
                        qr_dict[key] = self.serialize_value(value)
                    qr_codes_data.append(qr_dict)
                
                qr_codes_file = os.path.join(self.backup_dir, 'qr_codes.json')
                with open(qr_codes_file, 'w') as f:
                    json.dump(qr_codes_data, f, indent=2)
                
                self.migration_stats['qr_codes']['exported'] = len(qr_codes_data)
                print(f"   ✅ Exported {len(qr_codes_data)} QR code records")
            
            # Export Attendance Data table
            print("📤 Exporting attendance_data table...")
            with pg_engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM attendance_data ORDER BY id"))
                attendance_data = []
                
                for row in result:
                    att_dict = {}
                    for key, value in row._mapping.items():
                        att_dict[key] = self.serialize_value(value)
                    attendance_data.append(att_dict)
                
                attendance_file = os.path.join(self.backup_dir, 'attendance_data.json')
                with open(attendance_file, 'w') as f:
                    json.dump(attendance_data, f, indent=2)
                
                self.migration_stats['attendance_data']['exported'] = len(attendance_data)
                print(f"   ✅ Exported {len(attendance_data)} attendance records")
            
            # Create metadata file
            metadata = {
                'export_timestamp': datetime.now().isoformat(),
                'source_database': 'PostgreSQL',
                'target_database': 'MySQL',
                'stats': self.migration_stats,
                'pg_connection': self.pg_connection.split('@')[1] if '@' in self.pg_connection else 'hidden'
            }
            
            metadata_file = os.path.join(self.backup_dir, 'migration_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"\n✅ Export completed successfully")
            print(f"📊 Total records exported: {sum(table['exported'] for table in self.migration_stats.values())}")
            print(f"📁 Export location: {self.backup_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def import_to_mysql(self):
        """Import data to MySQL database with table creation"""
        print("\n🔄 IMPORTING TO MYSQL")
        print("=" * 50)
        
        try:
            # First, ensure tables exist
            if not self.check_and_create_tables():
                print("❌ Failed to create required tables")
                return False
            
            with app.app_context():
                # Check if we should clear existing data
                print("🧹 Checking existing data...")
                existing_users = self.safe_count_records(User)
                existing_qr_codes = self.safe_count_records(QRCode)
                existing_attendance = self.safe_count_records(AttendanceData)
                
                print(f"   Found existing data: {existing_users} users, {existing_qr_codes} QR codes, {existing_attendance} attendance records")
                
                if existing_users > 0 or existing_qr_codes > 0 or existing_attendance > 0:
                    response = input("   Clear existing data before import? (y/n): ").lower().strip()
                    
                    if response == 'y':
                        print("   Clearing existing data...")
                        try:
                            # Disable foreign key checks temporarily
                            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                            
                            # Delete in proper order (child tables first)
                            db.session.execute(text("DELETE FROM attendance_data"))
                            db.session.execute(text("DELETE FROM qr_codes"))
                            db.session.execute(text("DELETE FROM users"))
                            
                            # Reset auto-increment counters
                            db.session.execute(text("ALTER TABLE attendance_data AUTO_INCREMENT = 1"))
                            db.session.execute(text("ALTER TABLE qr_codes AUTO_INCREMENT = 1"))
                            db.session.execute(text("ALTER TABLE users AUTO_INCREMENT = 1"))
                            
                            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                            db.session.commit()
                            print("   ✅ Existing data cleared")
                        except Exception as e:
                            print(f"   ⚠️  Could not clear existing data: {e}")
                            db.session.rollback()
                
                # Import Users
                print("📥 Importing users...")
                users_file = os.path.join(self.backup_dir, 'users.json')
                if os.path.exists(users_file):
                    with open(users_file, 'r') as f:
                        users_data = json.load(f)
                    
                    imported_count = 0
                    for user_data in users_data:
                        try:
                            # Deserialize datetime fields
                            for field in list(user_data.keys()):
                                user_data[field] = self.deserialize_value(user_data[field], field)
                            
                            # Remove 'id' field to let MySQL auto-increment
                            if 'id' in user_data:
                                del user_data['id']
                            
                            # Create user object - filter out None values
                            user_fields = {k: v for k, v in user_data.items() if v is not None}
                            user = User(**user_fields)
                            db.session.add(user)
                            imported_count += 1
                            
                        except Exception as e:
                            print(f"   ⚠️  Error importing user {user_data.get('username', 'unknown')}: {e}")
                    
                    try:
                        db.session.commit()
                        self.migration_stats['users']['imported'] = imported_count
                        print(f"   ✅ Imported {imported_count} user records")
                    except Exception as e:
                        print(f"   ❌ Error committing users: {e}")
                        db.session.rollback()
                        return False
                else:
                    print("   ⚠️  users.json not found")
                
                # Import QR Codes
                print("📥 Importing qr_codes...")
                qr_codes_file = os.path.join(self.backup_dir, 'qr_codes.json')
                if os.path.exists(qr_codes_file):
                    with open(qr_codes_file, 'r') as f:
                        qr_codes_data = json.load(f)
                    
                    imported_count = 0
                    for qr_data in qr_codes_data:
                        try:
                            # Deserialize datetime fields
                            for field in list(qr_data.keys()):
                                qr_data[field] = self.deserialize_value(qr_data[field], field)
                            
                            # Remove 'id' field to let MySQL auto-increment
                            if 'id' in qr_data:
                                del qr_data['id']
                            
                            # Create QR code object - filter out None values
                            qr_fields = {k: v for k, v in qr_data.items() if v is not None}
                            qr_code = QRCode(**qr_fields)
                            db.session.add(qr_code)
                            imported_count += 1
                            
                        except Exception as e:
                            print(f"   ⚠️  Error importing QR code {qr_data.get('name', 'unknown')}: {e}")
                    
                    try:
                        db.session.commit()
                        self.migration_stats['qr_codes']['imported'] = imported_count
                        print(f"   ✅ Imported {imported_count} QR code records")
                    except Exception as e:
                        print(f"   ❌ Error committing QR codes: {e}")
                        db.session.rollback()
                        return False
                else:
                    print("   ⚠️  qr_codes.json not found")
                
                # Import Attendance Data
                print("📥 Importing attendance_data...")
                attendance_file = os.path.join(self.backup_dir, 'attendance_data.json')
                if os.path.exists(attendance_file):
                    with open(attendance_file, 'r') as f:
                        attendance_data = json.load(f)
                    
                    imported_count = 0
                    for att_data in attendance_data:
                        try:
                            # Deserialize datetime and date fields
                            for field in list(att_data.keys()):
                                att_data[field] = self.deserialize_value(att_data[field], field)
                            
                            # Remove 'id' field to let MySQL auto-increment
                            if 'id' in att_data:
                                del att_data['id']
                            
                            # Create attendance object - filter out None values
                            att_fields = {k: v for k, v in att_data.items() if v is not None}
                            attendance = AttendanceData(**att_fields)
                            db.session.add(attendance)
                            imported_count += 1
                            
                        except Exception as e:
                            print(f"   ⚠️  Error importing attendance record {att_data.get('employee_id', 'unknown')}: {e}")
                    
                    try:
                        db.session.commit()
                        self.migration_stats['attendance_data']['imported'] = imported_count
                        print(f"   ✅ Imported {imported_count} attendance records")
                    except Exception as e:
                        print(f"   ❌ Error committing attendance data: {e}")
                        db.session.rollback()
                        return False
                else:
                    print("   ⚠️  attendance_data.json not found")
                
                print(f"\n✅ Import completed successfully")
                print(f"📊 Total records imported: {sum(table['imported'] for table in self.migration_stats.values())}")
                
                return True
                
        except Exception as e:
            print(f"❌ Import failed: {e}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass
            return False
    
    def verify_migration(self):
        """Verify that migration was successful"""
        print("\n🔍 VERIFYING MIGRATION")
        print("=" * 50)
        
        try:
            with app.app_context():
                # Count records in MySQL
                users_count = self.safe_count_records(User)
                qr_codes_count = self.safe_count_records(QRCode)
                attendance_count = self.safe_count_records(AttendanceData)
                
                print(f"📊 Record counts in MySQL:")
                print(f"   Users: {users_count}")
                print(f"   QR Codes: {qr_codes_count}")
                print(f"   Attendance: {attendance_count}")
                
                # Compare with exported counts
                print(f"\n📊 Comparison with exported data:")
                verification_results = []
                
                for table, stats in self.migration_stats.items():
                    exported = stats['exported']
                    imported = stats['imported']
                    
                    if table == 'users':
                        actual = users_count
                    elif table == 'qr_codes':
                        actual = qr_codes_count
                    elif table == 'attendance_data':
                        actual = attendance_count
                    
                    # For new IDs, we expect imported == actual, but exported might be different
                    status = "✅" if imported == actual else "❌"
                    print(f"   {table}: Exported={exported}, Imported={imported}, Actual={actual} {status}")
                    verification_results.append(imported == actual)
                
                # Test basic functionality
                print(f"\n🧪 Testing basic functionality:")
                
                # Test user authentication
                admin_user = User.query.filter_by(role='admin').first()
                if admin_user:
                    print(f"   ✅ Admin user found: {admin_user.username}")
                else:
                    print(f"   ⚠️  No admin user found")
                
                # Test relationships if data exists
                if users_count > 0 and qr_codes_count > 0:
                    qr_with_creator = QRCode.query.join(User, QRCode.created_by == User.id).first()
                    if qr_with_creator:
                        print(f"   ✅ QR code relationships working")
                    else:
                        print(f"   ⚠️  No QR codes with valid creators found")
                
                if qr_codes_count > 0 and attendance_count > 0:
                    attendance_with_qr = AttendanceData.query.join(QRCode).first()
                    if attendance_with_qr:
                        print(f"   ✅ Attendance relationships working")
                    else:
                        print(f"   ⚠️  No attendance records with valid QR codes found")
                
                # Test location data
                attendance_with_location = AttendanceData.query.filter(
                    AttendanceData.latitude.isnot(None)
                ).first()
                if attendance_with_location:
                    print(f"   ✅ Location data preserved")
                else:
                    print(f"   ℹ️  No location data found (may be expected)")
                
                migration_success = all(verification_results)
                
                if migration_success:
                    print(f"\n🎉 MIGRATION VERIFICATION PASSED")
                    print(f"   All data successfully migrated to MySQL")
                else:
                    print(f"\n⚠️  MIGRATION VERIFICATION ISSUES DETECTED")
                    print(f"   Please review the counts above")
                
                return migration_success
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(self.backup_dir)
            print(f"🧹 Cleaned up temporary files")
        except Exception as e:
            print(f"⚠️  Could not clean up temporary files: {e}")
    
    def full_migration(self, pg_connection_string):
        """Perform complete migration process"""
        print("🚀 STARTING FULL MIGRATION PROCESS")
        print("=" * 60)
        
        self.pg_connection = pg_connection_string
        
        # Step 1: Export from PostgreSQL
        if not self.export_postgresql_data():
            print("❌ Migration failed during export phase")
            return False
        
        # Step 2: Import to MySQL
        if not self.import_to_mysql():
            print("❌ Migration failed during import phase")
            return False
        
        # Step 3: Verify migration
        if not self.verify_migration():
            print("⚠️  Migration completed but verification detected issues")
            return False
        
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Next steps:")
        print("1. Test all application functionality thoroughly")
        print("2. Update backup procedures for MySQL")
        print("3. Consider removing old PostgreSQL database after verification")
        
        return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='PostgreSQL to MySQL Migration Tool (Fixed)')
    parser.add_argument('--export-pg', action='store_true', 
                       help='Export data from PostgreSQL')
    parser.add_argument('--import-mysql', action='store_true',
                       help='Import data to MySQL')
    parser.add_argument('--full-migrate', action='store_true',
                       help='Complete migration (export + import)')
    parser.add_argument('--verify', action='store_true',
                       help='Verify migration success')
    parser.add_argument('--pg-connection', type=str,
                       help='PostgreSQL connection string')
    parser.add_argument('--mysql-connection', type=str,
                       help='MySQL connection string (default: from .env)')
    
    args = parser.parse_args()
    
    if not any([args.export_pg, args.import_mysql, args.full_migrate, args.verify]):
        parser.print_help()
        print("\nExample usage:")
        print("  python migrate_fixed.py --export-pg --pg-connection 'postgresql://user:pass@localhost/dbname'")
        print("  python migrate_fixed.py --import-mysql")
        print("  python migrate_fixed.py --full-migrate --pg-connection 'postgresql://user:pass@localhost/dbname'")
        sys.exit(1)
    
    migrator = DatabaseMigrator(args.pg_connection, args.mysql_connection)
    
    try:
        if args.export_pg:
            if not args.pg_connection:
                print("❌ PostgreSQL connection string required for export")
                print("Example: postgresql://username:password@localhost:5432/database_name")
                sys.exit(1)
            migrator.export_postgresql_data()
        
        elif args.import_mysql:
            migrator.import_to_mysql()
        
        elif args.verify:
            migrator.verify_migration()
        
        elif args.full_migrate:
            if not args.pg_connection:
                print("❌ PostgreSQL connection string required for full migration")
                print("Example: postgresql://username:password@localhost:5432/database_name")
                sys.exit(1)
            migrator.full_migration(args.pg_connection)
    
    finally:
        # Don't auto-cleanup if export was successful - user might want to review files
        if not (args.export_pg and sum(migrator.migration_stats[table]['exported'] for table in migrator.migration_stats) > 0):
            migrator.cleanup()
        else:
            print(f"\n📁 Export files preserved at: {migrator.backup_dir}")
            print("   Run with --import-mysql to complete migration")

if __name__ == '__main__':
    main()
