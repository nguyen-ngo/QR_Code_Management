# quick_fix_tables.py
"""
Quick Fix for Missing Maintenance Tables
======================================

Run this script to quickly create the missing tables that are causing the cleanup error.
"""

import sys
import os
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, logger_handler

def quick_create_missing_tables():
    """Quickly create the missing tables for maintenance system"""
    
    print("🔧 Quick Fix: Creating Missing Maintenance Tables")
    print("=" * 55)
    
    with app.app_context():
        try:
            # Create attendance_audit table
            print("📋 Creating attendance_audit table...")
            
            audit_sql = """
                CREATE TABLE IF NOT EXISTS attendance_audit (
                    audit_id INT AUTO_INCREMENT PRIMARY KEY,
                    record_id INT NOT NULL,
                    action_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
                    old_values JSON,
                    new_values JSON,
                    changed_by VARCHAR(100),
                    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    INDEX idx_audit_timestamp (change_timestamp DESC),
                    INDEX idx_audit_record (record_id)
                ) ENGINE=InnoDB
            """
            
            db.session.execute(text(audit_sql))
            print("   ✅ attendance_audit table created")
            
            # Create attendance_statistics_cache table
            print("📋 Creating attendance_statistics_cache table...")
            
            cache_sql = """
                CREATE TABLE IF NOT EXISTS attendance_statistics_cache (
                    cache_key VARCHAR(255) PRIMARY KEY,
                    cache_data JSON NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    INDEX idx_cache_expires (expires_at),
                    INDEX idx_cache_updated (last_updated DESC)
                ) ENGINE=InnoDB
            """
            
            db.session.execute(text(cache_sql))
            print("   ✅ attendance_statistics_cache table created")
            
            # Commit the changes
            db.session.commit()
            
            print("\n✅ SUCCESS: Missing tables created successfully!")
            print("\n🧪 Testing the tables...")
            
            # Test the tables
            test_queries = [
                "SELECT COUNT(*) FROM attendance_audit",
                "SELECT COUNT(*) FROM attendance_statistics_cache"
            ]
            
            for query in test_queries:
                try:
                    result = db.session.execute(text(query)).fetchone()
                    table_name = query.split("FROM ")[1]
                    print(f"   ✅ {table_name}: OK (rows: {result[0]})")
                except Exception as e:
                    print(f"   ❌ Test failed: {e}")
            
            print(f"\n🎉 QUICK FIX COMPLETED!")
            print("\nNow you can run:")
            print("   python maintenance_cli.py cleanup")
            print("   python maintenance_cli.py health-check")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    quick_create_missing_tables()