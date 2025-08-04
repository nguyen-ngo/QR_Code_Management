from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, time, timedelta
import qrcode
import io
import base64
import os
from sqlalchemy import text
import re
import uuid
from user_agents import parse
import requests
import json
from math import radians, cos, sin, asin, sqrt

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres1411@localhost/qr_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

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
    password_hash = db.Column(db.String(128), nullable=False)
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
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin privileges"""
        return self.role == 'admin'

# QR Code Model
class QRCode(db.Model):
    """
    Enhanced QR Code model to manage QR code records and metadata with address coordinates
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
    qr_url = db.Column(db.String(255), unique=True, nullable=True)
    
    # NEW: Address Coordinates Fields
    address_latitude = db.Column(db.Float, nullable=True)
    address_longitude = db.Column(db.Float, nullable=True)
    coordinate_accuracy = db.Column(db.String(50), nullable=True, default='geocoded')
    coordinates_updated_date = db.Column(db.DateTime, nullable=True)
    
    @property
    def has_coordinates(self):
        """Check if this QR code has address coordinates"""
        return self.address_latitude is not None and self.address_longitude is not None
    @property
    def coordinates_display(self):
        """Get formatted coordinates for display"""
        if self.has_coordinates:
            return f"{self.address_latitude:.6f}, {self.address_longitude:.6f}"
        return "Coordinates not available"

    def update_coordinates(self, latitude, longitude, accuracy='geocoded'):
        """Update the address coordinates for this QR code"""
        self.address_latitude = latitude
        self.address_longitude = longitude
        self.coordinate_accuracy = accuracy
        self.coordinates_updated_date = datetime.utcnow()

# Attendance Data Model
class AttendanceData(db.Model):
    """Enhanced attendance tracking model with location support"""
    __tablename__ = 'attendance_data'
    
    # Existing fields
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_codes.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False, default=datetime.today)
    check_in_time = db.Column(db.Time, nullable=False, default=datetime.now().time)
    device_info = db.Column(db.String(200))
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    location_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='present')
    created_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    updated_timestamp = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # LOCATION FIELDS - Add these if missing
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    accuracy = db.Column(db.Float, nullable=True)
    altitude = db.Column(db.Float, nullable=True)
    location_source = db.Column(db.String(50), default='manual')
    address = db.Column(db.String(500), nullable=True)
    
    # Relationships
    qr_code = db.relationship('QRCode', backref=db.backref('attendance_records', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AttendanceData {self.employee_id} at {self.location_name} on {self.check_in_date}>'
    
    @property
    def has_location_data(self):
        """Check if this record has GPS coordinates"""
        return self.latitude is not None and self.longitude is not None
    
    @property
    def location_accuracy_level(self):
        """Get human-readable accuracy level"""
        if not self.accuracy:
            return 'unknown'
        elif self.accuracy <= 50:
            return 'high'
        elif self.accuracy <= 100:
            return 'medium'
        else:
            return 'low'
    
    @property
    def coordinates_display(self):
        """Get formatted coordinates for display"""
        if self.has_location_data:
            return f"{self.latitude:.6f}, {self.longitude:.6f}"
        return "No GPS data"
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'check_in_date': self.check_in_date.isoformat(),
            'check_in_time': self.check_in_time.isoformat(),
            'location_name': self.location_name,
            'status': self.status,
            'has_location': self.has_location_data,
            'coordinates': self.coordinates_display,
            'accuracy': self.accuracy,
            'address': self.address,
            'location_source': self.location_source
        }

# Utility functions    
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
                print(f"   Coordinates: {lat:.6f}, {lng:.6f}")
                print(f"   Accuracy: {accuracy}")
                
                return lat, lng, accuracy
            
        print(f"⚠️ No results from enhanced geocoding for: {address}")
        return None, None, None
        
    except Exception as e:
        print(f"❌ Enhanced geocoding error: {e}")
        return None, None, None
    
def geocode_address_enhanced(address):
    """
    Enhanced geocoding function for new coordinate features
    Returns (lat, lng, accuracy) tuple or (None, None, None) if failed
    """
    if not address or address.strip() == '':
        return None, None, None
    
    try:
        # Using Nominatim (OpenStreetMap) geocoding service
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
                print(f"   Coordinates: {lat:.6f}, {lng:.6f}")
                print(f"   Accuracy: {accuracy} ({place_type})")
                
                return lat, lng, accuracy
            
        print(f"⚠️ No geocoding results for address: {address}")
        return None, None, None
        
    except Exception as e:
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
        print(f"   Point 1: {lat1*180/3.14159:.6f}, {lng1*180/3.14159:.6f}")
        print(f"   Point 2: {lat2*180/3.14159:.6f}, {lng2*180/3.14159:.6f}")
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
    
    Parameters:
    - qr_address: Address associated with the QR code
    - checkin_address: Address where user checked in (from reverse geocoding)
    - checkin_lat: GPS latitude from check-in (if available)
    - checkin_lng: GPS longitude from check-in (if available)
    
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
    qr_lat, qr_lng, qr_accuracy = get_coordinates_from_address_enhanced(qr_address)
    
    if qr_lat is None or qr_lng is None:
        print(f"❌ Could not geocode QR address: {qr_address}")
        return None
    
    print(f"✅ QR location coordinates: {qr_lat:.6f}, {qr_lng:.6f} (accuracy: {qr_accuracy})")
    
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
                print(f"✅ Using GPS coordinates: {lat_val:.6f}, {lng_val:.6f}")
            else:
                print(f"⚠️ Invalid GPS coordinates: {lat_val}, {lng_val}")
        except (ValueError, TypeError):
            print(f"⚠️ Could not parse GPS coordinates")
    
    # Priority 2: Fallback to geocoding check-in address
    if checkin_coords_lat is None and checkin_address:
        print(f"🌍 Falling back to geocoding check-in address...")
        checkin_coords_lat, checkin_coords_lng, checkin_accuracy = get_coordinates_from_address_enhanced(checkin_address)
        if checkin_coords_lat is not None:
            checkin_source = "address"
            print(f"✅ Using geocoded coordinates: {checkin_coords_lat:.6f}, {checkin_coords_lng:.6f} (accuracy: {checkin_accuracy})")
    
    # Check if we have valid coordinates for both locations
    if checkin_coords_lat is None or checkin_coords_lng is None:
        print(f"❌ Could not determine check-in coordinates")
        print(f"   GPS: {checkin_lat}, {checkin_lng}")
        print(f"   Address: {checkin_address}")
        return None
    
    # Step 3: Calculate enhanced distance
    print(f"\n📏 Step 3: Calculating enhanced distance...")
    distance = calculate_distance_miles(qr_lat, qr_lng, checkin_coords_lat, checkin_coords_lng)
    
    if distance is not None:
        print(f"✅ Enhanced location accuracy calculated successfully!")
        print(f"   QR Location: {qr_lat:.6f}, {qr_lng:.6f}")
        print(f"   Check-in Location: {checkin_coords_lat:.6f}, {checkin_coords_lng:.6f}")
        print(f"   Source: {checkin_source}")
        print(f"   Distance: {distance:.4f} miles")
        print(f"   Accuracy Level: {get_location_accuracy_level_enhanced(distance)}")
    else:
        print(f"❌ Failed to calculate distance")
    
    return distance

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

def calculate_distance_miles(lat1, lng1, lat2, lng2):
    """
    Calculate the great circle distance between two points on Earth in miles
    Using the Haversine formula
    """
    if any(coord is None for coord in [lat1, lng1, lat2, lng2]):
        return None
    
    try:
        # Convert decimal degrees to radians
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlng = lng2 - lng1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of Earth in miles
        r_miles = 3959
        
        # Calculate the result
        distance = c * r_miles
        
        print(f"📏 Calculated distance: {distance:.3f} miles")
        return round(distance, 3)
        
    except Exception as e:
        print(f"❌ Error calculating distance: {e}")
        return None

def get_location_accuracy_level(location_accuracy):
    """Get human-readable location accuracy level based on distance"""
    if not location_accuracy:
        return 'unknown'
    elif location_accuracy <= 0.1:  # Within 0.1 mile (528 feet)
        return 'excellent'
    elif location_accuracy <= 0.5:  # Within 0.5 mile
        return 'good'
    elif location_accuracy <= 1.0:  # Within 1 mile
        return 'fair'
    else:
        return 'poor'

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

def process_location_data_enhanced(form_data):
    """
    Enhanced location data processing with better validation and error handling
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
        # Enhanced latitude validation
        if form_data.get('latitude') and form_data['latitude'] not in ['null', '', 'undefined']:
            lat = float(form_data['latitude'])
            if -90 <= lat <= 90:
                processed['latitude'] = round(lat, 6)  # 6 decimal precision
            else:
                print(f"⚠️ Invalid latitude range: {lat}")
        
        # Enhanced longitude validation  
        if form_data.get('longitude') and form_data['longitude'] not in ['null', '', 'undefined']:
            lng = float(form_data['longitude'])
            if -180 <= lng <= 180:
                processed['longitude'] = round(lng, 6)  # 6 decimal precision
            else:
                print(f"⚠️ Invalid longitude range: {lng}")
        
        # Enhanced accuracy validation
        if form_data.get('accuracy') and form_data['accuracy'] not in ['null', '', 'undefined']:
            acc = float(form_data['accuracy'])
            if 0 <= acc <= 50000:  # Reasonable accuracy range in meters
                processed['accuracy'] = round(acc, 1)
            else:
                print(f"⚠️ Invalid accuracy value: {acc}")
        
        # Enhanced altitude validation
        if form_data.get('altitude') and form_data['altitude'] not in ['null', '', 'undefined']:
            alt = float(form_data['altitude'])
            if -1000 <= alt <= 10000:  # Reasonable altitude range in meters
                processed['altitude'] = round(alt, 1)
            else:
                print(f"⚠️ Invalid altitude value: {alt}")
        
        # Enhanced address processing
        if form_data.get('address'):
            address = form_data['address'].strip()
            if len(address) > 0:
                processed['address'] = address[:500]  # Limit to 500 characters
        
        print(f"✅ Enhanced location data processed: {processed}")
        
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error in enhanced location data processing: {e}")
    
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
    """Check if the location_accuracy column exists in the attendance_data table"""
    try:
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='attendance_data' AND column_name='location_accuracy'
        """))
        
        column_exists = result.fetchone() is not None
        return column_exists
        
    except Exception as e:
        print(f"⚠️ Error checking location_accuracy column: {e}")
        return False
    
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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        if session.get('role') != 'admin':
            flash('Administrator privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Utility function to generate QR code
def generate_qr_code(data):
    """Generate QR code image and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

@app.template_filter('strftime')
def strftime_filter(value, format='%Y-%m-%d'):
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
def register():
    """User registration endpoint"""
    if request.method == 'POST':
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
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout endpoint"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard after login - Fixed to show all QR codes"""
    user = User.query.get(session['user_id'])
    
    # Get ALL QR codes (both active and inactive) with proper error handling
    # The frontend filtering will handle display logic
    try:
        qr_codes = QRCode.query.order_by(QRCode.created_date.desc()).all()  # ✅ Fixed: removed filter
    except Exception as e:
        print(f"Error fetching QR codes: {e}")
        qr_codes = []
    
    return render_template('dashboard.html', user=user, qr_codes=qr_codes)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'profile':
            # Update profile information
            user.full_name = request.form['full_name']
            user.email = request.form['email']
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            
        elif form_type == 'password':
            # Update password
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            
            if user.check_password(current_password):
                user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect.', 'error')
        
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=user)

@app.route('/users')
@admin_required
def users():
    """User management page (Admin only) - Enhanced with better data"""
    try:
        # Get all users with their QR code counts
        all_users = db.session.query(User).all()
        
        # Add QR code counts to each user
        for user in all_users:
            user.qr_code_count = user.created_qr_codes.count()
            user.active_qr_count = user.created_qr_codes.filter_by(active_status=True).count()
        
        print(f"Found {len(all_users)} users for admin view")
        return render_template('users.html', users=all_users)
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        flash('Error loading users. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user (Admin only)"""
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            username = request.form.get('username', '').strip().lower()
            password = request.form.get('password', '')
            role = request.form.get('role', '')
            
            # Validation
            if not all([full_name, email, username, password, role]):
                flash('All fields are required.', 'error')
                return render_template('create_user.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('create_user.html')
            
            if role not in ['staff', 'admin']:
                flash('Invalid role specified.', 'error')
                return render_template('create_user.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('create_user.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('create_user.html')
            
            # Create user
            new_user = User(
                full_name=full_name,
                email=email,
                username=username,
                role=role,
                created_by=session['user_id'],
                created_date=datetime.utcnow(),
                active_status=True
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'User "{full_name}" created successfully!', 'success')
            print(f"Admin {session['username']} created user: {username} with role: {role}")
            
            return redirect(url_for('users'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            flash('Error creating user. Please try again.', 'error')
            return render_template('create_user.html')
    
    return render_template('create_user.html')

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
        
        if user_to_demote.role == 'staff':
            flash('User is already staff.', 'info')
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
def edit_user(user_id):
    """Edit user information (Admin only)"""
    try:
        user_to_edit = User.query.get(user_id)
        current_user = User.query.get(session['user_id'])
        
        if not user_to_edit:
            flash('User not found.', 'error')
            return redirect(url_for('users'))
        
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            new_role = request.form.get('role', '')
            new_password = request.form.get('new_password', '').strip()
            
            # Validation
            if not all([full_name, email, new_role]):
                flash('Name, email, and role are required.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            if new_role not in ['staff', 'admin']:
                flash('Invalid role specified.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Check for email conflicts (excluding current user)
            existing_email_user = User.query.filter_by(email=email).first()
            if existing_email_user and existing_email_user.id != user_to_edit.id:
                flash('Email already in use by another user.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Prevent self-demotion
            if (user_to_edit.id == current_user.id and 
                user_to_edit.role == 'admin' and new_role == 'staff'):
                flash('You cannot demote yourself. Have another admin do this.', 'error')
                return render_template('edit_user.html', user=user_to_edit)
            
            # Check if demoting the last admin
            if (user_to_edit.role == 'admin' and new_role == 'staff'):
                active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
                if active_admin_count <= 1:
                    flash('Cannot demote the last admin user. Promote another user to admin first.', 'error')
                    return render_template('edit_user.html', user=user_to_edit)
            
            # Update user information
            user_to_edit.full_name = full_name
            user_to_edit.email = email
            user_to_edit.role = new_role
            
            # Handle password change if provided
            if new_password:
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'error')
                    return render_template('edit_user.html', user=user_to_edit)
                user_to_edit.set_password(new_password)
            
            db.session.commit()
            flash(f'User "{user_to_edit.full_name}" updated successfully.', 'success')
            print(f"Admin {current_user.username} updated user: {user_to_edit.username}")
            
            return redirect(url_for('users'))
        
        return render_template('edit_user.html', user=user_to_edit)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error editing user: {e}")
        flash('Error updating user. Please try again.', 'error')
        return redirect(url_for('users'))

# ENHANCED USER STATISTICS API
@app.route('/api/users/stats')
@admin_required
def user_stats_api():
    """API endpoint for user statistics"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(active_status=True).count()
        admin_users = User.query.filter_by(role='admin', active_status=True).count()
        staff_users = User.query.filter_by(role='staff', active_status=True).count()
        inactive_users = User.query.filter_by(active_status=False).count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = User.query.filter(User.created_date >= thirty_days_ago).count()
        
        # Recent logins (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = User.query.filter(
            User.last_login_date >= seven_days_ago,
            User.active_status == True
        ).count()
        
        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'staff_users': staff_users,
            'inactive_users': inactive_users,
            'recent_registrations': recent_registrations,
            'recent_logins': recent_logins
        })
        
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        return jsonify({'error': 'Failed to fetch user statistics'}), 500

@app.route('/api/geocode', methods=['POST'])
@login_required  # Add this decorator if you have it
def geocode_address():
    """
    API endpoint to geocode an address and return coordinates
    """
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
                    'coordinates_display': f"{lat:.6f}, {lng:.6f}"
                },
                'message': f'Address geocoded successfully with {accuracy} accuracy'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to geocode the provided address. Please verify the address is complete and accurate.'
            }), 400
            
    except Exception as e:
        print(f"❌ Geocoding API error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while geocoding the address'
        }), 500

@app.route('/users/<int:user_id>/permanently-delete', methods=['GET', 'POST'])
@admin_required
def permanently_delete_user(user_id):
    """Permanently delete user and all associated data (Admin only)"""
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
        
        # Delete all QR codes created by this user
        QRCode.query.filter_by(created_by=user_id).delete()
        
        # Update any users that were created by this user (set created_by to None)
        created_users = User.query.filter_by(created_by=user_id).all()
        for created_user in created_users:
            created_user.created_by = None
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'User "{user_name}" and {user_qr_count} associated QR codes have been permanently deleted.', 'success')
        print(f"Admin {current_user.username} permanently deleted user: {user_to_delete.username}")
        
        return redirect(url_for('users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error permanently deleting user: {e}")
        flash('Error deleting user. Please try again.', 'error')
        return redirect(url_for('users'))
    
# BULK USER OPERATIONS
@app.route('/users/bulk/deactivate', methods=['POST'])
@admin_required
def bulk_deactivate_users():
    """Bulk deactivate multiple users (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        current_user_id = session['user_id']
        current_user = User.query.get(current_user_id)
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Filter out current user and validate
        valid_user_ids = []
        admin_count = User.query.filter_by(role='admin', active_status=True).count()
        admins_to_deactivate = 0
        
        for user_id in user_ids:
            if user_id == current_user_id:
                continue  # Skip current user
            
            user = User.query.get(user_id)
            if user and user.active_status:
                if user.role == 'admin':
                    admins_to_deactivate += 1
                valid_user_ids.append(user_id)
        
        # Check if we're trying to deactivate all admins
        if admin_count - admins_to_deactivate < 1:
            return jsonify({'error': 'Cannot deactivate all admin users'}), 400
        
        # Deactivate users
        deactivated_count = 0
        for user_id in valid_user_ids:
            user = User.query.get(user_id)
            if user:
                user.active_status = False
                deactivated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deactivated {deactivated_count} users',
            'deactivated_count': deactivated_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk deactivate: {e}")
        return jsonify({'error': 'Failed to deactivate users'}), 500

@app.route('/users/bulk/activate', methods=['POST'])
@admin_required
def bulk_activate_users():
    """Bulk activate multiple users (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Activate users
        activated_count = 0
        for user_id in user_ids:
            user = User.query.get(user_id)
            if user and not user.active_status:
                user.active_status = True
                activated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully activated {activated_count} users',
            'activated_count': activated_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk activate: {e}")
        return jsonify({'error': 'Failed to activate users'}), 500

@app.route('/users/bulk/permanently-delete', methods=['POST'])
@admin_required
def bulk_permanently_delete_users():
    """Bulk permanently delete multiple users and all associated data (Admin only)"""
    try:
        user_ids = request.json.get('user_ids', [])
        current_user_id = session['user_id']
        current_user = User.query.get(current_user_id)
        
        if not user_ids:
            return jsonify({'error': 'No users selected'}), 400
        
        # Convert string IDs to integers for safety
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid user IDs provided'}), 400
        
        # Security validations
        deleted_users = []
        deleted_qr_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                # Skip current user
                if user_id == current_user_id:
                    errors.append(f"Cannot delete your own account")
                    continue
                
                user_to_delete = User.query.get(user_id)
                if not user_to_delete:
                    errors.append(f"User with ID {user_id} not found")
                    continue
                
                # Only allow deletion of inactive users for safety
                if user_to_delete.active_status:
                    errors.append(f"User '{user_to_delete.full_name}' must be deactivated before permanent deletion")
                    continue
                
                # If deleting an admin, ensure at least one admin remains
                if user_to_delete.role == 'admin':
                    active_admin_count = User.query.filter_by(role='admin', active_status=True).count()
                    if active_admin_count <= 1:
                        errors.append(f"Cannot delete the last admin user '{user_to_delete.full_name}'")
                        continue
                
                # Count QR codes before deletion for reporting
                user_qr_count = user_to_delete.created_qr_codes.count()
                deleted_qr_count += user_qr_count
                
                # Delete all QR codes created by this user
                QRCode.query.filter_by(created_by=user_id).delete()
                
                # Update any users that were created by this user (set created_by to None)
                created_users = User.query.filter_by(created_by=user_id).all()
                for created_user in created_users:
                    created_user.created_by = None
                
                # Delete the user
                deleted_users.append({
                    'name': user_to_delete.full_name,
                    'username': user_to_delete.username,
                    'qr_count': user_qr_count
                })
                
                db.session.delete(user_to_delete)
                
            except Exception as e:
                print(f"Error processing user {user_id}: {e}")
                errors.append(f"Error processing user ID {user_id}")
                continue
        
        # Commit all changes if we have deletions
        if deleted_users:
            db.session.commit()
            
            # Log the bulk deletion
            deleted_names = [user['name'] for user in deleted_users]
            print(f"Admin {current_user.username} permanently deleted {len(deleted_users)} users: {', '.join(deleted_names)}")
        
        # Prepare response message
        if deleted_users and not errors:
            message = f'Successfully deleted {len(deleted_users)} users and {deleted_qr_count} associated QR codes'
        elif deleted_users and errors:
            message = f'Deleted {len(deleted_users)} users and {deleted_qr_count} QR codes. {len(errors)} operations failed'
        elif not deleted_users and errors:
            return jsonify({
                'success': False,
                'error': 'No users could be deleted',
                'details': errors
            }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'No valid users to delete'
            }), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': len(deleted_users),
            'deleted_qr_count': deleted_qr_count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in bulk permanently delete users: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete users. Please try again.'
        }), 500
    
# ENHANCED LOGIN WITH BETTER SESSION MANAGEMENT
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced user authentication with better error handling"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        try:
            # Find user (case-insensitive username)
            user = User.query.filter(
                User.username.ilike(username),
                User.active_status == True
            ).first()
            
            if user and user.check_password(password):
                # Successful login
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['full_name'] = user.full_name
                
                # Update last login date
                user.last_login_date = datetime.utcnow()
                db.session.commit()
                
                flash(f'Welcome back, {user.full_name}!', 'success')
                print(f"User {user.username} logged in successfully")
                
                # Redirect to intended page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
                
            else:
                # Invalid credentials
                flash('Invalid username or password.', 'error')
                print(f"Failed login attempt for username: {username}")
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
    
    return render_template('login.html')

# Add this helper function to check admin requirements more safely
def is_admin_user(user_id):
    """Helper function to safely check if user is admin"""
    try:
        user = User.Query.get(user_id)
        return user and user.active_status and user.role == 'admin'
    except:
        return False

@app.route('/qr-codes/create', methods=['GET', 'POST'])
@login_required
def create_qr_code():
    """Enhanced create QR code with address coordinates"""
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        location_address = request.form['location_address']
        location_event = request.form['location_event']
        
        # Get coordinates from hidden form fields (set by JavaScript)
        address_latitude = request.form.get('address_latitude')
        address_longitude = request.form.get('address_longitude')
        coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')
        
        # Create QR code record first (without QR image and URL)
        new_qr_code = QRCode(
            name=name,
            location=location,
            location_address=location_address,
            location_event=location_event,
            qr_code_image='',  # Temporary empty value
            qr_url='',         # Temporary empty value
            created_by=session['user_id']
        )
        
        # Add coordinates if available
        if address_latitude and address_longitude:
            try:
                lat = float(address_latitude)
                lng = float(address_longitude)
                new_qr_code.address_latitude = lat
                new_qr_code.address_longitude = lng
                new_qr_code.coordinate_accuracy = coordinate_accuracy
                new_qr_code.coordinates_updated_date = datetime.utcnow()
                print(f"✅ Added coordinates to QR code: {lat:.6f}, {lng:.6f}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ Invalid coordinates provided: {e}")
        
        # Add to session and flush to get the ID
        db.session.add(new_qr_code)
        db.session.flush()  # This assigns the ID without committing
        
        # Now we can use the ID to generate the URL
        qr_url = generate_qr_url(name, new_qr_code.id)
        
        # Generate QR code data with the destination URL
        qr_data = f"{request.url_root}qr/{qr_url}"
        qr_image = generate_qr_code(qr_data)
        
        # Update the QR code with the URL and image
        new_qr_code.qr_url = qr_url
        new_qr_code.qr_code_image = qr_image
        
        # Now commit all changes
        db.session.commit()
        
        coord_msg = ""
        if new_qr_code.has_coordinates:
            coord_msg = f" with coordinates ({new_qr_code.coordinates_display})"
            
        flash(f'QR code created successfully{coord_msg}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_qr_code.html')

@app.route('/qr-codes/<int:qr_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_qr_code(qr_id):
    """Enhanced edit QR code with address coordinates"""
    qr_code = QRCode.query.get_or_404(qr_id)
    
    if request.method == 'POST':
        # Store original values for comparison
        original_name = qr_code.name
        original_address = qr_code.location_address
        
        # Update QR code fields
        new_name = request.form['name']
        new_address = request.form['location_address']
        
        qr_code.name = new_name
        qr_code.location = request.form['location']
        qr_code.location_address = new_address
        qr_code.location_event = request.form['location_event']
        
        # Handle address coordinates
        address_latitude = request.form.get('address_latitude')
        address_longitude = request.form.get('address_longitude')
        coordinate_accuracy = request.form.get('coordinate_accuracy', 'geocoded')
        
        # Update coordinates if provided
        if address_latitude and address_longitude:
            try:
                lat = float(address_latitude)
                lng = float(address_longitude)
                qr_code.address_latitude = lat
                qr_code.address_longitude = lng
                qr_code.coordinate_accuracy = coordinate_accuracy
                qr_code.coordinates_updated_date = datetime.utcnow()
                print(f"✅ Updated coordinates for QR code: {lat:.6f}, {lng:.6f}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ Invalid coordinates provided during edit: {e}")

        # Check if name changed and handle URL regeneration
        if original_name != new_name:
            # Name changed, regenerate URL
            new_qr_url = generate_qr_url(new_name, qr_code.id)
            qr_code.qr_url = new_qr_url
            
            # Update QR code data with new URL
            qr_data = f"{request.url_root}qr/{new_qr_url}"
        else:
            # Name didn't change, use existing URL (if it exists)
            if qr_code.qr_url:
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
            else:
                # Fallback: generate URL if it doesn't exist (for legacy QR codes)
                new_qr_url = generate_qr_url(new_name, qr_code.id)
                qr_code.qr_url = new_qr_url
                qr_data = f"{request.url_root}qr/{new_qr_url}"

        # Regenerate QR code with updated data (destination URL)
        qr_code.qr_code_image = generate_qr_code(qr_data)

        db.session.commit()
        
        coord_msg = ""
        if qr_code.has_coordinates:
            coord_msg = f" Coordinates: ({qr_code.coordinates_display})"
            
        flash(f'QR code updated successfully!{coord_msg}', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_qr_code.html', qr_code=qr_code)

@app.route('/qr-codes/<int:qr_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_qr_code(qr_id):
    """Permanently delete QR code (Admin only) - Hard delete"""
    
    # OBVIOUS DEBUGGING - You MUST see this in console
    print("\n" + "="*60)
    print("🔥 DELETE ROUTE WAS CALLED! 🔥")
    print(f"🔥 QR ID: {qr_id}")
    print(f"🔥 Method: {request.method}")
    print(f"🔥 User: {session.get('username', 'NO_USER')}")
    print(f"🔥 Role: {session.get('role', 'NO_ROLE')}")
    print("="*60 + "\n")
    
    try:
        qr_code = QRCode.query.get_or_404(qr_id)
        print(f"✅ Found QR Code: {qr_code.name}")
        
        if request.method == 'POST':
            qr_name = qr_code.name
            print(f"🗑️ ATTEMPTING TO DELETE: {qr_name}")
            
            # Check if QR exists before delete
            before_count = QRCode.query.count()
            print(f"📊 QR count before delete: {before_count}")
            
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
        print(f"❌ ERROR in delete route: {e}")
        print(f"❌ Exception type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        flash('Error deleting QR code. Please try again.', 'error')
        return redirect(url_for('dashboard'))
    
@app.route('/test-delete-simple/<int:qr_id>')
@admin_required 
def test_delete_simple(qr_id):
    print(f"🧪 TEST ROUTE CALLED FOR QR {qr_id}")
    return f"Test route works! QR ID: {qr_id}, User: {session.get('username')}"

@app.route('/qr/<string:qr_url>')
def qr_destination(qr_url):
    """QR code destination page where staff check in"""
    try:
        # Find QR code by URL
        qr_code = QRCode.query.filter_by(qr_url=qr_url, active_status=True).first()
        
        if not qr_code:
            flash('QR code not found or inactive.', 'error')
            return render_template('qr_not_found.html'), 404
        
        # Log the scan
        print(f"QR Code scanned: {qr_code.name} at {datetime.now()}")
        
        return render_template('qr_destination.html', qr_code=qr_code)
        
    except Exception as e:
        print(f"Error loading QR destination: {e}")
        flash('Error loading QR code destination.', 'error')
        return render_template('qr_not_found.html'), 500

@app.route('/qr/<string:qr_url>/checkin', methods=['POST'])
def qr_checkin(qr_url):
    """
    Enhanced staff check-in with improved location accuracy calculation
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
        
        # Get form data
        employee_id = request.form.get('employee_id', '').strip()
        
        if not employee_id:
            return jsonify({
                'success': False,
                'message': 'Employee ID is required.'
            }), 400
        
        # Check for duplicate check-ins
        today = date.today()
        existing_checkin = AttendanceData.query.filter_by(
            qr_code_id=qr_code.id,
            employee_id=employee_id.upper(),
            check_in_date=today
        ).first()
        
        if existing_checkin:
            print(f"⚠️ Duplicate check-in attempt for {employee_id}")
            return jsonify({
                'success': False,
                'message': f'You have already checked in today at {existing_checkin.check_in_time.strftime("%H:%M")}.'
            }), 400
        
        # Process location data with enhanced validation
        location_data = process_location_data_enhanced(request.form)
        
        # Get device and network info
        user_agent_string = request.headers.get('User-Agent', '')
        device_info = detect_device_info(user_agent_string)
        client_ip = get_client_ip()
        
        print(f"📱 Device Info: {device_info}")
        print(f"🌐 IP Address: {client_ip}")
        print(f"📍 Location Data: {location_data}")
        
        # Create attendance record
        print(f"\n💾 CREATING ENHANCED ATTENDANCE RECORD:")
        
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
        
        # ENHANCED LOCATION ACCURACY CALCULATION
        print(f"\n🎯 CALCULATING ENHANCED LOCATION ACCURACY...")
        location_accuracy = None
        
        try:
            location_accuracy = calculate_location_accuracy_enhanced(
                qr_address=qr_code.location_address,
                checkin_address=location_data['address'],
                checkin_lat=location_data['latitude'],
                checkin_lng=location_data['longitude']
            )
            
            if location_accuracy is not None:
                attendance.location_accuracy = location_accuracy
                accuracy_level = get_location_accuracy_level_enhanced(location_accuracy)
                print(f"✅ Enhanced location accuracy set: {location_accuracy:.4f} miles ({accuracy_level})")
            else:
                print(f"⚠️ Could not calculate enhanced location accuracy")
                
        except Exception as e:
            print(f"❌ Error in enhanced location accuracy calculation: {e}")
        
        # Save to database
        try:
            db.session.add(attendance)
            db.session.commit()
            print(f"✅ Successfully saved enhanced attendance record with ID: {attendance.id}")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Database error occurred. Please try again.'
            }), 500
        
        # Build enhanced success response
        response_data = {
            'success': True,
            'message': 'Enhanced check-in successful!',
            'data': {
                'employee_id': attendance.employee_id,
                'location': attendance.location_name,
                'check_in_time': attendance.check_in_time.strftime('%H:%M'),
                'has_gps': attendance.latitude is not None and attendance.longitude is not None,
                'location_accuracy': f"{location_accuracy:.4f} miles" if location_accuracy else "Not calculated",
                'accuracy_level': get_location_accuracy_level_enhanced(location_accuracy) if location_accuracy else "unknown",
                'location_source': location_data['source'],
                'enhanced_features': True
            }
        }
        
        print(f"✅ ENHANCED CHECK-IN COMPLETED SUCCESSFULLY!")
        print(f"   Employee: {attendance.employee_id}")
        print(f"   Location: {attendance.location_name}")
        print(f"   Accuracy: {location_accuracy:.4f} miles" if location_accuracy else "Not calculated")
        print(f"   Time: {attendance.check_in_time}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Critical error in enhanced check-in: {e}")
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
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
@admin_required
def attendance_report():
    """Safe attendance report with backward compatibility for location_accuracy"""
    try:
        print("📊 Loading attendance report...")
        
        # Check if location_accuracy column exists
        has_location_accuracy = check_location_accuracy_column_exists()
        print(f"🔍 Location accuracy column exists: {has_location_accuracy}")
        
        # Get filter parameters
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        location_filter = request.args.get('location', '')
        employee_filter = request.args.get('employee', '')
        
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
                    ad.device_info
                FROM attendance_data ad
                LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
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
                    ad.device_info
                FROM attendance_data ad
                LEFT JOIN qr_codes qc ON ad.qr_code_id = qc.id
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
            conditions.append("ad.location_name ILIKE :location")
            params['location'] = f"%{location_filter}%"
        
        # Apply employee filter
        if employee_filter:
            conditions.append("ad.employee_id ILIKE :employee")
            params['employee'] = f"%{employee_filter}%"
        
        # Add conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Add ordering
        base_query += " ORDER BY ad.check_in_date DESC, ad.check_in_time DESC"
        
        print(f"🔍 Executing query with {len(params)} parameters")
        
        # Execute query
        query_result = db.session.execute(text(base_query), params)
        attendance_records = query_result.fetchall()
        
        print(f"✅ Found {len(attendance_records)} attendance records")
        
        # Process records to add calculated fields
        processed_records = []
        for record in attendance_records:
            # Safe attribute access with fallbacks
            location_accuracy = getattr(record, 'location_accuracy', None)
            gps_accuracy = getattr(record, 'gps_accuracy', None)
            
            record_dict = {
                'id': record.id,
                'employee_id': record.employee_id,
                'check_in_date': record.check_in_date,
                'check_in_time': record.check_in_time,
                'location_name': record.location_name,
                'location_event': getattr(record, 'location_event', ''),
                'qr_address': getattr(record, 'qr_address', None) or 'Not available',
                'checked_in_address': getattr(record, 'checked_in_address', None) or 'Location not captured',
                'device_info': getattr(record, 'device_info', ''),
                'location_accuracy': location_accuracy,
                'gps_accuracy': gps_accuracy,
                'accuracy_level': get_location_accuracy_level(location_accuracy) if location_accuracy else 'unknown',
                'has_location_data': record.latitude is not None and record.longitude is not None,
                'coordinates': f"{record.latitude:.6f}, {record.longitude:.6f}" if record.latitude and record.longitude else "No GPS data",
                'has_location_accuracy_feature': has_location_accuracy
            }
            processed_records.append(record_dict)
        
        print(f"✅ Processed {len(processed_records)} records")
        
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
                             stats=stats,
                             date_from=date_from,
                             date_to=date_to,
                             location_filter=location_filter,
                             employee_filter=employee_filter,
                             today_date=today_date,
                             current_date_formatted=current_date_formatted,
                             has_location_accuracy_feature=has_location_accuracy)
        
    except Exception as e:
        print(f"❌ Error loading attendance report: {e}")
        print(f"❌ Exception type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        flash('Error loading attendance report. Please check the server logs for details.', 'error')
        return redirect(url_for('dashboard'))

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
def create_tables():
    """Create database tables and default admin user"""
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

def update_existing_qr_codes():
    """Update existing QR codes with URLs and regenerate QR images"""
    try:
        qr_codes = QRCode.query.filter_by(active_status=True).all()
        
        for qr_code in qr_codes:
            if not qr_code.qr_url:
                # Generate URL
                qr_code.qr_url = generate_qr_url(qr_code.name, qr_code.id)
                
                # Regenerate QR code with destination URL
                qr_data = f"{request.url_root}qr/{qr_code.qr_url}"
                qr_code.qr_code_image = generate_qr_code(qr_data)
        
        db.session.commit()
        print(f"Updated {len(qr_codes)} QR codes with destination URLs")
        
    except Exception as e:
        print(f"Error updating existing QR codes: {e}")
        db.session.rollback()

def add_coordinate_columns():
    """Add coordinate columns to existing qr_codes table"""
    try:
        # Check if columns already exist
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='qr_codes' AND column_name IN 
            ('address_latitude', 'address_longitude', 'coordinate_accuracy', 'coordinates_updated_date')
        """))
        
        existing_columns = [row.column_name for row in result.fetchall()]
        
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

if __name__ == '__main__':
    with app.app_context():
        create_tables()
        add_coordinate_columns()
        update_existing_qr_codes()
    app.run(debug=True, host="0.0.0.0")
