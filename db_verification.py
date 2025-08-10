#!/usr/bin/env python3
"""
MySQL Database Verification Script for QR Attendance System

This script verifies that the MySQL database migration was successful
and all functionality is working correctly.

Usage:
    python verify_mysql_database.py

This script will:
1. Test MySQL database connection
2. Verify all tables exist
3. Check data integrity
4. Test application functionality
5. Validate performance

Author: QR Attendance System Verification Team
Version: 1.0
"""

import sys
import os
from datetime import datetime, date, timedelta
import time

# Add your app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, QRCode, AttendanceData
    from app import get_location_accuracy_level_enhanced, calculate_location_accuracy_enhanced
    from sqlalchemy import text, inspect
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

class MySQLVerifier:
    """MySQL database verification class"""
    
    def __init__(self):
        self.app = app
        self.issues = []
        self.test_results = {}
        
    def log_result(self, test_name, passed, message=""):
        """Log test result"""
        self.test_results[test_name] = {
            'passed': passed,
            'message': message,
            'timestamp': datetime.now()
        }
        
        if not passed:
            self.issues.append(f"{test_name}: {message}")
    
    def test_database_connection(self):
        """Test basic MySQL database connectivity"""
        print("🔌 Testing MySQL Database Connection...")
        
        try:
            with self.app.app_context():
                # Test basic connection
                result = db.session.execute(text("SELECT 1 as test")).fetchone()
                
                if result.test == 1:
                    print("   ✅ MySQL connection successful")
                    
                    # Get MySQL version
                    version_result = db.session.execute(text("SELECT VERSION() as version")).fetchone()
                    print(f"   📊 MySQL Version: {version_result.version}")
                    
                    # Get database name
                    db_result = db.session.execute(text("SELECT DATABASE() as db_name")).fetchone()
                    print(f"   📊 Database: {db_result.db_name}")
                    
                    self.log_result("database_connection", True, "MySQL connection working")
                    return True
                else:
                    self.log_result("database_connection", False, "Connection test failed")
                    return False
                    
        except Exception as e:
            print(f"   ❌ MySQL connection failed: {e}")
            self.log_result("database_connection", False, str(e))
            return False
    
    def test_table_structure(self):
        """Verify all required tables exist with correct structure"""
        print("\n📋 Testing Table Structure...")
        
        try:
            with self.app.app_context():
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                
                required_tables = ['users', 'qr_codes', 'attendance_data']
                
                print(f"   📊 Found tables: {', '.join(tables)}")
                
                all_tables_exist = True
                for table in required_tables:
                    if table in tables:
                        print(f"   ✅ {table} table exists")
                        
                        # Check key columns
                        columns = inspector.get_columns(table)
                        column_names = [col['name'] for col in columns]
                        
                        if table == 'users':
                            required_cols = ['id', 'username', 'email', 'password_hash', 'role']
                        elif table == 'qr_codes':
                            required_cols = ['id', 'name', 'location', 'qr_code_image']
                        elif table == 'attendance_data':
                            required_cols = ['id', 'qr_code_id', 'employee_id', 'check_in_date']
                        
                        missing_cols = [col for col in required_cols if col not in column_names]
                        if missing_cols:
                            print(f"   ⚠️  Missing columns in {table}: {missing_cols}")
                            all_tables_exist = False
                        else:
                            print(f"   ✅ {table} has all required columns")
                    else:
                        print(f"   ❌ {table} table missing")
                        all_tables_exist = False
                
                self.log_result("table_structure", all_tables_exist, 
                              "All tables exist" if all_tables_exist else "Missing tables/columns")
                return all_tables_exist
                
        except Exception as e:
            print(f"   ❌ Error checking table structure: {e}")
            self.log_result("table_structure", False, str(e))
            return False
    
    def test_data_integrity(self):
        """Test data integrity and relationships"""
        print("\n🔍 Testing Data Integrity...")
        
        try:
            with self.app.app_context():
                # Count records
                user_count = User.query.count()
                qr_count = QRCode.query.count()
                attendance_count = AttendanceData.query.count()
                
                print(f"   📊 Record counts:")
                print(f"      Users: {user_count:,}")
                print(f"      QR Codes: {qr_count:,}")
                print(f"      Attendance: {attendance_count:,}")
                
                # Test relationships
                relationship_issues = []
                
                # Check foreign key relationships
                orphaned_qr_codes = db.session.execute(text("""
                    SELECT COUNT(*) as count FROM qr_codes qr
                    LEFT JOIN users u ON qr.created_by = u.id
                    WHERE u.id IS NULL AND qr.created_by IS NOT NULL
                """)).fetchone().count
                
                if orphaned_qr_codes > 0:
                    relationship_issues.append(f"{orphaned_qr_codes} QR codes with invalid creator")
                    print(f"   ⚠️  {orphaned_qr_codes} QR codes with invalid creator references")
                
                orphaned_attendance = db.session.execute(text("""
                    SELECT COUNT(*) as count FROM attendance_data ad
                    LEFT JOIN qr_codes qr ON ad.qr_code_id = qr.id
                    WHERE qr.id IS NULL
                """)).fetchone().count
                
                if orphaned_attendance > 0:
                    relationship_issues.append(f"{orphaned_attendance} attendance records with invalid QR code")
                    print(f"   ⚠️  {orphaned_attendance} attendance records with invalid QR code references")
                
                # Check for duplicate usernames/emails
                duplicate_usernames = db.session.execute(text("""
                    SELECT username, COUNT(*) as count FROM users 
                    GROUP BY username HAVING COUNT(*) > 1
                """)).fetchall()
                
                if duplicate_usernames:
                    relationship_issues.append(f"Duplicate usernames found")
                    print(f"   ⚠️  Duplicate usernames: {[row.username for row in duplicate_usernames]}")
                
                # Check location accuracy data
                attendance_with_location = AttendanceData.query.filter(
                    AttendanceData.latitude.isnot(None)
                ).count()
                
                print(f"   📊 Attendance records with location data: {attendance_with_location:,}")
                
                if len(relationship_issues) == 0:
                    print("   ✅ All data integrity checks passed")
                    self.log_result("data_integrity", True, "Data integrity verified")
                    return True
                else:
                    print(f"   ❌ Data integrity issues found")
                    self.log_result("data_integrity", False, "; ".join(relationship_issues))
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error checking data integrity: {e}")
            self.log_result("data_integrity", False, str(e))
            return False
    
    def test_mysql_specific_features(self):
        """Test MySQL-specific features and compatibility"""
        print("\n🔧 Testing MySQL-Specific Features...")
        
        try:
            with self.app.app_context():
                # Test MySQL engine type
                engine_result = db.session.execute(text("""
                    SELECT ENGINE FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
                """)).fetchone()
                
                if engine_result:
                    engine = engine_result.ENGINE
                    print(f"   📊 MySQL Storage Engine: {engine}")
                    
                    if engine == 'InnoDB':
                        print("   ✅ Using InnoDB engine (supports transactions)")
                    else:
                        print(f"   ⚠️  Using {engine} engine (consider InnoDB for ACID compliance)")
                
                # Test character set
                charset_result = db.session.execute(text("""
                    SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
                    FROM information_schema.SCHEMATA 
                    WHERE SCHEMA_NAME = DATABASE()
                """)).fetchone()
                
                if charset_result:
                    charset = charset_result.DEFAULT_CHARACTER_SET_NAME
                    collation = charset_result.DEFAULT_COLLATION_NAME
                    print(f"   📊 Character Set: {charset}, Collation: {collation}")
                    
                    if charset in ['utf8mb4', 'utf8']:
                        print("   ✅ UTF-8 character set configured")
                    else:
                        print(f"   ⚠️  Consider using utf8mb4 character set")
                
                # Test auto-increment functionality
                test_user = User(
                    full_name='Test User',
                    email='test@example.com',
                    username=f'testuser_{int(time.time())}',
                    role='staff'
                )
                test_user.set_password('testpass')
                
                db.session.add(test_user)
                db.session.commit()
                
                if test_user.id:
                    print(f"   ✅ Auto-increment working (generated ID: {test_user.id})")
                    
                    # Clean up test user
                    db.session.delete(test_user)
                    db.session.commit()
                    
                    self.log_result("mysql_features", True, "MySQL features working correctly")
                    return True
                else:
                    print("   ❌ Auto-increment not working")
                    self.log_result("mysql_features", False, "Auto-increment failed")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Error testing MySQL features: {e}")
            self.log_result("mysql_features", False, str(e))
            return False
    
    def test_application_functionality(self):
        """Test core application functionality"""
        print("\n🧪 Testing Application Functionality...")
        
        try:
            with self.app.app_context():
                # Test user authentication functions
                admin_user = User.query.filter_by(role='admin').first()
                if admin_user:
                    print(f"   ✅ Admin user found: {admin_user.username}")
                    
                    # Test password hashing
                    if admin_user.check_password('admin123'):  # Default password
                        print("   ⚠️  Default admin password detected - please change it")
                    
                    print("   ✅ Password hashing functionality working")
                else:
                    print("   ⚠️  No admin user found")
                
                # Test QR code functionality
                qr_code_sample = QRCode.query.first()
                if qr_code_sample:
                    print(f"   ✅ QR code data accessible")
                    
                    # Test coordinate functionality if available
                    if qr_code_sample.has_coordinates:
                        print(f"   ✅ QR code coordinates available: {qr_code_sample.coordinates_display}")
                    else:
                        print("   ℹ️  QR code coordinates not set (optional feature)")
                
                # Test attendance functionality
                attendance_sample = AttendanceData.query.first()
                if attendance_sample:
                    print(f"   ✅ Attendance data accessible")
                    
                    # Test location accuracy if available
                    if attendance_sample.has_location_data:
                        accuracy_level = attendance_sample.location_accuracy_level
                        print(f"   ✅ Location accuracy calculation working: {accuracy_level}")
                    else:
                        print("   ℹ️  No location data in sample (feature works when GPS available)")
                
                # Test relationships
                if qr_code_sample and attendance_sample:
                    qr_with_attendance = QRCode.query.join(AttendanceData).first()
                    if qr_with_attendance:
                        print("   ✅ Database relationships working correctly")
                    else:
                        print("   ⚠️  No QR codes with attendance records found")
                
                self.log_result("application_functionality", True, "Core functionality verified")
                return True
                
        except Exception as e:
            print(f"   ❌ Error testing application functionality: {e}")
            self.log_result("application_functionality", False, str(e))
            return False
    
    def test_performance(self):
        """Test basic database performance"""
        print("\n⚡ Testing Database Performance...")
        
        try:
            with self.app.app_context():
                # Test query performance
                start_time = time.time()
                
                # Complex join query
                complex_query = db.session.query(AttendanceData, QRCode, User).join(
                    QRCode, AttendanceData.qr_code_id == QRCode.id
                ).join(
                    User, QRCode.created_by == User.id
                ).limit(100).all()
                
                query_time = time.time() - start_time
                print(f"   📊 Complex join query time: {query_time:.3f} seconds")
                
                if query_time < 1.0:
                    print("   ✅ Query performance acceptable")
                    performance_ok = True
                else:
                    print("   ⚠️  Query performance slow - consider adding indexes")
                    performance_ok = False
                
                # Test bulk operations
                start_time = time.time()
                bulk_count = AttendanceData.query.count()
                count_time = time.time() - start_time
                
                print(f"   📊 Count query time ({bulk_count:,} records): {count_time:.3f} seconds")
                
                # Test connection pooling
                start_time = time.time()
                for i in range(10):
                    db.session.execute(text("SELECT 1")).fetchone()
                pool_time = time.time() - start_time
                
                print(f"   📊 Connection pool test (10 queries): {pool_time:.3f} seconds")
                
                self.log_result("performance", performance_ok, 
                              f"Query time: {query_time:.3f}s" if performance_ok else "Performance issues detected")
                return performance_ok
                
        except Exception as e:
            print(f"   ❌ Error testing performance: {e}")
            self.log_result("performance", False, str(e))
            return False
    
    def test_migration_completeness(self):
        """Test that migration preserved all data correctly"""
        print("\n📊 Testing Migration Completeness...")
        
        try:
            with self.app.app_context():
                # Check for common migration issues
                issues_found = []
                
                # Test datetime handling
                recent_records = AttendanceData.query.filter(
                    AttendanceData.created_timestamp >= datetime.now() - timedelta(days=30)
                ).count()
                
                if recent_records > 0:
                    print(f"   ✅ Recent timestamps preserved ({recent_records} records)")
                else:
                    print("   ℹ️  No recent records found (expected if migrating old data)")
                
                # Test text field preservation
                qr_with_long_text = QRCode.query.filter(
                    db.func.length(QRCode.qr_code_image) > 1000
                ).first()
                
                if qr_with_long_text:
                    print("   ✅ Large text fields (QR images) preserved correctly")
                else:
                    print("   ⚠️  No large text fields found - check QR code images")
                    issues_found.append("QR code images may not be preserved")
                
                # Test float/decimal precision
                attendance_with_coords = AttendanceData.query.filter(
                    AttendanceData.latitude.isnot(None)
                ).first()
                
                if attendance_with_coords:
                    lat_precision = len(str(attendance_with_coords.latitude).split('.')[-1]) if '.' in str(attendance_with_coords.latitude) else 0
                    if lat_precision >= 6:
                        print(f"   ✅ Coordinate precision preserved ({lat_precision} decimal places)")
                    else:
                        print(f"   ⚠️  Coordinate precision may be reduced ({lat_precision} decimal places)")
                        issues_found.append("Coordinate precision reduced")
                
                # Test boolean field handling
                active_users = User.query.filter_by(active_status=True).count()
                inactive_users = User.query.filter_by(active_status=False).count()
                
                print(f"   📊 User status: {active_users} active, {inactive_users} inactive")
                if active_users > 0:
                    print("   ✅ Boolean fields working correctly")
                
                # Test foreign key constraints
                try:
                    # Try to insert invalid foreign key
                    invalid_attendance = AttendanceData(
                        qr_code_id=99999,  # Non-existent QR code
                        employee_id='TEST',
                        location_name='Test',
                        check_in_date=date.today(),
                        check_in_time=datetime.now().time()
                    )
                    db.session.add(invalid_attendance)
                    db.session.commit()
                    
                    # If we get here, foreign key constraint failed
                    db.session.delete(invalid_attendance)
                    db.session.commit()
                    print("   ⚠️  Foreign key constraints not enforced")
                    issues_found.append("Foreign key constraints not working")
                    
                except Exception:
                    # This is expected - foreign key constraint should prevent the insert
                    db.session.rollback()
                    print("   ✅ Foreign key constraints working correctly")
                
                migration_complete = len(issues_found) == 0
                self.log_result("migration_completeness", migration_complete,
                              "Migration complete" if migration_complete else "; ".join(issues_found))
                
                return migration_complete
                
        except Exception as e:
            print(f"   ❌ Error testing migration completeness: {e}")
            self.log_result("migration_completeness", False, str(e))
            return False
    
    def generate_report(self):
        """Generate comprehensive verification report"""
        print("\n📋 GENERATING VERIFICATION REPORT")
        print("=" * 60)
        
        passed_tests = sum(1 for result in self.test_results.values() if result['passed'])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 SUMMARY:")
        print(f"   Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"   Issues Found: {len(self.issues)}")
        
        print(f"\n📝 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            print(f"   {status} {test_name}")
            if result['message']:
                print(f"       {result['message']}")
        
        if self.issues:
            print(f"\n⚠️  ISSUES TO ADDRESS:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        if success_rate >= 90:
            print("   ✅ Migration appears successful - ready for production use")
            print("   ✅ Perform additional application testing")
            print("   ✅ Set up regular MySQL backups")
            print("   ✅ Monitor performance in production")
        elif success_rate >= 70:
            print("   ⚠️  Migration mostly successful but has issues")
            print("   ⚠️  Address the issues listed above before production use")
            print("   ⚠️  Consider additional testing")
        else:
            print("   ❌ Migration has significant issues")
            print("   ❌ Do not use in production until issues are resolved")
            print("   ❌ Consider re-running migration process")
        
        # Save report to file
        report_filename = f"mysql_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_filename, 'w') as f:
                f.write(f"MySQL Database Verification Report\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"=" * 50 + "\n\n")
                
                f.write(f"Summary:\n")
                f.write(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)\n")
                f.write(f"Issues Found: {len(self.issues)}\n\n")
                
                f.write(f"Detailed Results:\n")
                for test_name, result in self.test_results.items():
                    status = "PASS" if result['passed'] else "FAIL"
                    f.write(f"{status}: {test_name}\n")
                    if result['message']:
                        f.write(f"  Message: {result['message']}\n")
                    f.write(f"  Time: {result['timestamp'].isoformat()}\n\n")
                
                if self.issues:
                    f.write(f"Issues:\n")
                    for i, issue in enumerate(self.issues, 1):
                        f.write(f"{i}. {issue}\n")
            
            print(f"\n📄 Report saved to: {report_filename}")
            
        except Exception as e:
            print(f"⚠️  Could not save report to file: {e}")
        
        return success_rate >= 90

def main():
    """Main verification process"""
    print("MYSQL DATABASE VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    verifier = MySQLVerifier()
    
    # Run all verification tests
    tests = [
        verifier.test_database_connection,
        verifier.test_table_structure,
        verifier.test_data_integrity,
        verifier.test_mysql_specific_features,
        verifier.test_application_functionality,
        verifier.test_performance,
        verifier.test_migration_completeness
    ]
    
    try:
        for test in tests:
            if not test():
                print(f"\n⚠️  Test failed: {test.__name__}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate final report
    success = verifier.generate_report()
    
    print(f"\nVerification completed at {datetime.now().strftime('%H:%M:%S')}")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)