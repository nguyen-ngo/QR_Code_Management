from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, time, timedelta
from sqlalchemy import text
from user_agents import parse
import io, os, base64, re, uuid, requests, json, qrcode, math
from PIL import Image, ImageDraw
from math import radians, sin, cos, asin, sqrt
from dotenv import load_dotenv
# Import the logging handler
from logger_handler import AppLogger, log_user_activity, log_database_operations


# Load environment variables in .env
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config['TEMPLATES_AUTO_RELOAD'] = os.environ.get('TEMPLATES_AUTO_RELOAD')

# Initialize database
db = SQLAlchemy(app)

# Valid user roles with new additions
VALID_ROLES = ['admin', 'staff', 'payroll', 'project_manager']

# Roles that have staff-level permissions (non-admin roles)
STAFF_LEVEL_ROLES = ['staff', 'payroll', 'project_manager']

# Import and initialize models
from models import set_db
User, QRCode, QRCodeStyle, Project, AttendanceData = set_db(db)

# Initialize the logging system
logger_handler = AppLogger(app, db)

# Utility functions
def is_valid_role(role):
    """Check if role is valid"""
    return role in VALID_ROLES

def has_admin_privileges(role):
    """Check if role has admin privileges"""
    return role == 'admin'

def has_staff_level_access(role):
    """Check if role has staff-level access (includes new roles)"""
    return role in STAFF_LEVEL_ROLES

def get_role_permissions(role):
    """Get permissions description for a role"""
    permissions = {
        'admin': {
            'title': 'Administrator Permissions',
            'permissions': [
                'Full QR code management (create, edit, delete)',
                'Complete user management capabilities',
                'System configuration access',
                'View all system analytics',
                'Bulk operations and data export',
                'Access to all admin features'
            ],
            'restrictions': ['With great power comes great responsibility!']
        },
        'staff': {
            'title': 'Staff User Permissions',
            'permissions': [
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        },
        'payroll': {
            'title': 'Payroll Specialist Permissions',
            'permissions': [
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
                'Access dashboard and reports',
                'Same permissions as Staff (additional features coming soon)'
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        },
        'project_manager': {
            'title': 'Project Manager Permissions',
            'permissions': [
                'Create and edit QR codes',
                'View all QR codes in the system',
                'Download QR code images',
                'Update personal profile information',
                'Access dashboard and reports',
                'Same permissions as Staff (additional features coming soon)'
            ],
            'restrictions': [
                'Cannot delete QR codes',
                'Cannot manage other users',
                'Cannot access admin settings'
            ]
        }
    }
    return permissions.get(role, {})
    
def get_coordinates_from_address(address):
    """
    Get latitude and longitude from address using geocoding service
    Returns (lat, lng) tuple or (None, None) if failed
    """
    if not address or address.strip() == '':
        return None, None
    
    try:
        # Using a free geocoding service (Nominatim/OpenStreetMap)
        # In production, consider using Google Maps Geocoding API for better accuracy
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'QR-Attendance-System/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                print(f"✅ Geocoded address '{address[:50]}...' to coordinates: {lat}, {lng}")
                return lat, lng
        
        print(f"⚠️ Could not geocode address: {address}")
        return None, None
        
    except Exception as e:
        print(f"❌ Error geocoding address '{address}': {e}")
        return None, None

def get_coordinates_from_address_enhanced(address):
    """
    Enhanced geocoding function with better error handling
    Returns (latitude, longitude, accuracy_level)
    """
    if not address or address.strip() == "":
        print("⚠️ Empty address provided for geocoding")
        return None, None, None
    
    address = address.strip()
    print(f"🌍 Enhanced geocoding for: {address}")
    
    try:
        # Primary geocoding using Nominatim (OpenStreetMap)
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
            'extratags': 1
        }
        
        headers = {
            'User-Agent': 'QR-Attendance-System/1.0 (Enhanced Location Accuracy)'
        }
        
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            if results:
                result = results[0]
                lat = float(result['lat'])
                lng = float(result['lon'])
                
                # Enhanced accuracy assessment
                place_type = result.get('type', 'unknown')
                osm_type = result.get('osm_type', 'unknown')
                importance = float(result.get('importance', 0))
                
                # More sophisticated accuracy determination
                if place_type in ['house', 'building', 'shop', 'office'] or osm_type == 'way':
                    accuracy = 'excellent'
                elif place_type in ['neighbourhood', 'suburb', 'quarter', 'residential']:
                    accuracy = 'good'
                elif place_type in ['city', 'town', 'village'] and importance > 0.5:
                    accuracy = 'fair'
                else:
                    accuracy = 'poor'
                
                print(f"✅ Enhanced geocoding successful:")
                print(f"   Coordinates: {lat:.10f}, {lng:.10f}")
                print(f"   Accuracy: {accuracy}")
                
                return lat, lng, accuracy
            
        print(f"⚠️ No results from enhanced geocoding for: {address}")
        return None, None, None
        
    except Exception as e:
        print(f"❌ Enhanced geocoding error: {e}")
        return None, None, None
    
def geocode_address_enhanced(address):
    """
    Enhanced geocoding using Nominatim API with better accuracy classification
    Returns: (latitude, longitude, accuracy_level)
    """
    if not address or len(address.strip()) < 5:
        print("❌ Address too short for geocoding")
        return None, None, None
    
    try:
        # Nominatim API endpoint
        url = "https://nominatim.openstreetmap.org/search"
        
        params = {
            'q': address.strip(),
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': 'QR-Attendance-System/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                result = data[0]
                lat = float(result['lat'])
                lng = float(result['lon'])
                
                # Determine accuracy based on result type
                place_type = result.get('type', 'unknown')
                osm_type = result.get('osm_type', 'unknown')
                
                if place_type in ['house', 'building'] or osm_type == 'way':
                    accuracy = 'high'
                elif place_type in ['neighbourhood', 'suburb', 'quarter']:
                    accuracy = 'medium'
                else:
                    accuracy = 'low'
                
                print(f"✅ Geocoded address: {address}")
                print(f"   Coordinates: {lat:.10f}, {lng:.10f}")
                print(f"   Accuracy: {accuracy} ({place_type})")
                
                return lat, lng, accuracy
            
        print(f"⚠️ No geocoding results for address: {address}")
        return None, None, None
        
    except Exception as e:
        logger_handler.log_flask_error('geocoding_error', str(e))
        print(f"❌ Geocoding error: {e}")
        return None, None, None
    
def calculate_distance_miles(lat1, lng1, lat2, lng2):
    """
    Enhanced Haversine formula to calculate distance between two points in miles
    Improved with better precision and error handling
    """
    if any(coord is None for coord in [lat1, lng1, lat2, lng2]):
        print("⚠️ Missing coordinates for distance calculation")
        return None
    
    try:
        # Validate coordinate ranges
        if not (-90 <= lat1 <= 90) or not (-90 <= lat2 <= 90):
            print(f"⚠️ Invalid latitude values: {lat1}, {lat2}")
            return None
        
        if not (-180 <= lng1 <= 180) or not (-180 <= lng2 <= 180):
            print(f"⚠️ Invalid longitude values: {lng1}, {lng2}")
            return None
        
        # Convert decimal degrees to radians
        lat1, lng1, lat2, lng2 = map(radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
        
        # Enhanced Haversine formula for better precision
        dlng = lng2 - lng1
        dlat = lat2 - lat1
        
        # Haversine calculation
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth's radius in miles (more precise value)
        r_miles = 3959.87433
        
        # Calculate distance with enhanced precision
        distance = c * r_miles
        
        # Round to 4 decimal places for better precision
        distance = round(distance, 4)
        
        print(f"📏 Enhanced distance calculation:")
        print(f"   Point 1: {lat1*180/3.14159:.10f}, {lng1*180/3.14159:.10f}")
        print(f"   Point 2: {lat2*180/3.14159:.10f}, {lng2*180/3.14159:.10f}")
        print(f"   Distance: {distance:.4f} miles")
        
        return distance
        
    except Exception as e:
        print(f"❌ Error in enhanced distance calculation: {e}")
        return None

def calculate_location_accuracy(qr_address, checkin_address, checkin_lat=None, checkin_lng=None):
    """
    Calculate location accuracy by comparing QR code address with check-in location
    Returns distance in miles between the two locations
    """
    print(f"\n📍 CALCULATING LOCATION ACCURACY:")
    print(f"   QR Address: {qr_address}")
    print(f"   Check-in Address: {checkin_address}")
    print(f"   Check-in Coordinates: {checkin_lat}, {checkin_lng}")
    
    # Get QR code coordinates from address
    qr_lat, qr_lng = get_coordinates_from_address(qr_address)
    
    if qr_lat is None or qr_lng is None:
        print(f"⚠️ Could not geocode QR address, cannot calculate accuracy")
        return None
    
    # Use check-in coordinates if available, otherwise geocode check-in address
    if checkin_lat is not None and checkin_lng is not None:
        checkin_coords_lat, checkin_coords_lng = checkin_lat, checkin_lng
        print(f"✅ Using GPS coordinates for check-in location")
    else:
        checkin_coords_lat, checkin_coords_lng = get_coordinates_from_address(checkin_address)
        if checkin_coords_lat is None or checkin_coords_lng is None:
            print(f"⚠️ Could not geocode check-in address, cannot calculate accuracy")
            return None
        print(f"✅ Using geocoded coordinates for check-in address")
    
    # Calculate distance
    distance = calculate_distance_miles(qr_lat, qr_lng, checkin_coords_lat, checkin_coords_lng)
    
    if distance is not None:
        print(f"✅ Location accuracy calculated: {distance} miles")
    
    return distance

def calculate_location_accuracy_enhanced(qr_address, checkin_address, checkin_lat=None, checkin_lng=None):
    """
    ENHANCED location accuracy calculation comparing QR address with check-in location
    This function provides improved precision and better error handling
    Returns:
    - Distance in miles between QR location and check-in location
    """
    print(f"\n🎯 ENHANCED LOCATION ACCURACY CALCULATION:")
    print(f"   QR Address: {qr_address}")
    print(f"   Check-in Address: {checkin_address}")
    print(f"   Check-in GPS: {checkin_lat}, {checkin_lng}")
    print(f"   Timestamp: {datetime.now()}")
    
    # Validate input parameters
    if not qr_address or qr_address.strip() == "":
        print(f"❌ QR address is empty or invalid")
        return None
    
    # Step 1: Get coordinates for QR address using enhanced geocoding
    print(f"\n📍 Step 1: Geocoding QR address...")
    try:
        qr_lat, qr_lng, qr_accuracy = get_coordinates_from_address_enhanced(qr_address)
        print(f"   Geocoding result: lat={qr_lat}, lng={qr_lng}, accuracy={qr_accuracy}")
        
        if qr_lat is None or qr_lng is None:
            print(f"❌ Could not geocode QR address: {qr_address}")
            return None
        
        print(f"✅ QR location coordinates: {qr_lat:.10f}, {qr_lng:.10f} (accuracy: {qr_accuracy})")
    except Exception as e:
        print(f"❌ Error geocoding QR address: {e}")
        return None
    
    # Step 2: Determine check-in coordinates
    print(f"\n📱 Step 2: Determining check-in coordinates...")
    
    checkin_coords_lat = None
    checkin_coords_lng = None
    checkin_source = "unknown"
    
    # Priority 1: Use GPS coordinates if available and valid
    if checkin_lat is not None and checkin_lng is not None:
        try:
            lat_val = float(checkin_lat)
            lng_val = float(checkin_lng)
            
            # Validate GPS coordinates
            if -90 <= lat_val <= 90 and -180 <= lng_val <= 180:
                checkin_coords_lat = lat_val
                checkin_coords_lng = lng_val
                checkin_source = "gps"
                print(f"✅ Using GPS coordinates: {lat_val:.10f}, {lng_val:.10f}")
            else:
                print(f"⚠️ Invalid GPS coordinates: {lat_val}, {lng_val}")
        except (ValueError, TypeError) as e:
            print(f"⚠️ Could not parse GPS coordinates: {e}")
    
    # Priority 2: Fallback to geocoding check-in address
    if checkin_coords_lat is None and checkin_address:
        print(f"🌍 Falling back to geocoding check-in address...")
        try:
            checkin_coords_lat, checkin_coords_lng, checkin_accuracy = get_coordinates_from_address_enhanced(checkin_address)
            print(f"   Checkin geocoding result: lat={checkin_coords_lat}, lng={checkin_coords_lng}, accuracy={checkin_accuracy}")
            
            if checkin_coords_lat is not None:
                checkin_source = "address"
                print(f"✅ Using geocoded coordinates: {checkin_coords_lat:.10f}, {checkin_coords_lng:.10f} (accuracy: {checkin_accuracy})")
        except Exception as e:
            print(f"❌ Error geocoding check-in address: {e}")
    
    # Check if we have valid coordinates for both locations
    if checkin_coords_lat is None or checkin_coords_lng is None:
        print(f"❌ Could not determine check-in coordinates")
        print(f"   GPS: {checkin_lat}, {checkin_lng}")
        print(f"   Address: {checkin_address}")
        return None
    
    # Step 3: Calculate distance
    print(f"\n📏 Step 3: Calculating distance...")
    try:
        print(f"   QR coordinates: {qr_lat:.10f}, {qr_lng:.10f}")
        print(f"   Check-in coordinates: {checkin_coords_lat:.10f}, {checkin_coords_lng:.10f}")
        print(f"   Source: {checkin_source}")
        
        distance = calculate_distance_miles(qr_lat, qr_lng, checkin_coords_lat, checkin_coords_lng)
        print(f"   Distance calculation result: {distance}")
        
        if distance is not None:
            accuracy_level = get_location_accuracy_level_enhanced(distance)
            print(f"✅ Enhanced location accuracy calculated successfully!")
            print(f"   Distance: {distance:.4f} miles")
            print(f"   Accuracy Level: {accuracy_level}")
            return distance
        else:
            print(f"❌ Distance calculation returned None")
            return None
            
    except Exception as e:
        print(f"❌ Error calculating distance: {e}")
        import traceback
        print(f"❌ Distance calculation traceback: {traceback.format_exc()}")
        return None

def generate_qr_url(name, qr_id):
    """Generate a unique URL for QR code destination"""
    # Clean the name for URL use
    clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    clean_name = re.sub(r'\s+', '-', clean_name.strip())
    clean_name = clean_name.lower()
    
    # Create unique URL
    url_slug = f"qr-{qr_id}-{clean_name}"
    return url_slug[:200]  # Limit length

def detect_device_info(user_agent_string):
    """Extract device information from user agent"""
    try:
        user_agent = parse(user_agent_string)
        device_info = f"{user_agent.device.family}"
        
        if user_agent.os.family:
            device_info += f" - {user_agent.os.family}"
            if user_agent.os.version_string:
                device_info += f" {user_agent.os.version_string}"
        
        if user_agent.browser.family:
            device_info += f" ({user_agent.browser.family})"
            
        return device_info[:200]  # Limit length
    except:
        return "Unknown Device"

def get_client_ip():
    """Get client IP address"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

def get_location_accuracy_level_enhanced(location_accuracy):
    """
    Enhanced function to categorize location accuracy with more granular levels
    """
    if not location_accuracy or location_accuracy is None:
        return 'unknown'
    
    # More precise accuracy thresholds
    if location_accuracy <= 0.05:  # Within 264 feet (50 meters)
        return 'excellent'
    elif location_accuracy <= 0.1:  # Within 528 feet (100 meters)
        return 'very_good'
    elif location_accuracy <= 0.25:  # Within 0.25 mile (1320 feet)
        return 'good'
    elif location_accuracy <= 0.5:   # Within 0.5 mile
        return 'fair'
    elif location_accuracy <= 1.0:   # Within 1 mile
        return 'poor'
    else:                            # Greater than 1 mile
        return 'very_poor'

def process_location_data(location_data):
    """
    Process and validate location data from form
    Returns clean location data or None values for invalid data
    """
    processed = {
        'latitude': None,
        'longitude': None,
        'accuracy': None,
        'altitude': None,
        'source': location_data.get('location_source', 'manual'),
        'address': location_data.get('address', '')[:500] if location_data.get('address') else None
    }
    
    try:
        # Process latitude
        if location_data.get('latitude') and location_data['latitude'] not in ['null', '']:
            lat = float(location_data['latitude'])
            if -90 <= lat <= 90:  # Valid latitude range
                processed['latitude'] = lat
            else:
                print(f"⚠️ Invalid latitude: {lat}")
        
        # Process longitude
        if location_data.get('longitude') and location_data['longitude'] not in ['null', '']:
            lng = float(location_data['longitude'])
            if -180 <= lng <= 180:  # Valid longitude range
                processed['longitude'] = lng
            else:
                print(f"⚠️ Invalid longitude: {lng}")
        
        # Process accuracy
        if location_data.get('accuracy') and location_data['accuracy'] not in ['null', '']:
            acc = float(location_data['accuracy'])
            if acc >= 0:  # Accuracy should be positive
                processed['accuracy'] = acc
            else:
                print(f"⚠️ Invalid accuracy: {acc}")
        
        # Process altitude
        if location_data.get('altitude') and location_data['altitude'] not in ['null', '']:
            alt = float(location_data['altitude'])
            # Altitude can be negative (below sea level)
            processed['altitude'] = alt
            
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error processing location data: {e}")
    
    return processed

def reverse_geocode_coordinates(latitude, longitude):
    """
    Convert GPS coordinates to human-readable address using reverse geocoding
    Returns address string or None if failed
    """
    if not latitude or not longitude:
        return None
    
    try:
        print(f"🌍 Reverse geocoding coordinates: {latitude}, {longitude}")
        
        # Using Nominatim (OpenStreetMap) reverse geocoding service
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 18  # High detail level
        }
        
        headers = {
            'User-Agent': 'QR-Attendance-System/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data and 'display_name' in data:
                address = data['display_name']
                print(f"✅ Reverse geocoded address: {address}")
                return address
            else:
                print(f"⚠️ No address found for coordinates")
                return None
        else:
            print(f"⚠️ Reverse geocoding API returned status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error in reverse geocoding: {e}")
        return None

def process_location_data_enhanced(form_data):
    """
    Enhanced processing of location data from form submission
    Validates and cleans location data for storage, including reverse geocoding
    """
    processed = {
        'latitude': None,
        'longitude': None,
        'accuracy': None,
        'altitude': None,
        'source': form_data.get('location_source', 'manual'),
        'address': None
    }
    
    try:
        # Process latitude
        if form_data.get('latitude') and form_data['latitude'] not in ['null', '', 'undefined']:
            lat = float(form_data['latitude'])
            if -90 <= lat <= 90:  # Valid latitude range
                processed['latitude'] = lat
            else:
                print(f"⚠️ Invalid latitude: {lat}")
        
        # Process longitude
        if form_data.get('longitude') and form_data['longitude'] not in ['null', '', 'undefined']:
            lng = float(form_data['longitude'])
            if -180 <= lng <= 180:  # Valid longitude range
                processed['longitude'] = lng
            else:
                print(f"⚠️ Invalid longitude: {lng}")
        
        # Process GPS accuracy
        if form_data.get('accuracy') and form_data['accuracy'] not in ['null', '', 'undefined']:
            acc = float(form_data['accuracy'])
            if acc >= 0:  # Accuracy should be positive
                processed['accuracy'] = acc
            else:
                print(f"⚠️ Invalid GPS accuracy: {acc}")
        
        # Process altitude
        if form_data.get('altitude') and form_data['altitude'] not in ['null', '', 'undefined']:
            alt = float(form_data['altitude'])
            processed['altitude'] = alt
        
        # Process address - First check if address was provided
        if form_data.get('address'):
            address = form_data['address'].strip()
            if address and address not in ['null', '', 'undefined']:
                # Check if the address is just coordinates (like "38.8104192000, -77.1850240000")
                if re.match(r'^-?\d+\.\d+,?\s*-?\d+\.\d+$', address.replace(' ', '')):
                    print(f"🔍 Detected coordinate-format address: {address}")
                    # This is just coordinates, we need to reverse geocode
                    processed['address'] = None  # Reset so reverse geocoding will trigger
                else:
                    # This is a real address
                    processed['address'] = address[:500]  # Limit to 500 characters
                    print(f"✅ Using provided address: {processed['address'][:100]}...")
        
        # CRITICAL: If we have coordinates but no real address, perform reverse geocoding
        if (processed['latitude'] is not None and processed['longitude'] is not None 
            and not processed['address']):
            print(f"🌍 Performing reverse geocoding for coordinates: {processed['latitude']}, {processed['longitude']}")
            reverse_geocoded_address = reverse_geocode_coordinates(processed['latitude'], processed['longitude'])
            if reverse_geocoded_address:
                processed['address'] = reverse_geocoded_address[:500]
                print(f"✅ Reverse geocoded address: {processed['address']}")
            else:
                print(f"⚠️ Could not reverse geocode coordinates, keeping coordinates as fallback")
                processed['address'] = f"{processed['latitude']:.10f}, {processed['longitude']:.10f}"
        
        print(f"📍 Final processed location data:")
        print(f"   Coordinates: {processed['latitude']}, {processed['longitude']}")
        print(f"   GPS Accuracy: {processed['accuracy']}m")
        print(f"   Source: {processed['source']}")
        print(f"   Address: {processed['address'][:100] if processed['address'] else 'None'}...")
        
        return processed
        
    except Exception as e:
        print(f"❌ Error processing location data: {e}")
        return processed

def migrate_to_enhanced_location_accuracy():
    """
    Migration function to recalculate all existing records with enhanced accuracy
    """
    try:
        print("🔄 Starting enhanced location accuracy migration...")
        
        # Get all records that need recalculation
        records = db.session.execute(text("""
            SELECT ad.id, qc.location_address, ad.address, ad.latitude, ad.longitude, ad.location_accuracy
            FROM attendance_data ad
            LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
            WHERE qc.location_address IS NOT NULL
        """)).fetchall()
        
        print(f"📊 Found {len(records)} records to process")
        
        updated_count = 0
        improved_count = 0
        
        for record in records:
            try:
                # Calculate enhanced location accuracy
                new_accuracy = calculate_location_accuracy_enhanced(
                    qr_address=record.location_address,
                    checkin_address=record.address,
                    checkin_lat=record.latitude,
                    checkin_lng=record.longitude
                )
                
                if new_accuracy is not None:
                    # Update the record
                    db.session.execute(text("""
                        UPDATE attendance_data 
                        SET location_accuracy = :accuracy
                        WHERE id = :record_id
                    """), {
                        'accuracy': new_accuracy,
                        'record_id': record.id
                    })
                    
                    updated_count += 1
                    
                    # Check if this is an improvement
                    if record.location_accuracy is None or abs(new_accuracy - (record.location_accuracy or 0)) > 0.001:
                        improved_count += 1
                        print(f"   ✅ Updated record {record.id}: {record.location_accuracy} → {new_accuracy:.4f} miles")
                
            except Exception as e:
                print(f"   ⚠️ Error processing record {record.id}: {e}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Enhanced migration completed!")
        print(f"   📊 Records processed: {len(records)}")
        print(f"   ✅ Records updated: {updated_count}")
        print(f"   📈 Records improved: {improved_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced migration failed: {e}")
        db.session.rollback()
        return False

def check_location_accuracy_column_exists():
    """
    Check if location_accuracy column exists in attendance_data table (MySQL compatible)
    """
    try:
        # MySQL-compatible query for checking column existence
        result = db.session.execute(text("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'attendance_data' 
            AND COLUMN_NAME = 'location_accuracy'
        """))
        
        count = result.fetchone().count
        return count > 0
        
    except Exception as e:
        print(f"Error checking location_accuracy column: {e}")
        return False

def get_employee_checkin_history(employee_id, qr_code_id, date_filter=None):
    """
    Get check-in history for an employee at a specific location
    """
    try:
        if date_filter is None:
            date_filter = date.today()
        
        checkins = AttendanceData.query.filter_by(
            employee_id=employee_id.upper(),
            qr_code_id=qr_code_id,
            check_in_date=date_filter
        ).order_by(AttendanceData.check_in_time.asc()).all()
        
        return checkins
        
    except Exception as e:
        print(f"❌ Error retrieving checkin history: {e}")
        return []

def format_checkin_intervals(checkins):
    """
    Format time intervals between check-ins for display
    """
    if len(checkins) < 2:
        return []
    
    intervals = []
    for i in range(1, len(checkins)):
        previous_time = datetime.combine(checkins[i-1].check_in_date, checkins[i-1].check_in_time)
        current_time = datetime.combine(checkins[i].check_in_date, checkins[i].check_in_time)
        
        interval = current_time - previous_time
        interval_minutes = int(interval.total_seconds() / 60)
        
        intervals.append({
            'from_time': checkins[i-1].check_in_time.strftime('%H:%M'),
            'to_time': checkins[i].check_in_time.strftime('%H:%M'),
            'interval_minutes': interval_minutes,
            'interval_text': format_time_interval(interval_minutes)
        })
    
    return intervals

def format_time_interval(minutes):
    """
    Format minutes into human-readable time interval
    """
    if minutes < 60:
        return f"{minutes} minutes"
    elif minutes < 1440:  # Less than 24 hours
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours}h {remaining_minutes}m"
    else:
        days = minutes // 1440
        remaining_hours = (minutes % 1440) // 60
        if remaining_hours == 0:
            return f"{days} day{'s' if days != 1 else ''}"
        else:
            return f"{days}d {remaining_hours}h"
            
# Authentication decorator
def login_required(f):
    """Decorator to ensure user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to ensure user has admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user_role = session.get('role')
        if not has_admin_privileges(user_role):
            flash('Administrator privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def staff_or_admin_required(f):
    """Decorator to ensure user has staff-level or admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user_role = session.get('role')
        if not (has_admin_privileges(user_role) or has_staff_level_access(user_role)):
            flash('Insufficient privileges to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Add this helper function to check admin requirements more safely
def is_admin_user(user_id):
    """Helper function to safely check if user is admin"""
    try:
        user = User.Query.get(user_id)
        return user and user.active_status and user.role == 'admin'
    except:
        return False

# Utility function to generate QR code
def generate_qr_code(data, fill_color="black", back_color="white", box_size=10, border=4, error_correction='L'):
    # Error correction mapping
    error_correction_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H
    }
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction_map.get(error_correction, qrcode.constants.ERROR_CORRECT_L),
            box_size=int(box_size),
            border=int(border),
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Generate QR code image with custom colors
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Log successful generation if logger is available
        try:
            logger_handler.log_qr_code_generated(
                data_length=len(data),
                fill_color=fill_color,
                back_color=back_color,
                box_size=box_size,
                border=border,
                error_correction=error_correction
            )
        except:
            pass  # Ignore logging errors
        
        return img_str
        
    except Exception as e:
        logger_handler.log_database_error('qr_code_generation', e)
        # Return default QR code on error
        return generate_default_qr_code(data)
    
def generate_default_qr_code(data):
    """Fallback function for basic QR code generation"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

def get_qr_styling(qr_code):
    """Extract QR code styling parameters from database record"""
    return {
        'fill_color': getattr(qr_code, 'fill_color', '#000000') or '#000000',
        'back_color': getattr(qr_code, 'back_color', '#FFFFFF') or '#FFFFFF',
        'box_size': getattr(qr_code, 'box_size', 10) or 10,
        'border': getattr(qr_code, 'border', 4) or 4,
        'error_correction': getattr(qr_code, 'error_correction', 'L') or 'L'
    }

@app.template_filter('strftime')
def strftime_filter(value, format='%m/%d/%Y'):
    """Format datetime/date/string as strftime"""
    if isinstance(value, str):
        if value.lower() == 'now':
            return datetime.now().strftime(format)
        try:
            # Try to parse string as datetime
            dt = datetime.fromisoformat(value)
            return dt.strftime(format)
        except (ValueError, TypeError):
            return value
    
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    
    return str(value)

# Routes
@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@log_user_activity('user_registration')
def register():
    """User registration endpoint"""
    if request.method == 'POST':
        try:
            full_name = request.form['full_name']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template('register.html')
            
            # Create new user (default role: staff)
            new_user = User(
                full_name=full_name,
                email=email,
                username=username,
                role='staff'
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log successful user registration
            logger_handler.logger.info(f"New user registered: {username} ({email})")
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('user_registration', e)
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced user authentication with comprehensive logging"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        try:
            # Find user (case-insensitive username)
            user = User.query.filter(
                User.username.like(username),
                User.active_status == True
            ).first()
            
            if user and user.check_password(password):
                # Successful login
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['full_name'] = user.full_name
                session['login_time'] = datetime.now().isoformat()
                
                # Update last login date
                user.last_login_date = datetime.utcnow()
                db.session.commit()
                
                # Log successful login
                logger_handler.log_user_login(
                    user_id=user.id,
                    username=user.username,
                    success=True
                )
                
                flash(f'Welcome back, {user.full_name}!', 'success')
                print(f"User {user.username} logged in successfully")
                
                # Redirect to intended page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
                
            else:
                # Invalid credentials - log failed attempt
                user_id = user.id if user else None
                logger_handler.log_user_login(
                    user_id=user_id,
                    username=username,
                    success=False,
                    failure_reason="Invalid credentials"
                )
                
                flash('Invalid username or password.', 'error')
                print(f"Failed login attempt for username: {username}")
                
        except Exception as e:
            logger_handler.log_database_error('user_login', e)
            print(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout endpoint with session duration logging"""
    user_id = session.get('user_id')
    username = session.get('username')
    login_time_str = session.get('login_time')
    
    # Calculate session duration
    session_duration = None
    if login_time_str:
        try:
            login_time = datetime.fromisoformat(login_time_str)
            session_duration = (datetime.now() - login_time).total_seconds() / 60  # minutes
        except:
            pass
    
    # Log user logout
    if user_id and username:
        logger_handler.log_user_logout(
            user_id=user_id,
            username=username,
            session_duration=session_duration
        )
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Enhanced project-centric dashboard"""
    try:
        user = User.query.get(session['user_id'])
        
        # Get ALL QR codes and projects for project-centric view
        qr_codes = QRCode.query.order_by(QRCode.created_date.desc()).all()
        projects = Project.query.order_by(Project.name.asc()).all()
        
        # Log dashboard access with project info
        logger_handler.logger.info(f"User {session['username']} accessed project dashboard: {len(qr_codes)} QR codes, {len(projects)} projects")
        
        return render_template('dashboard.html', 
                             user=user, 
                             qr_codes=qr_codes, 
                             projects=projects)
        
    except Exception as e:
        logger_handler.log_database_error('dashboard_load', e)
        print(f"Error loading dashboard: {e}")
        flash('Error loading dashboard. Please try again.', 'error')
        return redirect(url_for('login'))

# User management routes
@app.route('/profile', methods=['GET', 'POST'])
@login_required
@log_user_activity('profile_update')
def profile():
    """User profile management with logging"""
    try:
        user = User.query.get(session['user_id'])
        
        if request.method == 'POST':
            form_type = request.form.get('form_type')
            
            if form_type == 'profile':
                # Track changes for logging
                old_name = user.full_name
                old_email = user.email
                
                # Update profile information
                user.full_name = request.form['full_name']
                user.email = request.form['email']
                
                # Check for changes
                changes = {}
                if old_name != user.full_name:
                    changes['full_name'] = {'old': old_name, 'new': user.full_name}
                if old_email != user.email:
                    changes['email'] = {'old': old_email, 'new': user.email}
                
                db.session.commit()
                
                # Log profile update if there were changes
                if changes:
                    logger_handler.logger.info(f"User profile updated: {user.username} - Changes: {json.dumps(changes)}")
                
                flash('Profile updated successfully!', 'success')
                
            elif form_type == 'password':
                # Update password
                current_password = request.form['current_password']
                new_password = request.form['new_password']
                
                if user.check_password(current_password):
                    user.set_password(new_password)
                    db.session.commit()
                    
                    # Log password change
                    logger_handler.log_security_event(
                        event_type="password_change",
                        description=f"User {user.username} changed password",
                        severity="MEDIUM"
                    )
                    
                    flash('Password updated successfully!', 'success')
                else:
                    # Log failed password change attempt
                    logger_handler.log_security_event(
                        event_type="password_change_failed",
                        description=f"Failed password change attempt for user {user.username}",
                        severity="HIGH"
                    )
                    flash('Current password is incorrect.', 'error')
        
        return render_template('profile.html', user=user)
        
    except Exception as e:
        logger_handler.log_database_error('profile_update', e)
        flash('Profile update failed. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/users')
@admin_required
def users():
    """Display all users (Admin only)"""
    try:
        users = User.query.order_by(User.created_date.desc()).all()
        return render_template('users.html', users=users)
    except Exception as e:
        logger_handler.log_database_error('users_list', e)
        flash('Error loading users list.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/users/create', methods=['GET', 'POST'])
@admin_required
@log_database_operations('user_creation')
def create_user():
    """Create new user (Admin only)"""
    if request.method == 'POST':
        try:
            full_name = request.form['full_name']
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            
            # Validate role
            if role not in VALID_ROLES:
                flash(f'Invalid role selected. Valid roles: {", ".join(VALID_ROLES)}', 'error')
                return render_template('create_user.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'error')
                return render_template('create_user.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
                return render_template('create_user.html')
            
            # Create new user
            new_user = User(
                full_name=full_name,
                email=email,
                username=username,
                role=role,
                created_by=session['user_id']
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log user creation
            logger_handler.logger.info(f"Admin user {session['username']} created new user: {username} with role {role}")
            
            flash(f'User "{full_name}" created successfully with role "{role}".', 'success')
            return redirect(url_for('users'))
            
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('user_creation', e)
            flash('Failed to create user. Please try again.', 'error')
    
    return render_template('create_user.html', valid_roles=VALID_ROLES)

@app.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    """Deactivate user (Admin only) - Fixed with proper validation"""
    try:
        user_to_delete = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_delete:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        # Prevent self-deletion
        if user_to_delete.id == current_user.id:
            flash('You cannot deactivate your own account. Ask another admin to do this.', 'error')
            return redirect(url_for('users'))
        
        # Check if trying to delete the last admin
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate the last admin user. Promote another user to admin first.', 'error')
                return redirect(url_for('users'))
        
        # Deactivate the user instead of deleting
        user_to_delete.active_status = False
        db.session.commit()
        
        flash(f'User "{user_to_delete.full_name}" has been deactivated successfully.', 'success')
        print(f"Admin {current_user.username} deactivated user: {user_to_delete.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deactivating user: {e}")
        flash('Error deactivating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/reactivate', methods=['GET', 'POST'])
@admin_required
def reactivate_user(user_id):
    """Reactivate a deactivated user (Admin only)"""
    try:
        user_to_reactivate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_reactivate:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if user_to_reactivate.active_status:
            flash('User is already active.', 'info')
        else:
            user_to_reactivate.active_status = True
            db.session.commit()
            flash(f'User "{user_to_reactivate.full_name}" has been reactivated successfully.', 'success')
            print(f"Admin {current_user.username} reactivated user: {user_to_reactivate.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error reactivating user: {e}")
        flash('Error reactivating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/promote', methods=['GET', 'POST'])
@admin_required
def promote_user(user_id):
    """Promote a staff user to admin (Admin only)"""
    try:
        user_to_promote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_promote:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if user_to_promote.role == 'admin':
            flash('User is already an admin.', 'info')
        else:
            user_to_promote.role = 'admin'
            db.session.commit()
            flash(f'"{user_to_promote.full_name}" has been promoted to admin.', 'success')
            print(f"Admin {current_user.username} promoted user {user_to_promote.username} to admin")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error promoting user: {e}")
        flash('Error promoting user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/demote', methods=['GET', 'POST'])
@admin_required
def demote_user(user_id):
    """Demote an admin user to staff (Admin only)"""
    try:
        user_to_demote = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_demote:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        # Prevent self-demotion
        if user_to_demote.id == current_user.id:
            flash('You cannot demote yourself. Have another admin do this.', 'error')
            return redirect(url_for('users'))
        
        # Check if this is the last admin
        active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
        if active_admin_count <= 1 and user_to_demote.role == 'admin':
            flash('Cannot demote the last admin user. Promote another user to admin first.', 'error')
            return redirect(url_for('users'))
        
        if has_staff_level_access(user_to_demote.role):
            flash('User already has staff-level permissions.', 'info')
        else:
            user_to_demote.role = 'staff'
            db.session.commit()
            flash(f'"{user_to_demote.full_name}" has been demoted to staff.', 'success')
            print(f"Admin {current_user.username} demoted user {user_to_demote.username} to staff")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error demoting user: {e}")
        flash('Error demoting user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
@log_database_operations('user_update')
def edit_user(user_id):
    """Edit user details (Admin only)"""
    try:
        user_to_edit = User.query.get_or_404(user_id)
        
        if request.method == 'POST':
            # Track changes
            changes = {}
            old_values = {
                'full_name': user_to_edit.full_name,
                'email': user_to_edit.email,
                'role': user_to_edit.role
            }
            
            # Update user details
            user_to_edit.full_name = request.form['full_name']
            user_to_edit.email = request.form['email']
            new_role = request.form['role']
            
            # Validate role
            if new_role not in VALID_ROLES:
                flash(f'Invalid role selected. Valid roles: {", ".join(VALID_ROLES)}', 'error')
                return render_template('edit_user.html', user=user_to_edit, valid_roles=VALID_ROLES)
            
            user_to_edit.role = new_role
            
            # Handle password update if provided
            new_password = request.form.get('password')
            if new_password and new_password.strip():
                user_to_edit.set_password(new_password)
                changes['password'] = 'Password updated'
            
            # Track changes
            for field, old_value in old_values.items():
                new_value = getattr(user_to_edit, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
            
            db.session.commit()
            
            # Log user update
            if changes:
                logger_handler.logger.info(f"Admin user {session['username']} updated user {user_to_edit.username}: {json.dumps(changes)}")
            
            flash(f'User "{user_to_edit.full_name}" updated successfully.', 'success')
            return redirect(url_for('users'))
        
        return render_template('edit_user.html', user=user_to_edit, valid_roles=VALID_ROLES)
        
    except Exception as e:
        logger_handler.log_database_error('user_update', e)
        flash('Error updating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status via AJAX (Admin only)"""
    try:
        user_to_toggle = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_toggle:
            return jsonify({
                'success': False,
                'message': 'User not found.'
            }), 404
        
        # Prevent self-deactivation
        if user_to_toggle.id == current_user.id:
            return jsonify({
                'success': False,
                'message': 'You cannot deactivate yourself.'
            }), 400
        
        # Check if trying to deactivate the last admin
        if (user_to_toggle.role == 'admin' and 
            user_to_toggle.active_status and 
            User.query.filter_by(role='admin', active_status=True).count() <= 1):
            return jsonify({
                'success': False,
                'message': 'Cannot deactivate the last admin user.'
            }), 400
        
        # Toggle the status
        new_status = not user_to_toggle.active_status
        user_to_toggle.active_status = new_status
        db.session.commit()
        
        action = 'activated' if new_status else 'deactivated'
        message = f'"{user_to_toggle.full_name}" has been {action} successfully.'
        
        # Log status change
        logger_handler.logger.info(f"Admin {current_user.username} {action} user {user_to_toggle.username}")
        
        print(f"Admin {current_user.username} {action} user {user_to_toggle.username}")
        
        return jsonify({
            'success': True,
            'message': message,
            'new_status': new_status,
            'user_id': user_id
        })
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_status_toggle', e)
        print(f"Error toggling user status: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating user status. Please try again.'
        }), 500

@app.route('/users/<int:user_id>/activate', methods=['GET', 'POST'])
@admin_required
def activate_user(user_id):
    """Activate a user (Admin only) - Alternative route"""
    try:
        user_to_activate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_activate:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if user_to_activate.active_status:
            flash('User is already active.', 'info')
        else:
            user_to_activate.active_status = True
            db.session.commit()
            
            # Log activation
            logger_handler.logger.info(f"Admin {current_user.username} activated user {user_to_activate.username}")
            
            flash(f'"{user_to_activate.full_name}" has been activated.', 'success')
            print(f"Admin {current_user.username} activated user {user_to_activate.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_activation', e)
        print(f"Error activating user: {e}")
        flash('Error activating user. Please try again.', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/deactivate', methods=['GET', 'POST'])
@admin_required
def deactivate_user(user_id):
    """Deactivate a user (Admin only) - Alternative route"""
    try:
        user_to_deactivate = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_deactivate:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        # Prevent self-deactivation
        if user_to_deactivate.id == current_user.id:
            flash('You cannot deactivate yourself.', 'error')
            return redirect(url_for('users'))
        
        # Check if this is the last admin
        if user_to_deactivate.role == 'admin' and user_to_deactivate.active_status:
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot deactivate the last admin user.', 'error')
                return redirect(url_for('users'))
        
        if not user_to_deactivate.active_status:
            flash('User is already inactive.', 'info')
        else:
            user_to_deactivate.active_status = False
            db.session.commit()
            
            # Log deactivation
            logger_handler.logger.info(f"Admin {current_user.username} deactivated user {user_to_deactivate.username}")
            
            flash(f'"{user_to_deactivate.full_name}" has been deactivated.', 'success')
            print(f"Admin {current_user.username} deactivated user {user_to_deactivate.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_deactivation', e)
        print(f"Error deactivating user: {e}")
        flash('Error deactivating user. Please try again.', 'error')
        return redirect(url_for('users'))

# ENHANCED USER STATISTICS API
@app.route('/api/users/stats')
@admin_required
def user_stats_api():
    """API endpoint to get user statistics for dashboard"""
    try:
        # Get current date for recent activity calculations
        one_week_ago = datetime.now() - timedelta(days=7)
        
        total_users = User.query.count()
        active_users = User.query.filter_by(active_status=True).count()
        admin_users = User.query.filter_by(role='admin', active_status=True).count()
        staff_users = User.query.filter_by(role='staff', active_status=True).count()
        payroll_users = User.query.filter_by(role='payroll', active_status=True).count()
        project_manager_users = User.query.filter_by(role='project_manager', active_status=True).count()
        inactive_users = User.query.filter_by(active_status=False).count()
        
        recent_registrations = User.query.filter(
            User.created_date >= one_week_ago
        ).count()
        
        recent_logins = User.query.filter(
            User.last_login_date >= one_week_ago
        ).count()
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'staff_users': staff_users,
            'payroll_users': payroll_users,
            'project_manager_users': project_manager_users,
            'inactive_users': inactive_users,
            'recent_registrations': recent_registrations,
            'recent_logins': recent_logins
        })
        
    except Exception as e:
        logger_handler.log_database_error('user_stats_api', e)
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': 'Failed to fetch user statistics'}), 500

@app.route('/api/roles/permissions')
@admin_required
def role_permissions_api():
    """API endpoint to get role permissions data"""
    try:
        permissions_data = {}
        for role in VALID_ROLES:
            permissions_data[role] = get_role_permissions(role)
        
        return jsonify({
            'success': True,
            'roles': permissions_data,
            'valid_roles': VALID_ROLES,
            'staff_level_roles': STAFF_LEVEL_ROLES
        })
        
    except Exception as e:
        print(f"Error fetching role permissions: {e}")
        return jsonify({'error': 'Failed to fetch role permissions'}), 500
    
@app.route('/api/geocode', methods=['POST'])
@login_required
def geocode_address():
    """API endpoint to geocode an address and return coordinates"""
    try:
        data = request.get_json()
        address = data.get('address', '').strip()
        
        if not address:
            return jsonify({
                'success': False,
                'message': 'Address is required'
            }), 400
        
        # Use the enhanced function that returns 3 values
        lat, lng, accuracy = geocode_address_enhanced(address)
        
        if lat is not None and lng is not None:
            return jsonify({
                'success': True,
                'data': {
                    'latitude': lat,
                    'longitude': lng,
                    'accuracy': accuracy,
                    'coordinates_display': f"{lat:.10f}, {lng:.10f}"
                },
                'message': f'Address geocoded successfully with {accuracy} accuracy'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to geocode the provided address. Please verify the address is complete and accurate.'
            }), 400
            
    except Exception as e:
        logger_handler.log_flask_error('geocode_api_error', str(e))
        print(f"❌ Geocoding API error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while geocoding the address'
        }), 500

@app.route('/users/<int:user_id>/permanently-delete', methods=['GET', 'POST'])
@admin_required
def permanently_delete_user(user_id):
    """Permanently delete user but preserve associated QR codes (Admin only)"""
    try:
        user_to_delete = User.query.get_or_404(user_id)
        current_user = User.query.get(session['user_id'])
        
        # Security checks
        if user_to_delete.id == current_user.id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('users'))
        
        # Only allow deletion of inactive users for safety
        if user_to_delete.active_status:
            flash('User must be deactivated before permanent deletion.', 'error')
            return redirect(url_for('users'))
        
        # If deleting an admin, ensure at least one admin remains
        if user_to_delete.role == 'admin':
            active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
            if active_admin_count <= 1:
                flash('Cannot delete the last admin user in the system.', 'error')
                return redirect(url_for('users'))
        
        user_name = user_to_delete.full_name
        user_qr_count = user_to_delete.created_qr_codes.count()
        username = user_to_delete.username
        
        # MODIFIED: Preserve QR codes by setting created_by to NULL instead of deleting them
        orphaned_qr_codes = QRCode.query.filter_by(created_by=user_id).all()
        for qr_code in orphaned_qr_codes:
            qr_code.created_by = None
        
        # Update any users that were created by this user (set created_by to None)
        created_users = User.query.filter_by(created_by=user_id).all()
        for created_user in created_users:
            created_user.created_by = None
        
        # Log user deletion before actual deletion
        logger_handler.log_security_event(
            event_type="user_permanent_deletion",
            description=f"Admin {current_user.username} permanently deleted user {username}",
            severity="HIGH",
            additional_data={'deleted_user': username, 'qr_codes_orphaned': user_qr_count}
        )
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        # Updated flash message to reflect QR codes are preserved
        flash(f'User "{user_name}" has been permanently deleted. {user_qr_count} QR codes created by this user are now orphaned but preserved.', 'success')
        print(f"Admin {current_user.username} permanently deleted user: {username}, preserved {user_qr_count} QR codes")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('user_permanent_deletion', e)
        print(f"Error permanently deleting user: {e}")
        flash('Error deleting user. Please try again.', 'error')
        return redirect(url_for('users'))
    
# Admin logging routes
@app.route('/admin/logs')
@admin_required
def admin_logs():
    """Admin logging dashboard"""
    try:
        # Get log statistics for the last 7 days
        stats = logger_handler.get_log_statistics(days=7)
        return render_template('admin_logs.html', log_stats=stats)
    except Exception as e:
        logger_handler.log_database_error('admin_logs_load', e)
        flash('Error loading log statistics.', 'error')
        return redirect(url_for('dashboard'))

# API endpoints for logging data (admin only)
@app.route('/api/logs/recent')
@admin_required
def api_recent_logs():
    """API endpoint to get recent log entries with full details and pagination support"""
    try:
        days = request.args.get('days', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        category = request.args.get('category', '')
        severity = request.args.get('severity', '')
        search = request.args.get('search', '')
        
        print(f"📊 API request - Days: {days}, Limit: {limit}, Page: {page}")
        print(f"📊 Filters - Category: {category}, Severity: {severity}, Search: {search}")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Build the base SQL query with filters
        base_sql = """
        SELECT 
            event_id,
            event_type, 
            event_category, 
            event_description, 
            event_data,
            severity_level, 
            created_timestamp, 
            username, 
            user_id,
            ip_address
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """
        
        count_sql = """
        SELECT COUNT(*) as total_count
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """
        
        params = {'cutoff_date': cutoff_date}
        
        # Add category filter
        if category:
            base_sql += " AND event_category = :category"
            count_sql += " AND event_category = :category"
            params['category'] = category
        
        # Add severity filter
        if severity:
            base_sql += " AND severity_level = :severity"
            count_sql += " AND severity_level = :severity"
            params['severity'] = severity
        
        # Add search filter
        if search:
            search_condition = " AND (event_type LIKE :search OR event_description LIKE :search OR username LIKE :search)"
            base_sql += search_condition
            count_sql += search_condition
            params['search'] = f'%{search}%'
        
        # Get total count first
        count_result = db.session.execute(text(count_sql), params).fetchone()
        total_count = count_result.total_count if count_result else 0
        
        # Add ordering, limit and offset to main query
        base_sql += " ORDER BY created_timestamp DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Execute main query
        result = db.session.execute(text(base_sql), params).fetchall()
        
        logs = []
        for row in result:
            # Parse event_data if it's JSON
            event_data = None
            if row.event_data:
                try:
                    event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                except (json.JSONDecodeError, TypeError):
                    event_data = row.event_data
            
            logs.append({
                'event_id': row.event_id,
                'event_type': row.event_type,
                'event_category': row.event_category,
                'description': row.event_description,
                'event_data': event_data,
                'severity': row.severity_level,
                'timestamp': row.created_timestamp.isoformat(),
                'username': row.username or 'System',
                'user_id': row.user_id,
                'ip_address': row.ip_address or '-'
            })
        
        print(f"📊 Returning {len(logs)} logs out of {total_count} total")
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total_count,
            'page': page,
            'limit': limit,
            'total_pages': math.ceil(total_count / limit) if total_count > 0 else 0,
            'has_next': offset + limit < total_count,
            'has_prev': page > 1
        })
        
    except Exception as e:
        logger_handler.log_database_error('api_recent_logs', e)
        print(f"Error in api_recent_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch recent logs: {str(e)}'
        }), 500

@app.route('/api/logs/stats')
@admin_required
def api_log_stats():
    """API endpoint to get logging statistics"""
    try:
        days = request.args.get('days', 7, type=int)
        print(f"📊 Getting log statistics for last {days} days")
        
        # Get statistics from logger handler
        stats = logger_handler.get_log_statistics(days=days)
        print(f"📈 Retrieved stats: {stats}")
        
        # Ensure all expected keys exist
        expected_stats = {
            'total_events': stats.get('total_events', 0),
            'security_events': stats.get('security_events', 0),
            'database_errors': stats.get('database_errors', 0),
            'user_activities': stats.get('user_activities', 0),
            'system_events': stats.get('system_events', 0)
        }
        
        return jsonify({
            'success': True,
            'stats': expected_stats,
            'days': days,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger_handler.log_database_error('api_log_stats', e)
        print(f"❌ Error in api_log_stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch log statistics: {str(e)}',
            'stats': {
                'total_events': 0,
                'security_events': 0,
                'database_errors': 0,
                'user_activities': 0,
                'system_events': 0
            }
        }), 500

@app.route('/api/logs/cleanup', methods=['POST'])
@admin_required
def api_cleanup_logs():
    """API endpoint to cleanup old log entries"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            print("❌ No JSON data provided")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        days_to_keep = data.get('days_to_keep', 90)
        print(f"🧹 Cleanup request: keep last {days_to_keep} days")
        
        # Validate input
        if not isinstance(days_to_keep, int) or days_to_keep < 7:
            print(f"❌ Invalid days_to_keep: {days_to_keep}")
            return jsonify({
                'success': False,
                'error': 'days_to_keep must be an integer >= 7'
            }), 400
        
        if days_to_keep > 365:
            print(f"❌ days_to_keep too large: {days_to_keep}")
            return jsonify({
                'success': False,
                'error': 'days_to_keep cannot exceed 365 days'
            }), 400
        
        # Perform cleanup using logger handler
        deleted_count = logger_handler.cleanup_old_logs(days_to_keep=days_to_keep)
        
        admin_username = session.get('username', 'unknown')
        print(f"✅ Cleanup completed by {admin_username}: {deleted_count} records deleted")
        
        # Log the admin action
        logger_handler.log_security_event(
            event_type="admin_log_cleanup",
            description=f"Admin {admin_username} performed log cleanup: {deleted_count} entries removed (keeping last {days_to_keep} days)",
            severity="HIGH",
            additional_data={
                'admin_user': admin_username,
                'days_to_keep': days_to_keep,
                'deleted_count': deleted_count,
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            }
        )
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'days_to_keep': days_to_keep,
            'message': f'Successfully cleaned up {deleted_count} old log entries (keeping last {days_to_keep} days)',
            'performed_by': admin_username,
            'performed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger_handler.log_database_error('api_cleanup_logs', e)
        print(f"❌ Error in api_cleanup_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to cleanup old logs: {str(e)}'
        }), 500
    
@app.route('/api/logs/clear', methods=['POST'])
@admin_required
def api_clear_logs():
    """API endpoint to clear ALL log entries"""
    try:
        admin_username = session.get('username', 'unknown')
        print(f"🧹 Clear logs request by admin: {admin_username}")
        
        # Count existing logs before deletion
        try:
            count_sql = "SELECT COUNT(*) as total_logs FROM log_events"
            count_result = db.session.execute(text(count_sql)).fetchone()
            total_logs = count_result.total_logs if count_result else 0
            
            print(f"📊 Total logs to be cleared: {total_logs}")
            
            if total_logs == 0:
                print("✅ No logs found to clear")
                return jsonify({
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No logs found to clear'
                })
                
        except Exception as count_error:
            print(f"⚠️ Error counting logs: {count_error}")
            total_logs = 0
        
        # Perform the clear operation
        try:
            clear_sql = "DELETE FROM log_events"
            result = db.session.execute(text(clear_sql))
            deleted_count = result.rowcount
            db.session.commit()
            
            print(f"🗑️ Successfully cleared {deleted_count} log entries")
            
            # Log the clear operation (this will be the first entry in the new log)
            logger_handler.log_security_event(
                event_type="admin_log_clear",
                description=f"Admin {admin_username} cleared all log entries: {deleted_count} records deleted",
                severity="HIGH",
                additional_data={
                    'admin_user': admin_username,
                    'deleted_count': deleted_count,
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                }
            )
            
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Successfully cleared {deleted_count} log entries',
                'performed_by': admin_username,
                'performed_at': datetime.now().isoformat()
            })
            
        except Exception as delete_error:
            print(f"❌ Error during log clearing: {delete_error}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Failed to clear logs: {str(delete_error)}'
            }), 500
            
    except Exception as e:
        logger_handler.log_database_error('api_clear_logs', e)
        print(f"❌ Error in api_clear_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear logs: {str(e)}'
        }), 500
    
@app.route('/api/logs/clear-old', methods=['POST'])
@admin_required
def api_clear_old_logs():
    """API endpoint to clear log entries older than specified days"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            print("❌ No JSON data provided")
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        days_threshold = data.get('days_threshold', 90)
        admin_username = session.get('username', 'unknown')
        print(f"🧹 Clear old logs request by admin: {admin_username}, threshold: {days_threshold} days")
        
        # Validate input
        if not isinstance(days_threshold, int) or days_threshold not in [30, 60, 90]:
            print(f"❌ Invalid days_threshold: {days_threshold}")
            return jsonify({
                'success': False,
                'error': 'days_threshold must be 30, 60, or 90'
            }), 400
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        # Count existing logs before deletion
        try:
            count_sql = "SELECT COUNT(*) as total_logs FROM log_events WHERE created_timestamp < :cutoff_date"
            count_result = db.session.execute(text(count_sql), {'cutoff_date': cutoff_date}).fetchone()
            total_logs = count_result.total_logs if count_result else 0
            
            print(f"📊 Total logs older than {days_threshold} days to be cleared: {total_logs}")
            
            if total_logs == 0:
                print("✅ No old logs found to clear")
                return jsonify({
                    'success': True,
                    'deleted_count': 0,
                    'message': f'No logs older than {days_threshold} days found to clear'
                })
                
        except Exception as count_error:
            print(f"⚠️ Error counting old logs: {count_error}")
            total_logs = 0
        
        # Perform the clear operation
        try:
            clear_sql = "DELETE FROM log_events WHERE created_timestamp < :cutoff_date"
            result = db.session.execute(text(clear_sql), {'cutoff_date': cutoff_date})
            deleted_count = result.rowcount
            db.session.commit()
            
            print(f"🗑️ Successfully cleared {deleted_count} log entries older than {days_threshold} days")
            
            # Log the clear operation
            logger_handler.log_security_event(
                event_type="admin_clear_old_logs",
                description=f"Admin {admin_username} cleared {deleted_count} log entries older than {days_threshold} days",
                severity="HIGH",
                additional_data={
                    'admin_user': admin_username,
                    'days_threshold': days_threshold,
                    'deleted_count': deleted_count,
                    'cutoff_date': cutoff_date.isoformat(),
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                }
            )
            
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'days_threshold': days_threshold,
                'message': f'Successfully cleared {deleted_count} log entries older than {days_threshold} days',
                'performed_by': admin_username,
                'performed_at': datetime.now().isoformat()
            })
            
        except Exception as delete_error:
            print(f"❌ Error during old log clearing: {delete_error}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Failed to clear old logs: {str(delete_error)}'
            }), 500
            
    except Exception as e:
        logger_handler.log_database_error('api_clear_old_logs', e)
        print(f"❌ Error in api_clear_old_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear old logs: {str(e)}'
        }), 500
    
@app.route('/api/logs/export')
@admin_required
def api_export_logs():
    """API endpoint to export log entries"""
    try:
        days = request.args.get('days', 7, type=int)
        category = request.args.get('category', '')
        severity = request.args.get('severity', '')
        search = request.args.get('search', '')
        
        admin_username = session.get('username', 'unknown')
        print(f"📊 Export logs request by admin: {admin_username}")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Build the SQL query with filters
        base_sql = """
        SELECT 
            event_id,
            event_type, 
            event_category, 
            event_description, 
            event_data,
            severity_level, 
            created_timestamp, 
            username, 
            user_id,
            ip_address
        FROM log_events 
        WHERE created_timestamp >= :cutoff_date
        """
        
        params = {'cutoff_date': cutoff_date}
        
        # Add category filter
        if category:
            base_sql += " AND event_category = :category"
            params['category'] = category
        
        # Add severity filter
        if severity:
            base_sql += " AND severity_level = :severity"
            params['severity'] = severity
        
        # Add search filter
        if search:
            base_sql += " AND (event_type LIKE :search OR event_description LIKE :search OR username LIKE :search)"
            params['search'] = f'%{search}%'
        
        base_sql += " ORDER BY created_timestamp DESC"
        
        result = db.session.execute(text(base_sql), params).fetchall()
        
        logs = []
        for row in result:
            # Parse event_data if it's JSON
            event_data = None
            if row.event_data:
                try:
                    event_data = json.loads(row.event_data) if isinstance(row.event_data, str) else row.event_data
                except (json.JSONDecodeError, TypeError):
                    event_data = row.event_data
            
            logs.append({
                'event_id': row.event_id,
                'event_type': row.event_type,
                'event_category': row.event_category,
                'description': row.event_description,
                'event_data': event_data,
                'severity': row.severity_level,
                'timestamp': row.created_timestamp.isoformat(),
                'username': row.username or 'System',
                'user_id': row.user_id,
                'ip_address': row.ip_address or '-'
            })
        
        # Log the export operation
        logger_handler.log_security_event(
            event_type="admin_log_export",
            description=f"Admin {admin_username} exported {len(logs)} log entries (last {days} days)",
            severity="MEDIUM",
            additional_data={
                'admin_user': admin_username,
                'exported_count': len(logs),
                'days_exported': days,
                'filters': {
                    'category': category,
                    'severity': severity,
                    'search': search
                },
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            }
        )
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs),
            'filters_applied': {
                'days': days,
                'category': category,
                'severity': severity,
                'search': search
            }
        })
        
    except Exception as e:
        logger_handler.log_database_error('api_export_logs', e)
        print(f"❌ Error in api_export_logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to export logs: {str(e)}'
        }), 500

# PROJECT MANAGEMENT ROUTES
@app.route('/projects')
@admin_required
def projects():
    """Display all projects"""
    try:
        projects = Project.query.order_by(Project.created_date.desc()).all()
        return render_template('projects.html', projects=projects)
    except Exception as e:
        logger_handler.log_database_error('projects_list', e)
        flash('Error loading projects list.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/projects/create', methods=['GET', 'POST'])
@admin_required
@log_database_operations('project_creation')
def create_project():
    """Create new project"""
    if request.method == 'POST':
        try:
            name = request.form['name']
            description = request.form.get('description', '')
            
            # Check if project name already exists
            if Project.query.filter_by(name=name).first():
                flash('Project name already exists.', 'error')
                return render_template('create_project.html')
            
            # Create new project
            new_project = Project(
                name=name,
                description=description,
                created_by=session['user_id']
            )
            
            db.session.add(new_project)
            db.session.commit()
            
            # Log project creation
            logger_handler.logger.info(f"User {session['username']} created new project: {name}")
            
            flash(f'Project "{name}" created successfully.', 'success')
            return redirect(url_for('projects'))
            
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('project_creation', e)
            flash('Project creation failed. Please try again.', 'error')
    
    return render_template('create_project.html')

@app.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@admin_required
@log_database_operations('project_edit')
def edit_project(project_id):
    """Edit existing project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'POST':
            old_name = project.name
            old_description = project.description
            
            project.name = request.form['name']
            project.description = request.form.get('description', '')
            
            db.session.commit()
            
            # Log project update
            changes = {}
            if old_name != project.name:
                changes['name'] = {'old': old_name, 'new': project.name}
            if old_description != project.description:
                changes['description'] = {'old': old_description, 'new': project.description}
            
            if changes:
                logger_handler.logger.info(f"User {session['username']} updated project {project_id}: {json.dumps(changes)}")
            
            flash(f'Project "{project.name}" updated successfully.', 'success')
            return redirect(url_for('projects'))
        
        return render_template('edit_project.html', project=project)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('project_edit', e)
        flash('Project update failed. Please try again.', 'error')
        return redirect(url_for('projects'))

@app.route('/projects/<int:project_id>/toggle', methods=['POST'])
@admin_required
@log_database_operations('project_toggle')
def toggle_project(project_id):
    """Toggle project active status"""
    try:
        project = Project.query.get_or_404(project_id)
        old_status = project.active_status
        project.active_status = not project.active_status
        
        db.session.commit()
        
        # Log status change
        status = "activated" if project.active_status else "deactivated"
        logger_handler.logger.info(f"User {session['username']} {status} project: {project.name}")
        
        flash(f'Project "{project.name}" {status} successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('project_toggle', e)
        flash('Failed to update project status.', 'error')
    
    return redirect(url_for('projects'))

# API ENDPOINTS FOR DROPDOWN FUNCTIONALITY
@app.route('/api/projects/active')
@login_required
def api_active_projects():
    """Get active projects for dropdown"""
    try:
        projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()
        
        projects_data = [
            {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'qr_count': project.qr_count
            }
            for project in projects
        ]
        
        return jsonify({
            'success': True,
            'projects': projects_data
        })
        
    except Exception as e:
        logger_handler.log_database_error('api_active_projects', e)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch projects'
        }), 500
        
# QR code management routes
@app.route('/qr-codes/create', methods=['GET', 'POST'])
@login_required
@log_database_operations('qr_code_creation')
def create_qr_code():
    """Enhanced create QR code with customization options"""
    if request.method == 'POST':
        try:
            # Existing form data
            name = request.form['name']
            location = request.form['location']
            location_address = request.form['location_address']
            location_event = request.form.get('location_event', '')
            project_id = request.form.get('project_id')
            
            # Extract coordinates data from form
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')
            
            # NEW: QR Code customization data
            fill_color = request.form.get('fill_color', '#000000')
            back_color = request.form.get('back_color', '#FFFFFF')
            box_size = int(request.form.get('box_size', 10))
            border = int(request.form.get('border', 4))
            error_correction = request.form.get('error_correction', 'L')
            style_id = request.form.get('style_id')  # Pre-defined style
            
            # Validate colors (basic hex validation)
            if not (fill_color.startswith('#') and len(fill_color) == 7):
                fill_color = '#000000'
            if not (back_color.startswith('#') and len(back_color) == 7):
                back_color = '#FFFFFF'
            
            # Convert coordinates to float if they exist
            address_latitude = None
            address_longitude = None
            has_coordinates = False
            
            if latitude and longitude:
                try:
                    address_latitude = float(latitude)
                    address_longitude = float(longitude)
                    has_coordinates = True
                    print(f"✓ Coordinates received: {address_latitude}, {address_longitude}")
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Invalid coordinates format: {e}")
                    address_latitude = None
                    address_longitude = None
                    has_coordinates = False
            
            # Validate project_id if provided
            project = None
            if project_id:
                try:
                    project_id = int(project_id)
                    project = Project.query.get(project_id)
                    if not project or not project.active_status:
                        flash('Selected project is not valid or inactive.', 'error')
                        return render_template('create_qr_code.html', 
                                             projects=Project.query.filter_by(active_status=True).all(),
                                             styles=QRCodeStyle.query.all() if 'QRCodeStyle' in globals() else [])
                except (ValueError, TypeError):
                    flash('Invalid project selection.', 'error')
                    return render_template('create_qr_code.html', 
                                         projects=Project.query.filter_by(active_status=True).all(),
                                         styles=QRCodeStyle.query.all() if 'QRCodeStyle' in globals() else [])
            
            # Create new QR code record first (without URL and image)
            new_qr_code = QRCode(
                name=name,
                location=location,
                location_address=location_address,
                location_event=location_event,
                qr_code_image="",  # Will be updated after URL generation
                qr_url="",  # Will be updated after ID is assigned
                created_by=session['user_id'],
                project_id=project_id,
                address_latitude=address_latitude,
                address_longitude=address_longitude,
                coordinate_accuracy=coordinate_accuracy if has_coordinates else None,
                coordinates_updated_date=datetime.utcnow() if has_coordinates else None,
                # NEW: Customization fields (only if columns exist)
                **({
                    'fill_color': fill_color,
                    'back_color': back_color,
                    'box_size': box_size,
                    'border': border,
                    'error_correction': error_correction,
                    'style_id': int(style_id) if style_id and style_id.isdigit() else None
                } if hasattr(QRCode, 'fill_color') else {})
            )
            
            # Add to session and flush to get the ID
            db.session.add(new_qr_code)
            db.session.flush()  # This assigns the ID without committing
            
            # Now generate the readable URL using the ID
            qr_url = generate_qr_url(name, new_qr_code.id)
            
            # Generate QR code data with the destination URL and custom styling
            qr_data = f"{request.url_root}qr/{qr_url}"
            qr_image = generate_qr_code(
                data=qr_data,
                fill_color=fill_color,
                back_color=back_color,
                box_size=box_size,
                border=border,
                error_correction=error_correction
            )
            
            # Update the QR code with the URL and image
            new_qr_code.qr_url = qr_url
            new_qr_code.qr_code_image = qr_image
            
            # Now commit all changes
            db.session.commit()
            
            # Enhanced logging with customization information
            logger_handler.log_qr_code_created(
                qr_code_id=new_qr_code.id,
                qr_code_name=name,
                created_by_user_id=session['user_id'],
                qr_data={
                    'location': location,
                    'location_address': location_address,
                    'location_event': location_event,
                    'has_coordinates': has_coordinates,
                    'customization': {
                        'fill_color': fill_color,
                        'back_color': back_color,
                        'box_size': box_size,
                        'border': border,
                        'error_correction': error_correction
                    }
                }
            )

            # Success message with customization info
            project_info = f" in project '{project.name}'" if project else ""
            coord_info = f" with coordinates ({new_qr_code.coordinates_display})" if has_coordinates else ""
            style_info = f" with custom styling (Fill: {fill_color}, Background: {back_color})"

            flash(f'QR Code "{name}" created successfully{project_info}{coord_info}{style_info}! URL: {qr_url}', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logger_handler.log_database_error('qr_code_creation', e)
            flash('QR Code creation failed. Please try again.', 'error')
            print(f"❌ QR Code creation error: {e}")
    
    # Get active projects and styles for dropdown
    projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()
    styles = QRCodeStyle.query.order_by(QRCodeStyle.name.asc()).all() if 'QRCodeStyle' in globals() else []
    
    return render_template('create_qr_code.html', projects=projects, styles=styles)

@app.route('/qr-codes/<int:qr_id>/edit', methods=['GET', 'POST'])
@login_required
@log_database_operations('qr_code_edit')
def edit_qr_code(qr_id):
    """Enhanced edit QR code with customization support"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        
        if request.method == 'POST':
            # Track changes for logging
            old_data = {
                'name': qr_code.name,
                'location': qr_code.location,
                'location_address': qr_code.location_address,
                'location_event': qr_code.location_event,
                'project_id': qr_code.project_id,
                'qr_url': qr_code.qr_url,
                'address_latitude': qr_code.address_latitude,
                'address_longitude': qr_code.address_longitude,
                'coordinate_accuracy': qr_code.coordinate_accuracy,
                # Track old styling
                'fill_color': getattr(qr_code, 'fill_color', '#000000'),
                'back_color': getattr(qr_code, 'back_color', '#FFFFFF')
            }
            
            # Update QR code fields
            new_name = request.form['name']
            qr_code.name = new_name
            qr_code.location = request.form['location']
            qr_code.location_address = request.form['location_address']
            qr_code.location_event = request.form.get('location_event', '')
            
            # Handle coordinates
            latitude = request.form.get('address_latitude')
            longitude = request.form.get('address_longitude')
            coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')
            
            if latitude and longitude:
                try:
                    qr_code.address_latitude = float(latitude)
                    qr_code.address_longitude = float(longitude)
                    qr_code.coordinate_accuracy = coordinate_accuracy
                    qr_code.coordinates_updated_date = datetime.utcnow()
                except (ValueError, TypeError):
                    pass
            elif latitude == '' and longitude == '':
                qr_code.address_latitude = None
                qr_code.address_longitude = None
                qr_code.coordinate_accuracy = None
                qr_code.coordinates_updated_date = None
            
            # Handle project association
            new_project_id = request.form.get('project_id')
            if new_project_id and new_project_id.strip():
                try:
                    new_project_id = int(new_project_id)
                    project = Project.query.get(new_project_id)
                    if project and project.active_status:
                        qr_code.project_id = new_project_id
                    else:
                        flash('Selected project is not valid or inactive.', 'error')
                        return render_template('edit_qr_code.html', qr_code=qr_code, 
                                             projects=Project.query.filter_by(active_status=True).all(),
                                             styles=QRCodeStyle.query.all() if 'QRCodeStyle' in globals() else [])
                except (ValueError, TypeError):
                    flash('Invalid project selection.', 'error')
                    return render_template('edit_qr_code.html', qr_code=qr_code, 
                                         projects=Project.query.filter_by(active_status=True).all(),
                                         styles=QRCodeStyle.query.all() if 'QRCodeStyle' in globals() else [])
            else:
                qr_code.project_id = None
            
            # Handle QR code customization (only if columns exist)
            fill_color = request.form.get('fill_color', '#000000')
            back_color = request.form.get('back_color', '#FFFFFF')
            box_size = int(request.form.get('box_size', 10))
            border = int(request.form.get('border', 4))
            error_correction = request.form.get('error_correction', 'L')
            style_id = request.form.get('style_id')
            
            # Update styling fields if they exist
            if hasattr(qr_code, 'fill_color'):
                qr_code.fill_color = fill_color
                qr_code.back_color = back_color
                qr_code.box_size = box_size
                qr_code.border = border
                qr_code.error_correction = error_correction
                qr_code.style_id = int(style_id) if style_id and style_id.isdigit() else None
            
            # Check if QR code needs regeneration
            name_changed = old_data['name'] != new_name
            styling_changed = (hasattr(qr_code, 'fill_color') and 
                             (old_data['fill_color'] != fill_color or 
                              old_data['back_color'] != back_color))
            
            if name_changed:
                new_qr_url = generate_qr_url(new_name, qr_code.id)
                qr_code.qr_url = new_qr_url
            
            # Regenerate QR code if name or styling changed
            if name_changed or styling_changed:
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
                
                # Use new styling if available, otherwise use defaults
                styling = get_qr_styling(qr_code)
                qr_code.qr_code_image = generate_qr_code(
                    data=qr_data,
                    fill_color=styling['fill_color'],
                    back_color=styling['back_color'],
                    box_size=styling['box_size'],
                    border=styling['border'],
                    error_correction=styling['error_correction']
                )
            
            db.session.commit()
            
            # Success message
            flash(f'QR Code "{qr_code.name}" updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        # GET request - render edit form
        projects = Project.query.filter_by(active_status=True).order_by(Project.name.asc()).all()
        styles = QRCodeStyle.query.order_by(QRCodeStyle.name.asc()).all() if 'QRCodeStyle' in globals() else []
        
        return render_template('edit_qr_code.html', qr_code=qr_code, projects=projects, styles=styles)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('qr_code_edit', e)
        flash('QR Code update failed. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/qr-codes/<int:qr_id>/delete', methods=['GET', 'POST'])
@admin_required
@log_database_operations('qr_code_deletion')
def delete_qr_code(qr_id):
    """Permanently delete QR code (Admin only) - Hard delete - PRESERVING EXACT ROUTE"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        print(f"✅ Found QR Code: {qr_code.name}")
        
        if request.method == 'POST':
            qr_name = qr_code.name
            qr_code_id = qr_code.id
            print(f"🗑️ ATTEMPTING TO DELETE: {qr_name}")
            
            # Check if QR exists before delete
            before_count = QRCode.query.count()
            print(f"📊 QR count before delete: {before_count}")
            
            # Log QR code deletion before actual deletion
            logger_handler.log_qr_code_deleted(
                qr_code_id=qr_code_id,
                qr_code_name=qr_name,
                deleted_by_user_id=session['user_id']
            )
            
            # Delete the QR code
            db.session.delete(qr_code)
            print("💾 Called db.session.delete()")
            
            db.session.commit()
            print("💾 Called db.session.commit()")
            
            # Check count after delete
            after_count = QRCode.query.count()
            print(f"📊 QR count after delete: {after_count}")
            print(f"✅ DELETE SUCCESS! Removed {before_count - after_count} records")
            
            flash(f'QR code "{qr_name}" has been permanently deleted!', 'success')
            return redirect(url_for('dashboard'))
        
        # GET request - show confirmation page
        print("📄 Showing confirmation page")
        return render_template('confirm_delete_qr.html', qr_code=qr_code)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('qr_code_deletion', e)
        print(f"❌ ERROR in delete route: {e}")
        print(f"❌ Exception type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        flash('Error deleting QR code. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    
@app.route('/qr/<string:qr_url>')
def qr_destination(qr_url):
    """QR code destination page where staff check in - PRESERVING EXACT ROUTE"""
    try:
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        
        if not qr_code:
            # Log invalid QR code access attempt
            logger_handler.log_security_event(
                event_type="invalid_qr_access",
                description=f"Attempt to access invalid QR code URL: {qr_url}",
                severity="MEDIUM"
            )
            flash('QR code not found or inactive.', 'error')
            return redirect(url_for('index'))
        
        # Log QR code access
        logger_handler.log_qr_code_accessed(
            qr_code_id=qr_code.id,
            qr_code_name=qr_code.name,
            access_method='scan'
        )
        
        return render_template('qr_destination.html', qr_code=qr_code)
        
    except Exception as e:
        logger_handler.log_database_error('qr_code_scan', e)
        flash('Error processing QR code scan.', 'error')
        return redirect(url_for('index'))

@app.route('/qr/<string:qr_url>/checkin', methods=['POST'])
def qr_checkin(qr_url):
    """
    Enhanced staff check-in with location accuracy calculation
    Allows multiple check-ins with minimum interval between them
    PRESERVES coordinate-to-address conversion functionality
    """
    try:
        print(f"\n🚀 STARTING ENHANCED CHECK-IN PROCESS")
        print(f"   QR URL: {qr_url}")
        print(f"   Timestamp: {datetime.now()}")
        
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        
        if not qr_code:
            print(f"❌ QR code not found or inactive: {qr_url}")
            return jsonify({
                'success': False,
                'message': 'QR code not found or inactive.'
            }), 404
        
        print(f"✅ Found QR code: {qr_code.name} (ID: {qr_code.id})")
        print(f"   Location: {qr_code.location}")
        print(f"   QR Address: {qr_code.location_address}")
        
        # Get and validate employee ID
        employee_id = request.form.get('employee_id', '').strip()
        
        if not employee_id:
            return jsonify({
                'success': False,
                'message': 'Employee ID is required.'
            }), 400
        
        # Check for recent check-ins with 30-minute interval validation
        today = date.today()
        current_time = datetime.now()
        time_interval = int(os.environ.get('TIME_INTERVAL'))
        the_last_checkin_time = current_time - timedelta(minutes=time_interval)
        
        # Find the most recent check-in for this employee at this location today
        recent_checkin = AttendanceData.query.filter_by(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today
        ).order_by(AttendanceData.check_in_time.desc()).first()
        
        if recent_checkin:
            # Convert check_in_time (time) to datetime for comparison
            recent_checkin_datetime = datetime.combine(today, recent_checkin.check_in_time)
            
            # Check if 30 minutes have passed since the last check-in
            if recent_checkin_datetime > the_last_checkin_time:
                minutes_remaining = time_interval - int((current_time - recent_checkin_datetime).total_seconds() / 60)
                print(f"⚠️ Too soon for another {qr_code.location_event} for {employee_id}")
                print(f"   Last {qr_code.location_event}: {recent_checkin.check_in_time.strftime('%H:%M')}")
                print(f"   Minutes remaining: {minutes_remaining}")
                
                return jsonify({
                    'success': False,
                    'message': f"You can {qr_code.location_event} again in {minutes_remaining} minutes. Last {qr_code.location_event} was at {recent_checkin.check_in_time.strftime("%H:%M")}. \n"
                               f"Puedes volver a registrarte en {minutes_remaining} minutos. El último registro fue a las {recent_checkin.check_in_time.strftime("%H:%M")}."
                }), 400
            else:
                print(f"✅ 30-minute interval satisfied. Allowing new {qr_code.location_event} for {employee_id}")
        else:
            print(f"✅ First {qr_code.location_event} today for {employee_id}")
        
        # Process location data with coordinate-to-address conversion
        location_data = process_location_data_enhanced(request.form)
        
        # Get device and network info
        user_agent_string = request.headers.get('User-Agent', '')
        device_info = detect_device_info(user_agent_string)
        client_ip = get_client_ip()
        
        print(f"📱 Device Info: {device_info}")
        print(f"🌐 IP Address: {client_ip}")
        print(f"📍 Location Data: {location_data}")
        
        # Create attendance record
        print(f"\n💾 CREATING ATTENDANCE RECORD:")
        
        attendance = AttendanceData(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today,
            check_in_time=datetime.now().time(),
            device_info=device_info,
            user_agent=user_agent_string,
            ip_address=client_ip,
            location_name=qr_code.location,
            latitude=location_data['latitude'],
            longitude=location_data['longitude'],
            accuracy=location_data['accuracy'],
            altitude=location_data['altitude'],
            location_source=location_data['source'],
            address=location_data['address'],
            status='present'
        )
        
        print(f"✅ Created base attendance record")
        
        # ENHANCED DEBUG: Calculate location accuracy with detailed logging
        print(f"\n🎯 CALCULATING LOCATION ACCURACY WITH ENHANCED DEBUG...")
        print(f"   📊 QR Code Details:")
        print(f"      ID: {qr_code.id}")
        print(f"      Name: {qr_code.name}")
        print(f"      Location: {qr_code.location}")
        print(f"      Location Address: {qr_code.location_address}")
        print(f"      Has location_address: {qr_code.location_address is not None}")
        print(f"      Location Address Length: {len(qr_code.location_address) if qr_code.location_address else 0}")
        
        print(f"   📍 Check-in Data:")
        print(f"      Latitude: {location_data['latitude']}")
        print(f"      Longitude: {location_data['longitude']}")
        print(f"      GPS Accuracy: {location_data['accuracy']}")
        print(f"      Address: {location_data['address']}")
        print(f"      Address Length: {len(location_data['address']) if location_data['address'] else 0}")
        print(f"      Source: {location_data['source']}")
        
        location_accuracy = None
        
        try:
            # Check if we have the required data
            if not qr_code.location_address:
                print(f"❌ QR code location_address is empty or None")
                print(f"   QR Code location_address value: '{qr_code.location_address}'")
            elif not location_data['address'] and not (location_data['latitude'] and location_data['longitude']):
                print(f"❌ No check-in address or coordinates available")
                print(f"   Check-in address: '{location_data['address']}'")
                print(f"   Check-in coords: {location_data['latitude']}, {location_data['longitude']}")
            else:
                print(f"✅ Required data available, proceeding with calculation...")
                
                location_accuracy = calculate_location_accuracy_enhanced(
                    qr_address=qr_code.location_address,
                    checkin_address=location_data['address'],
                    checkin_lat=location_data['latitude'],
                    checkin_lng=location_data['longitude']
                )
                
                print(f"📐 Location accuracy calculation result: {location_accuracy}")
                
                if location_accuracy is not None:
                    attendance.location_accuracy = location_accuracy
                    accuracy_level = get_location_accuracy_level_enhanced(location_accuracy)
                    print(f"✅ Location accuracy set successfully: {location_accuracy:.4f} miles ({accuracy_level})")
                    print(f"📊 Final attendance.location_accuracy value: {attendance.location_accuracy}")
                else:
                    print(f"⚠️ Could not calculate location accuracy - calculation returned None")
                    
        except Exception as e:
            print(f"❌ Error in location accuracy calculation: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
        
        # ENHANCED DEBUG: Save to database with verification
        try:
            print(f"\n💾 SAVING TO DATABASE...")
            print(f"   Attendance object before save:")
            print(f"      Employee ID: {attendance.employee_id}")
            print(f"      Location: {attendance.location_name}")
            print(f"      Latitude: {attendance.latitude}")
            print(f"      Longitude: {attendance.longitude}")
            print(f"      Address: {attendance.address}")
            print(f"      Location Accuracy: {attendance.location_accuracy}")
            
            db.session.add(attendance)
            db.session.commit()
            
            # VERIFICATION: Read back from database
            saved_record = AttendanceData.query.get(attendance.id)
            print(f"✅ Successfully saved attendance record with ID: {attendance.id}")
            print(f"📊 Verification - location accuracy in database: {saved_record.location_accuracy}")
            
            if saved_record.location_accuracy != attendance.location_accuracy:
                print(f"⚠️ WARNING: Database value differs from object value!")
                print(f"   Object value: {attendance.location_accuracy}")
                print(f"   Database value: {saved_record.location_accuracy}")
            
            # Add enhanced logging for location accuracy save
            if attendance.location_accuracy is not None:
                logger_handler.logger.info(f"Location accuracy calculated and saved: {attendance.location_accuracy:.4f} miles for employee {attendance.employee_id}")
            else:
                logger_handler.logger.warning(f"Location accuracy could not be calculated for employee {attendance.employee_id} at QR {qr_code.name}")

            # Count total check-ins for today for this employee at this location
            today_checkin_count = AttendanceData.query.filter_by(
                qr_code_id=qr_code.id,
                employee_id=employee_id.upper(),
                check_in_date=today
            ).count()
            
            checkin_sequence_text = f"{qr_code.location_event} details"
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            db.session.rollback()
            logger_handler.log_database_error('checkin_save', e)
            return jsonify({
                'success': False,
                'message': 'Database error occurred.'
            }), 500
        
        # Return success response with sequence information
        response_data = {
            'success': True,
            'message': f'Check-in successful! {checkin_sequence_text} for today.',
            'data': {
                'employee_id': attendance.employee_id,
                'location': attendance.location_name,
                'location_event': qr_code.location_event,
                'check_in_time': attendance.check_in_time.strftime('%H:%M:%S'),
                'check_in_date': attendance.check_in_date.strftime('%m/%d/%Y'),
                'device_info': attendance.device_info,
                'ip_address': attendance.ip_address,
                'location_accuracy': location_accuracy,
                'checkin_count_today': today_checkin_count,
                'checkin_sequence': checkin_sequence_text
            }
        }
        
        if location_data['address']:
            response_data['data']['address'] = location_data['address']
            
        if location_data['latitude'] and location_data['longitude']:
            response_data['data']['coordinates'] = f"{location_data['latitude']:.10f}, {location_data['longitude']:.10f}"
        
        print(f"✅ Check-in completed successfully")
        print(f"   Employee: {attendance.employee_id}")
        print(f"   Time: {attendance.check_in_time}")
        print(f"   Location: {attendance.location_name}")
        print(f"   Address: {attendance.address}")
        print(f"   Today's count: {today_checkin_count}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Unexpected error in check-in process: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred during check-in.'
        }), 500

@app.route('/qr-codes/<int:qr_id>/toggle-status', methods=['POST'])
@login_required
def toggle_qr_status(qr_id):
    """Toggle QR code active/inactive status"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        
        # Toggle the status
        qr_code.active_status = not qr_code.active_status
        db.session.commit()
        
        status_text = "activated" if qr_code.active_status else "deactivated"
        flash(f'QR code "{qr_code.name}" has been {status_text} successfully!', 'success')
        
        return jsonify({
            'success': True,
            'new_status': qr_code.active_status,
            'status_text': 'Active' if qr_code.active_status else 'Inactive',
            'message': f'QR code {status_text} successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling QR status: {e}")
        return jsonify({
            'success': False,
            'message': 'Error updating QR code status. Please try again.'
        }), 500

@app.route('/qr-codes/<int:qr_id>/activate', methods=['POST'])
@login_required
def activate_qr_code(qr_id):
    """Activate a QR code"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        qr_code.active_status = True
        db.session.commit()
        
        flash(f'QR code "{qr_code.name}" has been activated successfully!', 'success')
        return jsonify({
            'success': True,
            'new_status': True,
            'status_text': 'Active',
            'message': 'QR code activated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error activating QR code: {e}")
        return jsonify({
            'success': False,
            'message': 'Error activating QR code. Please try again.'
        }), 500

@app.route('/qr-codes/<int:qr_id>/deactivate', methods=['POST'])
@login_required
def deactivate_qr_code(qr_id):
    """Deactivate a QR code"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        qr_code.active_status = False
        db.session.commit()
        
        flash(f'QR code "{qr_code.name}" has been deactivated successfully!', 'success')
        return jsonify({
            'success': True,
            'new_status': False,
            'status_text': 'Inactive',
            'message': 'QR code deactivated successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deactivating QR code: {e}")
        return jsonify({
            'success': False,
            'message': 'Error deactivating QR code. Please try again.'
        }), 500
    
@app.route('/qr-codes/<int:qr_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_qr_status_api(qr_id):
    """Toggle QR code active/inactive status - Enhanced JSON API"""
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        qr_code.active_status = not qr_code.active_status
        db.session.commit()
        
        status_text = "activated" if qr_code.active_status else "deactivated"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'new_status': qr_code.active_status,
                'status_text': 'Active' if qr_code.active_status else 'Inactive',
                'message': f'QR code "{qr_code.name}" has been {status_text} successfully!'
            })
        else:
            flash(f'QR code "{qr_code.name}" has been {status_text} successfully!', 'success')
            return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Error updating QR code status. Please try again.'
            }), 500
        else:
            flash('Error updating QR code status. Please try again.', 'error')
            return redirect(url_for('dashboard'))

@app.route('/attendance')
@login_required
def attendance_report():
    """Safe attendance report with backward compatibility for location_accuracy and fixed datetime handling"""
    try:
        print("📊 Loading attendance report...")
        
        # Log attendance report access
        try:
            user_role = session.get('role', 'unknown')
            logger_handler.logger.info(f"User {session.get('username', 'unknown')} accessed attendance report")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        # Check if location_accuracy column exists
        has_location_accuracy = check_location_accuracy_column_exists()
        print(f"🔍 Location accuracy column exists: {has_location_accuracy}")
        
        # Get filter parameters
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        location_filter = request.args.get('location', '')
        employee_filter = request.args.get('employee', '')
        project_filter = request.args.get('project', '')

        # Build base query - conditional based on column existence
        if has_location_accuracy:
            # New query with location accuracy
            base_query = """
                SELECT 
                    ad.id,
                    ad.employee_id,
                    ad.check_in_date,
                    ad.check_in_time,
                    ad.location_name,
                    qc.location_event,
                    qc.location_address as qr_address,
                    ad.address as checked_in_address,
                    ad.latitude,
                    ad.longitude,
                    ad.location_accuracy,
                    ad.accuracy as gps_accuracy,
                    ad.device_info,
                    CONCAT(e.firstName, ' ', e.lastName) as employee_name
                FROM attendance_data ad
                LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
                LEFT JOIN employee e ON CAST(ad.employee_id AS UNSIGNED) = e.id
                WHERE 1=1
            """
        else:
            # Fallback query without location accuracy
            base_query = """
                SELECT 
                    ad.id,
                    ad.employee_id,
                    ad.check_in_date,
                    ad.check_in_time,
                    ad.location_name,
                    qc.location_event,
                    qc.location_address as qr_address,
                    ad.address as checked_in_address,
                    ad.latitude,
                    ad.longitude,
                    NULL as location_accuracy,
                    ad.accuracy as gps_accuracy,
                    ad.device_info,
                    CONCAT(e.firstName, ' ', e.lastName) as employee_name
                FROM attendance_data ad
                LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
                LEFT JOIN employee e ON CAST(ad.employee_id AS UNSIGNED) = e.id
                WHERE 1=1
            """
        
        conditions = []
        params = {}
        
        # Apply date range filter
        if date_from:
            conditions.append("ad.check_in_date >= :date_from")
            params['date_from'] = date_from
        
        if date_to:
            conditions.append("ad.check_in_date <= :date_to")
            params['date_to'] = date_to
        
        # Apply location filter
        if location_filter:
            conditions.append("ad.location_name LIKE :location")
            params['location'] = f"%{location_filter}%"
        
        # Apply employee filter
        if employee_filter:
            conditions.append("ad.employee_id LIKE :employee")
            params['employee'] = f"%{employee_filter}%"
        
        # Apply project filter using SQL approach (not ORM)
        if project_filter:
            conditions.append("qc.project_id = :project_id")
            params['project_id'] = int(project_filter)
            print(f"📊 Applied project filter: {project_filter}")
        
        # Add conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Add ordering
        base_query += " ORDER BY ad.check_in_date DESC, ad.check_in_time DESC"
        
        print(f"🔍 Executing query with {len(params)} parameters")
        
        # Execute query
        query_result = db.session.execute(text(base_query), params)
        attendance_records = query_result.fetchall()

        # FIXED: Process records to add calculated fields with proper datetime handling
        processed_records = []
        for record in attendance_records:
            # Safe attribute access with fallbacks
            location_accuracy = getattr(record, 'location_accuracy', None)
            gps_accuracy = getattr(record, 'gps_accuracy', None)
            
            # Create processed record with calculated fields
            processed_record = {
                'id': record.id,
                'employee_id': record.employee_id or 'Unknown',
                'employee_name': getattr(record, 'employee_name', None) or record.employee_id or 'Unknown',
                'check_in_date': record.check_in_date,
                'check_in_time': record.check_in_time,
                'location_name': record.location_name or 'Unknown Location',
                'location_event': getattr(record, 'location_event', None) or 'Check In',
                'qr_address': getattr(record, 'qr_address', None) or 'N/A',
                'checked_in_address': getattr(record, 'checked_in_address', None) or 'N/A',
                'latitude': record.latitude,
                'longitude': record.longitude,
                'location_accuracy': location_accuracy,
                'gps_accuracy': gps_accuracy,
                'device_info': getattr(record, 'device_info', None) or 'Unknown Device',
            }
            
            # FIXED: Add address display logic based on location accuracy
            # If location accuracy < 0.3 miles, display QR address; otherwise display actual check-in address
            if location_accuracy is not None:
                try:
                    accuracy_value = float(location_accuracy) if isinstance(location_accuracy, str) else location_accuracy
                    if accuracy_value < 0.3:
                        # High accuracy - use QR code address
                        processed_record['display_address'] = getattr(record, 'qr_address', None) or 'N/A'
                        processed_record['address_source'] = 'qr'
                        print(f"📍 Using QR address for employee {record.employee_id} (accuracy: {accuracy_value:.3f} miles)")
                    else:
                        # Lower accuracy - use actual check-in address
                        processed_record['display_address'] = getattr(record, 'checked_in_address', None) or 'N/A'
                        processed_record['address_source'] = 'checkin'
                        print(f"📍 Using check-in address for employee {record.employee_id} (accuracy: {accuracy_value:.3f} miles)")
                except (ValueError, TypeError):
                    # If accuracy can't be converted to float, use check-in address
                    processed_record['display_address'] = getattr(record, 'checked_in_address', None) or 'N/A'
                    processed_record['address_source'] = 'checkin'
            else:
                # No location accuracy data - use actual check-in address
                processed_record['display_address'] = getattr(record, 'checked_in_address', None) or 'N/A'
                processed_record['address_source'] = 'checkin'
            
            # Add accuracy level calculation if location_accuracy exists
            if location_accuracy is not None:
                if location_accuracy <= 10:
                    processed_record['accuracy_level'] = 'High'
                elif location_accuracy <= 50:
                    processed_record['accuracy_level'] = 'Medium'
                else:
                    processed_record['accuracy_level'] = 'Low'
            else:
                processed_record['accuracy_level'] = 'Unknown'
                
            # Add formatted datetime for display
            try:
                if record.check_in_date and record.check_in_time:
                    datetime_obj = datetime.combine(record.check_in_date, record.check_in_time)
                    processed_record['formatted_datetime'] = datetime_obj.strftime('%m/%d/%Y %I:%M %p')
                else:
                    processed_record['formatted_datetime'] = 'Invalid Date/Time'
            except Exception as e:
                print(f"⚠️ Error formatting datetime for record {record.id}: {e}")
                processed_record['formatted_datetime'] = 'Error'
                
            processed_records.append(processed_record)
        
        # Get unique locations for filter dropdown
        try:
            locations_query = db.session.execute(text("""
                SELECT DISTINCT location_name 
                FROM attendance_data 
                WHERE location_name IS NOT NULL 
                ORDER BY location_name
            """))
            locations = [row[0] for row in locations_query.fetchall()]
            print(f"✅ Found {len(locations)} unique locations")
        except Exception as e:
            print(f"⚠️ Error loading locations: {e}")
            locations = []

        # Update the projects query to get only active projects for the dropdown
        try:
            projects = db.session.execute(text("""
                SELECT p.id, p.name, COUNT(DISTINCT ad.id) as attendance_count
                FROM projects p
                LEFT JOIN qr_codes qc ON qc.project_id = p.id
                LEFT JOIN attendance_data ad ON ad.qr_code_id = qc.id
                WHERE p.active_status = true
                GROUP BY p.id, p.name
                HAVING COUNT(DISTINCT ad.id) > 0
                ORDER BY p.name
            """)).fetchall()
            print(f"✅ Loaded {len(projects)} projects with attendance data")
        except Exception as e:
            print(f"⚠️ Error loading projects: {e}")
            projects = []
        
        # Get attendance statistics
        try:
            if has_location_accuracy:
                stats_query = db.session.execute(text("""
                    SELECT 
                        COUNT(*) as total_checkins,
                        COUNT(DISTINCT employee_id) as unique_employees,
                        COUNT(DISTINCT qr_code_id) as active_locations,
                        COUNT(CASE WHEN check_in_date = CURRENT_DATE THEN 1 END) as today_checkins,
                        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as records_with_gps,
                        COUNT(CASE WHEN location_accuracy IS NOT NULL THEN 1 END) as records_with_accuracy,
                        AVG(location_accuracy) as avg_location_accuracy
                    FROM attendance_data
                """))
            else:
                stats_query = db.session.execute(text("""
                    SELECT 
                        COUNT(*) as total_checkins,
                        COUNT(DISTINCT employee_id) as unique_employees,
                        COUNT(DISTINCT qr_code_id) as active_locations,
                        COUNT(CASE WHEN check_in_date = CURRENT_DATE THEN 1 END) as today_checkins,
                        COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as records_with_gps,
                        0 as records_with_accuracy,
                        0 as avg_location_accuracy
                    FROM attendance_data
                """))
            
            stats = stats_query.fetchone()
            print(f"✅ Loaded statistics: {stats.total_checkins} total check-ins")
        except Exception as e:
            print(f"⚠️ Error loading statistics: {e}")
            # Fallback stats
            stats = type('Stats', (), {
                'total_checkins': 0,
                'unique_employees': 0,
                'active_locations': 0,
                'today_checkins': 0,
                'records_with_gps': 0,
                'records_with_accuracy': 0,
                'avg_location_accuracy': 0
            })()
        
        # Add today's date for template
        today_date = datetime.now().strftime('%Y-%m-%d')
        current_date_formatted = datetime.now().strftime('%B %d')
        
        print("✅ Rendering attendance report template")
        
        return render_template('attendance_report.html', 
                             attendance_records=processed_records,
                             locations=locations,
                             projects=projects,
                             stats=stats,
                             date_from=date_from,
                             date_to=date_to,
                             location_filter=location_filter,
                             employee_filter=employee_filter,
                             project_filter=project_filter,
                             today_date=today_date,
                             current_date_formatted=current_date_formatted,
                             has_location_accuracy_feature=has_location_accuracy,
                             user_role=user_role)
        
    except Exception as e:
        print(f"❌ Error loading attendance report: {e}")
        print(f"❌ Exception type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Log the error
        try:
            logger_handler.log_database_error('attendance_report', e)
        except Exception as log_error:
            print(f"⚠️ Additional logging error: {log_error}")
        
        flash('Error loading attendance report. Please check the server logs for details.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/attendance/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
@log_database_operations('attendance_update')
def edit_attendance(record_id):
    """Edit attendance record (Admin and Payroll only)"""
    # Check if user has permission to edit attendance records
    if session.get('role') not in ['admin', 'payroll']:
        flash('Access denied. Only administrators and payroll staff can edit attendance records.', 'error')
        return redirect(url_for('attendance_report'))
    
    try:
        attendance_record = AttendanceData.query.get_or_404(record_id)
        
        if request.method == 'POST':
            # Track changes for logging
            changes = {}
            old_values = {
                'employee_id': attendance_record.employee_id,
                'check_in_date': attendance_record.check_in_date,
                'check_in_time': attendance_record.check_in_time,
                'location_name': attendance_record.location_name
            }
            
            # Update attendance record fields
            new_employee_id = request.form['employee_id'].strip().upper()
            new_check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
            new_check_in_time = datetime.strptime(request.form['check_in_time'], '%H:%M').time()
            new_location_name = request.form['location_name'].strip()
            
            # Track what changed
            if attendance_record.employee_id != new_employee_id:
                changes['employee_id'] = f"{attendance_record.employee_id} → {new_employee_id}"
            if attendance_record.check_in_date != new_check_in_date:
                changes['check_in_date'] = f"{attendance_record.check_in_date} → {new_check_in_date}"
            if attendance_record.check_in_time != new_check_in_time:
                changes['check_in_time'] = f"{attendance_record.check_in_time} → {new_check_in_time}"
            if attendance_record.location_name != new_location_name:
                changes['location_name'] = f"{attendance_record.location_name} → {new_location_name}"
            
            # Apply changes
            attendance_record.employee_id = new_employee_id
            attendance_record.check_in_date = new_check_in_date
            attendance_record.check_in_time = new_check_in_time
            attendance_record.location_name = new_location_name
            attendance_record.updated_timestamp = datetime.utcnow()
            
            db.session.commit()
            
            # Log the successful update
            if changes:
                logger_handler.log_security_event(
                    event_type="attendance_record_update",
                    description=f"{session.get('role', 'unknown').title()} {session.get('username')} updated attendance record {record_id}",
                    severity="MEDIUM",
                    additional_data={'record_id': record_id, 'changes': changes, 'user_role': session.get('role')}
                )
                print(f"[LOG] {session.get('role', 'unknown').title()} {session.get('username')} updated attendance record {record_id}: {changes}")
            
            flash(f'Attendance record for {new_employee_id} updated successfully!', 'success')
            return redirect(url_for('attendance_report'))
        
        # GET request - show edit form
        # Get available QR codes for location dropdown
        qr_codes = QRCode.query.filter_by(active_status=True).all()
        
        return render_template('edit_attendance.html', 
                             attendance_record=attendance_record,
                             qr_codes=qr_codes)
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('attendance_update', e)
        print(f"[LOG] Error updating attendance record {record_id}: {e}")
        flash('Error updating attendance record. Please try again.', 'error')
        return redirect(url_for('attendance_report'))

@app.route('/attendance/<int:record_id>/delete', methods=['POST'])
@login_required
@log_database_operations('attendance_delete')
def delete_attendance(record_id):
    """Delete attendance record (Admin and Payroll only)"""
    # Check if user has permission to delete attendance records
    if session.get('role') not in ['admin', 'payroll']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Access denied. Only administrators and payroll staff can delete attendance records.'
            }), 403
        else:
            flash('Access denied. Only administrators and payroll staff can delete attendance records.', 'error')
            return redirect(url_for('attendance_report'))
    
    try:
        attendance_record = AttendanceData.query.get_or_404(record_id)
        
        # Store record info for logging before deletion
        employee_id = attendance_record.employee_id
        location_name = attendance_record.location_name
        check_in_date = attendance_record.check_in_date
        
        # Log the deletion
        logger_handler.log_security_event(
            event_type="attendance_record_deletion",
            description=f"{session.get('role', 'unknown').title()} {session.get('username')} deleted attendance record {record_id}",
            severity="HIGH",
            additional_data={
                'record_id': record_id,
                'employee_id': employee_id,
                'location_name': location_name,
                'check_in_date': str(check_in_date),
                'user_role': session.get('role')
            }
        )
        
        # Delete the record
        db.session.delete(attendance_record)
        db.session.commit()
        
        print(f"[LOG] {session.get('role', 'unknown').title()} {session.get('username')} deleted attendance record {record_id} for employee {employee_id}")
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': f'Attendance record for {employee_id} deleted successfully!'
            })
        else:
            flash(f'Attendance record for {employee_id} deleted successfully!', 'success')
            return redirect(url_for('attendance_report'))
        
    except Exception as e:
        db.session.rollback()
        logger_handler.log_database_error('attendance_delete', e)
        print(f"[LOG] Error deleting attendance record {record_id}: {e}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Error deleting attendance record. Please try again.'
            }), 500
        else:
            flash('Error deleting attendance record. Please try again.', 'error')
            return redirect(url_for('attendance_report'))

@app.route('/api/attendance/stats')
@admin_required
def attendance_stats_api():
    """API endpoint for attendance statistics"""
    try:
        # Daily stats for the last 7 days
        daily_stats = db.session.execute(text("""
            SELECT 
                check_in_date,
                COUNT(*) as checkins,
                COUNT(DISTINCT employee_id) as unique_employees
            FROM attendance_data 
            WHERE check_in_date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY check_in_date
            ORDER BY check_in_date DESC
        """)).fetchall()
        
        # Location stats
        location_stats = db.session.execute(text("""
            SELECT 
                location_name,
                COUNT(*) as total_checkins,
                COUNT(DISTINCT employee_id) as unique_employees
            FROM attendance_data
            GROUP BY location_name
            ORDER BY total_checkins DESC
            LIMIT 10
        """)).fetchall()
        
        # Peak hours
        hourly_stats = db.session.execute(text("""
            SELECT 
                EXTRACT(hour FROM check_in_time) as hour,
                COUNT(*) as checkins
            FROM attendance_data
            WHERE check_in_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY EXTRACT(hour FROM check_in_time)
            ORDER BY hour
        """)).fetchall()
        
        return jsonify({
            'daily_stats': [{'date': str(row[0]), 'checkins': row[1], 'employees': row[2]} for row in daily_stats],
            'location_stats': [{'location': row[0], 'checkins': row[1], 'employees': row[2]} for row in location_stats],
            'hourly_stats': [{'hour': int(row[0]), 'checkins': row[1]} for row in hourly_stats]
        })
        
    except Exception as e:
        print(f"Error fetching attendance stats: {e}")
        return jsonify({'error': 'Failed to fetch attendance statistics'}), 500

@app.route('/export-configuration')
@login_required
def export_configuration():
    """Route to display export configuration page"""
    try:
        print("📊 Export configuration route accessed")
        # Check if user has export permissions
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll']:
            logger_handler.logger.warning(f"User {session.get('username', 'unknown')} (role: {user_role}) attempted to access export configuration without permissions")
            flash('Access denied. Only administrators and payroll staff can access export configuration.', 'error')
            return redirect(url_for('attendance_report'))
        
        # Log export configuration access using your existing logger
        try:
            logger_handler.logger.info(f"User {session.get('username', 'unknown')} (role: {user_role}) accessed export configuration")
            logger_handler.logger.info(f"User {session.get('username', 'unknown')} accessed export configuration page")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        # Get current filters from session or request args
        filters = {
            'date_from': request.args.get('date_from', ''),
            'date_to': request.args.get('date_to', ''),
            'location_filter': request.args.get('location', ''),
            'employee_filter': request.args.get('employee', ''),
            'project_filter': request.args.get('project', '')
        }
        
        print(f"📊 Filters: {filters}")
        
        # Check if location accuracy feature exists
        try:
            has_location_accuracy = check_location_accuracy_column_exists()
        except Exception as e:
            print(f"⚠️ Error checking location accuracy column: {e}")
            has_location_accuracy = False
        
        # Define all available columns with their default settings
        available_columns = [
            {'key': 'employee_id', 'label': 'Employee ID', 'default_name': 'Employee ID', 'enabled': True},
            {'key': 'location_name', 'label': 'Location', 'default_name': 'Location', 'enabled': True},
            {'key': 'status', 'label': 'Event', 'default_name': 'Event', 'enabled': True},
            {'key': 'check_in_date', 'label': 'Date', 'default_name': 'Date', 'enabled': True},
            {'key': 'check_in_time', 'label': 'Time', 'default_name': 'Time', 'enabled': True},
            {'key': 'qr_address', 'label': 'QR Address', 'default_name': 'QR Code Address', 'enabled': False},
            {'key': 'address', 'label': 'Check-in Address', 'default_name': 'Check-in Address', 'enabled': False},
            {'key': 'device_info', 'label': 'Device', 'default_name': 'Device Information', 'enabled': False},
            {'key': 'ip_address', 'label': 'IP Address', 'default_name': 'IP Address', 'enabled': False},
            {'key': 'user_agent', 'label': 'User Agent', 'default_name': 'Browser/User Agent', 'enabled': False},
            {'key': 'latitude', 'label': 'Latitude', 'default_name': 'GPS Latitude', 'enabled': False},
            {'key': 'longitude', 'label': 'Longitude', 'default_name': 'GPS Longitude', 'enabled': False},
            {'key': 'accuracy', 'label': 'GPS Accuracy', 'default_name': 'GPS Accuracy (meters)', 'enabled': False},
        ]
        
        # Add location accuracy column if feature exists
        if has_location_accuracy:
            available_columns.append({
                'key': 'location_accuracy', 
                'label': 'Location Accuracy', 
                'default_name': 'Location Accuracy (miles)', 
                'enabled': False
            })
        
        print(f"📊 Rendering export configuration with {len(available_columns)} columns")
        
        return render_template('export_configuration.html',
                             available_columns=available_columns,
                             filters=filters,
                             has_location_accuracy_feature=has_location_accuracy)
        
    except Exception as e:
        print(f"❌ Error in export_configuration route: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Use your existing logger error method with correct parameters
        try:
            logger_handler.log_flask_error(
                error_type="export_configuration_error",
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
        except Exception as log_error:
            print(f"⚠️ Could not log error: {log_error}")
            
        flash('Error loading export configuration page.', 'error')
        return redirect(url_for('attendance_report'))

@app.route('/generate-excel-export', methods=['POST'])
@login_required
def generate_excel_export():
    """Generate and download Excel file with selected columns in specified order"""
    try:
        user_role = session.get('role')
        if user_role not in ['admin', 'payroll']:
            logger_handler.logger.warning(f"User {session.get('username', 'unknown')} (role: {user_role}) attempted unauthorized Excel export")
            flash('Access denied. Only administrators and payroll staff can export data.', 'error')
            return redirect(url_for('attendance_report'))
        
        print("📊 Excel export generation started")
        
        # Log export action using your existing logger
        try:
            logger_handler.logger.info(f"User {session.get('username', 'unknown')} generated Excel export")
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        
        # Get selected columns and custom names from form
        selected_columns_raw = request.form.getlist('selected_columns')
        print(f"📊 Selected columns (raw): {selected_columns_raw}")
        
        # Get column order from form
        column_order_json = request.form.get('column_order', '[]')
        try:
            column_order = json.loads(column_order_json) if column_order_json else []
        except (json.JSONDecodeError, TypeError):
            column_order = []
        
        print(f"📊 Column order from form: {column_order}")
        
        # Determine final column order
        if column_order:
            # Use the specified order, but only include actually selected columns
            selected_columns = [col for col in column_order if col in selected_columns_raw]
            # Add any selected columns that weren't in the order (shouldn't happen, but safety check)
            for col in selected_columns_raw:
                if col not in selected_columns:
                    selected_columns.append(col)
        else:
            # Fallback to raw selection order
            selected_columns = selected_columns_raw
        
        print(f"📊 Final column order: {selected_columns}")
        
        if not selected_columns:
            flash('Please select at least one column to export.', 'error')
            return redirect(url_for('export_configuration'))
        
        column_names = {}
        for column in selected_columns:
            column_names[column] = request.form.get(f'name_{column}', column)
        
        # Get filters
        filters = {
            'date_from': request.form.get('date_from'),
            'date_to': request.form.get('date_to'),
            'location_filter': request.form.get('location_filter'),
            'employee_filter': request.form.get('employee_filter')
        }
        
        print(f"📊 Export filters: {filters}")
        print(f"📊 Column names: {column_names}")
        
        # Save user preferences in session for next time
        session['export_preferences'] = {
            'selected_columns': selected_columns,
            'column_names': column_names,
            'column_order': selected_columns  # This is now the ordered list
        }
        
        # Generate Excel file with ordered columns
        excel_file = create_excel_export_ordered(selected_columns, column_names, filters)
        
        if excel_file:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'attendance_report_{timestamp}.xlsx'
            
            print(f"📊 Excel file generated successfully: {filename}")
            print(f"📊 Column order in export: {selected_columns}")
            
            # Log successful export using your existing logger
            try:
                logger_handler.logger.info(f"Excel export generated successfully with {len(selected_columns)} columns in custom order by user {session.get('username', 'unknown')}")
            except Exception as log_error:
                print(f"⚠️ Logging error (non-critical): {log_error}")
            
            return send_file(
                excel_file,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('Error generating Excel file.', 'error')
            return redirect(url_for('export_configuration'))
            
    except Exception as e:
        print(f"❌ Error in generate_excel_export route: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Use your existing logger error method with correct parameters
        try:
            logger_handler.log_flask_error(
                error_type="excel_export_error",
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
        except Exception as log_error:
            print(f"⚠️ Could not log error: {log_error}")
            
        flash('Error generating Excel export.', 'error')
        return redirect(url_for('export_configuration'))

def create_excel_export(selected_columns, column_names, filters):
    """Create Excel file with selected attendance data - Fixed to use QR address (not location)"""
    try:
        print(f"📊 Creating Excel export with {len(selected_columns)} columns")
        
        # Import openpyxl modules
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError as e:
            print(f"❌ openpyxl import error: {e}")
            print("💡 Install openpyxl: pip install openpyxl")
            return None
        
        # Build query based on filters - JOIN with QRCode to get location_event and location_address
        query = db.session.query(AttendanceData, QRCode).join(QRCode, AttendanceData.qr_code_id == QRCode.id)
        
        # Apply date filters
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(AttendanceData.check_in_date >= date_from)
                print(f"📊 Applied date_from filter: {date_from}")
            except ValueError as e:
                print(f"⚠️ Invalid date_from format: {e}")
                
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(AttendanceData.check_in_date <= date_to)
                print(f"📊 Applied date_to filter: {date_to}")
            except ValueError as e:
                print(f"⚠️ Invalid date_to format: {e}")
        
        # Apply location filter
        if filters.get('location_filter'):
            query = query.filter(AttendanceData.location_name.like(f"%{filters['location_filter']}%"))
            print(f"📊 Applied location filter: {filters['location_filter']}")
        
        # Apply employee filter
        if filters.get('employee_filter'):
            query = query.filter(AttendanceData.employee_id.like(f"%{filters['employee_filter']}%"))
            print(f"📊 Applied employee filter: {filters['employee_filter']}")
        
        # Apply project filter
        if filters.get('project_filter'):
            query = query.filter(QRCode.project_id == int(filters['project_filter']))
            print(f"📊 Applied project filter to export: {filters['project_filter']}")
        
        # Execute query and get results
        results = query.order_by(AttendanceData.check_in_date.desc(), AttendanceData.check_in_time.desc()).all()
        print(f"📊 Found {len(results)} records for export")
        
        if not results:
            print("⚠️ No records found for export")
            return None
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Report"
        
        # Define header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # Add headers
        for idx, column_key in enumerate(selected_columns, 1):
            cell = ws.cell(row=1, column=idx)
            cell.value = column_names.get(column_key, column_key)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Add data
        for row_idx, (attendance_record, qr_code) in enumerate(results, 2):
            for col_idx, column_key in enumerate(selected_columns, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                
                # Get value based on column key
                try:
                    if column_key == 'employee_id':
                        cell.value = attendance_record.employee_id
                    elif column_key == 'location_name':
                        cell.value = attendance_record.location_name
                    elif column_key == 'status':
                        # Use location_event from QR code instead of status
                        cell.value = qr_code.location_event if qr_code.location_event else 'Check In'
                    elif column_key == 'check_in_date':
                        cell.value = attendance_record.check_in_date.strftime('%Y-%m-%d') if attendance_record.check_in_date else ''
                    elif column_key == 'check_in_time':
                        cell.value = attendance_record.check_in_time.strftime('%H:%M:%S') if attendance_record.check_in_time else ''
                    elif column_key == 'qr_address':
                        # FIXED: Use QR Code address (location_address), not location
                        cell.value = qr_code.location_address if qr_code and qr_code.location_address else ''
                    elif column_key == 'address':
                        # IMPLEMENTED: Check-in address logic based on location accuracy
                        # If location accuracy < 0.3 miles, use QR address; otherwise use actual check-in address
                        if hasattr(attendance_record, 'location_accuracy') and attendance_record.location_accuracy is not None:
                            try:
                                accuracy_value = float(attendance_record.location_accuracy)
                                if accuracy_value < 0.3:
                                    # High accuracy - use QR code ADDRESS (not location)
                                    cell.value = qr_code.location_address if qr_code and qr_code.location_address else ''
                                    print(f"📍 Using QR address for employee {attendance_record.employee_id} (accuracy: {accuracy_value:.3f} miles)")
                                else:
                                    # Lower accuracy - use actual check-in address
                                    cell.value = attendance_record.address or ''
                                    print(f"📍 Using check-in address for employee {attendance_record.employee_id} (accuracy: {accuracy_value:.3f} miles)")
                            except (ValueError, TypeError):
                                # If accuracy can't be converted to float, use check-in address
                                cell.value = attendance_record.address or ''
                        else:
                            # No location accuracy data - use actual check-in address
                            cell.value = attendance_record.address or ''
                    elif column_key == 'device_info':
                        cell.value = attendance_record.device_info or ''
                    elif column_key == 'ip_address':
                        cell.value = attendance_record.ip_address or ''
                    elif column_key == 'user_agent':
                        cell.value = attendance_record.user_agent or ''
                    elif column_key == 'latitude':
                        cell.value = attendance_record.latitude or ''
                    elif column_key == 'longitude':
                        cell.value = attendance_record.longitude or ''
                    elif column_key == 'accuracy':
                        cell.value = attendance_record.accuracy or ''
                    elif column_key == 'location_accuracy':
                        cell.value = attendance_record.location_accuracy or ''
                    else:
                        cell.value = ''
                except Exception as cell_error:
                    print(f"⚠️ Error setting cell value for {column_key}: {cell_error}")
                    cell.value = ''
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to BytesIO
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        print("📊 Excel file created successfully with QR address (not QR location)")
        return excel_buffer
        
    except Exception as e:
        print(f"❌ Error creating Excel export: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None

def create_excel_export_ordered(selected_columns, column_names, filters):
    """Create Excel file with selected attendance data in specified column order"""
    try:
        print(f"📊 Creating Excel export with {len(selected_columns)} columns in order: {selected_columns}")
        
        # Import openpyxl modules
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError as e:
            print(f"❌ openpyxl import error: {e}")
            print("💡 Install openpyxl: pip install openpyxl")
            return None
        
        # Build query based on filters - JOIN with QRCode to get location_event and location_address
        query = db.session.query(AttendanceData, QRCode).join(QRCode, AttendanceData.qr_code_id == QRCode.id)
        
        # Apply date filters
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(AttendanceData.check_in_date >= date_from)
                print(f"📊 Applied date_from filter: {date_from}")
            except ValueError as e:
                print(f"⚠️ Invalid date_from format: {e}")
                
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(AttendanceData.check_in_date <= date_to)
                print(f"📊 Applied date_to filter: {date_to}")
            except ValueError as e:
                print(f"⚠️ Invalid date_to format: {e}")
        
        # Apply location filter
        if filters.get('location_filter'):
            query = query.filter(AttendanceData.location_name.like(f"%{filters['location_filter']}%"))
            print(f"📊 Applied location filter: {filters['location_filter']}")
        
        # Apply employee filter
        if filters.get('employee_filter'):
            query = query.filter(AttendanceData.employee_id.like(f"%{filters['employee_filter']}%"))
            print(f"📊 Applied employee filter: {filters['employee_filter']}")
        
        # Execute query and get results
        results = query.order_by(AttendanceData.check_in_date.desc(), AttendanceData.check_in_time.desc()).all()
        print(f"📊 Found {len(results)} records for export")
        
        if not results:
            print("⚠️ No records found for export")
            return None
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Report"
        
        # Define header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # Add headers in the specified order
        for idx, column_key in enumerate(selected_columns, 1):
            cell = ws.cell(row=1, column=idx)
            cell.value = column_names.get(column_key, column_key)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            print(f"📊 Column {idx}: {column_key} -> '{cell.value}'")
        
        # Add data in the same column order
        for row_idx, (attendance_record, qr_code) in enumerate(results, 2):
            for col_idx, column_key in enumerate(selected_columns, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                
                # Get value based on column key (same logic as before)
                try:
                    if column_key == 'employee_id':
                        cell.value = attendance_record.employee_id
                    elif column_key == 'location_name':
                        cell.value = attendance_record.location_name
                    elif column_key == 'status':
                        # Use location_event from QR code instead of status
                        cell.value = qr_code.location_event if qr_code.location_event else 'Check In'
                    elif column_key == 'check_in_date':
                        cell.value = attendance_record.check_in_date.strftime('%Y-%m-%d') if attendance_record.check_in_date else ''
                    elif column_key == 'check_in_time':
                        cell.value = attendance_record.check_in_time.strftime('%H:%M:%S') if attendance_record.check_in_time else ''
                    elif column_key == 'qr_address':
                        # Use QR Code address (location_address), not location
                        cell.value = qr_code.location_address if qr_code and qr_code.location_address else ''
                    elif column_key == 'address':
                        # Check-in address logic based on location accuracy with hyperlink support
                        if hasattr(attendance_record, 'location_accuracy') and attendance_record.location_accuracy is not None:
                            try:
                                accuracy_value = float(attendance_record.location_accuracy)
                                if accuracy_value < 0.3:
                                    # High accuracy - use QR code ADDRESS (not location)
                                    address_text = qr_code.location_address if qr_code and qr_code.location_address else ''
                                    # For QR address, use QR coordinates if available
                                    if address_text and hasattr(qr_code, 'address_latitude') and hasattr(qr_code, 'address_longitude') and qr_code.address_latitude and qr_code.address_longitude:
                                        # Format coordinates with 10 decimal places
                                        lat_formatted = f"{float(qr_code.address_latitude):.10f}"
                                        lng_formatted = f"{float(qr_code.address_longitude):.10f}"
                                        hyperlink_formula = f'=HYPERLINK("http://maps.google.com/maps?q={lat_formatted},{lng_formatted}","{address_text}")'
                                        cell.value = hyperlink_formula
                                        print(f"📍 Added QR address hyperlink for employee {attendance_record.employee_id}")
                                    else:
                                        cell.value = address_text
                                else:
                                    # Lower accuracy - use actual check-in address
                                    address_text = attendance_record.address or ''
                                    # Create hyperlink using check-in coordinates
                                    if address_text and attendance_record.latitude and attendance_record.longitude:
                                        # Format coordinates with 10 decimal places
                                        lat_formatted = f"{float(attendance_record.latitude):.10f}"
                                        lng_formatted = f"{float(attendance_record.longitude):.10f}"
                                        hyperlink_formula = f'=HYPERLINK("http://maps.google.com/maps?q={lat_formatted},{lng_formatted}","{address_text}")'
                                        cell.value = hyperlink_formula
                                        print(f"📍 Added check-in address hyperlink for employee {attendance_record.employee_id}")
                                    else:
                                        cell.value = address_text
                            except (ValueError, TypeError):
                                # If accuracy can't be converted to float, use check-in address
                                address_text = attendance_record.address or ''
                                if address_text and attendance_record.latitude and attendance_record.longitude:
                                    # Format coordinates with 10 decimal places
                                    lat_formatted = f"{float(attendance_record.latitude):.10f}"
                                    lng_formatted = f"{float(attendance_record.longitude):.10f}"
                                    hyperlink_formula = f'=HYPERLINK("http://maps.google.com/maps?q={lat_formatted},{lng_formatted}","{address_text}")'
                                    cell.value = hyperlink_formula
                                    print(f"📍 Added check-in address hyperlink for employee {attendance_record.employee_id} (fallback)")
                                else:
                                    cell.value = address_text
                        else:
                            # No location accuracy data - use actual check-in address
                            address_text = attendance_record.address or ''
                            if address_text and attendance_record.latitude and attendance_record.longitude:
                                # Format coordinates with 10 decimal places
                                lat_formatted = f"{float(attendance_record.latitude):.10f}"
                                lng_formatted = f"{float(attendance_record.longitude):.10f}"
                                hyperlink_formula = f'=HYPERLINK("http://maps.google.com/maps?q={lat_formatted},{lng_formatted}","{address_text}")'
                                cell.value = hyperlink_formula
                                print(f"📍 Added check-in address hyperlink for employee {attendance_record.employee_id} (no accuracy data)")
                            else:
                                cell.value = address_text
                    elif column_key == 'device_info':
                        cell.value = attendance_record.device_info or ''
                    elif column_key == 'ip_address':
                        cell.value = attendance_record.ip_address or ''
                    elif column_key == 'user_agent':
                        cell.value = attendance_record.user_agent or ''
                    elif column_key == 'latitude':
                        cell.value = attendance_record.latitude or ''
                    elif column_key == 'longitude':
                        cell.value = attendance_record.longitude or ''
                    elif column_key == 'accuracy':
                        cell.value = attendance_record.accuracy or ''
                    elif column_key == 'location_accuracy':
                        cell.value = attendance_record.location_accuracy or ''
                    else:
                        cell.value = ''
                except Exception as cell_error:
                    print(f"⚠️ Error setting cell value for {column_key}: {cell_error}")
                    cell.value = ''
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to BytesIO
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        print("📊 Excel file created successfully with custom column order")
        return excel_buffer
        
    except Exception as e:
        print(f"❌ Error creating Excel export: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None
   
           
# Jinja2 filters for better template functionality
@app.template_filter('days_since')
def days_since_filter(date):
    """Calculate days since a given date"""
    if not date:
        return 0
    from datetime import datetime
    now = datetime.utcnow()
    return (now - date).days

@app.template_filter('time_ago')
def time_ago_filter(date):
    """Human readable time ago"""
    if not date:
        return 'Never'
    from datetime import datetime
    now = datetime.utcnow()
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors with user-friendly page"""
    if app.debug:
        # Let Flask handle debug errors naturally
        return None
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Server Error</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>🔧 Something went wrong</h1>
        <p>We're working to fix this issue. Please try again later.</p>
        <a href="/" style="color: #2563eb;">← Back to Home</a>
    </body>
    </html>
    ''', 500

@app.errorhandler(404)
def not_found(error):
    """Handle page not found errors"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Page Not Found</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>🔍 Page Not Found</h1>
        <p>The page you're looking for doesn't exist.</p>
        <a href="/" style="color: #2563eb;">← Back to Home</a>
    </body>
    </html>
    ''', 404

# Initialize database tables
@log_database_operations('database_initialization')
def create_tables():
    """Create database tables and default admin user with logging"""
    try:
        db.create_all()
        
        # Create default admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                full_name='System Administrator',
                email='admin@example.com',
                username='admin',
                role='admin'
            )
            admin.set_password('admin123')  # Change this in production
            db.session.add(admin)
            db.session.commit()
            
            # Log admin user creation
            logger_handler.logger.info("Default admin user created during initialization")
            
        # Initialize logging table
        logger_handler._create_log_table()
        
    except Exception as e:
        logger_handler.log_database_error('database_initialization', e)
        raise

def update_existing_qr_codes():
    """Update existing QR codes with URLs and regenerate QR images with logging"""
    try:
        qr_codes = QRCode.query.filter_by(active_status=True).all()
        updated_count = 0
        
        for qr_code in qr_codes:
            if not qr_code.qr_url or not qr_code.qr_code_image:
                try:
                    # Generate URL if missing
                    if not qr_code.qr_url:
                        qr_code.qr_url = generate_qr_url(qr_code.name, qr_code.id)
                    
                    # Generate QR image if missing
                    if not qr_code.qr_code_image:
                        qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
                        
                        # Use styling from database if available, otherwise defaults
                        styling = get_qr_styling(qr_code)
                        qr_code.qr_code_image = generate_qr_code(
                            data=qr_data,
                            fill_color=styling['fill_color'],
                            back_color=styling['back_color'],
                            box_size=styling['box_size'],
                            border=styling['border'],
                            error_correction=styling['error_correction']
                        )
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger_handler.log_flask_error(
                        error_type="qr_code_update_error",
                        error_message=f"Failed to update QR code {qr_code.id}: {str(e)}"
                    )
                    continue
        
        if updated_count > 0:
            db.session.commit()
            logger_handler.logger.info(f"Updated {updated_count} existing QR codes with missing URLs/images")
            
    except Exception as e:
        logger_handler.log_database_error('update_existing_qr_codes', e)
        print(f"Error updating existing QR codes: {e}")

def add_qr_customization_columns():
    """Add QR code customization columns to existing table"""
    try:
        with app.app_context():
            # Add columns to QRCode table if they don't exist
            db.engine.execute("""
                ALTER TABLE qr_codes 
                ADD COLUMN IF NOT EXISTS fill_color VARCHAR(7) DEFAULT '#000000',
                ADD COLUMN IF NOT EXISTS back_color VARCHAR(7) DEFAULT '#FFFFFF',
                ADD COLUMN IF NOT EXISTS box_size INT DEFAULT 10,
                ADD COLUMN IF NOT EXISTS border INT DEFAULT 4,
                ADD COLUMN IF NOT EXISTS error_correction VARCHAR(1) DEFAULT 'L',
                ADD COLUMN IF NOT EXISTS style_id INT,
                ADD FOREIGN KEY (style_id) REFERENCES qr_code_styles(id)
            """)
            
            # Create QRCodeStyle table
            db.create_all()
            
            # Insert default styles
            default_styles = [
                QRCodeStyle(name="Classic Black", fill_color="#000000", back_color="#FFFFFF", is_default=True),
                QRCodeStyle(name="Blue Professional", fill_color="#2563eb", back_color="#FFFFFF"),
                QRCodeStyle(name="Green Success", fill_color="#10b981", back_color="#FFFFFF"),
                QRCodeStyle(name="Red Alert", fill_color="#ef4444", back_color="#FFFFFF"),
                QRCodeStyle(name="Dark Mode", fill_color="#FFFFFF", back_color="#1f2937"),
                QRCodeStyle(name="High Contrast", fill_color="#000000", back_color="#FFFF00"),
                QRCodeStyle(name="Corporate Blue", fill_color="#1e40af", back_color="#f8fafc"),
                QRCodeStyle(name="Minimalist Gray", fill_color="#6b7280", back_color="#FFFFFF")
            ]
            
            for style in default_styles:
                if not QRCodeStyle.query.filter_by(name=style.name).first():
                    db.session.add(style)
            
            db.session.commit()
            print("QR Code customization tables and default styles created successfully!")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error adding QR customization columns: {e}")

def add_coordinate_columns():
    """Add coordinate columns to existing qr_codes table (MySQL compatible)"""
    try:
        # Check if columns already exist - MySQL compatible query
        result = db.session.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'qr_codes' 
            AND COLUMN_NAME IN ('address_latitude', 'address_longitude', 'coordinate_accuracy', 'coordinates_updated_date')
        """))
        
        existing_columns = [row.COLUMN_NAME for row in result.fetchall()]
        
        # Add missing columns
        if 'address_latitude' not in existing_columns:
            db.session.execute(text("""
                ALTER TABLE qr_codes ADD COLUMN address_latitude FLOAT
            """))
            print("✅ Added address_latitude column")
        
        if 'address_longitude' not in existing_columns:
            db.session.execute(text("""
                ALTER TABLE qr_codes ADD COLUMN address_longitude FLOAT
            """))
            print("✅ Added address_longitude column")
        
        if 'coordinate_accuracy' not in existing_columns:
            db.session.execute(text("""
                ALTER TABLE qr_codes ADD COLUMN coordinate_accuracy VARCHAR(50) DEFAULT 'geocoded'
            """))
            print("✅ Added coordinate_accuracy column")
        
        if 'coordinates_updated_date' not in existing_columns:
            db.session.execute(text("""
                ALTER TABLE qr_codes ADD COLUMN coordinates_updated_date TIMESTAMP
            """))
            print("✅ Added coordinates_updated_date column")
        
        db.session.commit()
        print("✅ Database migration completed successfully")
        
    except Exception as e:
        print(f"❌ Database migration error: {e}")
        db.session.rollback()

# Application context processor for logging status
@app.context_processor
def inject_logging_status():
    """Inject logging status into all templates"""
    return {
        'logging_enabled': hasattr(app, 'logger_handler'),
        'is_admin': has_admin_privileges(session.get('role', ''))
    }

# Before request handler for request logging
@app.before_request
def log_request_info():
    """Log request information for security monitoring"""
    # Skip logging for static files and API calls
    if (request.endpoint and 
        (request.endpoint.startswith('static') or 
         request.path.startswith('/api/logs'))):
        return
    
    # Log suspicious activity
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Check for potential security threats
    suspicious_patterns = [
        'sqlmap', 'nikto', 'nmap', 'dirb', 'dirbuster',
        'wget', 'curl.*bot', 'scanner', 'exploit'
    ]
    
    if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
        logger_handler.log_security_event(
            event_type="suspicious_user_agent",
            description=f"Suspicious user agent detected: {user_agent[:200]}",
            severity="HIGH",
            additional_data={'user_agent': user_agent, 'ip_address': ip_address}
        )

# After request handler for performance monitoring
@app.after_request
def log_response_info(response):
    """Log response information for performance monitoring"""
    # Skip logging for static files
    if request.endpoint and request.endpoint.startswith('static'):
        return response
    
    # Log slow requests (over 5 seconds)
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        if duration > 5.0:
            logger_handler.logger.warning(f"Slow request: {request.path} took {duration:.2f} seconds")
    
    # Log error responses
    if response.status_code >= 400:
        logger_handler.logger.warning(
            f"Error response: {response.status_code} for {request.path} "
            f"by user {session.get('username', 'anonymous')}"
        )
    
    return response

if __name__ == '__main__':
    with app.app_context():
        try:
            # Initialize database and logging
            create_tables()
            # update_existing_qr_codes()
            # add_qr_customization_columns()

            # Log application startup
            logger_handler.logger.info("QR Attendance Management System started successfully")
            
            print("🚀 QR Attendance Management System")
            print("="*50)
            print("✅ Database initialized")
            print("✅ Logging system enabled")
            print("✅ Application ready")
            print("\n📋 Logging Features:")
            print("   • User login/logout tracking")
            print("   • QR code creation/modification/deletion")
            print("   • Database error monitoring")
            print("   • Flask application error tracking")
            print("   • Security event logging")
            print("\n📁 Log Files Location: ./logs/")
            print("   • application.log - General application events")
            print("   • errors.log - Error events")
            print("   • security.log - Security-related events")
            print("\n💾 Database Logging: log_events table")
            
        except Exception as e:
            print(f"❌ Application startup failed: {e}")
            if hasattr(app, 'logger_handler'):
                logger_handler.log_flask_error(
                    error_type="application_startup_error",
                    error_message=str(e)
                )
            raise

    app.run(debug=os.environ.get('DEBUG'), 
            host=os.environ.get('FLASK_HOST'),
            port=os.environ.get('FLASK_PORT'))
