"""
utils/geocoding.py
==================
All geocoding, distance calculation, and location-accuracy helpers.

Extracted verbatim from app.py (lines 188–1317).
No logic changes — only import paths updated.
"""

import os
import re
import requests
import traceback
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

import googlemaps

from extensions import db, logger_handler
from address_normalization_fix import normalize_address, addresses_are_similar

# ---------------------------------------------------------------------------
# Google Maps client (initialized once at module import)
# ---------------------------------------------------------------------------
try:
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    if GOOGLE_MAPS_API_KEY:
        gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        print("✅ Google Maps client initialized successfully")
    else:
        gmaps_client = None
        print("⚠️ Google Maps API key not found, falling back to OpenStreetMap")
except Exception as e:
    gmaps_client = None
    print(f"❌ Error initializing Google Maps client: {e}")


def is_gmaps_available():
    """Return True if the Google Maps client is initialized and usable.

    Always call this (or check ``if gmaps_client:``) before calling any
    method on ``gmaps_client`` to prevent AttributeError when the API key
    is absent.
    """
    return gmaps_client is not None

# ---------------------------------------------------------------------------
# Geocoding cache
# ---------------------------------------------------------------------------
geocoding_cache = {}
CACHE_MAX_SIZE = 1000
CACHE_EXPIRY_HOURS = 24


def get_cached_coordinates(address):
    """Get coordinates from cache if available and not expired"""
    if address in geocoding_cache:
        cached_data = geocoding_cache[address]
        cache_time = cached_data.get('timestamp', datetime.min)
        if datetime.now() - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
            print(f"📋 Using cached coordinates for: {address[:50]}...")
            return cached_data.get('lat'), cached_data.get('lng'), cached_data.get('accuracy')
    return None, None, None


def cache_coordinates(address, lat, lng, accuracy):
    """Cache coordinates to reduce future API calls"""
    try:
        if len(geocoding_cache) >= CACHE_MAX_SIZE:
            oldest_key = min(geocoding_cache.keys(), key=lambda k: geocoding_cache[k]['timestamp'])
            del geocoding_cache[oldest_key]
        geocoding_cache[address] = {
            'lat': lat,
            'lng': lng,
            'accuracy': accuracy,
            'timestamp': datetime.now()
        }
        print(f"💾 Cached coordinates for: {address[:50]}...")
    except Exception as e:
        print(f"⚠️ Error caching coordinates: {e}")


# ---------------------------------------------------------------------------
# Geocoding helpers
# ---------------------------------------------------------------------------

def log_google_maps_usage(operation_type):
    """Log Google Maps API usage for monitoring"""
    try:
        logger_handler.log_user_activity('google_maps_api_usage', f'Google Maps API used: {operation_type}')
    except Exception as e:
        print(f"⚠️ Usage logging error: {e}")


def get_coordinates_from_address(address):
    """
    Get latitude and longitude from address using Google Maps Geocoding API.
    Falls back to OpenStreetMap if Google Maps is unavailable.
    Returns (lat, lng) tuple or (None, None) if failed.
    """
    if not address or address.strip() == '':
        return None, None

    address = address.strip()
    print(f"🌍 Geocoding address: {address}")

    try:
        logger_handler.log_user_activity('geocoding', f'Geocoding address: {address[:50]}...')
    except Exception as log_error:
        print(f"⚠️ Logging error (non-critical): {log_error}")

    try:
        if gmaps_client:
            print("🗺️ Using Google Maps Geocoding API")
            geocode_result = gmaps_client.geocode(address)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                print(f"✅ Google Maps geocoded address '{address[:50]}...' to coordinates: {lat}, {lng}")
                try:
                    logger_handler.log_user_activity('geocoding_success', f'Successfully geocoded: {address[:50]}... -> {lat}, {lng}')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return lat, lng
            else:
                print(f"⚠️ Google Maps: No results found for address: {address}")

        print("🌐 Falling back to OpenStreetMap Nominatim")
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': address, 'format': 'json', 'limit': 1, 'addressdetails': 1}
        headers = {'User-Agent': 'QR-Attendance-System/1.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                print(f"✅ OSM geocoded address '{address[:50]}...' to coordinates: {lat}, {lng}")
                try:
                    logger_handler.log_user_activity('geocoding_fallback', f'OSM fallback geocoded: {address[:50]}... -> {lat}, {lng}')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return lat, lng

        print(f"⚠️ Could not geocode address: {address}")
        try:
            logger_handler.log_user_activity('geocoding_failed', f'Failed to geocode: {address[:50]}...')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        return None, None

    except Exception as e:
        print(f"❌ Error geocoding address '{address}': {e}")
        try:
            logger_handler.log_flask_error('geocoding_error', f'Error geocoding {address[:50]}...: {str(e)}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        return None, None


def get_coordinates_from_address_enhanced(address):
    """
    Enhanced geocoding function using Google Maps with caching and better error handling.
    Returns (latitude, longitude, accuracy_level).
    """
    if not address or address.strip() == "":
        return None, None, None

    address = address.strip()
    print(f"🌍 Enhanced geocoding for: {address}")

    normalized_address = normalize_address(address)
    cached_lat, cached_lng, cached_accuracy = get_cached_coordinates(normalized_address)
    if cached_lat is not None:
        print("✅ Using cached coordinates for normalized address")
        return cached_lat, cached_lng, cached_accuracy

    try:
        logger_handler.log_user_activity('enhanced_geocoding', f'Enhanced geocoding: {address[:50]}...')
    except Exception as log_error:
        print(f"⚠️ Logging error (non-critical): {log_error}")

    try:
        if gmaps_client:
            print("🗺️ Using Google Maps Geocoding API (Enhanced)")
            geocode_result = gmaps_client.geocode(address)
            if geocode_result:
                result = geocode_result[0]
                location = result['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                location_type = result['geometry'].get('location_type', 'UNKNOWN')
                place_types = result.get('types', [])

                if location_type == 'ROOFTOP':
                    accuracy = 'excellent'
                elif location_type == 'RANGE_INTERPOLATED':
                    accuracy = 'good'
                elif location_type == 'GEOMETRIC_CENTER':
                    if any(ptype in place_types for ptype in ['premise', 'subpremise', 'street_address']):
                        accuracy = 'good'
                    elif any(ptype in place_types for ptype in ['neighborhood', 'sublocality']):
                        accuracy = 'fair'
                    else:
                        accuracy = 'poor'
                elif location_type == 'APPROXIMATE':
                    accuracy = 'poor'
                else:
                    accuracy = 'fair'

                print(f"✅ Google Maps enhanced geocoding successful:")
                print(f"   Coordinates: {lat:.10f}, {lng:.10f}")
                print(f"   Accuracy: {accuracy} (location_type: {location_type})")
                print(f"   Place types: {place_types[:3]}")

                cache_coordinates(normalized_address, lat, lng, accuracy)
                try:
                    logger_handler.log_user_activity('enhanced_geocoding_success', f'Google Maps enhanced: {address[:50]}... -> {lat}, {lng} ({accuracy})')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return lat, lng, accuracy
            else:
                print(f"⚠️ Google Maps: No results found for enhanced geocoding: {address}")

        print("🌐 Falling back to OpenStreetMap Nominatim (Enhanced)")
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {'q': address, 'format': 'json', 'limit': 1, 'addressdetails': 1, 'extratags': 1}
        headers = {'User-Agent': 'QR-Attendance-System/1.0 (Enhanced Location Accuracy)'}
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                lat = float(result['lat'])
                lng = float(result['lon'])
                place_type = result.get('type', 'unknown')
                osm_type = result.get('osm_type', 'unknown')

                if place_type in ['house', 'building', 'shop', 'office'] or osm_type == 'way':
                    accuracy = 'good'
                elif place_type in ['neighbourhood', 'suburb', 'quarter', 'residential']:
                    accuracy = 'fair'
                elif place_type in ['city', 'town', 'village']:
                    accuracy = 'poor'
                else:
                    accuracy = 'poor'

                print(f"✅ OSM enhanced geocoding successful:")
                print(f"   Coordinates: {lat:.10f}, {lng:.10f}")
                print(f"   Accuracy: {accuracy} (fallback)")
                cache_coordinates(normalized_address, lat, lng, accuracy)
                try:
                    logger_handler.log_user_activity('enhanced_geocoding_fallback', f'OSM enhanced fallback: {address[:50]}... -> {lat}, {lng} ({accuracy})')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return lat, lng, accuracy

        print(f"⚠️ No results from enhanced geocoding for: {address}")
        try:
            logger_handler.log_user_activity('enhanced_geocoding_failed', f'Enhanced geocoding failed: {address[:50]}...')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        return None, None, None

    except Exception as e:
        print(f"❌ Enhanced geocoding error: {e}")
        try:
            logger_handler.log_flask_error('enhanced_geocoding_error', f'Enhanced geocoding error {address[:50]}...: {str(e)}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        return None, None, None


def geocode_address_enhanced(address):
    """
    Enhanced geocoding using Nominatim API with better accuracy classification.
    Returns: (latitude, longitude, accuracy_level)
    """
    if not address or len(address.strip()) < 5:
        print("❌ Address too short for geocoding")
        return None, None, None

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': address.strip(), 'format': 'json', 'limit': 1, 'addressdetails': 1}
        headers = {'User-Agent': 'QR-Attendance-System/1.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                lat = float(result['lat'])
                lng = float(result['lon'])
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


# ---------------------------------------------------------------------------
# Distance / accuracy
# ---------------------------------------------------------------------------

def calculate_distance_miles(lat1, lng1, lat2, lng2):
    """
    Calculate DIRECT straight-line distance between two points using Haversine formula.
    Returns distance in miles (float) or None if calculation fails.
    """
    if any(coord is None for coord in [lat1, lng1, lat2, lng2]):
        print("⚠️ Missing coordinates for distance calculation")
        return None

    try:
        try:
            lat1_val = float(lat1)
            lng1_val = float(lng1)
            lat2_val = float(lat2)
            lng2_val = float(lng2)
        except (ValueError, TypeError) as e:
            print(f"⚠️ Invalid coordinate format: {e}")
            return None

        if not (-90 <= lat1_val <= 90) or not (-90 <= lat2_val <= 90):
            print(f"⚠️ Invalid latitude values: {lat1_val}, {lat2_val}")
            return None
        if not (-180 <= lng1_val <= 180) or not (-180 <= lng2_val <= 180):
            print(f"⚠️ Invalid longitude values: {lng1_val}, {lng2_val}")
            return None

        try:
            logger_handler.log_user_activity(
                'distance_calculation',
                f'Calculating direct distance: ({lat1_val:.6f}, {lng1_val:.6f}) to ({lat2_val:.6f}, {lng2_val:.6f})'
            )
        except Exception:
            pass

        print("📐 Calculating direct straight-line distance using Haversine formula")

        lat1_rad = radians(lat1_val)
        lng1_rad = radians(lng1_val)
        lat2_rad = radians(lat2_val)
        lng2_rad = radians(lng2_val)

        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad

        sin_dlat_half = sin(dlat / 2.0)
        sin_dlng_half = sin(dlng / 2.0)

        a = (sin_dlat_half * sin_dlat_half +
             cos(lat1_rad) * cos(lat2_rad) * sin_dlng_half * sin_dlng_half)
        a = max(0.0, min(1.0, a))
        c = 2.0 * asin(sqrt(a))

        # DO NOT CHANGE Earth's mean radius value
        EARTH_RADIUS_MILES = 3959.87433
        distance = round(c * EARTH_RADIUS_MILES, 4)

        print(f"📏 Direct straight-line distance calculation:")
        print(f"   Point 1: ({lat1_val:.10f}, {lng1_val:.10f})")
        print(f"   Point 2: ({lat2_val:.10f}, {lng2_val:.10f})")
        print(f"   Δlat: {abs(lat2_val - lat1_val):.10f}° = {dlat:.12f} radians")
        print(f"   Δlng: {abs(lng2_val - lng1_val):.10f}° = {dlng:.12f} radians")
        print(f"   a value: {a:.15f}")
        print(f"   c value (central angle): {c:.15f} radians")
        print(f"   🎯 Distance: {distance:.4f} miles = {distance * 5280:.2f} feet = {distance * 1609.34:.2f} meters")

        try:
            logger_handler.log_user_activity('distance_calculation_success', f'Direct distance: {distance:.4f} miles')
        except Exception:
            pass

        return distance

    except Exception as e:
        print(f"❌ Error in distance calculation: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        try:
            logger_handler.log_flask_error('distance_calculation_error', f'Distance calculation error: {str(e)}')
        except Exception:
            pass
        return None


def get_location_accuracy_level_enhanced(location_accuracy):
    """
    Enhanced function to categorize location accuracy with more granular levels.
    """
    if not location_accuracy or location_accuracy is None:
        return 'unknown'
    if location_accuracy <= 0.05:
        return 'excellent'
    elif location_accuracy <= 0.1:
        return 'very_good'
    elif location_accuracy <= 0.25:
        return 'good'
    elif location_accuracy <= 0.5:
        return 'fair'
    elif location_accuracy <= 1.0:
        return 'poor'
    else:
        return 'very_poor'


def calculate_location_accuracy(qr_address, checkin_address, checkin_lat=None, checkin_lng=None):
    """
    Calculate location accuracy by comparing QR code address with check-in location.
    Returns distance in miles between the two locations.
    """
    print(f"\n📍 CALCULATING LOCATION ACCURACY:")
    print(f"   QR Address: {qr_address}")
    print(f"   Check-in Address: {checkin_address}")
    print(f"   Check-in Coordinates: {checkin_lat}, {checkin_lng}")

    qr_lat, qr_lng = get_coordinates_from_address(qr_address)
    if qr_lat is None or qr_lng is None:
        print("⚠️ Could not geocode QR address, cannot calculate accuracy")
        return None

    if checkin_lat is not None and checkin_lng is not None:
        checkin_coords_lat, checkin_coords_lng = checkin_lat, checkin_lng
        print("✅ Using GPS coordinates for check-in location")
    else:
        checkin_coords_lat, checkin_coords_lng = get_coordinates_from_address(checkin_address)
        if checkin_coords_lat is None or checkin_coords_lng is None:
            print("⚠️ Could not geocode check-in address, cannot calculate accuracy")
            return None
        print("✅ Using geocoded coordinates for check-in address")

    distance = calculate_distance_miles(qr_lat, qr_lng, checkin_coords_lat, checkin_coords_lng)
    if distance is not None:
        print(f"✅ Location accuracy calculated: {distance} miles")
    return distance


def calculate_location_accuracy_enhanced(qr_address, checkin_address, checkin_lat=None, checkin_lng=None):
    """
    ENHANCED location accuracy calculation comparing QR address with check-in location.
    Returns distance in miles between QR location and check-in location.
    """
    print(f"\n🎯 ENHANCED LOCATION ACCURACY CALCULATION:")
    print(f"   QR Address: {qr_address}")
    print(f"   Check-in Address: {checkin_address}")
    print(f"   Check-in GPS: {checkin_lat}, {checkin_lng}")
    print(f"   Timestamp: {datetime.now()}")

    if not qr_address or qr_address.strip() == "":
        print("❌ QR address is empty or invalid")
        return None

    print("\n📍 Step 1: Geocoding QR address...")
    try:
        if addresses_are_similar(qr_address, checkin_address, threshold=0.90):
            print("🎯 Addresses are essentially identical - returning near-zero distance")
            return 0.01

        qr_lat, qr_lng, qr_accuracy = get_coordinates_from_address_enhanced(qr_address)
        print(f"   Geocoding result: lat={qr_lat}, lng={qr_lng}, accuracy={qr_accuracy}")
        if qr_lat is None or qr_lng is None:
            print(f"❌ Could not geocode QR address: {qr_address}")
            return None
        print(f"✅ QR location coordinates: {qr_lat:.10f}, {qr_lng:.10f} (accuracy: {qr_accuracy})")
    except Exception as e:
        print(f"❌ Error geocoding QR address: {e}")
        return None

    print("\n📱 Step 2: Determining check-in coordinates...")
    checkin_coords_lat = None
    checkin_coords_lng = None
    checkin_source = "unknown"

    if checkin_lat is not None and checkin_lng is not None:
        try:
            lat_val = float(checkin_lat)
            lng_val = float(checkin_lng)
            if -90 <= lat_val <= 90 and -180 <= lng_val <= 180:
                checkin_coords_lat = lat_val
                checkin_coords_lng = lng_val
                checkin_source = "gps"
                print(f"✅ Using GPS coordinates: {lat_val:.10f}, {lng_val:.10f}")
            else:
                print(f"⚠️ Invalid GPS coordinates: {lat_val}, {lng_val}")
        except (ValueError, TypeError) as e:
            print(f"⚠️ Could not parse GPS coordinates: {e}")

    if checkin_coords_lat is None and checkin_address:
        print("🌍 Falling back to geocoding check-in address...")
        try:
            checkin_coords_lat, checkin_coords_lng, checkin_accuracy = get_coordinates_from_address_enhanced(checkin_address)
            print(f"   Checkin geocoding result: lat={checkin_coords_lat}, lng={checkin_coords_lng}, accuracy={checkin_accuracy}")
            if checkin_coords_lat is not None:
                checkin_source = "address"
                print(f"✅ Using geocoded coordinates: {checkin_coords_lat:.10f}, {checkin_coords_lng:.10f} (accuracy: {checkin_accuracy})")
        except Exception as e:
            print(f"❌ Error geocoding check-in address: {e}")

    if checkin_coords_lat is None or checkin_coords_lng is None:
        print(f"❌ Could not determine check-in coordinates")
        print(f"   GPS: {checkin_lat}, {checkin_lng}")
        print(f"   Address: {checkin_address}")
        return None

    print("\n📏 Step 3: Calculating distance...")
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
            print("❌ Distance calculation returned None")
            return None
    except Exception as e:
        print(f"❌ Error calculating distance: {e}")
        print(f"❌ Distance calculation traceback: {traceback.format_exc()}")
        return None


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

def reverse_geocode_coordinates(latitude, longitude):
    """
    Convert GPS coordinates to human-readable address.
    Falls back to OpenStreetMap if Google Maps is unavailable.
    Returns address string or None if failed.
    """
    if not latitude or not longitude:
        return None

    try:
        print(f"🌍 Reverse geocoding coordinates: {latitude}, {longitude}")
        try:
            logger_handler.log_user_activity('reverse_geocoding', f'Reverse geocoding: {latitude}, {longitude}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")

        if gmaps_client:
            print("🗺️ Using Google Maps Reverse Geocoding API")
            reverse_geocode_result = gmaps_client.reverse_geocode((latitude, longitude))
            if reverse_geocode_result:
                address = reverse_geocode_result[0]['formatted_address']
                print(f"✅ Google Maps reverse geocoded address: {address}")
                try:
                    logger_handler.log_user_activity('reverse_geocoding_success', f'Google Maps reverse geocoded: {latitude}, {longitude} -> {address[:50]}...')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return address
            else:
                print("⚠️ Google Maps: No address found for coordinates")

        print("🌐 Falling back to OpenStreetMap Nominatim reverse geocoding")
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {'lat': latitude, 'lon': longitude, 'format': 'json', 'addressdetails': 1, 'zoom': 18}
        headers = {'User-Agent': 'QR-Attendance-System/1.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and 'display_name' in data:
                address = data['display_name']
                print(f"✅ OSM reverse geocoded address: {address}")
                try:
                    logger_handler.log_user_activity('reverse_geocoding_fallback', f'OSM reverse geocoded: {latitude}, {longitude} -> {address[:50]}...')
                except Exception as log_error:
                    print(f"⚠️ Logging error (non-critical): {log_error}")
                return address
            else:
                print("⚠️ No address found for coordinates")
                return None
        else:
            print(f"⚠️ Reverse geocoding API returned status: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error in reverse geocoding: {e}")
        try:
            logger_handler.log_flask_error('reverse_geocoding_error', f'Reverse geocoding error {latitude}, {longitude}: {str(e)}')
        except Exception as log_error:
            print(f"⚠️ Logging error (non-critical): {log_error}")
        return None


# ---------------------------------------------------------------------------
# Location data processing
# ---------------------------------------------------------------------------

def process_location_data(location_data):
    """
    Process and validate location data from form.
    Returns clean location data or None values for invalid data.
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
        if location_data.get('latitude') and location_data['latitude'] not in ['null', '']:
            lat = float(location_data['latitude'])
            if -90 <= lat <= 90:
                processed['latitude'] = lat
            else:
                print(f"⚠️ Invalid latitude: {lat}")

        if location_data.get('longitude') and location_data['longitude'] not in ['null', '']:
            lng = float(location_data['longitude'])
            if -180 <= lng <= 180:
                processed['longitude'] = lng
            else:
                print(f"⚠️ Invalid longitude: {lng}")

        if location_data.get('accuracy') and location_data['accuracy'] not in ['null', '']:
            acc = float(location_data['accuracy'])
            if acc >= 0:
                processed['accuracy'] = acc
            else:
                print(f"⚠️ Invalid accuracy: {acc}")

        if location_data.get('altitude') and location_data['altitude'] not in ['null', '']:
            alt = float(location_data['altitude'])
            processed['altitude'] = alt

    except (ValueError, TypeError) as e:
        print(f"⚠️ Error processing location data: {e}")

    return processed


def process_location_data_enhanced(form_data):
    """
    Enhanced processing of location data from form submission.
    Validates and cleans location data for storage, including reverse geocoding.
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
        if form_data.get('latitude') and form_data['latitude'] not in ['null', '', 'undefined']:
            lat = float(form_data['latitude'])
            if -90 <= lat <= 90:
                processed['latitude'] = lat
            else:
                print(f"⚠️ Invalid latitude: {lat}")

        if form_data.get('longitude') and form_data['longitude'] not in ['null', '', 'undefined']:
            lng = float(form_data['longitude'])
            if -180 <= lng <= 180:
                processed['longitude'] = lng
            else:
                print(f"⚠️ Invalid longitude: {lng}")

        if form_data.get('accuracy') and form_data['accuracy'] not in ['null', '', 'undefined']:
            acc = float(form_data['accuracy'])
            if acc >= 0:
                processed['accuracy'] = acc
            else:
                print(f"⚠️ Invalid GPS accuracy: {acc}")

        if form_data.get('altitude') and form_data['altitude'] not in ['null', '', 'undefined']:
            alt = float(form_data['altitude'])
            processed['altitude'] = alt

        if form_data.get('address'):
            address = form_data['address'].strip()
            if address and address not in ['null', '', 'undefined']:
                if re.match(r'^-?\d+\.\d+,?\s*-?\d+\.\d+$', address.replace(' ', '')):
                    print(f"🔍 Detected coordinate-format address: {address}")
                    processed['address'] = None
                else:
                    processed['address'] = address[:500]
                    print(f"✅ Using provided address: {processed['address'][:100]}...")

        if (processed['latitude'] is not None and processed['longitude'] is not None
                and not processed['address']):
            print(f"🌍 Performing reverse geocoding for coordinates: {processed['latitude']}, {processed['longitude']}")
            reverse_geocoded_address = reverse_geocode_coordinates(processed['latitude'], processed['longitude'])
            if reverse_geocoded_address:
                processed['address'] = reverse_geocoded_address[:500]
                print(f"✅ Reverse geocoded address: {processed['address']}")
            else:
                print("⚠️ Could not reverse geocode coordinates, keeping coordinates as fallback")
                processed['address'] = f"{processed['latitude']:.10f}, {processed['longitude']:.10f}"

        print("📍 Final processed location data:")
        print(f"   Coordinates: {processed['latitude']}, {processed['longitude']}")
        print(f"   GPS Accuracy: {processed['accuracy']}m")
        print(f"   Source: {processed['source']}")
        print(f"   Address: {processed['address'][:100] if processed['address'] else 'None'}...")

        return processed

    except Exception as e:
        print(f"❌ Error processing location data: {e}")
        return processed


def migrate_to_enhanced_location_accuracy():
    """Migration function to recalculate all existing records with enhanced accuracy."""
    from sqlalchemy import text as sa_text
    try:
        print("🔄 Starting enhanced location accuracy migration...")
        records = db.session.execute(sa_text("""
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
                new_accuracy = calculate_location_accuracy_enhanced(
                    qr_address=record.location_address,
                    checkin_address=record.address,
                    checkin_lat=record.latitude,
                    checkin_lng=record.longitude
                )
                if new_accuracy is not None:
                    db.session.execute(sa_text("""
                        UPDATE attendance_data SET location_accuracy = :accuracy WHERE id = :record_id
                    """), {'accuracy': new_accuracy, 'record_id': record.id})
                    updated_count += 1
                    if record.location_accuracy is None or abs(new_accuracy - (record.location_accuracy or 0)) > 0.001:
                        improved_count += 1
                        print(f"   ✅ Updated record {record.id}: {record.location_accuracy} → {new_accuracy:.4f} miles")
            except Exception as e:
                print(f"   ⚠️ Error processing record {record.id}: {e}")

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
    """Check if location_accuracy column exists in attendance_data table (MySQL compatible)."""
    from sqlalchemy import text as sa_text
    try:
        result = db.session.execute(sa_text("""
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


# ---------------------------------------------------------------------------
# QR code location helpers
# ---------------------------------------------------------------------------

def get_all_locations_from_qr_codes():
    """Helper function to get all unique locations from QR codes"""
    from sqlalchemy import text as sa_text
    try:
        result = db.session.execute(sa_text("""
            SELECT DISTINCT location
            FROM qr_codes
            WHERE location IS NOT NULL
            AND active_status = 1
            ORDER BY location
        """))
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger_handler.logger.error(f"Error loading locations: {e}")
        return []