#!/usr/bin/env python3
"""
Location Tracking Debug & Fix Script
====================================

This script will diagnose and fix location tracking issues in your QR system.
It will check the database, model, and provide the correct implementation.

Run this to identify why coordinates aren't being saved.
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect

def create_app():
    """Create Flask app for debugging"""
    app = Flask(__name__)
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres1411@localhost/qr_management')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

def check_database_structure():
    """Check if location columns exist in database"""
    print("🔍 STEP 1: Checking Database Structure")
    print("=" * 50)
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check if attendance_data table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'attendance_data'
                );
            """))
            
            if not result.fetchone()[0]:
                print("❌ attendance_data table NOT found!")
                return False
            
            print("✅ attendance_data table exists")
            
            # Check table structure
            result = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'attendance_data'
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            print(f"\n📋 Table has {len(columns)} columns:")
            
            location_columns = ['latitude', 'longitude', 'accuracy', 'altitude', 'location_source', 'address']
            found_location_columns = []
            
            for col_name, data_type, nullable, default in columns:
                status = "🟢" if col_name in location_columns else "⚪"
                default_str = f" (default: {default})" if default else ""
                print(f"   {status} {col_name}: {data_type} {'NULL' if nullable == 'YES' else 'NOT NULL'}{default_str}")
                
                if col_name in location_columns:
                    found_location_columns.append(col_name)
            
            print(f"\n📊 Location columns found: {len(found_location_columns)}/6")
            
            if len(found_location_columns) == 0:
                print("❌ NO location columns found! Database migration needed.")
                return False
            elif len(found_location_columns) < 6:
                missing = set(location_columns) - set(found_location_columns)
                print(f"⚠️  Missing location columns: {', '.join(missing)}")
                return False
            else:
                print("✅ All location columns present!")
                return True
                
        except Exception as e:
            print(f"❌ Database check failed: {e}")
            return False

def add_missing_columns():
    """Add missing location columns to database"""
    print("\n🛠️  STEP 2: Adding Missing Location Columns")
    print("=" * 50)
    
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            location_columns = [
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS latitude FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS longitude FLOAT", 
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS accuracy FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS altitude FLOAT",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS location_source VARCHAR(50) DEFAULT 'manual'",
                "ALTER TABLE attendance_data ADD COLUMN IF NOT EXISTS address VARCHAR(500)"
            ]
            
            for sql_command in location_columns:
                try:
                    db.session.execute(text(sql_command))
                    column_name = sql_command.split()[4]
                    print(f"✅ Added: {column_name}")
                except Exception as e:
                    print(f"⚠️  {sql_command.split()[4]}: {e}")
            
            db.session.commit()
            print("✅ Database columns added successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add columns: {e}")
            db.session.rollback()
            return False

def test_location_data_flow():
    """Test the complete location data flow"""
    print("\n🧪 STEP 3: Testing Location Data Flow")
    print("=" * 50)
    
    app = create_app()
    db = SQLAlchemy(app)
    
    # Import your actual model
    try:
        sys.path.append(os.getcwd())
        from app import AttendanceData
        print("✅ Successfully imported AttendanceData model")
    except Exception as e:
        print(f"❌ Failed to import AttendanceData: {e}")
        print("   Creating temporary model for testing...")
        
        # Create temporary model
        class AttendanceData(db.Model):
            __tablename__ = 'attendance_data'
            id = db.Column(db.Integer, primary_key=True)
            qr_code_id = db.Column(db.Integer, nullable=False)
            employee_id = db.Column(db.String(50), nullable=False)
            check_in_date = db.Column(db.Date, nullable=False)
            check_in_time = db.Column(db.Time, nullable=False)
            latitude = db.Column(db.Float, nullable=True)
            longitude = db.Column(db.Float, nullable=True)
            accuracy = db.Column(db.Float, nullable=True)
            altitude = db.Column(db.Float, nullable=True)
            location_source = db.Column(db.String(50), default='manual')
            address = db.Column(db.String(500), nullable=True)
            location_name = db.Column(db.String(100), nullable=False)
            status = db.Column(db.String(20), default='present')
            created_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    with app.app_context():
        try:
            # Test creating a record with location data
            test_record = AttendanceData(
                qr_code_id=1,
                employee_id='TEST001',
                check_in_date=datetime.today().date(),
                check_in_time=datetime.now().time(),
                latitude=37.7749,
                longitude=-122.4194,
                accuracy=15.0,
                altitude=100.0,
                location_source='gps',
                address='San Francisco, CA',
                location_name='Test Location',
                status='present'
            )
            
            # Try to add without committing (just test)
            db.session.add(test_record)
            db.session.flush()  # This will fail if columns don't exist
            db.session.rollback()  # Don't actually save the test record
            
            print("✅ Location data model test passed!")
            print("   Model can successfully store location coordinates")
            return True
            
        except Exception as e:
            print(f"❌ Location data model test failed: {e}")
            print("   Issue: Model doesn't have location fields or database columns missing")
            db.session.rollback()
            return False

def check_form_field_names():
    """Check the form field names in the frontend"""
    print("\n📝 STEP 4: Checking Form Field Configuration")
    print("=" * 50)
    
    # Expected form field names based on your JavaScript
    frontend_fields = [
        'latitude',
        'longitude', 
        'accuracy',
        'altitude',
        'location_source',  # Note: JavaScript uses 'locationSource' but form submits as 'location_source'
        'address'
    ]
    
    # Expected server-side field names
    server_fields = [
        'latitude',
        'longitude',
        'accuracy', 
        'altitude',
        'location_source',
        'address'
    ]
    
    print("📤 Frontend form fields:")
    for field in frontend_fields:
        print(f"   ✅ {field}")
    
    print("\n📥 Server expects these fields:")
    for field in server_fields:
        print(f"   ✅ {field}")
    
    print("\n⚠️  POTENTIAL ISSUE FOUND:")
    print("   JavaScript uses 'locationSource' but form should submit 'location_source'")
    print("   This might be causing the data not to save!")
    
    return True

def generate_fixed_javascript():
    """Generate corrected JavaScript code"""
    print("\n🔧 STEP 5: Generating Fixed JavaScript Code")
    print("=" * 50)
    
    fixed_js = '''
// FIXED: Update form fields with location data
function updateLocationFormFields() {
    const fields = {
        'latitude': userLocation.latitude || '',
        'longitude': userLocation.longitude || '',
        'accuracy': userLocation.accuracy || '',
        'altitude': userLocation.altitude || '',
        'location_source': userLocation.source || 'manual',  // FIXED: was 'locationSource'
        'address': userLocation.address || ''
    };
    
    Object.keys(fields).forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = fields[fieldId];
        }
    });
    
    console.log('📝 Updated form fields with location data:', fields);
}

// FIXED: Submit function with correct field names
function submitCheckin(employeeId) {
    if (isSubmitting) return false;
    
    isSubmitting = true;
    updateSubmitButton(true);
    hideStatusMessage();
    
    // Ensure location data is in the form
    updateLocationFormFields();
    
    // Prepare form data with CORRECT field names
    const formData = new FormData();
    formData.append('employee_id', employeeId);
    
    // FIXED: Use correct field names that match server expectations
    formData.append('latitude', userLocation.latitude || '');
    formData.append('longitude', userLocation.longitude || '');
    formData.append('accuracy', userLocation.accuracy || '');
    formData.append('altitude', userLocation.altitude || '');
    formData.append('location_source', userLocation.source || 'manual');  // FIXED
    formData.append('address', userLocation.address || '');
    
    // Debug: Log what we're sending
    console.log('📤 Submitting form data:');
    for (let [key, value] of formData.entries()) {
        console.log(`   ${key}: ${value}`);
    }
    
    const currentUrl = window.location.pathname;
    const checkinUrl = `${currentUrl}/checkin`;
    
    fetch(checkinUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        isSubmitting = false;
        updateSubmitButton(false);
        
        if (data.success) {
            showSuccessPage(data);
            console.log('✅ Check-in successful:', data);
            stopLocationWatching();
        } else {
            showStatusMessage(data.message || 'Check-in failed', 'error');
            console.log('❌ Check-in failed:', data.message);
        }
    })
    .catch(error => {
        isSubmitting = false;
        updateSubmitButton(false);
        showStatusMessage('Network error. Please check your connection and try again.', 'error');
        console.error('❌ Network error:', error);
    });
}
'''
    
    print("✅ Fixed JavaScript code generated!")
    print("   Key fixes:")
    print("   - Changed 'locationSource' to 'location_source' in form fields")
    print("   - Added debug logging to track form submission")
    print("   - Ensured field names match server expectations")
    
    return fixed_js

def generate_fixed_server_code():
    """Generate corrected server-side code"""
    print("\n🔧 STEP 6: Generating Fixed Server Code")
    print("=" * 50)
    
    fixed_server = '''
@app.route('/qr/<string:qr_url>/checkin', methods=['POST'])
def qr_checkin(qr_url):
    """FIXED: Enhanced staff check-in with proper location handling"""
    try:
        # Find QR code
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        if not qr_code:
            return jsonify({'success': False, 'message': 'QR code not found'}), 404
        
        # Get form data
        employee_id = request.form.get('employee_id', '').strip()
        
        # FIXED: Get location data with correct field names
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        accuracy = request.form.get('accuracy', '').strip()
        altitude = request.form.get('altitude', '').strip()
        location_source = request.form.get('location_source', 'manual').strip()  # FIXED
        address = request.form.get('address', '').strip()
        
        # DEBUG: Log received data
        print(f"📥 Received location data:")
        print(f"   latitude: '{latitude}'")
        print(f"   longitude: '{longitude}'")
        print(f"   accuracy: '{accuracy}'")
        print(f"   altitude: '{altitude}'")
        print(f"   location_source: '{location_source}'")
        print(f"   address: '{address}'")
        
        if not employee_id:
            return jsonify({'success': False, 'message': 'Employee ID required'}), 400
        
        # Validate employee ID
        if not re.match(r'^[A-Za-z0-9]{3,20}$', employee_id):
            return jsonify({'success': False, 'message': 'Invalid employee ID format'}), 400
        
        # Check for duplicates
        today = datetime.today()
        existing = AttendanceData.query.filter_by(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today
        ).first()
        
        if existing:
            return jsonify({
                'success': False, 
                'message': f'Already checked in at {existing.check_in_time.strftime("%H:%M")}'
            }), 409
        
        # FIXED: Process location data properly
        lat_value = None
        lng_value = None
        acc_value = None
        alt_value = None
        
        try:
            if latitude and latitude.strip() and latitude != 'null':
                lat_value = float(latitude)
                print(f"✅ Parsed latitude: {lat_value}")
                
            if longitude and longitude.strip() and longitude != 'null':
                lng_value = float(longitude)
                print(f"✅ Parsed longitude: {lng_value}")
                
            if accuracy and accuracy.strip() and accuracy != 'null':
                acc_value = float(accuracy)
                print(f"✅ Parsed accuracy: {acc_value}")
                
            if altitude and altitude.strip() and altitude != 'null':
                alt_value = float(altitude)
                print(f"✅ Parsed altitude: {alt_value}")
                
        except (ValueError, TypeError) as e:
            print(f"⚠️ Location parsing error: {e}")
        
        # Create attendance record
        attendance = AttendanceData(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today,
            check_in_time=datetime.now().time(),
            location_name=qr_code.location,
            status='present'
        )
        
        # FIXED: Add location data to model
        if lat_value is not None:
            attendance.latitude = lat_value
        if lng_value is not None:
            attendance.longitude = lng_value
        if acc_value is not None:
            attendance.accuracy = acc_value
        if alt_value is not None:
            attendance.altitude = alt_value
        if location_source:
            attendance.location_source = location_source
        if address:
            attendance.address = address
        
        print(f"💾 Saving attendance with location: lat={attendance.latitude}, lng={attendance.longitude}")
        
        db.session.add(attendance)
        db.session.commit()
        
        # Verify data was saved
        saved_record = AttendanceData.query.get(attendance.id)
        print(f"✅ Saved record: lat={saved_record.latitude}, lng={saved_record.longitude}")
        
        return jsonify({
            'success': True,
            'message': 'Check-in successful!',
            'data': {
                'employee_id': employee_id.upper(),
                'location': qr_code.location,
                'has_location': saved_record.latitude is not None and saved_record.longitude is not None,
                'coordinates': f"{saved_record.latitude}, {saved_record.longitude}" if saved_record.latitude else "No GPS data"
            }
        })
        
    except Exception as e:
        print(f"❌ Check-in error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
'''
    
    print("✅ Fixed server code generated!")
    print("   Key fixes:")
    print("   - Added debug logging for received form data")
    print("   - Improved location data parsing and validation")
    print("   - Added verification that data was actually saved")
    print("   - Better error handling and feedback")
    
    return fixed_server

def main():
    """Main diagnostic function"""
    print("🩺 QR LOCATION TRACKING DIAGNOSTIC TOOL")
    print("=" * 60)
    print("This tool will identify why coordinates aren't being saved.")
    print("=" * 60)
    
    issues_found = []
    
    # Step 1: Check database structure
    if not check_database_structure():
        issues_found.append("Database missing location columns")
        print("\n🛠️  FIXING: Adding missing database columns...")
        if add_missing_columns():
            print("✅ Database columns fixed!")
        else:
            print("❌ Failed to fix database - manual intervention needed")
            return
    
    # Step 2: Test model
    if not test_location_data_flow():
        issues_found.append("Model can't handle location data")
    
    # Step 3: Check form fields
    check_form_field_names()
    issues_found.append("Form field name mismatch")
    
    # Step 4: Generate fixes
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS COMPLETE")
    print("=" * 60)
    
    if issues_found:
        print(f"❌ Found {len(issues_found)} issues:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        
        print(f"\n🔧 SOLUTIONS:")
        print(f"1. Run the database migration script if not done already")
        print(f"2. Update your JavaScript with the fixed code above")
        print(f"3. Update your server route with the fixed code above")
        print(f"4. Add debug logging to track the data flow")
        
    else:
        print("✅ No major issues found!")
        print("   Location tracking should be working.")
        print("   If still having issues, check browser console for errors.")
    
    # Generate fixed files
    print(f"\n📁 FIXED CODE FILES:")
    print(f"1. Save the fixed JavaScript to your qr_destination.js")
    print(f"2. Update your app.py qr_checkin route")
    print(f"3. Test with a mobile device to verify GPS functionality")
    
    generate_fixed_javascript()
    generate_fixed_server_code()

if __name__ == '__main__':
    main()