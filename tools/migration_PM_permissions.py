"""
Database Migration Script for Project Manager Permissions (MySQL Version)
==========================================================================

This script creates the necessary tables for Project Manager role permissions.
It adds support for assigning specific projects and locations to Project Managers.

Tables Created:
1. user_project_permissions: Links users to projects they can access
2. user_location_permissions: Links users to locations they can access

Run this script ONCE after backing up your database.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask app for migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql://user:pass@localhost/qr_management')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def run_migration():
    """Execute the migration to add project manager permission tables"""
    
    with app.app_context():
        print("\n" + "="*70)
        print("PROJECT MANAGER PERMISSIONS MIGRATION (MySQL)")
        print("="*70 + "\n")
        
        try:
            # Check if tables already exist
            print("🔍 Checking if migration is needed...")
            
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME IN ('user_project_permissions', 'user_location_permissions')
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            if len(existing_tables) == 2:
                print("✅ Migration tables already exist. No action needed.")
                return True
            
            if 'user_project_permissions' in existing_tables:
                print("⚠️  user_project_permissions table already exists, skipping...")
            else:
                # Create user_project_permissions table
                print("\n📝 Creating user_project_permissions table...")
                db.session.execute(text("""
                    CREATE TABLE user_project_permissions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        project_id INT NOT NULL,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                        UNIQUE KEY unique_user_project (user_id, project_id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_project_id (project_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("✅ user_project_permissions table created successfully")
            
            if 'user_location_permissions' in existing_tables:
                print("⚠️  user_location_permissions table already exists, skipping...")
            else:
                # Create user_location_permissions table
                print("\n📝 Creating user_location_permissions table...")
                db.session.execute(text("""
                    CREATE TABLE user_location_permissions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        location_name VARCHAR(200) NOT NULL,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                        UNIQUE KEY unique_user_location (user_id, location_name),
                        INDEX idx_user_id (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("✅ user_location_permissions table created successfully")
            
            # Commit all changes
            db.session.commit()
            
            print("\n" + "="*70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("="*70)
            print("\nNext Steps:")
            print("1. The tables are ready for use")
            print("2. You can now assign projects and locations to Project Managers")
            print("3. Restart your application\n")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed: {e}")
            print("Please check your database and try again.")
            return False

if __name__ == '__main__':
    print("\n⚠️  IMPORTANT: Backup your database before running this migration!")
    response = input("Continue with migration? (yes/no): ")
    
    if response.lower() == 'yes':
        success = run_migration()
        if success:
            print("\n✅ Migration completed. You can now restart your application.")
        else:
            print("\n❌ Migration failed. Please check the errors above.")
    else:
        print("\n❌ Migration cancelled.")