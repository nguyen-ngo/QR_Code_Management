#!/usr/bin/env python3
"""
Database Migration Script for Project Model
==========================================

This script safely migrates your existing database to add the Project model
and associate QR codes with projects.

The script will:
1. Backup your current database
2. Create the new projects table
3. Add project_id column to qr_codes table
4. Create some sample projects (optional)
5. Provide rollback instructions

Usage:
    python migrate_projects.py

Requirements:
    - Your existing Flask app with database models
    - Database write permissions
"""

import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Add your app to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, QRCode, Project
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Make sure this script is in the same directory as your app.py file")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configuration
BACKUP_DIR = "database_backups"
MIGRATION_VERSION = "v1.1_add_project_model"

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
            # Check if required tables exist
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['users', 'qr_codes']
            for table in required_tables:
                if table not in tables:
                    print(f"❌ Required table '{table}' not found")
                    return False
                print(f"✓ Table '{table}' exists")
            
            # Check current data
            users = User.query.all()
            qr_codes = QRCode.query.all()
            print(f"✓ Found {len(users)} users in database")
            print(f"✓ Found {len(qr_codes)} QR codes in database")
            
            # Check if projects table already exists
            if 'projects' in tables:
                print("⚠ Projects table already exists - migration may have been run before")
                projects = Project.query.all()
                print(f"✓ Found {len(projects)} existing projects")
            
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
            # Create all tables (this will create the projects table if it doesn't exist)
            db.create_all()
            print("✓ Database tables created/updated")
            
            # Check if project_id column exists in qr_codes table
            inspector = inspect(db.engine)
            qr_columns = inspector.get_columns('qr_codes')
            qr_column_names = [col['name'] for col in qr_columns]
            
            if 'project_id' not in qr_column_names:
                # Add project_id column to qr_codes table
                print("➕ Adding project_id column to qr_codes table...")
                db.session.execute(text('ALTER TABLE qr_codes ADD COLUMN project_id INTEGER'))
                db.session.commit()
                print("✓ project_id column added to qr_codes table")
            else:
                print("✓ project_id column already exists in qr_codes table")
            
            print("✓ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_projects():
    """Create some sample projects (optional)"""
    print("\n📁 Creating sample projects...")
    
    try:
        with app.app_context():
            # Get the first admin user to assign as creator
            admin_user = User.query.filter_by(role='admin').first()
            creator_id = admin_user.id if admin_user else None
            
            # Check if any projects exist
            existing_projects = Project.query.count()
            if existing_projects > 0:
                print(f"✓ Found {existing_projects} existing projects - skipping sample creation")
                return True
            
            # Sample projects
            sample_projects = [
                {
                    'name': 'Office Locations',
                    'description': 'QR codes for various office locations and facilities'
                },
                {
                    'name': 'Events',
                    'description': 'QR codes for company events and meetings'
                },
                {
                    'name': 'Training Materials',
                    'description': 'QR codes for training sessions and educational content'
                }
            ]
            
            created_count = 0
            for project_data in sample_projects:
                # Check if project with this name already exists
                existing = Project.query.filter_by(name=project_data['name']).first()
                if not existing:
                    project = Project(
                        name=project_data['name'],
                        description=project_data['description'],
                        created_by=creator_id
                    )
                    db.session.add(project)
                    created_count += 1
            
            if created_count > 0:
                db.session.commit()
                print(f"✓ Created {created_count} sample projects")
            else:
                print("✓ Sample projects already exist")
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to create sample projects: {e}")
        return False

def test_new_functionality():
    """Test the new project functionality"""
    print("\n🧪 Testing new project functionality...")
    
    try:
        with app.app_context():
            # Test Project model
            projects = Project.query.all()
            print(f"✓ Can query projects: {len(projects)} found")
            
            # Test QRCode project relationship
            qr_codes = QRCode.query.all()
            for qr in qr_codes[:3]:  # Test first 3 QR codes
                project = qr.project  # This should not raise an error
                print(f"✓ QR code '{qr.name}' project: {project.name if project else 'None'}")
            
            # Test Project.qr_codes relationship
            if projects:
                first_project = projects[0]
                qr_count = first_project.qr_count
                print(f"✓ Project '{first_project.name}' has {qr_count} QR codes")
            
            print("✓ New functionality tests passed")
            return True
            
    except Exception as e:
        print(f"❌ Functionality tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def display_summary():
    """Display migration summary"""
    print("\n📊 MIGRATION SUMMARY")
    print("=" * 50)
    
    try:
        with app.app_context():
            users = User.query.count()
            projects = Project.query.count()
            qr_codes = QRCode.query.count()
            
            print(f"👥 Users: {users}")
            print(f"📁 Projects: {projects}")
            print(f"🔗 QR Codes: {qr_codes}")
            
            # Show project distribution
            if projects > 0:
                print(f"\n📁 Project Details:")
                for project in Project.query.all():
                    print(f"   • {project.name}: {project.qr_count} QR codes")
            
            # Show unassigned QR codes
            unassigned = QRCode.query.filter_by(project_id=None).count()
            if unassigned > 0:
                print(f"\n⚠️  {unassigned} QR codes are not assigned to any project")
            
    except Exception as e:
        print(f"Error generating summary: {e}")

def rollback_instructions():
    """Show rollback instructions"""
    print("\n🔄 ROLLBACK INSTRUCTIONS")
    print("=" * 50)
    print("If you need to rollback this migration:")
    print("1. Stop your application")
    print("2. Restore the database backup:")
    print("   - For SQLite: Replace your database file with the backup")
    print("   - For other databases: Restore from your backup")
    print("3. Remove the project_id column from qr_codes table:")
    print("   ALTER TABLE qr_codes DROP COLUMN project_id;")
    print("4. Drop the projects table:")
    print("   DROP TABLE projects;")
    print("5. Update your app.py to remove Project model and related code")
    print("6. Restart your application")

def main():
    """Main migration process"""
    print("🗃️  PROJECT MODEL MIGRATION")
    print("=" * 50)
    print("This will add project functionality to your QR code system.")
    print("Projects allow you to organize QR codes into logical groups.")
    print("\nWhat this migration does:")
    print("• Creates a new 'projects' table")
    print("• Adds 'project_id' column to 'qr_codes' table")
    print("• Creates sample projects (optional)")
    print("• Updates relationships between models")
    
    # Confirm migration
    response = input("\nProceed with migration? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Migration cancelled.")
        sys.exit(0)
    
    # Step 1: Create backup directory
    create_backup_directory()
    
    # Step 2: Backup database
    backup_path = backup_database()
    if not backup_path:
        response = input("No backup created. Continue anyway? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Migration cancelled for safety.")
            sys.exit(0)
    
    # Step 3: Validate current database
    if not validate_current_database():
        print("❌ Database validation failed. Migration cancelled.")
        sys.exit(1)
    
    # Step 4: Perform migration
    if not perform_migration():
        print("❌ Migration failed. Please check the errors above.")
        sys.exit(1)
    
    # Step 5: Create sample projects
    create_sample = input("\nCreate sample projects? (Y/n): ").strip().lower()
    if create_sample not in ['n', 'no']:
        create_sample_projects()
    
    # Step 6: Test new functionality
    if not test_new_functionality():
        print("❌ Functionality testing failed. Migration may be incomplete.")
        sys.exit(1)
    
    # Step 7: Display summary
    display_summary()
    
    # Step 8: Show rollback instructions
    show_rollback = input("\nWould you like to see rollback instructions? (y/N): ").strip().lower()
    if show_rollback in ['y', 'yes']:
        rollback_instructions()
    
    print("\n🚀 Migration completed successfully!")
    print("You can now:")
    print("• Create and manage projects")
    print("• Associate QR codes with projects")
    print("• Use the project dropdown in QR code forms")
    print("• View project statistics and organization")

if __name__ == "__main__":
    main()