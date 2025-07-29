#!/usr/bin/env python3
"""
Database Setup Script for QR Code Management System
Handles database initialization, migrations, and sample data creation
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

def create_app():
    """Create Flask application for database setup"""
    app = Flask(__name__)
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:Ratkhonho123@localhost/qr_management')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'setup-key-change-in-production'
    
    return app

def create_models(db):
    """Define database models"""
    
    # User Model
    class User(db.Model):
        """
        User model to manage system users with role-based access control
        """
        __tablename__ = 'users'
        
        id = db.Column(db.Integer, primary_key=True)
        full_name = db.Column(db.String(100), nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(256), nullable=False)
        role = db.Column(db.String(20), nullable=False, default='staff')  # admin or staff
        created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
        created_date = db.Column(db.DateTime, default=datetime.utcnow)
        active_status = db.Column(db.Boolean, default=True)
        last_login_date = db.Column(db.DateTime, nullable=True)
        
        # Relationships
        created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]))
        created_qr_codes = db.relationship('QRCode', backref='creator', lazy='dynamic')
        
        def set_password(self, password):
            """Hash and set user password"""
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            """Verify user password"""
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
        
        def is_admin(self):
            """Check if user has admin privileges"""
            return self.role == 'admin'

    # QR Code Model
    class QRCode(db.Model):
        """
        QR Code model to manage QR code records and metadata
        """
        __tablename__ = 'qr_codes'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        location = db.Column(db.String(100), nullable=False)
        location_address = db.Column(db.Text, nullable=False)
        location_event = db.Column(db.String(200), nullable=False)
        qr_code_image = db.Column(db.Text, nullable=False)  # Base64 encoded image
        created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        created_date = db.Column(db.DateTime, default=datetime.utcnow)
        active_status = db.Column(db.Boolean, default=True)
    
    return User, QRCode

def setup_database():
    """
    Complete database setup including:
    - Table creation
    - Default admin user
    - Sample data (optional)
    """
    
    print("🚀 Starting QR Code Management System Database Setup...")
    print("=" * 60)
    
    # Create Flask app and initialize database
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Create models
            User, QRCode = create_models(db)
            
            print("📊 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Create default admin user
            print("\n👤 Creating default admin user...")
            create_default_admin(db, User)
            
            # Ask if user wants sample data
            create_sample = input("\n❓ Would you like to create sample QR codes? (y/N): ").lower().strip()
            if create_sample in ['y', 'yes']:
                create_sample_data(db, User, QRCode)
            
            print("\n🎉 Database setup completed successfully!")
            print("\n📋 Setup Summary:")
            print("   - Database tables created")
            print("   - Default admin user created")
            print("   - Login credentials: admin / admin123")
            print("   - ⚠️  IMPORTANT: Change the default password after first login!")
            
            if create_sample in ['y', 'yes']:
                print("   - Sample QR codes created")
            
            print("\n🚀 You can now start the application with: python app.py")
            
        except Exception as e:
            print(f"❌ Error during database setup: {str(e)}")
            print("\n🔧 Troubleshooting tips:")
            print("   1. Make sure PostgreSQL is running")
            print("   2. Check your database connection string")
            print("   3. Ensure the database exists")
            print("   4. Verify database user permissions")
            sys.exit(1)

def create_default_admin(db, User):
    """Create default admin user if it doesn't exist"""
    
    # Check if admin user already exists
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print("   ℹ️  Admin user already exists, skipping creation")
        return
    
    try:
        # Create default admin user
        admin_user = User(
            full_name='System Administrator',
            email='admin@qrmanager.local',
            username='admin',
            role='admin',
            active_status=True,
            created_date=datetime.utcnow()
        )
        admin_user.set_password('admin123')  # Default password - should be changed
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("   ✅ Default admin user created successfully!")
        print("   📧 Email: admin@qrmanager.local")
        print("   👤 Username: admin")
        print("   🔑 Password: admin123")
        
    except Exception as e:
        print(f"   ❌ Failed to create admin user: {str(e)}")
        db.session.rollback()
        raise

def create_sample_data(db, User, QRCode):
    """Create sample QR codes for demonstration"""
    
    print("\n📦 Creating sample data...")
    
    # Get admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print("   ❌ Admin user not found, cannot create sample data")
        return
    
    # Sample QR codes data
    sample_qr_codes = [
        {
            'name': 'Conference Room A Check-in',
            'location': 'Conference Room A',
            'location_address': '123 Business Plaza, Suite 400, New York, NY 10001',
            'location_event': 'Weekly Team Meeting',
        },
        {
            'name': 'Main Lobby Registration',
            'location': 'Main Lobby',
            'location_address': '456 Corporate Center, Ground Floor, Chicago, IL 60601',
            'location_event': 'Annual Company Conference 2025',
        },
        {
            'name': 'Training Room B',
            'location': 'Training Room B',
            'location_address': '789 Innovation Hub, 2nd Floor, San Francisco, CA 94105',
            'location_event': 'Employee Onboarding Session',
        },
        {
            'name': 'Customer Service Desk',
            'location': 'Customer Service Counter',
            'location_address': '321 Service Plaza, Main Floor, Austin, TX 78701',
            'location_event': 'Customer Support Check-in',
        },
        {
            'name': 'Cafeteria Feedback Station',
            'location': 'Employee Cafeteria',
            'location_address': '654 Office Complex, Lower Level, Seattle, WA 98101',
            'location_event': 'Meal Feedback Collection',
        }
    ]
    
    try:
        # Import QR code generation function
        import qrcode
        import io
        import base64
        
        for qr_data in sample_qr_codes:
            # Generate QR code image
            qr_content = f"Event: {qr_data['location_event']}\nLocation: {qr_data['location']}\nAddress: {qr_data['location_address']}"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Create QR code record
            qr_code = QRCode(
                name=qr_data['name'],
                location=qr_data['location'],
                location_address=qr_data['location_address'],
                location_event=qr_data['location_event'],
                qr_code_image=img_str,
                created_by=admin.id,
                created_date=datetime.utcnow(),
                active_status=True
            )
            
            db.session.add(qr_code)
        
        db.session.commit()
        print(f"   ✅ Created {len(sample_qr_codes)} sample QR codes!")
        
    except Exception as e:
        print(f"   ❌ Failed to create sample data: {str(e)}")
        db.session.rollback()
        raise

def reset_database():
    """Reset database (drop all tables and recreate)"""
    
    print("⚠️  WARNING: This will delete ALL data in the database!")
    confirm = input("Are you sure you want to reset the database? Type 'RESET' to confirm: ")
    
    if confirm != 'RESET':
        print("❌ Database reset cancelled")
        return
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Create models
            User, QRCode = create_models(db)
            
            print("🗑️  Dropping all tables...")
            db.drop_all()
            
            print("📊 Recreating tables...")
            db.create_all()
            
            print("✅ Database reset completed!")
            
        except Exception as e:
            print(f"❌ Error during database reset: {str(e)}")
            sys.exit(1)

def check_database_connection():
    """Test database connectivity"""
    
    print("🔍 Testing database connection...")
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Create models
            User, QRCode = create_models(db)
            
            # Try to execute a simple query
            db.session.execute('SELECT 1').fetchone()
            print("✅ Database connection successful!")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'users' in tables and 'qr_codes' in tables:
                print("✅ Required tables exist")
                
                # Count records
                user_count = User.query.count()
                qr_count = QRCode.query.count()
                
                print(f"📊 Database contains: {user_count} users, {qr_count} QR codes")
            else:
                print("⚠️  Some tables are missing - run setup to create them")
            
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            print("\n🔧 Check your database configuration:")
            print(f"   Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            sys.exit(1)

def main():
    """Main setup script entry point"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'reset':
            reset_database()
        elif command == 'check':
            check_database_connection()
        elif command == 'setup':
            setup_database()
        else:
            print("❌ Unknown command. Available commands:")
            print("   setup  - Set up database and create default data")
            print("   reset  - Reset database (delete all data)")
            print("   check  - Check database connection and status")
    else:
        # Default action is setup
        setup_database()

if __name__ == '__main__':
    main()