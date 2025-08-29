# File: location_logging.py
# Enhanced location action logging for Android debugging

from flask import request, jsonify
from datetime import datetime
import json
import traceback

def create_location_logging_routes(app, db, logger_handler):
    """
    Create location logging routes for monitoring Android location issues
    This should be included in your main app.py file
    """
    
    @app.route('/api/log-location-action', methods=['POST'])
    def log_location_action():
        """
        Log location actions for debugging Android location issues
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
            
            action = data.get('action', 'unknown')
            action_data = data.get('data', {})
            timestamp = data.get('timestamp', datetime.now().isoformat())
            user_agent = data.get('userAgent', request.headers.get('User-Agent', ''))
            
            # Extract device information
            device_info = extract_device_info(user_agent)
            
            # Create log entry
            log_entry = {
                'action': action,
                'timestamp': timestamp,
                'device_info': device_info,
                'action_data': action_data,
                'ip_address': get_client_ip_enhanced(),
                'user_agent': user_agent[:500]  # Limit length
            }
            
            # Log to console for immediate debugging
            print(f"📊 LOCATION ACTION LOG: {action}")
            print(f"   Device: {device_info.get('platform')} {device_info.get('browser')}")
            print(f"   Data: {json.dumps(action_data, indent=2)}")
            
            # Use existing logger if available
            if logger_handler:
                logger_handler.log_user_activity(
                    f'location_action_{action}', 
                    f"Location action: {action} | Device: {device_info.get('platform')} | Data: {json.dumps(action_data)}"
                )
            
            # Store in database for analysis (optional)
            try:
                store_location_log_in_db(db, log_entry)
            except Exception as db_error:
                print(f"⚠️ Could not store location log in database: {db_error}")
            
            return jsonify({'status': 'success', 'message': 'Location action logged'})
            
        except Exception as e:
            print(f"❌ Error logging location action: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'status': 'error', 'message': 'Logging failed'}), 500

    @app.route('/api/location-debug-info', methods=['GET'])
    def get_location_debug_info():
        """
        Get debugging information about location services
        """
        try:
            user_agent = request.headers.get('User-Agent', '')
            device_info = extract_device_info(user_agent)
            
            debug_info = {
                'timestamp': datetime.now().isoformat(),
                'ip_address': get_client_ip_enhanced(),
                'device_info': device_info,
                'headers': dict(request.headers),
                'is_android': 'android' in user_agent.lower(),
                'is_chrome': 'chrome' in user_agent.lower() and 'edg' not in user_agent.lower(),
                'is_secure': request.is_secure,
                'protocol': request.scheme
            }
            
            return jsonify(debug_info)
            
        except Exception as e:
            print(f"❌ Error getting debug info: {e}")
            return jsonify({'error': str(e)}), 500

def extract_device_info(user_agent_string):
    """
    Extract detailed device information from user agent
    """
    try:
        # Use existing user agent parsing if available
        if 'user_agents' in globals():
            from user_agents import parse
            user_agent = parse(user_agent_string)
            
            return {
                'platform': user_agent.os.family,
                'platform_version': user_agent.os.version_string,
                'browser': user_agent.browser.family,
                'browser_version': user_agent.browser.version_string,
                'device': user_agent.device.family,
                'is_mobile': user_agent.is_mobile,
                'is_tablet': user_agent.is_tablet,
                'is_pc': user_agent.is_pc,
                'is_android': 'android' in user_agent_string.lower(),
                'is_chrome': 'chrome' in user_agent_string.lower() and 'edg' not in user_agent_string.lower()
            }
        else:
            # Fallback manual parsing
            ua_lower = user_agent_string.lower()
            
            return {
                'platform': 'Android' if 'android' in ua_lower else 'Unknown',
                'browser': 'Chrome' if 'chrome' in ua_lower else 'Unknown',
                'is_android': 'android' in ua_lower,
                'is_chrome': 'chrome' in ua_lower and 'edg' not in ua_lower,
                'user_agent_raw': user_agent_string[:200]
            }
            
    except Exception as e:
        print(f"⚠️ Error parsing user agent: {e}")
        return {
            'error': str(e),
            'user_agent_raw': user_agent_string[:200]
        }

def get_client_ip_enhanced():
    """
    Enhanced client IP detection
    """
    # Check various headers for real IP
    for header in ['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'HTTP_X_FORWARDED', 'HTTP_FORWARDED']:
        if header in request.environ:
            ip = request.environ[header].split(',')[0].strip()
            if ip:
                return ip
    
    return request.environ.get('REMOTE_ADDR', 'unknown')

def store_location_log_in_db(db, log_entry):
    """
    Store location log in database for analysis (optional)
    Create table if it doesn't exist
    """
    try:
        # Create table if it doesn't exist
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS location_action_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                action VARCHAR(100),
                timestamp TIMESTAMP,
                device_info JSON,
                action_data JSON,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Insert log entry
        db.session.execute(text("""
            INSERT INTO location_action_logs (
                action, timestamp, device_info, action_data, ip_address, user_agent
            ) VALUES (
                :action, :timestamp, :device_info, :action_data, :ip_address, :user_agent
            )
        """), {
            'action': log_entry['action'],
            'timestamp': log_entry['timestamp'],
            'device_info': json.dumps(log_entry['device_info']),
            'action_data': json.dumps(log_entry['action_data']),
            'ip_address': log_entry['ip_address'],
            'user_agent': log_entry['user_agent']
        })
        
        db.session.commit()
        
    except Exception as e:
        print(f"⚠️ Database logging error: {e}")
        db.session.rollback()

# Enhanced location processing for form submission
def process_location_data_enhanced(form_data):
    """
    Enhanced location data processing with better Android handling
    This replaces or enhances the existing process_location_data function
    """
    print(f"\n📱 ENHANCED LOCATION PROCESSING:")
    print(f"   Raw location data received: {dict(form_data)}")
    
    processed = {
        'latitude': None,
        'longitude': None,
        'accuracy': None,
        'altitude': None,
        'source': 'manual',
        'address': None
    }
    
    try:
        # Process coordinates with enhanced validation
        if form_data.get('latitude') and form_data.get('longitude'):
            lat_str = str(form_data['latitude']).strip()
            lng_str = str(form_data['longitude']).strip()
            
            # Handle various input formats
            if lat_str not in ['null', '', 'undefined', 'NaN'] and lng_str not in ['null', '', 'undefined', 'NaN']:
                try:
                    lat_val = float(lat_str)
                    lng_val = float(lng_str)
                    
                    # Validate coordinate ranges
                    if -90 <= lat_val <= 90 and -180 <= lng_val <= 180:
                        processed['latitude'] = lat_val
                        processed['longitude'] = lng_val
                        processed['source'] = form_data.get('location_source', 'gps')
                        print(f"✅ Valid coordinates processed: {lat_val:.10f}, {lng_val:.10f}")
                    else:
                        print(f"⚠️ Coordinates out of valid range: {lat_val}, {lng_val}")
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Could not convert coordinates to float: {e}")
        
        # Process accuracy
        if form_data.get('accuracy'):
            try:
                acc_str = str(form_data['accuracy']).strip()
                if acc_str not in ['null', '', 'undefined', 'NaN']:
                    acc_val = float(acc_str)
                    if acc_val > 0:  # Accuracy should be positive
                        processed['accuracy'] = acc_val
                        print(f"✅ Accuracy processed: {acc_val}m")
            except (ValueError, TypeError):
                print(f"⚠️ Could not process accuracy value")
        
        # Process altitude
        if form_data.get('altitude'):
            try:
                alt_str = str(form_data['altitude']).strip()
                if alt_str not in ['null', '', 'undefined', 'NaN']:
                    processed['altitude'] = float(alt_str)
            except (ValueError, TypeError):
                print(f"⚠️ Could not process altitude value")
        
        # Process address with coordinate detection
        if form_data.get('address'):
            address = str(form_data['address']).strip()
            if address and address not in ['null', '', 'undefined']:
                # Check if address is actually coordinates
                if re.match(r'^-?\d+\.\d+,?\s*-?\d+\.\d+$', address.replace(' ', '')):
                    print(f"🔍 Address appears to be coordinates: {address}")
                    processed['address'] = None  # Will trigger reverse geocoding
                else:
                    processed['address'] = address[:500]
                    print(f"✅ Address processed: {address[:50]}...")
        
        # Enhanced reverse geocoding trigger
        if (processed['latitude'] is not None and processed['longitude'] is not None 
            and not processed['address']):
            print(f"🌍 Triggering enhanced reverse geocoding...")
            try:
                # Use existing reverse geocoding function
                reverse_geocoded = reverse_geocode_coordinates(processed['latitude'], processed['longitude'])
                if reverse_geocoded:
                    processed['address'] = reverse_geocoded[:500]
                    print(f"✅ Reverse geocoding successful: {reverse_geocoded[:50]}...")
                else:
                    processed['address'] = f"{processed['latitude']:.6f}, {processed['longitude']:.6f}"
                    print(f"⚠️ Reverse geocoding failed, using coordinates")
            except Exception as geocoding_error:
                print(f"❌ Reverse geocoding error: {geocoding_error}")
                processed['address'] = f"{processed['latitude']:.6f}, {processed['longitude']:.6f}"
        
        print(f"📍 FINAL PROCESSED LOCATION:")
        print(f"   Coordinates: {processed['latitude']}, {processed['longitude']}")
        print(f"   Accuracy: {processed['accuracy']}m")
        print(f"   Source: {processed['source']}")
        print(f"   Address: {processed['address']}")
        
        return processed
        
    except Exception as e:
        print(f"❌ Error in enhanced location processing: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return processed