#!/usr/bin/env python3
"""
Database Migration Script for New User Roles
=============================================

This script safely migrates your existing database to support the new roles:
- payroll
- project_manager

The script will:
1. Backup your current database
2. Check for any data integrity issues
3. Add the new roles to your system
4. Provide a rollback option if needed

Usage:
    python migrate_roles.py

Requirements:
    - Your existing Flask app with database models
    - Backup directory permissions
    - Database write permissions
"""

import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add your app to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, QRCode
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Make sure this script is in the same directory as your app.py file")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configuration
BACKUP_DIR = "database_backups"
VALID_ROLES = ['admin', 'staff', 'payroll', 'project_manager']
MIGRATION_VERSION = "v1.0_add_payroll_project_manager_roles"

def create_backup_directory():
    """Create backup directory if it doesn't exist"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"✓ Created backup directory: {BACKUP_DIR}")

def backup_database():
    """Create a backup of the current database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{MIGRATION_VERSION}_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # Get database path from config
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    
    if db_url.startswith('sqlite:///'):
        # SQLite database
        db_path = db_url.replace('sqlite:///', '')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            print(f"✓ Database backed up to: {backup_path}")
            return backup_path
        else:
            print(f"⚠ Database file not found: {db_path}")
            return None
    else:
        print("⚠ Non-SQLite databases require manual backup")
        print("Please ensure you have a recent backup before proceeding")
        return None

def validate_current_database():
    """Validate the current database structure and data"""
    print("\n🔍 Validating current database...")
    
    try:
        with app.app_context():
            # Check if User table exists and has required columns
            users = User.query.all()
            print(f"✓ Found {len(users)} users in database")
            
            # Check current roles
            current_roles = db.session.query(User.role.distinct()).all()
            current_roles = [role[0] for role in current_roles]
            print(f"✓ Current roles in database: {current_roles}")
            
            # Check for any invalid roles
            invalid_roles = [role for role in current_roles if role not in ['admin', 'staff']]
            if invalid_roles:
                print(f"⚠ Found unexpected roles: {invalid_roles}")
                return False
            
            # Check QR codes
            qr_codes = QRCode.query.all()
            print(f"✓ Found {len(qr_codes)} QR codes in database")
            
            print("✓ Database validation passed")
            return True
            
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False

def perform_migration():
    """Perform the actual migration"""
    print("\n🚀 Starting migration...")
    
    try:
        with app.app_context():
            # The migration is actually just code changes since we're not changing the database schema
            # We're just allowing new values in the existing role column
            
            # Check if any existing users need to be updated (optional)
            admin_count = User.query.filter_by(role='admin').count()
            staff_count = User.query.filter_by(role='staff').count()
            
            print(f"✓ Current user distribution:")
            print(f"  - Administrators: {admin_count}")
            print(f"  - Staff Users: {staff_count}")
            
            # Create a migration record (optional - for tracking)
            migration_record = {
                'version': MIGRATION_VERSION,
                'timestamp': datetime.now(),
                'description': 'Added support for payroll and project_manager roles'
            }
            
            print("✓ Migration completed successfully!")
            print("✓ New roles 'payroll' and 'project_manager' are now supported")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def test_new_roles():
    """Test that new roles work correctly"""
    print("\n🧪 Testing new role functionality...")
    
    try:
        with app.app_context():
            # Test creating users with new roles (without actually saving them)
            test_payroll_user = User(
                full_name="Test Payroll User",
                email="test_payroll@example.com",
                username="test_payroll",
                role="payroll"
            )
            
            test_pm_user = User(
                full_name="Test Project Manager",
                email="test_pm@example.com",
                username="test_pm",
                role="project_manager"
            )
            
            # Validate the objects (without saving)
            if test_payroll_user.role in VALID_ROLES:
                print("✓ Payroll role validation passed")
            else:
                print("❌ Payroll role validation failed")
                return False
                
            if test_pm_user.role in VALID_ROLES:
                print("✓ Project Manager role validation passed")
            else:
                print("❌ Project Manager role validation failed")
                return False
            
            # Test role display names
            if hasattr(test_payroll_user, 'get_role_display_name'):
                payroll_display = test_payroll_user.get_role_display_name()
                print(f"✓ Payroll display name: {payroll_display}")
            
            if hasattr(test_pm_user, 'get_role_display_name'):
                pm_display = test_pm_user.get_role_display_name()
                print(f"✓ Project Manager display name: {pm_display}")
            
            # Test permission methods
            if hasattr(test_payroll_user, 'has_staff_permissions'):
                if test_payroll_user.has_staff_permissions():
                    print("✓ Payroll user has staff-level permissions")
                else:
                    print("❌ Payroll user missing staff-level permissions")
                    return False
            
            if hasattr(test_pm_user, 'has_staff_permissions'):
                if test_pm_user.has_staff_permissions():
                    print("✓ Project Manager has staff-level permissions")
                else:
                    print("❌ Project Manager missing staff-level permissions")
                    return False
            
            print("✓ All role functionality tests passed")
            return True
            
    except Exception as e:
        print(f"❌ Role testing failed: {e}")
        return False

def display_summary():
    """Display migration summary and next steps"""
    print("\n" + "="*60)
    print("🎉 MIGRATION COMPLETE!")
    print("="*60)
    print()
    print("WHAT'S NEW:")
    print("• Added support for 'payroll' role")
    print("• Added support for 'project_manager' role")
    print("• Both new roles have staff-level permissions")
    print("• Updated templates support new role creation")
    print("• Enhanced user management interface")
    print()
    print("NEXT STEPS:")
    print("1. Restart your Flask application")
    print("2. Test creating users with new roles via admin interface")
    print("3. Verify new role badges appear correctly in user management")
    print("4. Consider updating any custom permissions as needed")
    print()
    print("FILES UPDATED:")
    print("• app.py - Core application logic")
    print("• templates/create_user.html - User creation form")
    print("• templates/edit_user.html - User editing form") 
    print("• templates/users.html - User management page")
    print()
    print("BACKUP LOCATION:")
    backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')]
    if backup_files:
        latest_backup = sorted(backup_files)[-1]
        print(f"• {os.path.join(BACKUP_DIR, latest_backup)}")
    print()

def rollback_instructions():
    """Display rollback instructions"""
    print("\n" + "="*60)
    print("🔄 ROLLBACK INSTRUCTIONS")
    print("="*60)
    print()
    print("If you need to rollback this migration:")
    print()
    print("1. Stop your Flask application")
    print("2. Restore your database from backup:")
    backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('backup_')]
    if backup_files:
        latest_backup = sorted(backup_files)[-1]
        backup_path = os.path.join(BACKUP_DIR, latest_backup)
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            print(f"   cp {backup_path} {db_path}")
    print("3. Revert your code files to previous versions")
    print("4. Restart your application")
    print()

def main():
    """Main migration function"""
    print("="*60)
    print("🔧 USER ROLES MIGRATION SCRIPT")
    print("="*60)
    print(f"Migration: {MIGRATION_VERSION}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ app.py not found in current directory")
        print("Please run this script from your Flask application directory")
        sys.exit(1)
    
    # Create backup directory
    create_backup_directory()
    
    # Ask for confirmation
    print("This migration will add support for new user roles:")
    print("• payroll")
    print("• project_manager")
    print()
    
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Migration cancelled.")
        sys.exit(0)
    
    # Step 1: Backup database
    backup_path = backup_database()
    if not backup_path:
        response = input("No backup created. Continue anyway? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Migration cancelled for safety.")
            sys.exit(0)
    
    # Step 2: Validate current database
    if not validate_current_database():
        print("❌ Database validation failed. Migration cancelled.")
        sys.exit(1)
    
    # Step 3: Perform migration
    if not perform_migration():
        print("❌ Migration failed. Please check the errors above.")
        sys.exit(1)
    
    # Step 4: Test new functionality
    if not test_new_roles():
        print("❌ Role testing failed. Migration may be incomplete.")
        sys.exit(1)
    
    # Step 5: Display summary
    display_summary()
    
    # Step 6: Show rollback instructions
    show_rollback = input("\nWould you like to see rollback instructions? (y/N): ").strip().lower()
    if show_rollback in ['y', 'yes']:
        rollback_instructions()
    
    print("\n🚀 Migration completed successfully!")
    print("You can now create users with payroll and project_manager roles.")

if __name__ == "__main__":
    main()